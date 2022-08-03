#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

import pytest

from tests.testlib import on_time

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

_STRING_TABLE = [
    [
        '{"set":"rs0","date":{"$date":"2022-08-01T10:28:53.784Z"},"myState":1,"term":1628,"heartbeatIntervalMillis":2000,"optimes":{"lastCommittedOpTime":{"ts":{"$timestamp":{"t":1659349733,"i":6}},"t":1628},"readConcernMajorityOpTime":{"ts":{"$timestamp":{"t":1659349733,"i":6}},"t":1628},"appliedOpTime":{"ts":{"$timestamp":{"t":1659349733,"i":6}},"t":1628},"durableOpTime":{"ts":{"$timestamp":{"t":1659349733,"i":6}},"t":1628}},"members":[{"_id":0,"name":"mvgenmongodb01:27017","health":1.0,"state":1,"stateStr":"PRIMARY","uptime":33527,"optime":{"ts":{"$timestamp":{"t":1659349733,"i":6}},"t":1628},"optimeDate":{"$date":"2022-08-01T10:28:53Z"},"electionTime":{"$timestamp":{"t":1659317412,"i":1}},"electionDate":{"$date":"2022-08-01T01:30:12Z"},"configVersion":3,"self":true},{"_id":1,"name":"mvgenmongodb02:27017","health":1.0,"state":2,"stateStr":"SECONDARY","uptime":32920,"optime":{"ts":{"$timestamp":{"t":1659349732,"i":1}},"t":1628},"optimeDurable":{"ts":{"$timestamp":{"t":1659349732,"i":1}},"t":1628},"optimeDate":{"$date":"2022-08-01T10:28:52Z"},"optimeDurableDate":{"$date":"2022-08-01T10:28:52Z"},"lastHeartbeat":{"$date":"2022-08-01T10:28:52.699Z"},"lastHeartbeatRecv":{"$date":"2022-08-01T10:28:52.932Z"},"pingMs":0,"syncingTo":"mvgenmongodb03:27017","configVersion":3},{"_id":2,"name":"mvgenmongodb03:27017","health":1.0,"state":2,"stateStr":"SECONDARY","uptime":32325,"optime":{"ts":{"$timestamp":{"t":1659349733,"i":1}},"t":1628},"optimeDurable":{"ts":{"$timestamp":{"t":1659349733,"i":1}},"t":1628},"optimeDate":{"$date":"2022-08-01T10:28:53Z"},"optimeDurableDate":{"$date":"2022-08-01T10:28:53Z"},"lastHeartbeat":{"$date":"2022-08-01T10:28:53.405Z"},"lastHeartbeatRecv":{"$date":"2022-08-01T10:28:53.404Z"},"pingMs":0,"syncingTo":"mvgenmongodb01:27017","configVersion":3}],"ok":1.0,"operationTime":{"$timestamp":{"t":1659349733,"i":6}},"$clusterTime":{"clusterTime":{"$timestamp":{"t":1659349733,"i":6}},"signature":{"hash":{"$binary":{"base64":"AAAAAAAAAAAAAAAAAAAAAAAAAAA=","subType":"00"}},"keyId":0}}}'
    ]
]


@pytest.fixture(name="check_plugin", scope="module")
def check_plugin_fixutre(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("mongodb_replica_set")]


@pytest.fixture(name="section", scope="module")
def section_fixture(fix_register: FixRegister) -> Mapping[str, Any]:
    return fix_register.agent_sections[SectionName("mongodb_replica_set")].parse_function(
        _STRING_TABLE
    )


def test_discover_mongodb_replica_set(
    check_plugin: CheckPlugin,
    section: Mapping[str, Any],
) -> None:
    assert list(check_plugin.discovery_function(section)) == [Service()]


def test_check_mongodb_replica_set(
    check_plugin: CheckPlugin,
    section: Mapping[str, Any],
) -> None:
    with on_time(1659514516, "UTC"):
        assert list(
            check_plugin.check_function(
                item="genesys.cardsv2",
                params=check_plugin.check_default_parameters,
                section=section,
            )
        ) == [
            Result(
                state=State.OK,
                summary="6 additional details available",
                details="source: mvgenmongodb02:27017\nsyncedTo: 1970-01-20 04:55:49 (UTC)\nmember (mvgenmongodb02:27017) is 0s (0h) behind primary (mvgenmongodb01:27017)\nsource: mvgenmongodb03:27017\nsyncedTo: 1970-01-20 04:55:49 (UTC)\nmember (mvgenmongodb03:27017) is 0s (0h) behind primary (mvgenmongodb01:27017)",
            )
        ]
