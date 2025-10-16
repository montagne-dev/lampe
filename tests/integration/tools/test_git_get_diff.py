from pathlib import Path

from git import Repo

from lampe.core.tools.repository import get_diff_between_commits


def test_get_diff_with_files_ignore_patterns(git_repo_with_branches):
    """Test get_diff pattern filtering using gitignore-style patterns (*.txt, !readme.txt)"""
    # Create initial content with multiple files
    initial_content = """file1.txt content
file2.md content
docs/file3.txt content"""

    # Create modified content
    modified_content = """file1.txt MODIFIED
file2.md MODIFIED
docs/file3.txt MODIFIED"""

    # Use the fixture to create repo with initial state
    repo_path, _, _ = git_repo_with_branches("test_files.txt", initial_content, modified_content)

    # Manually add additional files to test exclude patterns
    repo = Repo(path=repo_path)
    # Create separate files for better testing
    file1 = Path(repo_path) / "file1.txt"
    file2_md = Path(repo_path) / "file2.md"
    file3 = Path(repo_path) / "docs" / "file3.txt"
    file4 = Path(repo_path) / "readme.txt"
    file5 = Path(repo_path) / "main.py"

    file1.write_text("a\nb\nc\n")
    file2_md.write_text("x\ny\nz\n")
    file3.parent.mkdir(exist_ok=True)
    file3.write_text("doc1\ndoc2\n")
    file4.write_text("readme\n")
    file5.write_text("main=1\n")

    repo.index.add([str(file1), str(file2_md), str(file3), str(file4), str(file5)])
    base_commit = repo.index.commit("Add multiple files")

    # Rename file2.md to file2.txt and delete file1.txt
    file2_txt = Path(repo_path) / "file2.txt"
    file2_md.rename(file2_txt)
    file1.unlink()

    file3.write_text("doc1\nMODIFIED\n")
    file4.write_text("readme\nMODIFIED\n")
    file5.write_text("")

    repo.index.remove([str(file1), str(file2_md)], working_tree=True)
    repo.index.add([str(file2_txt), str(file3), str(file4), str(file5)])
    head_commit = repo.index.commit("Modify all files, rename file2.md to file2.txt, remove file1.txt")

    # Exclude *.txt and re-include readme.txt
    diff_all = get_diff_between_commits(
        base_commit.hexsha,
        head_commit.hexsha,
        files_exclude_patterns=["*.txt"],
        repo_path=repo_path,
        files_reinclude_patterns=["readme.txt"],
    )
    assert "readme\n+MODIFIED" in diff_all
    assert "file1.txt" not in diff_all
    assert "file2.md" not in diff_all
    assert "file2.txt" not in diff_all
    assert "file3.txt" not in diff_all
    assert "readme.txt" in diff_all
    assert "main.py" in diff_all

    # Include *.py and exclude *.txt and re-include readme.txt
    diff_all = get_diff_between_commits(
        base_commit.hexsha,
        head_commit.hexsha,
        files_include_patterns=["*.py"],
        files_exclude_patterns=["*.txt"],
        files_reinclude_patterns=["readme.txt"],
        repo_path=repo_path,
    )
    assert diff_all.count("diff --git a/main.py b/main.py") == 1
    assert "file1.txt" not in diff_all
    assert "file2.md" not in diff_all
    assert "file2.txt" not in diff_all
    assert "file3.txt" not in diff_all
    assert "readme.txt" not in diff_all

    # Include *.py and exclude *.txt and re-include readme.txt
    diff_all = get_diff_between_commits(
        base_commit.hexsha,
        head_commit.hexsha,
        files_include_patterns=["*.py"],
        files_exclude_patterns=["*.txt"],
        files_reinclude_patterns=["readme.txt", "main.py"],
        repo_path=repo_path,
    )
    assert diff_all.count("diff --git a/main.py b/main.py") == 1
    assert "file1.txt" not in diff_all
    assert "file2.md" not in diff_all
    assert "file2.txt" not in diff_all
    assert "file3.txt" not in diff_all
    assert "readme.txt" not in diff_all


