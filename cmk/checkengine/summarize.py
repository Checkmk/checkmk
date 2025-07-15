#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import datetime
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol

import cmk.ccc.resulttype as result
from cmk.ccc.exceptions import (
    MKAgentError,
    MKFetcherError,
    MKIPAddressLookupError,
    MKSNMPError,
    MKTimeout,
)
from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils.sectionname import SectionName

from cmk.checkengine.checkresults import ActiveCheckResult
from cmk.checkengine.exitspec import ExitSpec
from cmk.checkengine.fetcher import FetcherType, SourceInfo
from cmk.checkengine.parser import AgentRawDataSection, HostSections

from cmk.piggyback.backend import Config as PiggybackConfig
from cmk.piggyback.backend import PiggybackMetaData, PiggybackTimeSettings

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
            ok=lambda host_sections: summarize_piggyback(
                host_sections=host_sections,
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
    return [ActiveCheckResult(state=0, summary="Success")]


def summarize_failure(exit_spec: ExitSpec, exc: Exception) -> Sequence[ActiveCheckResult]:
    def extract_status(exc: Exception) -> int:
        if isinstance(
            exc,
            MKAgentError | MKFetcherError | MKIPAddressLookupError | MKSNMPError,
        ):
            return exit_spec.get("connection", 2)
        if isinstance(exc, MKTimeout):
            return exit_spec.get("timeout", 2)
        return exit_spec.get("exception", 3)

    return [
        ActiveCheckResult(
            state=extract_status(exc),
            summary=str(exc).rsplit("\n", maxsplit=1)[-1],
            details=str(exc).split("\n") if "\n" in str(exc) else (),
        )
    ]


def summarize_piggyback(
    *,
    host_sections: HostSections[AgentRawDataSection],
    hostname: HostName,
    ipaddress: HostAddress | None,
    time_settings: PiggybackTimeSettings,
    expect_data: bool,
    now: int | None = None,
) -> Sequence[ActiveCheckResult]:
    summary_section = SectionName("piggyback_source_summary")
    config = PiggybackConfig(hostname, time_settings)
    now = int(time.time()) if now is None else now
    if meta_infos := [
        PiggybackMetaData.deserialize(raw_file_info)
        for (raw_file_info,) in host_sections.sections.get(summary_section, [])
    ]:
        return [_summarize_single_piggyback_source(info, config, now) for info in meta_infos]

    if expect_data:
        return [ActiveCheckResult(state=1, summary="Missing data")]
    return [ActiveCheckResult(state=0, summary="Success (but no data found for this host)")]


def _summarize_single_piggyback_source(
    meta: PiggybackMetaData, config: PiggybackConfig, now: float
) -> ActiveCheckResult:
    if (age := now - meta.last_update) > (allowed := config.max_cache_age(meta.source)):
        return ActiveCheckResult(
            state=0,
            summary=f"Piggyback data outdated (age: {_render_time(age)}, allowed: {_render_time(allowed)})",
        )

    if meta.last_contact is None or (meta.last_update < meta.last_contact):
        msg = f"Piggyback data not updated by source '{meta.source}'"
        state = 0  # TODO: can it be 'validity_state' here as well? Why would we go back to ok?
        if (time_left := meta.last_update + config.validity_period(meta.source) - now) > 0:
            msg += f" (still valid, {_render_time(time_left)} left)"
            state = config.validity_state(meta.source)
        return ActiveCheckResult(state=state, summary=msg)

    return ActiveCheckResult(state=0, summary=f"Successfully processed from source '{meta.source}'")


def _render_time(value: float | int) -> str:
    """Format time difference seconds into human readable text

    >>> _render_time(184)
    '0:03:04'

    Unlikely in this context, but still acceptable:
    >>> _render_time(92635.3)
    '1 day, 1:43:55'
    """
    return str(datetime.timedelta(seconds=round(value)))
