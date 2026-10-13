# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Regression tests: a deployer whose only change is a new file must redeploy.

Untracked files are invisible to ``git diff``, so ``check_skip`` used to
report "no changes" for a package whose entire new feature directory had
never been ``git add``-ed.  The deployer skipped itself indefinitely while
Bazel -- which globs the source tree -- happily built those files whenever
some unrelated tracked file in the same package changed.

These tests drive the real ``compute_dirty_hashes``/``get_dirty_files``
chain and mock only the git commands underneath it.
"""

import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from cmk.dev_deploy.state.deploy_state import (
    compute_file_hash,
    DeployerState,
    DeployState,
)
from cmk.dev_deploy.state.path_skip import check_skip

SITE = Path("/omd/sites/test")
HEAD = "a" * 40
PREFIX = "packages/cmk-frontend-vue/"
NEW_FILE = "packages/cmk-frontend-vue/src/check-ai/CheckAiApp.vue"


def _state(dirty: dict[str, str]) -> DeployState:
    """Deploy state whose install_spec last deployed at HEAD."""
    return DeployState(
        deployers={
            "install_spec": DeployerState(
                deployer="install_spec",
                git_commit=HEAD,
                dirty_file_hashes=dirty,
                deployed_at=1000.0,
            )
        }
    )


@contextmanager
def _git(*, untracked: list[str], tracked_diff: str = "") -> Iterator[None]:
    """Mock the git layer: no commits since the last deploy, given dirt."""

    def _run_checked(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with (
        patch(
            "cmk.dev_deploy.execution.source_paths.resolve_source_paths",
            return_value=(PREFIX,),
        ),
        patch("cmk.dev_deploy.state.path_skip.run_checked", _run_checked),
        patch(
            "cmk.dev_deploy.state.deploy_state.subprocess.run",
            lambda cmd, **_kw: subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout=tracked_diff, stderr=""
            ),
        ),
        patch(
            "cmk.dev_deploy.state.deploy_state.query_untracked_files",
            return_value=untracked,
        ),
    ):
        yield


class TestUntrackedFileSkipDecision:
    """check_skip() for a package whose only change is a brand-new file."""

    def test_new_file_forces_redeploy(self, tmp_path: Path) -> None:
        """A never-added file under the deployer's prefix is a change."""
        (tmp_path / NEW_FILE).parent.mkdir(parents=True)
        (tmp_path / NEW_FILE).write_text("<template />")

        with _git(untracked=[NEW_FILE]):
            result = check_skip("install_spec", tmp_path, SITE, _state({}), HEAD)

        assert result.should_skip is False
        assert NEW_FILE in result.changed_files

    def test_converges_once_deployed(self, tmp_path: Path) -> None:
        """After the new file is recorded, the next run skips.

        Without this the deployer would rebuild on every single run.
        """
        (tmp_path / NEW_FILE).parent.mkdir(parents=True)
        (tmp_path / NEW_FILE).write_text("<template />")
        recorded = {NEW_FILE: compute_file_hash(tmp_path / NEW_FILE)}

        with _git(untracked=[NEW_FILE]):
            result = check_skip("install_spec", tmp_path, SITE, _state(recorded), HEAD)

        assert result.should_skip is True

    def test_editing_a_new_file_redeploys(self, tmp_path: Path) -> None:
        """Editing an already-deployed new file makes it work again."""
        (tmp_path / NEW_FILE).parent.mkdir(parents=True)
        (tmp_path / NEW_FILE).write_text("<template />")
        recorded = {NEW_FILE: compute_file_hash(tmp_path / NEW_FILE)}
        (tmp_path / NEW_FILE).write_text("<template>edited</template>")

        with _git(untracked=[NEW_FILE]):
            result = check_skip("install_spec", tmp_path, SITE, _state(recorded), HEAD)

        assert result.should_skip is False

    def test_new_file_outside_prefix_does_not_redeploy(self, tmp_path: Path) -> None:
        """The prefix filter still applies to untracked files."""
        other = "packages/cmk-agent-ctl/src/new.rs"
        (tmp_path / other).parent.mkdir(parents=True)
        (tmp_path / other).write_text("fn main() {}")

        with _git(untracked=[other]):
            result = check_skip("install_spec", tmp_path, SITE, _state({}), HEAD)

        assert result.should_skip is True

    def test_deleting_a_new_file_redeploys(self, tmp_path: Path) -> None:
        """Removing a deployed new file must reach the site as a removal."""
        with _git(untracked=[]):
            result = check_skip("install_spec", tmp_path, SITE, _state({NEW_FILE: "h" * 64}), HEAD)

        assert result.should_skip is False
