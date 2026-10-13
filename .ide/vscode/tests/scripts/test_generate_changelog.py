# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import generate_changelog
import pytest
from generate_changelog import (
    collect_commits,
    COMMIT_SEP,
    current_package_version,
    FIELD_SEP,
    main,
    parse_version,
    render_changelog,
)


def _commit(summary: str, commit_type: str = "fix", jira: str = "") -> dict[str, str]:
    return {"sha": "cafe", "type": commit_type, "summary": summary, "jira": jira}


class TestParseVersion:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            pytest.param("0.4.27", (0, 4, 27), id="plain"),
            pytest.param("10.20.30", (10, 20, 30), id="multi-digit"),
            pytest.param("0.0.0", (0, 0, 0), id="zeros"),
        ],
    )
    def test_valid_version(self, raw: str, expected: tuple[int, int, int]) -> None:
        assert parse_version(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            pytest.param("0.4", id="two-components"),
            pytest.param("0.4.27.1", id="four-components"),
            pytest.param("v0.4.27", id="v-prefix"),
            pytest.param("a.b.c", id="non-numeric"),
            pytest.param("", id="empty"),
            pytest.param(" 0.4.27", id="leading-space"),
        ],
    )
    def test_invalid_version_returns_none(self, raw: str) -> None:
        assert parse_version(raw) is None

    def test_ordering_is_numeric_not_lexicographic(self) -> None:
        assert parse_version("0.1.50") < parse_version("0.4.27")  # type: ignore[operator]
        assert parse_version("0.10.0") > parse_version("0.9.9")  # type: ignore[operator]


class TestRenderChangelog:
    def test_empty_commit_list_renders_only_the_header(self) -> None:
        assert render_changelog("0.4.28", []) == "## v0.4.28\n\n"

    def test_bullet_without_jira(self) -> None:
        assert render_changelog("1.0.0", [_commit("thing")]) == "## v1.0.0\n\n- **fix**: thing\n"

    def test_bullet_with_jira(self) -> None:
        rendered = render_changelog("1.0.0", [_commit("thing", "feat", "CMK-42")])
        assert rendered == "## v1.0.0\n\n- **feat**: thing (CMK-42)\n"

    def test_commit_order_is_preserved(self) -> None:
        rendered = render_changelog("1.0.0", [_commit("first"), _commit("second", "feat")])
        assert rendered.splitlines()[2:] == ["- **fix**: first", "- **feat**: second"]


class TestCurrentPackageVersion:
    @staticmethod
    def _write_package_json(root: Path, content: str) -> None:
        package_json = root / generate_changelog.VSCODE_DIR_REL / "package.json"
        package_json.parent.mkdir(parents=True, exist_ok=True)
        package_json.write_text(content)

    def test_reads_the_version_field(self, tmp_path: Path) -> None:
        self._write_package_json(tmp_path, json.dumps({"version": "0.4.27"}))
        assert current_package_version(tmp_path) == "0.4.27"

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert current_package_version(tmp_path) is None

    def test_malformed_json_returns_none(self, tmp_path: Path) -> None:
        self._write_package_json(tmp_path, "{not json")
        assert current_package_version(tmp_path) is None

    def test_missing_version_key_returns_none(self, tmp_path: Path) -> None:
        self._write_package_json(tmp_path, json.dumps({"name": "cmk-vscode"}))
        assert current_package_version(tmp_path) is None

    def test_non_string_version_returns_none(self, tmp_path: Path) -> None:
        self._write_package_json(tmp_path, json.dumps({"version": 427}))
        assert current_package_version(tmp_path) is None


