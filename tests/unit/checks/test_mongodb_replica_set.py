#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.utils.sectionname import SectionName

from cmk.checkengine.plugins import AgentBasedPlugins, CheckPlugin, CheckPluginName

from cmk.agent_based.v2 import Result, Service, State

_STRING_TABLE = [
    [
        '{"set":"rs0","date":{"$date":"2022-08-01T10:28:53.784Z"},"myState":1,"term":1628,"heartbeatIntervalMillis":200'
        '0,"optimes":{"lastCommittedOpTime":{"ts":{"$timestamp":{"t":1659349733,"i":6}},"t":1628},"readConcernMajorityO'
        'pTime":{"ts":{"$timestamp":{"t":1659349733,"i":6}},"t":1628},"appliedOpTime":{"ts":{"$timestamp":{"t":16593497'
        '33,"i":6}},"t":1628},"durableOpTime":{"ts":{"$timestamp":{"t":1659349733,"i":6}},"t":1628}},"members":[{"_id":'
        '0,"name":"mvgenmongodb01:27017","health":1.0,"state":1,"stateStr":"PRIMARY","uptime":33527,"optime":{"ts":{"$t'
        'imestamp":{"t":1659349733,"i":6}},"t":1628},"optimeDate":{"$date":"2022-08-01T10:28:53Z"},"electionTime":{"$ti'
        'mestamp":{"t":1659317412,"i":1}},"electionDate":{"$date":"2022-08-01T01:30:12Z"},"configVersion":3,"self":true'
        '},{"_id":1,"name":"mvgenmongodb02:27017","health":1.0,"state":2,"stateStr":"SECONDARY","uptime":32920,"optime"'
        ':{"ts":{"$timestamp":{"t":1659349732,"i":1}},"t":1628},"optimeDurable":{"ts":{"$timestamp":{"t":1659349732,"i"'
        ':1}},"t":1628},"optimeDate":{"$date":"2022-08-01T10:28:52Z"},"optimeDurableDate":{"$date":"2022-08-01T10:28:52'
        'Z"},"lastHeartbeat":{"$date":"2022-08-01T10:28:52.699Z"},"lastHeartbeatRecv":{"$date":"2022-08-01T10:28:52.932'
        'Z"},"pingMs":0,"syncingTo":"mvgenmongodb03:27017","configVersion":3},{"_id":2,"name":"mvgenmongodb03:27017","h'
        'ealth":1.0,"state":2,"stateStr":"SECONDARY","uptime":32325,"optime":{"ts":{"$timestamp":{"t":1659349733,"i":1}'
        '},"t":1628},"optimeDurable":{"ts":{"$timestamp":{"t":1659349733,"i":1}},"t":1628},"optimeDate":{"$date":"2022-'
        '08-01T10:28:53Z"},"optimeDurableDate":{"$date":"2022-08-01T10:28:53Z"},"lastHeartbeat":{"$date":"2022-08-01T10'
        ':28:53.405Z"},"lastHeartbeatRecv":{"$date":"2022-08-01T10:28:53.404Z"},"pingMs":0,"syncingTo":"mvgenmongodb01:'
        '27017","configVersion":3}],"ok":1.0,"operationTime":{"$timestamp":{"t":1659349733,"i":6}},"$clusterTime":{"clu'
        'sterTime":{"$timestamp":{"t":1659349733,"i":6}},"signature":{"hash":{"$binary":{"base64":"AAAAAAAAAAAAAAAAAAAA'
        'AAAAAAA=","subType":"00"}},"keyId":0}}}'
    ]
]

