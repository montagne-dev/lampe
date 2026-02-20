"""Discover SKILL.md files in conventional locations within the reviewed repository."""

import re
from pathlib import Path

from pydantic import BaseModel, Field


class SkillInfo(BaseModel):
    """Metadata and content of a discovered skill."""

    path: str = Field(..., description="Path to the SKILL.md file")
    name: str = Field(..., description="Skill name from frontmatter")
    description: str = Field(default="", description="Skill description from frontmatter")
    content: str = Field(..., description="Full file content including frontmatter and body")


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter from markdown content.

    Returns:
        Tuple of (metadata dict, body content after frontmatter).
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return {}, content

    frontmatter_text, body = match.groups()
    metadata: dict[str, str] = {}

    for line in frontmatter_text.strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            metadata[key.strip().lower()] = value.strip().strip("\"'")
    return metadata, body.strip()


def discover_skills(repo_path: str) -> list[SkillInfo]:
    """Find all SKILL.md files in conventional locations.

    Scans:
    - {repo_path}/.cursor/skills/*/SKILL.md
    - {repo_path}/.lampe/skills/*/SKILL.md

    Returns:
        List of SkillInfo with path, name, description, and full content.
    """
    base = Path(repo_path)
    locations = [
        base / ".cursor" / "skills",
        base / ".lampe" / "skills",
    ]

    skills: list[SkillInfo] = []
    for base_dir in locations:
        if not base_dir.exists() or not base_dir.is_dir():
            continue

        for skill_dir in base_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                content = skill_file.read_text(encoding="utf-8")
            except Exception:
                continue

            metadata, _ = _parse_frontmatter(content)
            name = metadata.get("name", skill_dir.name)
            description = metadata.get("description", "")

            skills.append(
                SkillInfo(
                    path=str(skill_file),
                    name=name,
                    description=description,
                    content=content,
                )
            )
    return skills
