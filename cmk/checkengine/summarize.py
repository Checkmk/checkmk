#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol

import cmk.utils.resulttype as result
from cmk.utils.exceptions import (
    MKAgentError,
    MKFetcherError,
    MKIPAddressLookupError,
    MKSNMPError,
    MKTimeout,
)
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.piggyback import get_piggyback_raw_data, PiggybackTimeSettings

from cmk.checkengine.checkresults import ActiveCheckResult
from cmk.checkengine.exitspec import ExitSpec
from cmk.checkengine.fetcher import FetcherType, SourceInfo
from cmk.checkengine.parser import HostSections

__all__ = ["summarize", "SummarizerFunction", "SummaryConfig"]


@dataclass(frozen=True)
class SummaryConfig:
    """User config for summary."""

    exit_spec: ExitSpec
    time_settings: PiggybackTimeSettings
    expect_data: bool


class SummarizerFunction(Protocol):
    def __call__(
        self,
        host_sections: Iterable[tuple[SourceInfo, result.Result[HostSections, Exception]]],
    ) -> Iterable[ActiveCheckResult]: ...


def summarize(
    hostname: HostName,
    ipaddress: HostAddress | None,
    host_sections: result.Result[HostSections, Exception],
    config: SummaryConfig,
    *,
    fetcher_type: FetcherType,
) -> Sequence[ActiveCheckResult]:
    if fetcher_type is FetcherType.PIGGYBACK:
        return host_sections.fold(
            ok=lambda _: summarize_piggyback(
                hostname=hostname,
                ipaddress=ipaddress,
                time_settings=config.time_settings,
                expect_data=config.expect_data,
            ),
            error=lambda exc: summarize_failure(config.exit_spec, exc),
        )

    return host_sections.fold(
        ok=lambda _: summarize_success(config.exit_spec),
        error=lambda exc: summarize_failure(config.exit_spec, exc),
    )


def summarize_success(exit_spec: ExitSpec) -> Sequence[ActiveCheckResult]:
    return [ActiveCheckResult(0, "Success")]


def summarize_failure(exit_spec: ExitSpec, exc: Exception) -> Sequence[ActiveCheckResult]:
    def extract_status(exc: Exception) -> int:
        if isinstance(
            exc,
            (
                MKAgentError,
                MKFetcherError,
                MKIPAddressLookupError,
                MKSNMPError,
            ),
        ):
            return exit_spec.get("connection", 2)
        if isinstance(exc, MKTimeout):
            return exit_spec.get("timeout", 2)
        return exit_spec.get("exception", 3)

    return [
        ActiveCheckResult(
            extract_status(exc),
            str(exc).rsplit("\n", maxsplit=1)[-1],
            str(exc).split("\n") if "\n" in str(exc) else (),
        )
    ]


def summarize_piggyback(
    *,
    hostname: HostName,
    ipaddress: HostAddress | None,
    time_settings: PiggybackTimeSettings,
    expect_data: bool,
) -> Sequence[ActiveCheckResult]:
    if sources := [
        source
        for origin in (hostname, ipaddress)
        # TODO(ml): The code uses `get_piggyback_raw_data()` instead of
        # `HostSections.piggyback_raw_data` because this allows it to
        # sneakily use cached data.  At minimum, we should group all cache
        # handling performed after the parser.
        for source in get_piggyback_raw_data(origin, time_settings)
    ]:
        return [ActiveCheckResult(src.info.status, src.info.message) for src in sources]

    if expect_data:
        return [ActiveCheckResult(1, "Missing data")]
    return [ActiveCheckResult(0, "Success (but no data found for this host)")]