# SUP-18566
_STRING_TABLE_PYMONGO_3 = [
    [
        '{"set":"11111111111111","date":{"$date":1715604069990},"myState":1,"term":48,"syncSourceHost":"","syncSourceId'
        '":-1,"heartbeatIntervalMillis":2000,"majorityVoteCount":2,"writeMajorityCount":2,"votingMembersCount":3,"writa'
        'bleVotingMembersCount":3,"optimes":{"lastCommittedOpTime":{"ts":{"$timestamp":{"t":1715604069,"i":4}},"t":48},'
        '"lastCommittedWallTime":{"$date":1715604069930},"readConcernMajorityOpTime":{"ts":{"$timestamp":{"t":171560406'
        '9,"i":4}},"t":48},"appliedOpTime":{"ts":{"$timestamp":{"t":1715604069,"i":4}},"t":48},"durableOpTime":{"ts":{"'
        '$timestamp":{"t":1715604069,"i":4}},"t":48},"lastAppliedWallTime":{"$date":1715604069930},"lastDurableWallTime'
        '":{"$date":1715604069930}},"lastStableRecoveryTimestamp":{"$timestamp":{"t":1715604063,"i":11}},"electionCandi'
        'dateMetrics":{"lastElectionReason":"priorityTakeover","lastElectionDate":{"$date":1712317712551},"electionTerm'
        '":48,"lastCommittedOpTimeAtElection":{"ts":{"$timestamp":{"t":1712317709,"i":1}},"t":47},"lastSeenOpTimeAtElec'
        'tion":{"ts":{"$timestamp":{"t":1712317709,"i":1}},"t":47},"numVotesNeeded":2,"priorityAtElection":3.0,"electio'
        'nTimeoutMillis":10000,"priorPrimaryMemberId":1,"numCatchUpOps":0,"newTermStartDate":{"$date":1712317712566},"w'
        'MajorityWriteAvailabilityDate":{"$date":1712317713569}},"members":[{"_id":0,"name":"aaaaaaaaaaaaaaaaaaaaaa.aaa'
        'aaa:27017","health":1.0,"state":1,"stateStr":"PRIMARY","uptime":3286401,"optime":{"ts":{"$timestamp":{"t":1715'
        '604069,"i":4}},"t":48},"optimeDate":{"$date":1715604069000},"lastAppliedWallTime":{"$date":1715604069930},"las'
        'tDurableWallTime":{"$date":1715604069930},"syncSourceHost":"","syncSourceId":-1,"infoMessage":"","electionTime'
        '":{"$timestamp":{"t":1712317712,"i":1}},"electionDate":{"$date":1712317712000},"configVersion":9,"configTerm":'
        '48,"self":true,"lastHeartbeatMessage":""},{"_id":1,"name":"bbbbbbbbbbbbbbbbbbbbbb.bbbbbb:27017","health":1.0,"'
        'state":2,"stateStr":"SECONDARY","uptime":3286392,"optime":{"ts":{"$timestamp":{"t":1715604067,"i":3}},"t":48},'
        '"optimeDurable":{"ts":{"$timestamp":{"t":1715604067,"i":3}},"t":48},"optimeDate":{"$date":1715604067000},"opti'
        'meDurableDate":{"$date":1715604067000},"lastAppliedWallTime":{"$date":1715604069930},"lastDurableWallTime":{"$'
        'date":1715604069930},"lastHeartbeat":{"$date":1715604068223},"lastHeartbeatRecv":{"$date":1715604068366},"ping'
        'Ms":0,"lastHeartbeatMessage":"","syncSourceHost":"aaaaaaaaaaaaaaaaaaaaaa.aaaaaa:27017","syncSourceId":0,"infoM'
        'essage":"","configVersion":9,"configTerm":48},{"_id":3,"name":"cccccccccccccccccccccc.cccccc:27017","health":1'
        '.0,"state":2,"stateStr":"SECONDARY","uptime":3286392,"optime":{"ts":{"$timestamp":{"t":1715604067,"i":3}},"t":'
        '48},"optimeDurable":{"ts":{"$timestamp":{"t":1715604067,"i":3}},"t":48},"optimeDate":{"$date":1715604067000},"'
        'optimeDurableDate":{"$date":1715604067000},"lastAppliedWallTime":{"$date":1715604069930},"lastDurableWallTime"'
        ':{"$date":1715604069930},"lastHeartbeat":{"$date":1715604068412},"lastHeartbeatRecv":{"$date":1715604068484},"'
        'pingMs":0,"lastHeartbeatMessage":"","syncSourceHost":"aaaaaaaaaaaaaaaaaaaaaa.aaaaaa:27017","syncSourceId":0,"i'
        'nfoMessage":"","configVersion":9,"configTerm":48}],"ok":1.0,"$clusterTime":{"clusterTime":{"$timestamp":{"t":1'
        '715604069,"i":4}},"signature":{"hash":{"$binary":"AAAAAAAAAAAAAAAAAAAAAAAAAAA=","$type":"00"},"keyId":0}},"ope'
        'rationTime":{"$timestamp":{"t":1715604069,"i":4}}}'
    ]
]


