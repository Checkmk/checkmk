#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.ibm_mq.agent_based.ibm_mq_managers import (
    check_ibm_mq_managers,
    DEFAULT_PARAMETERS,
    discover_ibm_mq_managers,
    ManagerInfo,
    ManagerParams,
    parse_ibm_mq_managers,
)

pytestmark = pytest.mark.checks

CHECK_NAME = "ibm_mq_managers"


def parse_info(lines: str, separator: str | None = None) -> list[list[str]]:
    result = []
    for line in lines.splitlines():
        line = line.strip()
        result.append(line.split(separator))
    return result


def test_parse() -> None:
    lines = """\
QMNAME(THE.LOCAL.ONE)                                     STATUS(RUNNING) DEFAULT(NO) STANDBY(NOT PERMITTED) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(8.0.0.6) HA() DRROLE()
   INSTANCE(sb112233) MODE(ACTIVE)
QMNAME(THE.MULTI.INSTANCE.ONE)                            STATUS(RUNNING) DEFAULT(NO) STANDBY(PERMITTED) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(8.0.0.6) HA() DRROLE()
   INSTANCE(sb112233) MODE(ACTIVE)
   INSTANCE(sb112255) MODE(STANDBY)
QMNAME(THE.RDQM.ONE)                                      STATUS(RUNNING) DEFAULT(NO) STANDBY(NOT PERMITTED) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(9.1.0.4) HA(REPLICATED) DRROLE()
    INSTANCE(sb008877) MODE(ACTIVE)
QMNAME(THE.SLEEPING.ONE)                                  STATUS(ENDED NORMALLY) DEFAULT(NO) STANDBY(NOT APPLICABLE) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(7.5.0.1) HA() DRROLE()
QMNAME(THE.CRASHED.ONE)                                   STATUS(ENDED UNEXPECTEDLY) DEFAULT(NO) STANDBY(NOT APPLICABLE) INSTNAME(Installation2) INSTPATH(/opt/mqm9) INSTVER(9.0.0.6) HA() DRROLE()
"""
    section = parse_info(lines, chr(10))
    parsed = parse_ibm_mq_managers(section)
    assert len(parsed) == 5

    manager = parsed["THE.LOCAL.ONE"]
    assert manager.attributes["STATUS"] == "RUNNING"
    assert manager.instances == [("sb112233", "ACTIVE")]

    manager = parsed["THE.MULTI.INSTANCE.ONE"]
    assert manager.instances == [("sb112233", "ACTIVE"), ("sb112255", "STANDBY")]

    manager = parsed["THE.CRASHED.ONE"]
    assert manager.attributes["QMNAME"] == "THE.CRASHED.ONE"
    assert manager.attributes["STATUS"] == "ENDED UNEXPECTEDLY"
    assert manager.attributes["STANDBY"] == "NOT APPLICABLE"
    assert manager.instances == []


def test_check_single_instance_running() -> None:
    lines = """\
QMNAME(THE.LOCAL.ONE)                                     STATUS(RUNNING) DEFAULT(NO) STANDBY(NOT PERMITTED) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(8.0.0.6)
   INSTANCE(sb112233) MODE(ACTIVE)
"""
    section = parse_info(lines, chr(10))
    parsed = parse_ibm_mq_managers(section)

    attrs = parsed["THE.LOCAL.ONE"].attributes
    assert attrs["QMNAME"] == "THE.LOCAL.ONE"
    assert attrs["STATUS"] == "RUNNING"

    params = DEFAULT_PARAMETERS
    actual = list(check_ibm_mq_managers("THE.LOCAL.ONE", params, parsed))
    expected = [
        Result(state=State.OK, summary="Status: RUNNING"),
        Result(state=State.OK, summary="Version: 8.0.0.6"),
        Result(state=State.OK, summary="Installation: /opt/mqm (Installation1), Default: NO"),
        Result(state=State.OK, summary="Single-Instance: sb112233=ACTIVE"),
    ]
    assert expected == actual


def test_rdqm() -> None:
    lines = """\
QMNAME(THE.RDQM.ONE)                                      STATUS(RUNNING) DEFAULT(NO) STANDBY(NOT PERMITTED) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(9.1.0.4) HA(REPLICATED) DRROLE()
    INSTANCE(sb008877) MODE(ACTIVE)
QMNAME(THE.STANDBY.RDQM)                                  STATUS(RUNNING ELSEWHERE) DEFAULT(NO) STANDBY(NOT APPLICABLE) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(9.2.0.0) HA(REPLICATED) DRROLE()
"""
    section = parse_info(lines, chr(10))
    parsed = parse_ibm_mq_managers(section)

    attrs = parsed["THE.RDQM.ONE"].attributes
    assert attrs["QMNAME"] == "THE.RDQM.ONE"
    assert attrs["STATUS"] == "RUNNING"

    params = DEFAULT_PARAMETERS
    actual = list(check_ibm_mq_managers("THE.RDQM.ONE", params, parsed))
    expected = [
        Result(state=State.OK, summary="Status: RUNNING"),
        Result(state=State.OK, summary="Version: 9.1.0.4"),
        Result(state=State.OK, summary="Installation: /opt/mqm (Installation1), Default: NO"),
        Result(state=State.OK, summary="High availability: replicated, Instance: sb008877"),
    ]
    assert expected == actual


