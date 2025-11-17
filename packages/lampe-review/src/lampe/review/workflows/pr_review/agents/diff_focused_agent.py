"""Diff-focused agent that reviews one specific diff at a time to find bugs."""

from llama_index.core.workflow import Context, step
from llama_index.llms.litellm import LiteLLM

from lampe.core.llmconfig import MODELS
from lampe.core.tools.repository.diff import get_diff_for_files
from lampe.core.workflows.function_calling_agent import UserInputEvent
from lampe.review.workflows.pr_review.agents.diff_focused_agent_prompt import (
    DIFF_FOCUSED_AGENT_SYSTEM_PROMPT,
    DIFF_FOCUSED_CUSTOM_GUIDELINES_SECTION,
    DIFF_FOCUSED_USER_PROMPT,
)
from lampe.review.workflows.pr_review.agents.specialized_agent_base import (
    SpecializedAgentStart,
    SpecializedReviewAgent,
)
from lampe.review.workflows.pr_review.data_models import ReviewDepth


class DiffFocusedAgent(SpecializedReviewAgent):
    """Agent that focuses on reviewing one specific diff to find bugs introduced by that change."""

    def __init__(self, *args, **kwargs):
        # Default model, will be updated based on review_depth in setup_query_and_tools
        llm = LiteLLM(model=MODELS.GPT_5_2025_08_07, temperature=1.0, reasoning_effort="high")
        super().__init__(
            agent_name="Diff-Focused Bug Finder",
            focus_areas=[
                "Bug detection",
                "Regression identification",
                "Integration issues",
                "Logic errors",
                "Runtime errors",
            ],
            system_prompt=DIFF_FOCUSED_AGENT_SYSTEM_PROMPT,
            llm=llm,
            *args,
            **kwargs,
        )

    def _get_model_for_review_depth(self, review_depth: ReviewDepth) -> str:
        """Get model based on review depth."""
        match review_depth.value:
            case ReviewDepth.BASIC.value:
                return MODELS.GPT_5_NANO_2025_08_07
            case ReviewDepth.STANDARD.value:
                return MODELS.GPT_5_2025_08_07
            case ReviewDepth.COMPREHENSIVE.value:
                return MODELS.GPT_5_1_2025_11_13
            case _:
                return MODELS.GPT_5_2025_08_07

    def _get_custom_guidelines_section(self, custom_guidelines: list[str] | None) -> str:
        """Format custom guidelines section for the prompt."""
        if not custom_guidelines:
            return ""
        guidelines_text = "\n".join(custom_guidelines)
        return DIFF_FOCUSED_CUSTOM_GUIDELINES_SECTION.format(guidelines_text=guidelines_text)

    @step
    async def setup_query_and_tools(self, ctx: Context, ev: SpecializedAgentStart) -> UserInputEvent:
        """Setup the query and tools for the diff-focused agent."""
        if not ev.input.target_file_path:
            raise ValueError("DiffFocusedAgent requires target_file_path in AgentReviewInput")

        # Update LLM based on review depth
        model = self._get_model_for_review_depth(ev.input.review_depth)
        self.llm = LiteLLM(model=model, temperature=1.0, reasoning_effort="high")

        # Get the diff for the target file
        target_file_diff = get_diff_for_files(
            base_reference=ev.input.pull_request.base_commit_hash,
            head_reference=ev.input.pull_request.head_commit_hash,
            file_paths=[ev.input.target_file_path],
            repo_path=ev.input.repository.local_path,
        )

        # If diff is empty, provide a message
        if not target_file_diff.strip():
            target_file_diff = (
                f"(No diff content found for {ev.input.target_file_path} - file may be newly added or deleted)"
            )

        custom_guidelines_section = self._get_custom_guidelines_section(ev.input.custom_guidelines)

        query = DIFF_FOCUSED_USER_PROMPT.format(
            pull_request_number=ev.input.pull_request.number,
            pull_request_title=ev.input.pull_request.title,
            base_commit_hash=ev.input.pull_request.base_commit_hash,
            head_commit_hash=ev.input.pull_request.head_commit_hash,
            target_file_path=ev.input.target_file_path,
            target_file_diff=target_file_diff,
            custom_guidelines_section=custom_guidelines_section,
            files_changed=ev.input.files_changed,
        )

        self.update_tools(partial_params={"repo_path": ev.input.repository.local_path, "include_line_numbers": True})
        return UserInputEvent(input=query)