class TestCollectCommits:
    @staticmethod
    def _git_log(*commits: tuple[str, str]) -> str:
        return "".join(f"{COMMIT_SEP}{sha}{FIELD_SEP}{body}" for sha, body in commits)

    @pytest.fixture
    def fake_git_log(self, monkeypatch: pytest.MonkeyPatch) -> Callable[[str], None]:
        def install(output: str) -> None:
            monkeypatch.setattr(subprocess, "check_output", lambda *_a, **_kw: output)

        return install

    def test_groups_commits_by_version(self, fake_git_log: Callable[[str], None]) -> None:
        fake_git_log(
            self._git_log(
                ("sha1", "feat(vscode): a\n\nv0.4.27\n"),
                ("sha2", "fix(vscode): b\n\nv0.4.27\n"),
                ("sha3", "fix(vscode): c\n\nv0.4.26\n"),
            )
        )
        by_version = collect_commits(Path("/does-not-matter"))
        assert sorted(by_version) == ["0.4.26", "0.4.27"]
        assert [commit["summary"] for commit in by_version["0.4.27"]] == ["a", "b"]

    def test_extracts_sha_type_summary_and_jira(self, fake_git_log: Callable[[str], None]) -> None:
        fake_git_log(self._git_log(("deadbeef", "feat(vscode): add thing\n\nv1.2.3\nCMK-42\n")))
        (commit,) = collect_commits(Path("/does-not-matter"))["1.2.3"]
        assert commit == {
            "sha": "deadbeef",
            "type": "feat",
            "summary": "add thing",
            "jira": "CMK-42",
        }

    def test_version_on_the_line_after_a_blank_is_found(
        self, fake_git_log: Callable[[str], None]
    ) -> None:
        fake_git_log(self._git_log(("sha", "fix(vscode): x\n\nv0.9.9\n")))
        assert list(collect_commits(Path("/does-not-matter"))) == ["0.9.9"]

    def test_first_version_line_wins(self, fake_git_log: Callable[[str], None]) -> None:
        fake_git_log(self._git_log(("sha", "fix(vscode): x\n\nv1.0.0\nv2.0.0\n")))
        assert list(collect_commits(Path("/does-not-matter"))) == ["1.0.0"]

    @pytest.mark.parametrize(
        "body",
        [
            pytest.param("feat(vscode): no version line\n", id="no-version-line"),
            pytest.param("random subject\n\nv1.0.0\n", id="non-conventional-subject"),
            pytest.param("feat(gui): other scope\n\nv1.0.0\n", id="wrong-scope"),
            pytest.param("\n", id="empty-body"),
        ],
    )
    def test_unusable_commit_is_skipped(
        self, fake_git_log: Callable[[str], None], body: str
    ) -> None:
        fake_git_log(self._git_log(("sha", body)))
        assert collect_commits(Path("/does-not-matter")) == {}


class TestMain:
    @pytest.fixture
    def repo(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        (tmp_path / generate_changelog.VSCODE_DIR_REL).mkdir(parents=True)
        monkeypatch.setattr(generate_changelog, "repo_root", lambda: tmp_path)
        monkeypatch.setattr(sys, "argv", ["generate_changelog"])
        return tmp_path

    @staticmethod
    def _changelog_dir(root: Path) -> Path:
        return root / generate_changelog.VSCODE_DIR_REL / "changelog"

    @staticmethod
    def _set_package_version(root: Path, version: str) -> None:
        package_json = root / generate_changelog.VSCODE_DIR_REL / "package.json"
        package_json.write_text(json.dumps({"version": version}))

    @staticmethod
    def _fake_commits(
        monkeypatch: pytest.MonkeyPatch, by_version: dict[str, list[dict[str, str]]]
    ) -> None:
        monkeypatch.setattr(generate_changelog, "collect_commits", lambda _root: by_version)

    def test_writes_the_changelog_for_the_current_version(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._set_package_version(repo, "0.4.27")
        self._fake_commits(monkeypatch, {"0.4.27": [_commit("x")]})
        assert main() == 0
        written = self._changelog_dir(repo) / "v0.4.27.md"
        assert written.read_text() == "## v0.4.27\n\n- **fix**: x\n"

    def test_the_current_version_file_is_regenerated(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._set_package_version(repo, "0.4.27")
        changelog_dir = self._changelog_dir(repo)
        changelog_dir.mkdir()
        (changelog_dir / "v0.4.27.md").write_text("stale content\n")
        self._fake_commits(monkeypatch, {"0.4.27": [_commit("x")]})
        assert main() == 0
        assert "stale content" not in (changelog_dir / "v0.4.27.md").read_text()

    def test_an_older_existing_file_is_preserved(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._set_package_version(repo, "0.4.27")
        changelog_dir = self._changelog_dir(repo)
        changelog_dir.mkdir()
        (changelog_dir / "v0.4.26.md").write_text("hand-written release notes\n")
        self._fake_commits(monkeypatch, {"0.4.26": [_commit("x")]})
        assert main() == 0
        assert (changelog_dir / "v0.4.26.md").read_text() == "hand-written release notes\n"

    def test_an_older_missing_file_is_generated(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._set_package_version(repo, "0.4.27")
        self._fake_commits(monkeypatch, {"0.4.26": [_commit("x")]})
        assert main() == 0
        assert (self._changelog_dir(repo) / "v0.4.26.md").is_file()

    def test_versions_below_the_floor_are_skipped(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["generate_changelog", "--since-version", "0.4.0"])
        self._set_package_version(repo, "0.4.27")
        self._fake_commits(monkeypatch, {"0.3.9": [_commit("old")], "0.4.27": [_commit("new")]})
        assert main() == 0
        changelog_dir = self._changelog_dir(repo)
        assert not (changelog_dir / "v0.3.9.md").exists()
        assert (changelog_dir / "v0.4.27.md").is_file()

    def test_invalid_since_version_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "argv", ["generate_changelog", "--since-version", "nope"])
        assert main() == 2
