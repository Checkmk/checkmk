#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


import datetime
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

import cmk.ccc.resulttype as result
from cmk.ccc.exceptions import (
    MKIPAddressLookupError,
    MKTimeout,
)
from cmk.checkengine.fetcher_abc import FetcherError
from cmk.checkengine.helper_interface import FetcherType, SourceInfo
from cmk.checkengine.parser import AgentRawDataSection, HostSections
from cmk.checkengine.plugins import SectionName
from cmk.checkengine.specs.checkresults import ActiveCheckResult
from cmk.checkengine.specs.exitspec import ExitSpec
from cmk.piggyback.backend import Config as PiggybackConfig
from cmk.piggyback.backend import PiggybackMetaData
from cmk.server_side_programs.v1 import AgentMessages

__all__ = ["summarize", "SummarizerFunction", "SummaryConfig"]


@dataclass(frozen=True)
class SummaryConfig:
    """User config for summary."""

    exit_spec: ExitSpec
    piggyback_config: PiggybackConfig
    expect_data: bool


class SummarizerFunction(Protocol):
    def __call__(
        self,
        host_sections: Iterable[tuple[SourceInfo, result.Result[HostSections, Exception]]],
    ) -> Iterable[ActiveCheckResult]: ...


def summarize(
    host_sections: result.Result[HostSections, Exception],
    config: SummaryConfig,
    *,
    fetcher_type: FetcherType,
) -> Sequence[ActiveCheckResult]:
    if fetcher_type is FetcherType.PIGGYBACK:
        return host_sections.fold(
            ok=lambda host_sections: summarize_piggyback(
                host_sections=host_sections,
                config=config.piggyback_config,
                expect_data=config.expect_data,
            ),
            error=lambda exc: summarize_failure(config.exit_spec, exc),
        )

    return host_sections.fold(
        ok=lambda host_sections: summarize_success(host_sections, config.exit_spec),
        error=lambda exc: summarize_failure(config.exit_spec, exc),
    )


def summarize_success(
    host_sections: HostSections[AgentRawDataSection],
    exit_spec: ExitSpec,
) -> Sequence[ActiveCheckResult]:
    """Report the messages a special agent embedded in its output

    Infos are always OK, warnings get the configured state.

    Note that the messages section is subject to section selection like any other
    section, so the messages are not shown if only specific sections are fetched.
    """
    warning_state = exit_spec.get("warnings", 1)
    return [
        # even if the fetcher messages start with a warning, indicate that we did not _fail_:
        ActiveCheckResult(state=0, summary="Success"),
        *(
            _message_result(level, message, warning_state)
            for level, message in AgentMessages.from_string_table(
                host_sections.sections.get(SectionName(AgentMessages.SECTION_NAME), [])
            )
        ),
    ]


def _message_result(
    level: Literal["info", "warning"], message: str, warning_state: int
) -> ActiveCheckResult:
    text = message or f"Unspecified {level}"
    state = 3  # otherwise mypy complains
    match level:
        case "info":
            state = 0
        case "warning":
            state = warning_state
    return ActiveCheckResult(
        state=state,
        summary=text.partition("\n")[0],
        details=text.splitlines() if "\n" in text else (),
    )


def summarize_failure(exit_spec: ExitSpec, exc: Exception) -> Sequence[ActiveCheckResult]:
    def extract_status(exc: Exception) -> int:
        if isinstance(exc, FetcherError | MKIPAddressLookupError):
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
    config: PiggybackConfig,
    expect_data: bool,
    now: int | None = None,
) -> Sequence[ActiveCheckResult]:
    summary_section = SectionName("piggyback_source_summary")
    now = int(time.time()) if now is None else now
    # Note: this can raise, but only if someone fiddled with the data
    if meta_infos := [
        PiggybackMetaData.deserialize(raw_file_info)
        for (raw_file_info,) in host_sections.sections.get(summary_section, [])
    ]:
        results = [_summarize_single_piggyback_source(info, config, now) for info in meta_infos]
        if expect_data and all(
            meta.is_outdated(now, config.max_cache_age(meta.source)) for meta in meta_infos
        ):
            results.append(
                ActiveCheckResult(state=1, summary="All piggyback data sources outdated.")
            )
        return results

    if expect_data:
        return [ActiveCheckResult(state=1, summary="Missing data")]
    return [ActiveCheckResult(state=0, summary="Success (but no data found for this host)")]


def _summarize_single_piggyback_source(
    meta: PiggybackMetaData,
    config: PiggybackConfig,
    now: int,
) -> ActiveCheckResult:
    allowed = config.max_cache_age(meta.source)
    if meta.is_outdated(now=now, max_age=allowed):
        return ActiveCheckResult(
            state=0,
            summary=f"Piggyback data outdated (age: {_render_time(now - meta.last_update)}, allowed: {_render_time(allowed)})",
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
