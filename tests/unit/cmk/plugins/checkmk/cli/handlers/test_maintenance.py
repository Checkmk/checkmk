#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

import cmk.utils.paths
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.piggyback import backend
from cmk.plugins.checkmk.cli.handlers.maintenance import (
    _CleanupPiggybackCommand,
    _FlushCommand,
    _UpdateDNSCacheCommand,
    cli_handler_cleanup_piggyback,
)
from cmk.ruleset_matcher.matcher import RuleSpec

_SHORT_MAX_AGE = 60
_LONG_MAX_AGE = 7200

_OMD_ROOT = Path("/omd/sites/mysite")

_CONTEXT = CLIContext(
    omd_root=_OMD_ROOT,
    global_options=CLIGlobalOptions(),
    logger=logging.getLogger(__name__),
)

_FAILURE = MKGeneralException("Cannot load the configuration")


class _FakeUpdateDNSCache:
    def __init__(self, error: MKGeneralException | None = None) -> None:
        self.asked: list[tuple[HostAddress | None, bool]] = []
        self._error = error

    def __call__(self, fake_dns: HostAddress | None, *, debug: bool) -> None:
        self.asked.append((fake_dns, debug))
        if self._error is not None:
            raise self._error


def test_the_dns_cache_is_updated_with_the_fake_address() -> None:
    update = _FakeUpdateDNSCache()

    _UpdateDNSCacheCommand(update_dns_cache=update).run(_CONTEXT, HostAddress("127.0.0.1"))

    assert update.asked == [(HostAddress("127.0.0.1"), False)]


def test_a_failed_dns_cache_update_exits_three() -> None:
    assert (
        _UpdateDNSCacheCommand(update_dns_cache=_FakeUpdateDNSCache(error=_FAILURE)).run(
            _CONTEXT, None
        )
        == CLIExitCode.UNKNOWN
    )


class _FakeCleanupPiggyback:
    def __init__(self) -> None:
        self.asked: list[tuple[Path, bool]] = []

    def __call__(self, omd_root: Path, *, debug: bool) -> None:
        self.asked.append((omd_root, debug))


def test_the_sites_piggyback_files_are_cleaned_up() -> None:
    cleanup = _FakeCleanupPiggyback()

    _CleanupPiggybackCommand(cleanup_piggyback=cleanup).run(_CONTEXT, None)

    assert cleanup.asked == [(_OMD_ROOT, False)]


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
    exit_code = cli_handler_cleanup_piggyback.run(
        CLIContext(
            omd_root=tmp_path,
            global_options=CLIGlobalOptions(),
            logger=logger,
        ),
        None,
    )

    assert exit_code == CLIExitCode.SUCCESS
    assert set(backend.get_piggybacked_host_with_sources(tmp_path)) == {"still-valid"}


class _FakeFlush:
    def __init__(self, error: MKGeneralException | None = None) -> None:
        self.asked: list[tuple[Sequence[HostAddress], bool]] = []
        self._error = error

    def __call__(self, hosts: Sequence[HostAddress], *, debug: bool) -> None:
        self.asked.append((hosts, debug))
        if self._error is not None:
            raise self._error


def test_the_requested_hosts_are_flushed() -> None:
    flush = _FakeFlush()

    _FlushCommand(flush=flush).run(_CONTEXT, (HostAddress("host1"),))

    assert flush.asked == [((HostAddress("host1"),), False)]


def test_a_failed_flush_exits_three() -> None:
    assert _FlushCommand(flush=_FakeFlush(error=_FAILURE)).run(_CONTEXT, ()) == CLIExitCode.UNKNOWN
