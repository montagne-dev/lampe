"""Unit tests for skill discovery."""

from lampe.review.workflows.agentic_review.skill_selector.skill_discovery import (
    discover_skills,
)


def test_discover_skills_empty_when_no_skills(tmp_path):
    """When no skill directories exist, return empty list."""
    result = discover_skills(str(tmp_path))
    assert result == []


def test_discover_skills_finds_cursor_skills(tmp_path):
    """Discover skills in .cursor/skills/*/SKILL.md."""
    skill_dir = tmp_path / ".cursor" / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        """---
name: test-skill
description: A test skill for validation
---

# Test Skill
Content here.
"""
    )
    result = discover_skills(str(tmp_path))
    assert len(result) == 1
    assert result[0].name == "test-skill"
    assert result[0].description == "A test skill for validation"
    assert "Content here" in result[0].content


def test_discover_skills_finds_lampe_skills(tmp_path):
    """Discover skills in .lampe/skills/*/SKILL.md."""
    skill_dir = tmp_path / ".lampe" / "skills" / "django-data"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        """---
name: django-data
description: Django ORM and data management guidelines
---

# Django Data
Guidelines...
"""
    )
    result = discover_skills(str(tmp_path))
    assert len(result) == 1
    assert result[0].name == "django-data"


def test_discover_skills_multiple(tmp_path):
    """Discover multiple skills from both locations."""
    (tmp_path / ".cursor" / "skills" / "skill-a").mkdir(parents=True)
    (tmp_path / ".cursor" / "skills" / "skill-a" / "SKILL.md").write_text("---\nname: skill-a\ndescription: A\n---\n")
    (tmp_path / ".lampe" / "skills" / "skill-b").mkdir(parents=True)
    (tmp_path / ".lampe" / "skills" / "skill-b" / "SKILL.md").write_text("---\nname: skill-b\ndescription: B\n---\n")
    result = discover_skills(str(tmp_path))
    assert len(result) == 2
    names = {s.name for s in result}
    assert names == {"skill-a", "skill-b"}
