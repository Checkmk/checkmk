#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import itertools
from collections.abc import Sequence
from typing import Final

from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.exceptions import (
    MKAgentError,
    MKEmptyAgentData,
    MKFetcherError,
    MKIPAddressLookupError,
    MKSNMPError,
    MKTimeout,
)
from cmk.utils.piggyback import get_piggyback_raw_data, PiggybackRawDataInfo, PiggybackTimeSettings
from cmk.utils.type_defs import ExitSpec, HostAddress, HostName, result

from cmk.core_helpers.host_sections import HostSections
from cmk.core_helpers.type_defs import FetcherType

__all__ = ["summarize"]


def summarize(
    hostname: HostName,
    ipaddress: HostAddress | None,
    host_sections: result.Result[HostSections, Exception],
    *,
    exit_spec: ExitSpec,
    time_settings: PiggybackTimeSettings,
    # TODO(ml): Check if the next two parameters are redundant.
    fetcher_type: FetcherType,
    is_piggyback: bool,
) -> Sequence[ActiveCheckResult]:
    if fetcher_type is FetcherType.PIGGYBACK:
        return host_sections.fold(
            ok=lambda _: summarize_piggyback(
                hostname=hostname,
                ipaddress=ipaddress,
                time_settings=time_settings,
                is_piggyback=is_piggyback,
            ),
            error=lambda exc: summarize_failure(exit_spec, exc),
        )

    return host_sections.fold(
        ok=lambda _: summarize_success(exit_spec),
        error=lambda exc: summarize_failure(exit_spec, exc),
    )


def summarize_success(exit_spec: ExitSpec) -> Sequence[ActiveCheckResult]:
    return [ActiveCheckResult(0, "Success")]


def summarize_failure(exit_spec: ExitSpec, exc: Exception) -> Sequence[ActiveCheckResult]:
    def extract_status(exc: Exception) -> int:
        if isinstance(exc, MKEmptyAgentData):
            return exit_spec.get("empty_output", 2)
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
            str(exc).split("\n") if str(exc) else (),
        )
    ]


def summarize_piggyback(
    *,
    hostname: HostName,
    ipaddress: HostAddress | None,
    time_settings: PiggybackTimeSettings,
    # Tag: 'Always use and expect piggback data'
    is_piggyback: bool,
) -> Sequence[ActiveCheckResult]:
    sources: Final[Sequence[PiggybackRawDataInfo]] = list(
        itertools.chain.from_iterable(
            # TODO(ml): The code uses `get_piggyback_raw_data()` instead of
            # `HostSections.piggyback_raw_data` because this allows it to
            # sneakily use cached data.  At minimum, we should group all cache
            # handling performed after the parser.
            get_piggyback_raw_data(origin, time_settings)
            for origin in (hostname, ipaddress)
        )
    )
    if not sources:
        if is_piggyback:
            return [ActiveCheckResult(1, "Missing data")]
        return []
    return [
        ActiveCheckResult(src.info.status, src.info.message) for src in sources if src.info.message
    ]
