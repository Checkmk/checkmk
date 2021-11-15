#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict

import pytest

from tests.testlib import Check

from cmk.base.check_api import MKCounterWrapped  # noqa: F401 # pylint: disable=unused-import
from cmk.base.plugins.agent_based.ibm_mq_managers import parse_ibm_mq_managers

from .test_ibm_mq_include import parse_info

pytestmark = pytest.mark.checks

CHECK_NAME = "ibm_mq_managers"


def test_parse():
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

    attrs = parsed["THE.LOCAL.ONE"]
    assert attrs["STATUS"] == "RUNNING"
    assert [("sb112233", "ACTIVE")] == attrs["INSTANCES"]

    attrs = parsed["THE.MULTI.INSTANCE.ONE"]
    assert [("sb112233", "ACTIVE"), ("sb112255", "STANDBY")] == attrs["INSTANCES"]

    attrs = parsed["THE.CRASHED.ONE"]
    assert attrs["QMNAME"] == "THE.CRASHED.ONE"
    assert attrs["STATUS"] == "ENDED UNEXPECTEDLY"
    assert attrs["STANDBY"] == "NOT APPLICABLE"
    assert "INSTANCES" not in attrs


def test_check_single_instance_running():
    lines = """\
QMNAME(THE.LOCAL.ONE)                                     STATUS(RUNNING) DEFAULT(NO) STANDBY(NOT PERMITTED) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(8.0.0.6)
   INSTANCE(sb112233) MODE(ACTIVE)
"""
    section = parse_info(lines, chr(10))
    check = Check(CHECK_NAME)
    parsed = parse_ibm_mq_managers(section)

    attrs = parsed["THE.LOCAL.ONE"]
    assert attrs["QMNAME"] == "THE.LOCAL.ONE"
    assert attrs["STATUS"] == "RUNNING"

    params: Dict[str, Any] = {}
    actual = list(check.run_check("THE.LOCAL.ONE", params, parsed))
    expected = [
        (0, "Status: RUNNING"),
        (0, "Version: 8.0.0.6"),
        (0, "Installation: /opt/mqm (Installation1), Default: NO"),
        (0, "Single-Instance: sb112233=ACTIVE"),
    ]
    assert expected == actual


def test_rdqm():
    lines = """\
QMNAME(THE.RDQM.ONE)                                      STATUS(RUNNING) DEFAULT(NO) STANDBY(NOT PERMITTED) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(9.1.0.4) HA(REPLICATED) DRROLE()
    INSTANCE(sb008877) MODE(ACTIVE)
QMNAME(THE.STANDBY.RDQM)                                  STATUS(RUNNING ELSEWHERE) DEFAULT(NO) STANDBY(NOT APPLICABLE) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(9.2.0.0) HA(REPLICATED) DRROLE()
"""
    section = parse_info(lines, chr(10))
    check = Check(CHECK_NAME)
    parsed = parse_ibm_mq_managers(section)

    attrs = parsed["THE.RDQM.ONE"]
    assert attrs["QMNAME"] == "THE.RDQM.ONE"
    assert attrs["STATUS"] == "RUNNING"

    params: Dict[str, Any] = {}
    actual = list(check.run_check("THE.RDQM.ONE", params, parsed))
    expected = [
        (0, "Status: RUNNING"),
        (0, "Version: 9.1.0.4"),
        (0, "Installation: /opt/mqm (Installation1), Default: NO"),
        (0, "High availability: replicated, Instance: sb008877"),
    ]
    assert expected == actual


def test_ended_preemtively():
    lines = """\
QMNAME(THE.ENDED.ONE)                                     STATUS(ENDED PREEMPTIVELY) DEFAULT(NO) STANDBY(NOT APPLICABLE) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(7.5.0.2)
"""
    section = parse_info(lines, chr(10))
    check = Check(CHECK_NAME)
    parsed = parse_ibm_mq_managers(section)

    params: Dict[str, Any] = {}
    actual = list(check.run_check("THE.ENDED.ONE", params, parsed))
    expected = [
        (1, "Status: ENDED PREEMPTIVELY"),
        (0, "Version: 7.5.0.2"),
        (0, "Installation: /opt/mqm (Installation1), Default: NO"),
    ]
    assert expected == actual

    lines = """\
QMNAME(THE.ENDED.ONE)                                     STATUS(ENDED PRE-EMPTIVELY) DEFAULT(NO) STANDBY(NOT APPLICABLE) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(8.0.0.1)
"""
    section = parse_info(lines, chr(10))
    check = Check(CHECK_NAME)
    parsed = parse_ibm_mq_managers(section)

    actual = list(check.run_check("THE.ENDED.ONE", params, parsed))
    expected = [
        (1, "Status: ENDED PRE-EMPTIVELY"),
        (0, "Version: 8.0.0.1"),
        (0, "Installation: /opt/mqm (Installation1), Default: NO"),
    ]
    assert expected == actual


def test_status_wato_override():
    lines = """\
QMNAME(THE.ENDED.ONE)                                     STATUS(ENDED PRE-EMPTIVELY) DEFAULT(NO) STANDBY(NOT APPLICABLE) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(7.5.0.2)
"""
    section = parse_info(lines, chr(10))
    check = Check(CHECK_NAME)
    parsed = parse_ibm_mq_managers(section)

    # Factory defaults
    params: Dict[str, Any] = {}
    actual = list(check.run_check("THE.ENDED.ONE", params, parsed))
    expected = [
        (1, "Status: ENDED PRE-EMPTIVELY"),
        (0, "Version: 7.5.0.2"),
        (0, "Installation: /opt/mqm (Installation1), Default: NO"),
    ]
    assert expected == actual

    # Override factory defaults
    params = {"mapped_states": [("ended_pre_emptively", 2)]}
    actual = list(check.run_check("THE.ENDED.ONE", params, parsed))
    expected = [
        (2, "Status: ENDED PRE-EMPTIVELY"),
        (0, "Version: 7.5.0.2"),
        (0, "Installation: /opt/mqm (Installation1), Default: NO"),
    ]
    assert expected == actual

    # Override-does-not-match configuration
    params = {
        "mapped_states": [("running_as_standby", 2)],
        "mapped_states_default": 3,
    }
    actual = list(check.run_check("THE.ENDED.ONE", params, parsed))
    expected = [
        (3, "Status: ENDED PRE-EMPTIVELY"),
        (0, "Version: 7.5.0.2"),
        (0, "Installation: /opt/mqm (Installation1), Default: NO"),
    ]
    assert expected == actual


def test_version_mismatch():
    lines = """\
QMNAME(THE.RUNNING.ONE)                                   STATUS(RUNNING) DEFAULT(NO) STANDBY(NOT APPLICABLE) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(7.5.0.2)
"""
    section = parse_info(lines, chr(10))
    check = Check(CHECK_NAME)
    parsed = parse_ibm_mq_managers(section)

    params: Dict[str, Any] = {}
    params.update({"version": (("at_least", "8.0"), 2)})
    actual = list(check.run_check("THE.RUNNING.ONE", params, parsed))
    expected = [
        (0, "Status: RUNNING"),
        (2, "Version: 7.5.0.2 (should be at least 8.0)"),
        (0, "Installation: /opt/mqm (Installation1), Default: NO"),
    ]
    assert expected == actual
