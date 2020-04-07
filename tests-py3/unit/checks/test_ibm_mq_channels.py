#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore
from cmk.base.check_api import MKCounterWrapped
from test_ibm_mq_include import parse_info

pytestmark = pytest.mark.checks

CHECK_NAME = "ibm_mq_channels"

factory_settings = {}
factory_settings["ibm_mq_channels_default_levels"] = {
    'status': {
        'INACTIVE': 0,
        'INITIALIZING': 0,
        'BINDING': 0,
        'STARTING': 0,
        'RUNNING': 0,
        'RETRYING': 1,
        'STOPPING': 0,
        'STOPPED': 2,
    }
}


def test_parse(check_manager):
    lines = """\
QMNAME(MY.TEST)                                           STATUS(RUNNING) NOW(2020-04-03T17:27:02+0200)
5724-H72 (C) Copyright IBM Corp. 1994, 2015.
Starting MQSC for queue manager MY.TEST.

AMQ8414: Display Channel details.
   CHANNEL(HERE.TO.THERE.ONE)              CHLTYPE(SDR)
   XMITQ(HERE.TO.THERE.ONE.XMIT)
AMQ8414: Display Channel details.
   CHANNEL(HERE.TO.THERE.TWO)              CHLTYPE(SDR)
   XMITQ(HERE.TO.THERE.TWO.XMIT)
AMQ8414: Display Channel details.
   CHANNEL(SYSTEM.DEF.SENDER)              CHLTYPE(SDR)
   XMITQ( )
AMQ8417: Display Channel Status details.
   CHANNEL(HERE.TO.THERE.TWO)              CHLTYPE(SDR)
   CONNAME(55.888.222.333(1414),22,333.444.555(1414))
   CURRENT                                 RQMNAME( )
   STATUS(RETRYING)                        SUBSTATE( )
   XMITQ(HERE.TO.THERE.TWO.XMIT)
AMQ8417: Display Channel Status details.
   CHANNEL(HERE.TO.THERE.ONE)              CHLTYPE(SDR)
   CONNAME(62.240.197.243(1414),62.240.197.244(1414))
   CURRENT                                 RQMNAME( )
   STATUS(RETRYING)                        SUBSTATE( )
   XMITQ(HERE.TO.THERE.ONE.XMIT)
5 MQSC commands read.
No commands have a syntax error.
All valid MQSC commands were processed.
"""
    section = parse_info(lines, chr(10))
    check = check_manager.get_check(CHECK_NAME)
    parsed = check.run_parse(section)
    assert 2 + 1 == len(parsed)

    attrs = parsed['MY.TEST']
    assert attrs['STATUS'] == 'RUNNING'
    assert attrs['NOW'] is not None

    attrs = parsed['MY.TEST:HERE.TO.THERE.TWO']
    assert attrs['CHLTYPE'] == 'SDR'
    assert attrs['STATUS'] == 'RETRYING'
    assert attrs['CONNAME'] == '55.888.222.333(1414),22,333.444.555(1414)'

    attrs = parsed['MY.TEST:HERE.TO.THERE.TWO']
    assert attrs['CHLTYPE'] == 'SDR'
    assert attrs['STATUS'] == 'RETRYING'
    assert attrs['CONNAME'] == '55.888.222.333(1414),22,333.444.555(1414)'


def test_parse_svrconn_with_multiple_instances(check_manager):
    lines = """\
QMNAME(MY.TEST)                                           STATUS(RUNNING) NOW(2020-04-03T17:27:02+0200)
5724-H72 (C) Copyright IBM Corp. 1994, 2015.
Starting MQSC for queue manager MY.TEST.

AMQ8417: Display Channel Status details.
   CHANNEL(XXXXXX.IIB.SVRCONN)             CHLTYPE(SVRCONN)
   CONNAME(10.25.19.182)                   CURRENT
   STATUS(RUNNING)                         SUBSTATE(RECEIVE)
AMQ8417: Display Channel Status details.
   CHANNEL(XXXXXX.IIB.SVRCONN)             CHLTYPE(SVRCONN)
   CONNAME(10.25.19.183)                   CURRENT
   STATUS(RUNNING)                         SUBSTATE(RECEIVE)
One MQSC commands read.
No commands have a syntax error.
All valid MQSC commands were processed.
"""
    section = parse_info(lines, chr(10))
    check = check_manager.get_check(CHECK_NAME)
    parsed = check.run_parse(section)
    attrs = parsed['MY.TEST:XXXXXX.IIB.SVRCONN']
    assert attrs['CHLTYPE'] == 'SVRCONN'
    assert attrs['STATUS'] == 'RUNNING'
    # Last entry of the instances defines the values
    assert attrs['CONNAME'] == '10.25.19.183'


