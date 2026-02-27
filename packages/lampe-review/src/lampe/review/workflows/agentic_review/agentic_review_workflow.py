"""Main agentic review orchestrator workflow."""

import asyncio
import logging
from typing import Any

from llama_index.core.program import FunctionCallingProgram
from llama_index.llms.litellm import LiteLLM
from workflows import Context, Workflow, step
from workflows.events import Event, StartEvent, StopEvent

from lampe.core.data_models import PullRequest, Repository
from lampe.core.llmconfig import MODELS, get_model
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME
from lampe.core.tools.repository.diff import list_changed_files
from lampe.review.workflows.agentic_review.agentic_review_prompt import (
    INTENT_EXTRACTION_SYSTEM_PROMPT,
    INTENT_EXTRACTION_USER_PROMPT,
    TASK_PLANNING_SYSTEM_PROMPT,
    TASK_PLANNING_USER_PROMPT,
)
from lampe.review.workflows.agentic_review.data_models import (
    PRIntent,
    TaskPlanningOutput,
    ValidationAgentInput,
    ValidationResult,
    ValidationTask,
)
from lampe.review.workflows.agentic_review.skill_selector import (
    discover_skills,
    select_applicable_skills,
)
from lampe.review.workflows.agentic_review.validation.basic_validation_agent import (
    BasicValidationAgent,
)
from lampe.review.workflows.agentic_review.validation.skill_augmented_validation_agent import (
    SkillAugmentedValidationAgent,
)
from lampe.review.workflows.agentic_review.validation.validation_agent import (
    ValidationAgentComplete,
    ValidationAgentStart,
)
from lampe.review.workflows.pr_review.data_models import (
    AgentReviewOutput,
    FileReview,
    PRReviewInput,
    ReviewComment,
    ReviewDepth,
)
from lampe.review.workflows.pr_review.llm_aggregation_step import (
    LLMAggregationCompleteEvent,
    LLMAggregationStartEvent,
    LLMAggregationWorkflow,
)


class AgenticReviewStart(StartEvent):
    """Start event for agentic review workflow."""

    input: PRReviewInput


class IntentExtractedEvent(Event):
    """Event after intent extraction."""

    pr_intent: PRIntent
    files_changed: str
    skills: list
    selected_skills: list


class TasksPlannedEvent(Event):
    """Event after task planning."""

    tasks: list[ValidationTask]
    files_changed: str
    repo_path: str
    base_commit: str
    head_commit: str


class ValidationsCompleteEvent(Event):
    """Event after all validations complete."""

    results: list[ValidationResult]
    files_changed: str


class AgenticReviewComplete(StopEvent):
    """Complete event for agentic review workflow."""

    output: list[AgentReviewOutput]


def _validation_results_to_agent_review_output(
    results: list[ValidationResult],
) -> list[AgentReviewOutput]:
    """Convert ValidationResults to AgentReviewOutput for provider compatibility."""
    agent_outputs: list[AgentReviewOutput] = []
    for i, vr in enumerate(results):
        file_reviews: list[FileReview] = []
        file_findings: dict[str, list] = {}
        for f in vr.findings:
            file_findings.setdefault(f.file_path, []).append(f)

        for file_path, findings in file_findings.items():
            structured_comments: list[ReviewComment] = []
            for f in findings:
                structured_comments.append(
                    ReviewComment(
                        line_number=f.line_number,
                        comment=f.problem_summary,
                        severity=f.severity,
                        category=f.category,
                        agent_name=f"Validation-{vr.task_id}",
                        muted=False,
                    )
                )
            summary_parts = [f.problem_summary for f in findings]
            file_reviews.append(
                FileReview(
                    file_path=file_path,
                    line_comments={},
                    structured_comments=structured_comments,
                    summary="; ".join(summary_parts),
                    agent_name=f"Validation-{vr.task_id}",
                )
            )

        agent_outputs.append(
            AgentReviewOutput(
                agent_name=f"ValidationAgent-{vr.task_id}",
                focus_areas=[vr.task_id],
                reviews=file_reviews,
                sources=vr.sources,
                summary=(
                    f"Task {vr.task_id}: {len(vr.findings)} findings"
                    if vr.findings
                    else f"Task {vr.task_id}: No issues"
                ),
            )
        )
    return agent_outputs