def test_get_diff_with_files_exclude_patterns(git_repo_with_branches):
    """Test get_diff with files_exclude_patterns using the git_repo_with_branches fixture."""
    # Create initial content with multiple files
    initial_content = """file1.txt content
file2.md content
docs/file3.txt content"""

    # Create modified content
    modified_content = """file1.txt MODIFIED
file2.md MODIFIED
docs/file3.txt MODIFIED"""

    # Use the fixture to create repo with initial state
    repo_path, _, _ = git_repo_with_branches("test_files.txt", initial_content, modified_content)

    # Manually add additional files to test exclude patterns
    repo = Repo(path=repo_path)

    # Create separate files for better testing
    file1 = Path(repo_path) / "file1.txt"
    file2 = Path(repo_path) / "file2.md"
    file3 = Path(repo_path) / "docs" / "file3.txt"

    file1.write_text("a\nb\nc\n")
    file2.write_text("x\ny\nz\n")
    file3.parent.mkdir(exist_ok=True)
    file3.write_text("doc1\ndoc2\n")

    repo.index.add([str(file1), str(file2), str(file3)])
    base_commit = repo.index.commit("Add multiple files")

    # Modify all files
    file1.write_text("a\nb\nMODIFIED\n")
    file2.write_text("x\ny\nMODIFIED\n")
    file3.write_text("doc1\nMODIFIED\n")
    repo.index.add([str(file1), str(file2), str(file3)])
    head_commit = repo.index.commit("Modify all files")

    # No exclude: all files in diff
    diff_all = get_diff_between_commits(base_commit.hexsha, head_commit.hexsha, repo_path=repo_path)
    assert "MODIFIED" in diff_all
    assert "file1.txt" in diff_all
    assert "file2.md" in diff_all
    assert "file3.txt" in diff_all

    # Exclude *.md
    diff_exclude_md = get_diff_between_commits(
        base_commit.hexsha, head_commit.hexsha, files_exclude_patterns=["*.md"], repo_path=repo_path
    )
    assert "file2.md" not in diff_exclude_md
    assert "file1.txt" in diff_exclude_md
    assert "file3.txt" in diff_exclude_md

    # Exclude docs/*
    diff_exclude_docs = get_diff_between_commits(
        base_commit.hexsha, head_commit.hexsha, files_exclude_patterns=["docs/*"], repo_path=repo_path
    )
    assert "file3.txt" not in diff_exclude_docs
    assert "file1.txt" in diff_exclude_docs
    assert "file2.md" in diff_exclude_docs

    # Exclude both
    diff_exclude_both = get_diff_between_commits(
        base_commit.hexsha, head_commit.hexsha, files_exclude_patterns=["*.md", "docs/*"], repo_path=repo_path
    )
    assert "file2.md" not in diff_exclude_both
    assert "file3.txt" not in diff_exclude_both
    assert "file1.txt" in diff_exclude_both

    # Include only *.txt
    diff_include_txt = get_diff_between_commits(
        base_commit.hexsha, head_commit.hexsha, files_include_patterns=["*.txt"], repo_path=repo_path
    )
    assert "file1.txt" in diff_include_txt
    assert "file3.txt" in diff_include_txt
    assert "file2.md" not in diff_include_txt

    # Include *.txt and *.md
    diff_include_txt_md = get_diff_between_commits(
        base_commit.hexsha, head_commit.hexsha, files_include_patterns=["*.txt", "*.md"], repo_path=repo_path
    )
    assert "file1.txt" in diff_include_txt_md
    assert "file3.txt" in diff_include_txt_md
    assert "file2.md" in diff_include_txt_md

    # Include *.txt but exclude docs/*
    diff_include_exclude = get_diff_between_commits(
        base_commit.hexsha,
        head_commit.hexsha,
        files_include_patterns=["*.txt"],
        repo_path=repo_path,
        files_exclude_patterns=["docs/*"],
    )
    assert "file1.txt" in diff_include_exclude
    assert "file2.md" not in diff_include_exclude
    assert "file3.txt" not in diff_include_exclude
