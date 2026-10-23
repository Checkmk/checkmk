# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""--full --watch: full initial deploy, incremental watch cycles."""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock, patch

from cmk.dev_deploy.__main__ import _main_with_site
from cmk.dev_deploy.cli import parse_args
from cmk.dev_deploy.types import DeployCycleResult

_OK = DeployCycleResult(
    exit_code=0,
    deployed=(),
    skipped=(),
    skipped_reasons={},
    services_restarted=0,
    all_skipped=True,
)


def _run(argv: list[str], tmp_path: Path) -> list[bool]:
    """Return the `full` flag of every deploy cycle (initial + one watch cycle)."""
    cycle = MagicMock(return_value=_OK)

    def fake_watch_loop(_site: object, _repo: Path, deploy_fn: Callable[[], object]) -> int:
        deploy_fn()
        return 0

    with (
        patch("cmk.dev_deploy.__main__.load_state", return_value=None),
        patch("cmk.dev_deploy.__main__.resolve_backend_name"),
        patch("cmk.dev_deploy.__main__.create_backend"),
        patch("cmk.dev_deploy.__main__.check_backend_conflict", return_value=None),
        patch("cmk.dev_deploy.__main__.check_branch_mismatch", return_value=None),
        patch("cmk.dev_deploy.__main__._run_deploy_cycle", cycle),
        patch("cmk.dev_deploy.__main__.watch_loop", fake_watch_loop),
    ):
        assert _main_with_site(parse_args(argv), tmp_path, MagicMock()) == 0
    return [call.args[0].full for call in cycle.call_args_list]


def test_full_watch_deploys_full_once_then_incrementally(tmp_path: Path) -> None:
    assert _run(["--full", "--watch"], tmp_path) == [True, False]


def test_watch_without_full_has_no_initial_deploy(tmp_path: Path) -> None:
    assert _run(["--watch"], tmp_path) == [False]