@pytest.fixture(name="check_plugin", scope="module")
def check_plugin_fixture(agent_based_plugins: AgentBasedPlugins) -> CheckPlugin:
    return agent_based_plugins.check_plugins[CheckPluginName("mongodb_replica_set")]


def test_discover_mongodb_replica_set(
    check_plugin: CheckPlugin,
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    section = agent_based_plugins.agent_sections[SectionName("mongodb_replica_set")].parse_function(
        _STRING_TABLE
    )
    assert list(check_plugin.discovery_function(section)) == [Service()]


@pytest.mark.parametrize(
    ["string_table", "expected_result"],
    [
        [
            _STRING_TABLE,
            [
                Result(
                    state=State.OK,
                    summary="6 additional details available",
                    details="\n".join(
                        (
                            "source: mvgenmongodb02:27017",
                            "syncedTo: 2022-08-01 10:28:52 (UTC)",
                            "member (mvgenmongodb02:27017) is 1s (0h) behind primary (mvgenmongodb01:27017)",
                            "source: mvgenmongodb03:27017",
                            "syncedTo: 2022-08-01 10:28:53 (UTC)",
                            "member (mvgenmongodb03:27017) is 0s (0h) behind primary (mvgenmongodb01:27017)",
                        )
                    ),
                )
            ],
        ],
        [
            _STRING_TABLE_PYMONGO_3,
            [
                Result(
                    state=State.OK,
                    summary="6 additional details available",
                    details="\n".join(
                        (
                            "source: bbbbbbbbbbbbbbbbbbbbbb.bbbbbb:27017",
                            "syncedTo: 2024-05-13 12:41:07 (UTC)",
                            "member (bbbbbbbbbbbbbbbbbbbbbb.bbbbbb:27017) is 2s (0h) behind primary (aaaaaaaaaaaaaaaaaaaaaa.aaaaaa:27017)",
                            "source: cccccccccccccccccccccc.cccccc:27017",
                            "syncedTo: 2024-05-13 12:41:07 (UTC)",
                            "member (cccccccccccccccccccccc.cccccc:27017) is 2s (0h) behind primary (aaaaaaaaaaaaaaaaaaaaaa.aaaaaa:27017)",
                        )
                    ),
                ),
            ],
        ],
    ],
)
@pytest.mark.usefixtures("initialised_item_state")
def test_check_mongodb_replica_set(
    check_plugin: CheckPlugin,
    agent_based_plugins: AgentBasedPlugins,
    string_table: list[list[str]],
    expected_result: list[Result],
) -> None:
    section = agent_based_plugins.agent_sections[SectionName("mongodb_replica_set")].parse_function(
        string_table
    )
    with time_machine.travel(datetime.datetime.fromtimestamp(1659514516, tz=ZoneInfo("UTC"))):
        assert (
            list(
                check_plugin.check_function(
                    params=check_plugin.check_default_parameters,
                    section=section,
                )
            )
            == expected_result
        )
