"""Quick review workflow — single agent, grep-first, minimal context."""

import logging

from llama_index.core.workflow import Context, StartEvent, StopEvent, Workflow, step

from lampe.core.data_models import PullRequest, Repository
from lampe.core.tools.repository.diff import list_changed_files
from lampe.review.workflows.agentic_review.agentic_review_workflow import (
    _validation_results_to_agent_review_output,
)
from lampe.review.workflows.agentic_review.validation.validation_agent import (
    ValidationAgentComplete,
)
from lampe.review.workflows.pr_review.data_models import (
    AgentReviewOutput,
    PRReviewInput,
)
from lampe.review.workflows.quick_review.hallucination_filter_step import (
    HallucinationFilterCompleteEvent,
    HallucinationFilterStartEvent,
    HallucinationFilterWorkflow,
)
from lampe.review.workflows.quick_review.quick_review_agent import (
    QuickReviewAgent,
    QuickReviewAgentStart,
    QuickReviewInput,
)


class QuickReviewStart(StartEvent):
    """Start event for quick review workflow."""

    input: PRReviewInput


class QuickReviewComplete(StopEvent):
    """Complete event for quick review workflow."""

    output: list[AgentReviewOutput]


class QuickReviewWorkflow(Workflow):
    """Simple workflow: list files → run quick review agent → convert to AgentReviewOutput."""

    def __init__(self, timeout: int | None = None, verbose: bool = False, *args, **kwargs) -> None:
        super().__init__(*args, timeout=timeout, verbose=verbose, **kwargs)
        self.timeout = timeout
        self.verbose = verbose
        self.logger = logging.getLogger("lampe.review.quick_review")
        self.agent = QuickReviewAgent()
        self.hallucination_filter = HallucinationFilterWorkflow(
            timeout=timeout,
            verbose=verbose,
        )

    @step
    async def run_quick_review(self, ctx: Context, ev: QuickReviewStart) -> QuickReviewComplete:
        """Run the quick review agent on changed files."""
        inp = ev.input
        repo_path = inp.repository.local_path
        base_commit = inp.pull_request.base_commit_hash
        head_commit = inp.pull_request.head_commit_hash

        files_changed = list_changed_files(
            base_reference=base_commit,
            head_reference=head_commit,
            repo_path=repo_path,
        )

        agent_input = QuickReviewInput(
            repo_path=repo_path,
            base_commit=base_commit,
            head_commit=head_commit,
            files_changed=files_changed,
        )

        try:
            complete: ValidationAgentComplete = await self.agent.run(
                start_event=QuickReviewAgentStart(input=agent_input),
            )
        except Exception:
            self.logger.exception("Quick review agent failed")
            return QuickReviewComplete(output=[])

        agent_outputs = _validation_results_to_agent_review_output([complete.validation_result])
        if not agent_outputs:
            return QuickReviewComplete(output=[])

        filter_result: HallucinationFilterCompleteEvent = await self.hallucination_filter.run(
            start_event=HallucinationFilterStartEvent(
                agent_reviews=agent_outputs,
                files_changed=files_changed,
            ),
        )
        return QuickReviewComplete(output=filter_result.filtered_reviews)


async def generate_quick_pr_review(
    repository: Repository,
    pull_request: PullRequest,
    timeout: int | None = None,
    verbose: bool = False,
) -> QuickReviewComplete:
    """Generate a quick PR review using the single-agent quick review workflow."""
    input_data = PRReviewInput(
        repository=repository,
        pull_request=pull_request,
    )
    workflow = QuickReviewWorkflow(timeout=timeout, verbose=verbose)
    result: QuickReviewComplete = await workflow.run(start_event=QuickReviewStart(input=input_data))
    return result
