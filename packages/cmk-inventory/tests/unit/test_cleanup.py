#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.inventory.cleanup import filter_inventory_cleanup_parameters, matches
from cmk.inventory.config import (
    InvCleanupParams,
    InvCleanupParamsCombined,
    InvCleanupParamsDefaultCombined,
    InvCleanupParamsOfHosts,
)


def test_matches_the_host_name() -> None:
    assert matches(regex_or_name="hostname", host_name=HostName("hostname"))


def test_does_not_match_another_host_name() -> None:
    assert not matches(regex_or_name="hostname", host_name=HostName("other-hostname"))


def test_matches_a_regex() -> None:
    assert matches(regex_or_name="~host.*", host_name=HostName("hostname"))


def test_matches_a_regex_that_covers_the_beginning() -> None:
    assert matches(regex_or_name="~host", host_name=HostName("hostname"))


def test_does_not_match_a_regex_that_covers_the_end() -> None:
    assert not matches(regex_or_name="~name", host_name=HostName("hostname"))


def _cleanup_parameters(*regexes_or_explicits: Sequence[str]) -> InvCleanupParams:
    return InvCleanupParams(
        for_hosts=[
            InvCleanupParamsOfHosts(
                regex_or_explicit=regex_or_explicit,
                parameters=(
                    "combined",
                    InvCleanupParamsCombined(
                        strategy="and", file_age=1, number_of_history_entries=2
                    ),
                ),
            )
            for regex_or_explicit in regexes_or_explicits
        ],
        default=InvCleanupParamsDefaultCombined(
            strategy="and", file_age=123, number_of_history_entries=456
        ),
        abandoned_file_age=100,
    )


@pytest.mark.parametrize(
    "cleanup_parameters, host_names, expected",
    [
        pytest.param(_cleanup_parameters(), [], _cleanup_parameters(), id="no-hosts-at-all"),
        pytest.param(
            _cleanup_parameters(["hostname"]), [], _cleanup_parameters(), id="no-hosts-of-site"
        ),
        pytest.param(
            _cleanup_parameters(),
            [HostName("hostname")],
            _cleanup_parameters(),
            id="no-parameters-of-hosts",
        ),
        pytest.param(
            _cleanup_parameters(["hostname1"]),
            [HostName("hostname2")],
            _cleanup_parameters(),
            id="no-match",
        ),
        pytest.param(
            _cleanup_parameters(["hostname"]),
            [HostName("hostname")],
            _cleanup_parameters(["hostname"]),
            id="match",
        ),
        pytest.param(
            _cleanup_parameters(["~h", "~g", "hostname"]),
            [HostName("hostname")],
            _cleanup_parameters(["~h", "hostname"]),
            id="regex-match",
        ),
        pytest.param(
            _cleanup_parameters(["~g"]),
            [HostName("hostname")],
            _cleanup_parameters(),
            id="no-regex-match",
        ),
    ],
)
def test_filter_inventory_cleanup_parameters_keeps_the_matching_hosts(
    cleanup_parameters: InvCleanupParams,
    host_names: Sequence[HostName],
    expected: InvCleanupParams,
) -> None:
    assert (
        filter_inventory_cleanup_parameters(
            cleanup_parameters=cleanup_parameters,
            host_names=host_names,
        )
        == expected
    )
