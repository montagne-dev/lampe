"""Skill Selector Agent - selects which skills apply to a given PR."""

import logging

from llama_index.core.program import FunctionCallingProgram
from llama_index.llms.litellm import LiteLLM
from pydantic import BaseModel, Field

from lampe.core.llmconfig import MODELS, get_model
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME
from lampe.review.workflows.agentic_review.data_models import PRIntent
from lampe.review.workflows.agentic_review.skill_selector.skill_discovery import SkillInfo
from lampe.review.workflows.agentic_review.skill_selector.skill_selector_prompt import (
    SKILL_SELECTOR_SYSTEM_PROMPT,
    SKILL_SELECTOR_USER_PROMPT,
)


class SkillSelectionOutput(BaseModel):
    """Structured output from the Skill Selector Agent."""

    selected_skill_paths: list[str] = Field(
        default_factory=list,
        description="Paths to SKILL.md files that apply to this PR. Use exact paths from the available skills list.",
    )
    # Second field avoids llama_index call_tool bug: with 1 prop + 1 arg it unwraps
    # to tool(value) instead of tool(**kwargs), causing model_fn to receive empty kwargs
    note: str = Field(default="", description="Optional brief note. Can be empty.")


async def select_applicable_skills(
    pr_intent: PRIntent,
    files_changed: str,
    skills: list[SkillInfo],
    llm: LiteLLM | None = None,
) -> list[SkillInfo]:
    """Select which skills from the repo apply to this PR.

    Do not call this when skills is empty - the workflow should skip skill selection.

    Args:
        pr_intent: Extracted PR intent
        files_changed: List of changed files
        skills: List of discovered skills (must be non-empty)
        llm: Optional LLM instance

    Returns:
        List of SkillInfo that apply to this PR
    """
    if not skills:
        return []

    logger = logging.getLogger(LAMPE_LOGGER_NAME)
    _llm = llm or LiteLLM(model=get_model("LAMPE_MODEL_REVIEW_INTENT", MODELS.GPT_5_2_CODEX), temperature=1)

    skills_list = "\n".join(f'- path: "{s.path}" | name: {s.name} | description: {s.description}' for s in skills)

    prompt_template = f"{SKILL_SELECTOR_SYSTEM_PROMPT}\n\n{SKILL_SELECTOR_USER_PROMPT}"

    try:
        program = FunctionCallingProgram.from_defaults(
            output_cls=SkillSelectionOutput,
            llm=_llm,
            prompt_template_str=prompt_template,
            tool_required=True,
        )
        result = await program.acall(
            pr_intent_summary=pr_intent.summary,
            areas_touched=", ".join(pr_intent.areas_touched) or "unknown",
            suggested_tasks=", ".join(pr_intent.suggested_validation_tasks) or "general review",
            files_changed=files_changed,
            skills_list=skills_list,
        )
        if result is None:
            logger.warning("Skill selector returned None (LLM may not have invoked structured output)")
            selected_paths = []
        elif isinstance(result, SkillSelectionOutput):
            selected_paths = result.selected_skill_paths
        elif isinstance(result, list) and result:
            selected_paths = result[0].selected_skill_paths
        else:
            logger.warning(f"Skill selector returned unexpected type: {type(result)}")
            selected_paths = []
    except Exception as e:
        logger.warning(
            f"Skill selector failed, defaulting to no skills: {e}",
            exc_info=True,
        )
        selected_paths = []

    path_set = set(selected_paths)
    selected = [s for s in skills if s.path in path_set]
    if skills and not selected:
        logger.debug(f"Skill selector chose no skills from {len(skills)} available")
    return selected
