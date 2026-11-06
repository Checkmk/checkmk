#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time
from collections.abc import Mapping, Sequence
from contextlib import nullcontext
from pathlib import Path

import pytest

import cmk.utils.paths
from cmk.ccc.hostaddress import HostAddress
from cmk.cli.engine.arguments import RunCommand as CLIRunCommand
from cmk.cli.engine.call import call as cli_call
from cmk.cli.engine.discovery import make_command as cli_make_command
from cmk.cli.engine.readers import ParsedOptions as CLIParsedOptions
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.piggyback import backend
from cmk.plugins.checkmk.cli.maintenance import cli_command_cleanup_piggyback
from cmk.ruleset_matcher.matcher import RuleSpec

_SHORT_MAX_AGE = 60
_LONG_MAX_AGE = 7200


def _write_main_mk(
    max_cache_file_age: int, rules: Sequence[RuleSpec[Mapping[str, object]]]
) -> None:
    """The command loads the configuration itself, so it has to find it on disk."""
    cmk.utils.paths.main_config_file.parent.mkdir(parents=True, exist_ok=True)
    cmk.utils.paths.main_config_file.write_text(
        f"piggyback_max_cachefile_age = {max_cache_file_age!r}\n"
        f"piggybacked_host_files = {list(rules)!r}\n"
    )


def _store_aged(omd_root: Path, piggybacked: str, age: float) -> None:
    now = time.time()
    backend.store_piggyback_raw_data(
        HostAddress("source"),
        {HostAddress(piggybacked): (b"payload",)},
        message_timestamp=now - age,
        contact_timestamp=now,
        omd_root=omd_root,
    )


@pytest.mark.parametrize(
    "max_cache_file_age, rules",
    [
        pytest.param(_LONG_MAX_AGE, [], id="global setting"),
        pytest.param(
            _SHORT_MAX_AGE,
            [RuleSpec(value={"global_max_cache_age": _LONG_MAX_AGE}, condition={}, id="rule")],
            id="'Piggybacked host files' rule",
        ),
    ],
)
def test_cleanup_piggyback_removes_files_beyond_configured_max_age(
    tmp_path: Path,
    max_cache_file_age: int,
    rules: Sequence[RuleSpec[Mapping[str, object]]],
) -> None:
    _write_main_mk(max_cache_file_age, rules)
    _store_aged(tmp_path, "aged-out", age=_LONG_MAX_AGE + 600)
    _store_aged(tmp_path, "still-valid", age=_LONG_MAX_AGE - 600)

    logger = logging.getLogger(__name__)
    parsed = CLIRunCommand(cli_make_command(cli_command_cleanup_piggyback), "", [], [])

    exit_code = cli_call(
        CLIContext(omd_root=tmp_path, global_options=CLIGlobalOptions(), logger=logger),
        parsed,
        parsed.command.bind(CLIParsedOptions([], logger)),
        lambda *_args: nullcontext(),
    )

    assert exit_code == CLIExitCode.SUCCESS
    assert set(backend.get_piggybacked_host_with_sources(tmp_path)) == {"still-valid"}