class AgenticReviewWorkflow(Workflow):
    """Orchestrator workflow for agentic review."""

    def __init__(
        self,
        timeout: int | None = None,
        verbose: bool = False,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, timeout=timeout, verbose=verbose, **kwargs)
        self.verbose = verbose
        self.timeout = timeout
        self.logger = logging.getLogger(LAMPE_LOGGER_NAME)
        self.aggregation_workflow = LLMAggregationWorkflow(timeout=timeout, verbose=verbose)

    @step
    async def extract_intent_and_select_skills(self, ctx: Context, ev: AgenticReviewStart) -> TasksPlannedEvent:
        """Extract PR intent, discover/select skills, plan tasks."""
        inp = ev.input
        repo_path = inp.repository.local_path
        base_commit = inp.pull_request.base_commit_hash
        head_commit = inp.pull_request.head_commit_hash

        files_changed = list_changed_files(
            base_reference=base_commit,
            head_reference=head_commit,
            repo_path=repo_path,
        )

        # Intent extraction (FunctionCallingProgram for structured output)
        llm = LiteLLM(model=get_model("LAMPE_MODEL_REVIEW_INTENT", MODELS.GPT_5_2_CODEX), temperature=1)
        intent_prompt = f"{INTENT_EXTRACTION_SYSTEM_PROMPT}\n\n{INTENT_EXTRACTION_USER_PROMPT}"
        try:
            intent_program = FunctionCallingProgram.from_defaults(
                output_cls=PRIntent,
                llm=llm,
                prompt_template_str=intent_prompt,
                tool_required=True,
            )
            pr_intent = await intent_program.acall(
                pr_title=inp.pull_request.title,
                pr_description=inp.pull_request.body or "(no description)",
                files_changed=files_changed,
            )
            if pr_intent is None:
                self.logger.warning("Intent extraction returned None (LLM may not have invoked structured output)")
                pr_intent = PRIntent(
                    summary=inp.pull_request.title,
                    areas_touched=[],
                    suggested_validation_tasks=[],
                )
            elif isinstance(pr_intent, list) and pr_intent:
                pr_intent = pr_intent[0]
            if not isinstance(pr_intent, PRIntent):
                self.logger.warning(f"Intent extraction returned unexpected type: {type(pr_intent)}")
                pr_intent = PRIntent(
                    summary=inp.pull_request.title,
                    areas_touched=[],
                    suggested_validation_tasks=[],
                )
        except Exception as e:
            self.logger.warning(f"Intent extraction failed: {e}", exc_info=True)
            pr_intent = PRIntent(
                summary=inp.pull_request.title,
                areas_touched=[],
                suggested_validation_tasks=[],
            )

        # Skill discovery and selection
        skills = discover_skills(repo_path)
        selected_skills = []
        if skills:
            selected_skills = await select_applicable_skills(
                pr_intent=pr_intent,
                files_changed=files_changed,
                skills=skills,
                llm=llm,
            )

        # Task planning (basic tasks only; skill tasks added separately)
        task_prompt = f"{TASK_PLANNING_SYSTEM_PROMPT}\n\n{TASK_PLANNING_USER_PROMPT}"
        tasks: list[ValidationTask] = []
        try:
            task_program = FunctionCallingProgram.from_defaults(
                output_cls=TaskPlanningOutput,
                llm=llm,
                prompt_template_str=task_prompt,
                tool_required=True,
            )
            task_result = await task_program.acall(
                pr_intent_summary=pr_intent.summary,
                areas_touched=", ".join(pr_intent.areas_touched) or "unknown",
                suggested_tasks="\n".join(f"- {t}" for t in pr_intent.suggested_validation_tasks),
                files_changed=files_changed,
            )
            if task_result is None:
                self.logger.warning("Task planning returned None (LLM may not have invoked structured output)")
            elif isinstance(task_result, list) and task_result:
                task_result = task_result[0]
            if isinstance(task_result, TaskPlanningOutput):
                tasks = task_result.tasks
            else:
                self.logger.warning(
                    "Task planning returned unexpected type: %s",
                    type(task_result).__name__ if task_result is not None else "None",
                )
        except Exception as e:
            self.logger.warning(f"Task planning failed: {e}", exc_info=True)

        # Add skill tasks for selected skills
        for i, skill in enumerate(selected_skills):
            tasks.append(
                ValidationTask(
                    task_id=f"skill-{skill.name}-{i}",
                    description=f"Apply {skill.name} guidelines to validate the changes",
                    applicable_skill_paths=[skill.path],
                    skill_content=skill.content,
                )
            )

        if not tasks:
            self.logger.warning(
                "No tasks produced: task planning returned empty and no skills selected. "
                "Skipping validation (no fallback to basic validation)."
            )

        return TasksPlannedEvent(
            tasks=tasks,
            files_changed=files_changed,
            repo_path=repo_path,
            base_commit=base_commit,
            head_commit=head_commit,
        )

    @step
    async def run_validations(self, ctx: Context, ev: TasksPlannedEvent) -> ValidationsCompleteEvent:
        """Run all validation agents (parallel)."""
        results: list[ValidationResult] = []

        async def run_one(task: ValidationTask) -> ValidationResult:
            agent_input = ValidationAgentInput(
                task=task,
                repo_path=ev.repo_path,
                base_commit=ev.base_commit,
                head_commit=ev.head_commit,
                files_changed=ev.files_changed,
            )
            if task.skill_content:
                agent = SkillAugmentedValidationAgent(skill_content=task.skill_content)
            else:
                agent = BasicValidationAgent()
            try:
                complete: ValidationAgentComplete = await agent.run(start_event=ValidationAgentStart(input=agent_input))
                return complete.validation_result
            except Exception as e:
                self.logger.exception(f"Validation agent failed for {task.task_id}: {e}")
                return ValidationResult(task_id=task.task_id, findings=[], no_issue=True, sources=[])

        results = await asyncio.gather(*[run_one(t) for t in ev.tasks])
        return ValidationsCompleteEvent(results=list(results), files_changed=ev.files_changed)

    @step
    async def aggregate_and_deliver(self, ctx: Context, ev: ValidationsCompleteEvent) -> AgenticReviewComplete:
        """Convert to AgentReviewOutput, run QA, deliver."""
        agent_reviews = _validation_results_to_agent_review_output(ev.results)
        if not agent_reviews:
            return AgenticReviewComplete(output=[])

        aggregation_result: LLMAggregationCompleteEvent = await self.aggregation_workflow.run(
            start_event=LLMAggregationStartEvent(
                agent_reviews=agent_reviews,
                files_changed=ev.files_changed,
            )
        )
        return AgenticReviewComplete(output=aggregation_result.aggregated_reviews)


async def generate_agentic_pr_review(
    repository: Repository,
    pull_request: PullRequest,
    review_depth: ReviewDepth = ReviewDepth.STANDARD,
    custom_guidelines: list[str] | None = None,
    files_exclude_patterns: list[str] | None = None,
    timeout: int | None = None,
    verbose: bool = False,
) -> AgenticReviewComplete:
    """Generate a PR review using the agentic orchestrator workflow."""
    if files_exclude_patterns is None:
        files_exclude_patterns = []

    input_data = PRReviewInput(
        repository=repository,
        pull_request=pull_request,
        review_depth=review_depth,
        custom_guidelines=custom_guidelines,
        files_exclude_patterns=files_exclude_patterns,
        use_multi_agent=True,
    )
    workflow = AgenticReviewWorkflow(timeout=timeout, verbose=verbose)
    result: AgenticReviewComplete = await workflow.run(start_event=AgenticReviewStart(input=input_data))
    return result
