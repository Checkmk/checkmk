#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict
from testlib import Check  # type: ignore[import]
import pytest  # type: ignore[import]
from cmk.base.check_api import MKCounterWrapped  # noqa: F401 # pylint: disable=unused-import
from test_ibm_mq_include import parse_info

pytestmark = pytest.mark.checks

CHECK_NAME = "ibm_mq_managers"

factory_settings: Dict[str, Any] = {}
factory_settings["ibm_mq_managers_default_levels"] = {
    "status": {
        "STARTING": 0,
        "RUNNING": 0,
        "RUNNING AS STANDBY": 0,
        "RUNNING ELSEWHERE": 0,
        "QUIESCING": 0,
        "ENDING IMMEDIATELY": 0,
        "ENDING PREEMPTIVELY": 0,  # Older MQ-Versions (e.g. 7.5.0.2) use this status
        "ENDING PRE-EMPTIVELY": 0,
        "ENDED NORMALLY": 0,
        "ENDED IMMEDIATELY": 0,
        "ENDED UNEXPECTEDLY": 2,
        "ENDED PREEMPTIVELY": 2,  # Older MQ-Versions (e.g. 7.5.0.2) use this status
        "ENDED PRE-EMPTIVELY": 2,
        "NOT AVAILABLE": 1,  # Older MQ-Versions (e.g. 7.5.0.2) use this status
        "STATUS NOT AVAILABLE": 1,
    },
}


@pytest.mark.usefixtures("config_load_all_checks")
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
    check = Check(CHECK_NAME)
    parsed = check.run_parse(section)
    assert len(parsed) == 5

    attrs = parsed["THE.LOCAL.ONE"]
    assert attrs['STATUS'] == 'RUNNING'
    assert [(u'sb112233', u'ACTIVE')] == attrs['INSTANCES']

    attrs = parsed["THE.MULTI.INSTANCE.ONE"]
    assert [(u'sb112233', u'ACTIVE'), (u'sb112255', u'STANDBY')] \
            == attrs['INSTANCES']

    attrs = parsed["THE.CRASHED.ONE"]
    assert attrs['QMNAME'] == 'THE.CRASHED.ONE'
    assert attrs['STATUS'] == 'ENDED UNEXPECTEDLY'
    assert attrs['STANDBY'] == 'NOT APPLICABLE'
    assert 'INSTANCES' not in attrs


@pytest.mark.usefixtures("config_load_all_checks")
def test_check_single_instance_running():
    lines = """\
QMNAME(THE.LOCAL.ONE)                                     STATUS(RUNNING) DEFAULT(NO) STANDBY(NOT PERMITTED) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(8.0.0.6)
   INSTANCE(sb112233) MODE(ACTIVE)
"""
    section = parse_info(lines, chr(10))
    check = Check(CHECK_NAME)
    parsed = check.run_parse(section)

    attrs = parsed["THE.LOCAL.ONE"]
    assert attrs['QMNAME'] == 'THE.LOCAL.ONE'
    assert attrs['STATUS'] == 'RUNNING'

    params = factory_settings['ibm_mq_managers_default_levels']
    actual = list(check.run_check('THE.LOCAL.ONE', params, parsed))
    expected = [
        (0, u'Status: RUNNING'),
        (0, u'Version: 8.0.0.6'),
        (0, u'Installation: /opt/mqm (Installation1), Default: NO'),
        (0, u'Single-Instance: sb112233=ACTIVE'),
    ]
    assert expected == actual


@pytest.mark.usefixtures("config_load_all_checks")
def test_ended_preemtively():
    lines = """\
QMNAME(MTAVBS0P)                                          STATUS(ENDED PREEMPTIVELY) DEFAULT(NO) STANDBY(NOT APPLICABLE) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(7.5.0.2)
"""
    section = parse_info(lines, chr(10))
    check = Check(CHECK_NAME)
    parsed = check.run_parse(section)
    params = factory_settings['ibm_mq_managers_default_levels']
    actual = list(check.run_check('MTAVBS0P', params, parsed))
    expected = [
        (2, u'Status: ENDED PREEMPTIVELY'),
        (0, u'Version: 7.5.0.2'),
        (0, u'Installation: /opt/mqm (Installation1), Default: NO'),
    ]
    assert expected == actual

    lines = """\
QMNAME(MTAVBS0P)                                          STATUS(ENDED PRE-EMPTIVELY) DEFAULT(NO) STANDBY(NOT APPLICABLE) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(8.0.0.1)
"""
    section = parse_info(lines, chr(10))
    check = Check(CHECK_NAME)
    parsed = check.run_parse(section)
    params = factory_settings['ibm_mq_managers_default_levels']
    actual = list(check.run_check('MTAVBS0P', params, parsed))
    expected = [
        (2, u'Status: ENDED PRE-EMPTIVELY'),
        (0, u'Version: 8.0.0.1'),
        (0, u'Installation: /opt/mqm (Installation1), Default: NO'),
    ]
    assert expected == actual


@pytest.mark.usefixtures("config_load_all_checks")
def test_version_mismatch():
    lines = """\
QMNAME(MTAVBS0P)                                          STATUS(RUNNING) DEFAULT(NO) STANDBY(NOT APPLICABLE) INSTNAME(Installation1) INSTPATH(/opt/mqm) INSTVER(7.5.0.2)
"""
    section = parse_info(lines, chr(10))
    check = Check(CHECK_NAME)
    parsed = check.run_parse(section)
    params = factory_settings['ibm_mq_managers_default_levels']
    params.update({'version': ('at_least', '8.0')})
    actual = list(check.run_check('MTAVBS0P', params, parsed))
    expected = [
        (0, u'Status: RUNNING'),
        (2, u'Version: 7.5.0.2 (should be at least 8.0)'),
        (0, u'Installation: /opt/mqm (Installation1), Default: NO'),
    ]
    assert expected == actual