def test_discovery_qmgr_not_included(check_manager):
    check = check_manager.get_check(CHECK_NAME)
    parsed = {
        'QM1': {
            'STATUS': 'RUNNING'
        },
        'QM1:CHAN1': {
            'CHLTYPE': 'SDR',
            'STATUS': 'RETRYING',
            'XMITQ': 'MY.XMIT.Q'
        },
        'QM1:CHAN2': {
            'CHLTYPE': 'RCVR',
            'STATUS': 'STOPPED'
        },
        'QM1:CHAN3': {
            'CHLTYPE': 'SVRCONN'
        },
    }
    discovery = list(check.run_discovery(parsed))
    assert len(discovery) == 3
    assert ('QM1:CHAN2', {}) in discovery


def test_check(check_manager):
    check = check_manager.get_check(CHECK_NAME)
    params = factory_settings['ibm_mq_channels_default_levels']
    parsed = {
        'QM1': {
            'STATUS': 'RUNNING'
        },
        'QM1:CHAN1': {
            'CHLTYPE': 'SDR',
            'STATUS': 'RETRYING',
            'XMITQ': 'MY.XMIT.Q'
        },
        'QM1:CHAN2': {
            'CHLTYPE': 'RCVR',
            'STATUS': 'STOPPED'
        },
        'QM1:CHAN3': {
            'CHLTYPE': 'SVRCONN'
        },
    }

    actual = list(check.run_check('QM1:CHAN1', params, parsed))
    expected = [(1, u'Status: RETRYING, Type: SDR, Xmitq: MY.XMIT.Q', [])]
    assert actual == expected

    actual = list(check.run_check('QM1:CHAN2', params, parsed))
    expected = [(2, u'Status: STOPPED, Type: RCVR', [])]
    assert actual == expected

    actual = list(check.run_check('QM1:CHAN3', params, parsed))
    expected = [(0, u'Status: INACTIVE, Type: SVRCONN', [])]
    assert actual == expected


def test_no_xmit_queue_defined(check_manager):
    """
    Happened on queue manager MQSWISSFPMP1 and channel LXFPMS.TO.RESA. It
    is a misconfiguration on the queue manager, but the monitoring should
    not choke on this.
    """
    check = check_manager.get_check(CHECK_NAME)
    params = factory_settings['ibm_mq_channels_default_levels']
    parsed = {
        'QM1': {
            'STATUS': 'RUNNING'
        },
        'QM1:CHAN1': {
            'CHLTYPE': 'SDR',
            'STATUS': 'RETRYING',
            'XMITQ': 'MY.XMIT.Q'
        },
        'QM1:CHAN2': {
            'CHLTYPE': 'RCVR',
            'STATUS': 'STOPPED'
        },
        'QM1:CHAN3': {
            'CHLTYPE': 'SVRCONN'
        },
        'MQSWISSFPMP1:LXFPMS.TO.RESA': {
            'CHLTYPE': 'SDR'
        },
    }
    actual = list(check.run_check('MQSWISSFPMP1:LXFPMS.TO.RESA', params, parsed))
    expected = [(0, u'Status: INACTIVE, Type: SDR', [])]
    assert actual == expected


def test_stale_service_for_not_running_qmgr(check_manager):
    check = check_manager.get_check(CHECK_NAME)
    params = factory_settings['ibm_mq_channels_default_levels']
    parsed = {'QM1': {'STATUS': 'ENDED NORMALLY'}}
    with pytest.raises(MKCounterWrapped, match=r"Stale because queue manager ENDED NORMALLY"):
        list(check.run_check('QM1:CHAN2', params, parsed))


def test_vanished_service_for_running_qmgr(check_manager):
    check = check_manager.get_check(CHECK_NAME)
    params = factory_settings['ibm_mq_channels_default_levels']
    parsed = {
        'QM1': {
            'STATUS': 'RUNNING'
        },
        'QM1:CHAN1': {
            'CHLTYPE': 'SVRCONN'
        },
    }
    actual = list(check.run_check('QM1:VANISHED', params, parsed))
    assert len(actual) == 0
