#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.inventory.config import (
    filter_inventory_housekeeping_parameters,
    InvHousekeepingParams,
    InvHousekeepingParamsFallback,
    InvHousekeepingParamsOfHosts,
)


@pytest.mark.parametrize(
    "parameters, hosts_of_site, expected",
    [
        pytest.param(
            InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(
                    file_age=123,
                    number_of_history_entries=456,
                ),
            ),
            [],
            InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(
                    file_age=123,
                    number_of_history_entries=456,
                ),
            ),
            id="no-of-hosts-and-no-hosts-of-site",
        ),
        pytest.param(
            InvHousekeepingParams(
                of_hosts=[
                    InvHousekeepingParamsOfHosts(
                        regexes_or_names=["hostname"],
                        file_age=1,
                        number_of_history_entries=2,
                    )
                ],
                fallback=InvHousekeepingParamsFallback(
                    file_age=123,
                    number_of_history_entries=456,
                ),
            ),
            [],
            InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(
                    file_age=123,
                    number_of_history_entries=456,
                ),
            ),
            id="of-hosts-and-no-hosts-of-site",
        ),
        pytest.param(
            InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(
                    file_age=123,
                    number_of_history_entries=456,
                ),
            ),
            [HostName("hostname")],
            InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(
                    file_age=123,
                    number_of_history_entries=456,
                ),
            ),
            id="no-of-hosts-and-hosts-of-site",
        ),
        pytest.param(
            InvHousekeepingParams(
                of_hosts=[
                    InvHousekeepingParamsOfHosts(
                        regexes_or_names=["hostname1"],
                        file_age=1,
                        number_of_history_entries=2,
                    )
                ],
                fallback=InvHousekeepingParamsFallback(
                    file_age=123,
                    number_of_history_entries=456,
                ),
            ),
            [HostName("hostname2")],
            InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(
                    file_age=123,
                    number_of_history_entries=456,
                ),
            ),
            id="of-hosts-and-hosts-of-site-and-no-match",
        ),
        pytest.param(
            InvHousekeepingParams(
                of_hosts=[
                    InvHousekeepingParamsOfHosts(
                        regexes_or_names=["hostname"],
                        file_age=1,
                        number_of_history_entries=2,
                    )
                ],
                fallback=InvHousekeepingParamsFallback(
                    file_age=123,
                    number_of_history_entries=456,
                ),
            ),
            [HostName("hostname")],
            InvHousekeepingParams(
                of_hosts=[
                    InvHousekeepingParamsOfHosts(
                        regexes_or_names=["hostname"],
                        file_age=1,
                        number_of_history_entries=2,
                    )
                ],
                fallback=InvHousekeepingParamsFallback(
                    file_age=123,
                    number_of_history_entries=456,
                ),
            ),
            id="of-hosts-and-hosts-of-site-and-match",
        ),
        pytest.param(
            InvHousekeepingParams(
                of_hosts=[
                    InvHousekeepingParamsOfHosts(
                        regexes_or_names=["~h", "~g", "hostname"],
                        file_age=1,
                        number_of_history_entries=2,
                    )
                ],
                fallback=InvHousekeepingParamsFallback(
                    file_age=123,
                    number_of_history_entries=456,
                ),
            ),
            [HostName("hostname")],
            InvHousekeepingParams(
                of_hosts=[
                    InvHousekeepingParamsOfHosts(
                        regexes_or_names=["~h", "hostname"],
                        file_age=1,
                        number_of_history_entries=2,
                    )
                ],
                fallback=InvHousekeepingParamsFallback(
                    file_age=123,
                    number_of_history_entries=456,
                ),
            ),
            id="regex-match",
        ),
        pytest.param(
            InvHousekeepingParams(
                of_hosts=[
                    InvHousekeepingParamsOfHosts(
                        regexes_or_names=["~g"],
                        file_age=1,
                        number_of_history_entries=2,
                    )
                ],
                fallback=InvHousekeepingParamsFallback(
                    file_age=123,
                    number_of_history_entries=456,
                ),
            ),
            [HostName("hostname")],
            InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(
                    file_age=123,
                    number_of_history_entries=456,
                ),
            ),
            id="no-regex-match",
        ),
    ],
)
def test_filter_inventory_housekeeping_parameters(
    parameters: InvHousekeepingParams,
    hosts_of_site: Sequence[HostName],
    expected: InvHousekeepingParams,
) -> None:
    assert (
        filter_inventory_housekeeping_parameters(
            parameters=parameters,
            host_names=hosts_of_site,
        )
        == expected
    )
