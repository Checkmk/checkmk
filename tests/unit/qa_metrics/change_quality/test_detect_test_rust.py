#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""End-to-end test of detect_test_rust.py against fixture git repos in tmp_path."""

import os
import subprocess
from pathlib import Path

import pytest

from tests.qa_metrics.change_quality.detect_test_rust import attribute_rust_test_touch

_LIB_RS_BASE = """\
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add() {
        assert_eq!(add(2, 2), 4);
    }
}
"""

_LIB_RS_NO_TESTS = "pub fn mul(a: i32, b: i32) -> i32 {\n    a * b\n}\n"


def _git_env() -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", ""),
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_AUTHOR_DATE": "2023-03-08T12:00:00+0000",
        "GIT_COMMITTER_DATE": "2023-03-08T12:00:00+0000",
    }


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, env=_git_env())


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", message)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env=_git_env(),
    ).stdout.strip()


@pytest.fixture
def rust_repo(tmp_path: Path) -> Path:
    """A repo with one .rs file that already has a #[cfg(test)] mod tests block."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "master")
    (repo / "src").mkdir()
    (repo / "src" / "lib.rs").write_text(_LIB_RS_BASE)
    _commit(repo, "initial")
    return repo


def _write_lib_rs(repo: Path, content: str) -> None:
    (repo / "src" / "lib.rs").write_text(content)


def test_returns_false_without_subprocess_when_no_rust_files(tmp_path: Path) -> None:
    """No .rs path in files_changed short-circuits before any git call.

    tmp_path isn't even a git repo -- if the implementation tried to shell
    out anyway, ``check=True`` would raise instead of returning False.
    """
    assert attribute_rust_test_touch(tmp_path, "deadbeef", ["cmk/foo.py", ".werks/123.md"]) is False


def test_new_test_attribute_added_to_existing_module(rust_repo: Path) -> None:
    content = _LIB_RS_BASE.replace(
        "    fn test_add() {\n        assert_eq!(add(2, 2), 4);\n    }\n",
        "    fn test_add() {\n        assert_eq!(add(2, 2), 4);\n    }\n\n"
        "    #[test]\n    fn test_add_negative() {\n        assert_eq!(add(-1, -1), -2);\n    }\n",
    )
    _write_lib_rs(rust_repo, content)
    sha = _commit(rust_repo, "add negative-number test")
    assert attribute_rust_test_touch(rust_repo, sha, ["src/lib.rs"]) is True


def test_existing_test_body_modified_detected_via_hunk_context(rust_repo: Path) -> None:
    """A wrong assumption inside an already-existing test is fixed without

    touching the #[test]/mod lines -- must still be detected via the hunk
    header's function-context annotation.
    """
    content = _LIB_RS_BASE.replace(
        "assert_eq!(add(2, 2), 4);", "assert_eq!(add(2, 2), 4); // was previously wrong"
    )
    _write_lib_rs(rust_repo, content)
    sha = _commit(rust_repo, "fix wrong test assumption")
    assert attribute_rust_test_touch(rust_repo, sha, ["src/lib.rs"]) is True


def test_production_only_fix_returns_false(rust_repo: Path) -> None:
    content = _LIB_RS_BASE.replace(
        "pub fn add(a: i32, b: i32) -> i32 {\n    a + b\n}",
        "pub fn add(a: i32, b: i32) -> i32 {\n    a.wrapping_add(b)\n}",
    )
    _write_lib_rs(rust_repo, content)
    sha = _commit(rust_repo, "fix overflow panic")
    assert attribute_rust_test_touch(rust_repo, sha, ["src/lib.rs"]) is False


def test_only_rust_paths_are_diffed_in_mixed_commit(rust_repo: Path) -> None:
    content = _LIB_RS_BASE.replace(
        "pub fn add(a: i32, b: i32) -> i32 {\n    a + b\n}",
        "pub fn add(a: i32, b: i32) -> i32 {\n    a.wrapping_add(b)\n}",
    )
    _write_lib_rs(rust_repo, content)
    (rust_repo / "README.md").write_text("docs\n")
    sha = _commit(rust_repo, "fix overflow panic + docs")
    assert attribute_rust_test_touch(rust_repo, sha, ["src/lib.rs", "README.md"]) is False


def test_first_test_ever_added_to_file(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "master")
    (repo / "src").mkdir()
    _write_lib_rs(repo, _LIB_RS_NO_TESTS)
    _commit(repo, "initial")

    content = (
        _LIB_RS_NO_TESTS + "\n#[cfg(test)]\nmod tests {\n    use super::*;\n\n    #[test]\n"
        "    fn test_mul() {\n        assert_eq!(mul(2, 3), 6);\n    }\n}\n"
    )
    _write_lib_rs(repo, content)
    sha = _commit(repo, "add first test")
    assert attribute_rust_test_touch(repo, sha, ["src/lib.rs"]) is True


def test_production_fn_with_test_substring_in_name_returns_false(rust_repo: Path) -> None:
    """``fn latest_value()`` contains the substring "test" but isn't a test."""
    content = _LIB_RS_BASE.replace(
        "pub fn add(a: i32, b: i32) -> i32 {\n    a + b\n}",
        "pub fn add(a: i32, b: i32) -> i32 {\n    a + b\n}\n\n"
        "pub fn latest_value(a: i32, b: i32) -> i32 {\n    if a > b { a } else { b }\n}",
    )
    _write_lib_rs(rust_repo, content)
    _commit(rust_repo, "add latest_value helper")

    content2 = content.replace(
        "    if a > b { a } else { b }\n}", "    if a >= b { a } else { b }\n}"
    )
    _write_lib_rs(rust_repo, content2)
    sha = _commit(rust_repo, "fix tie-break in latest_value")
    assert attribute_rust_test_touch(rust_repo, sha, ["src/lib.rs"]) is False


def test_tokio_test_attribute_detected(rust_repo: Path) -> None:
    content = _LIB_RS_BASE.replace(
        "    fn test_add() {\n        assert_eq!(add(2, 2), 4);\n    }\n",
        "    fn test_add() {\n        assert_eq!(add(2, 2), 4);\n    }\n\n"
        '    #[tokio::test(flavor = "multi_thread")]\n    async fn test_async_add() {\n'
        "        assert_eq!(add(1, 1), 2);\n    }\n",
    )
    _write_lib_rs(rust_repo, content)
    sha = _commit(rust_repo, "add async test")
    assert attribute_rust_test_touch(rust_repo, sha, ["src/lib.rs"]) is True
