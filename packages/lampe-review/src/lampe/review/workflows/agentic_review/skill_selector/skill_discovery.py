"""Discover SKILL.md files within the reviewed repository."""

import re
from pathlib import Path

from pydantic import BaseModel, Field

# Directories to skip when scanning for skills (e.g. deps, build artifacts)
_SKIP_DIRS = frozenset({".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", "dist", "build"})


def _should_skip(path: Path, repo_root: Path) -> bool:
    """Return True if path is under a directory we should skip."""
    try:
        rel = path.relative_to(repo_root)
    except ValueError:
        return True
    for part in rel.parts:
        if part in _SKIP_DIRS:
            return True
    return False


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
    """Find all SKILL.md files in the repository.

    Scans for any SKILL.md file under the repo root.
    Skips directories: .git, node_modules, __pycache__, .venv, venv, .tox, dist, build.

    Returns:
        List of SkillInfo with path, name, description, and full content.
    """
    base = Path(repo_path).resolve()
    if not base.exists() or not base.is_dir():
        return []

    skills: list[SkillInfo] = []
    seen_paths: set[Path] = set()

    for skill_file in base.rglob("SKILL.md"):
        if not skill_file.is_file():
            continue
        if skill_file in seen_paths:
            continue
        if _should_skip(skill_file, base):
            continue

        seen_paths.add(skill_file)

        try:
            content = skill_file.read_text(encoding="utf-8")
        except Exception:
            continue

        metadata, _ = _parse_frontmatter(content)
        skill_dir = skill_file.parent
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