def test_ended_preemtively() -> None:
    lines = """\
QMNAME(THE.ENDED.ONE)                                     STATUS(ENDED PREEMPTIVELY) DEFAULT(NO) STANDBY(NOT APPLICABLE) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(7.5.0.2)
"""
    section = parse_info(lines, chr(10))
    parsed = parse_ibm_mq_managers(section)

    params = DEFAULT_PARAMETERS
    actual = list(check_ibm_mq_managers("THE.ENDED.ONE", params, parsed))
    expected = [
        Result(state=State.WARN, summary="Status: ENDED PREEMPTIVELY"),
        Result(state=State.OK, summary="Version: 7.5.0.2"),
        Result(state=State.OK, summary="Installation: /opt/mqm (Installation1), Default: NO"),
    ]
    assert expected == actual

    lines = """\
QMNAME(THE.ENDED.ONE)                                     STATUS(ENDED PRE-EMPTIVELY) DEFAULT(NO) STANDBY(NOT APPLICABLE) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(8.0.0.1)
"""
    section = parse_info(lines, chr(10))
    parsed = parse_ibm_mq_managers(section)

    actual = list(check_ibm_mq_managers("THE.ENDED.ONE", params, parsed))
    expected = [
        Result(state=State.WARN, summary="Status: ENDED PRE-EMPTIVELY"),
        Result(state=State.OK, summary="Version: 8.0.0.1"),
        Result(state=State.OK, summary="Installation: /opt/mqm (Installation1), Default: NO"),
    ]
    assert expected == actual


_PRE_EMPTIVELY_ENDED_MANAGER = """\
QMNAME(THE.ENDED.ONE)                                     STATUS(ENDED PRE-EMPTIVELY) DEFAULT(NO) STANDBY(NOT APPLICABLE) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(7.5.0.2)
"""


def test_configured_state_overrides_the_factory_default() -> None:
    parsed = parse_ibm_mq_managers(parse_info(_PRE_EMPTIVELY_ENDED_MANAGER, chr(10)))
    params: ManagerParams = {**DEFAULT_PARAMETERS, "mapped_states": {"ended_pre_emptively": 2}}

    actual = list(check_ibm_mq_managers("THE.ENDED.ONE", params, parsed))

    assert actual[0] == Result(state=State.CRIT, summary="Status: ENDED PRE-EMPTIVELY")


def test_states_the_rule_leaves_out_keep_their_factory_default() -> None:
    parsed = parse_ibm_mq_managers(parse_info(_PRE_EMPTIVELY_ENDED_MANAGER, chr(10)))
    params: ManagerParams = {**DEFAULT_PARAMETERS, "mapped_states": {"running_as_standby": 2}}

    actual = list(check_ibm_mq_managers("THE.ENDED.ONE", params, parsed))

    assert actual[0] == Result(state=State.WARN, summary="Status: ENDED PRE-EMPTIVELY")


def test_unknown_status_gets_the_configured_state() -> None:
    lines = """\
QMNAME(THE.ODD.ONE)                                       STATUS(SOMETHING NEW) DEFAULT(NO) STANDBY(NOT APPLICABLE) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(9.4.0.0)
"""
    parsed = parse_ibm_mq_managers(parse_info(lines, chr(10)))

    params: ManagerParams = {**DEFAULT_PARAMETERS, "mapped_states_default": 1}

    actual = list(check_ibm_mq_managers("THE.ODD.ONE", params, parsed))

    assert actual[0] == Result(state=State.WARN, summary="Status: SOMETHING NEW")


def test_version_mismatch() -> None:
    lines = """\
QMNAME(THE.RUNNING.ONE)                                   STATUS(RUNNING) DEFAULT(NO) STANDBY(NOT APPLICABLE) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(7.5.0.2)
"""
    section = parse_info(lines, chr(10))
    parsed = parse_ibm_mq_managers(section)

    params: ManagerParams = {
        **DEFAULT_PARAMETERS,
        "version": ("at_least", {"version": "8.0", "state": 2}),
    }
    actual = list(check_ibm_mq_managers("THE.RUNNING.ONE", params, parsed))
    expected = [
        Result(state=State.OK, summary="Status: RUNNING"),
        Result(state=State.CRIT, summary="Version: 7.5.0.2 (should be at least 8.0)"),
        Result(state=State.OK, summary="Installation: /opt/mqm (Installation1), Default: NO"),
    ]
    assert expected == actual


def test_discovery() -> None:
    parsed = {
        "QM1": ManagerInfo(attributes={"STATUS": "RUNNING"}, instances=[]),
        "QM2": ManagerInfo(attributes={"STATUS": "ENDED NORMALLY"}, instances=[]),
    }
    discovery = list(discover_ibm_mq_managers(parsed))
    assert len(discovery) == 2
    assert Service(item="QM1") in discovery
    assert Service(item="QM2") in discovery
