#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import pytest  # type: ignore[import]

from cmk.utils.regex import regex  # pylint: disable=unused-import
from cmk.base.check_api import MKCounterWrapped

with open(os.path.join(os.path.dirname(__file__), '../../../checks/ibm_mq.include')) as f:
    exec(f.read())

pytestmark = pytest.mark.checks


def parse_info(lines, separator=None):
    result = []
    for l in lines.splitlines():
        l = l.strip()
        l = l.split(separator)
        result.append(l)
    return result


class TestRunmqscParser:
    def test_normal(self):
        lines = """\
QMNAME(FOO.BAR)                                           STATUS(ENDED UNEXPECTEDLY) NOW(2020-04-03T17:27:02+0200)
5724-H72 (C) Copyright IBM Corp. 1994, 2015.
Starting MQSC for queue manager FOO.BAR.


AMQ8146: WebSphere MQ queue manager not available.

No MQSC commands read.
No commands have a syntax error.
All valid MQSC commands were processed.
QMNAME(MY.TEST)                                           STATUS(RUNNING) NOW(2019-04-03T17:27:02+0200)
5724-H72 (C) Copyright IBM Corp. 1994, 2015.
Starting MQSC for queue manager MY.TEST.


AMQ8409: Display Queue details.
   QUEUE(MY.LARGE.INPUT.TEST.FOR.CHECKMK)
   TYPE(QLOCAL)                            MAXDEPTH(5000)
AMQ8409: Display Queue details.
   QUEUE(OTHER.LARGE.INPUT.TEST.FOR.CHECKMK)
   TYPE(QLOCAL)                            MAXDEPTH(200000)
AMQ8409: Display Queue details.
   QUEUE(SYSTEM.ADMIN.ACCOUNTING.QUEUE)    TYPE(QLOCAL)
   MAXDEPTH(3000)
AMQ8450: Display queue status details.
   QUEUE(MY.LARGE.INPUT.TEST.FOR.CHECKMK)
   TYPE(QUEUE)                             CURDEPTH(0)
   LGETDATE( )                             LGETTIME( )
   LPUTDATE( )                             LPUTTIME( )
   MONQ(MEDIUM)                            MSGAGE(0)
   QTIME( , )
AMQ8450: Display queue status details.
   QUEUE(OTHER.LARGE.INPUT.TEST.FOR.CHECKMK)
   TYPE(QUEUE)                             CURDEPTH(1400)
   LGETDATE(2017-03-09)                    LGETTIME(08.49.13)
   LPUTDATE( )                             LPUTTIME( )
   OPPROCS(0)                              IPPROCS(5)
   MONQ(MEDIUM)                            MSGAGE(2201)
   QTIME(999999999, 999999999)
AMQ8450: Display queue status details.
   QUEUE(SYSTEM.ADMIN.ACCOUNTING.QUEUE)    TYPE(QUEUE)
   CURDEPTH(0)                             LGETDATE( )
   LGETTIME( )                             LPUTDATE( )
   LPUTTIME( )                             MONQ(MEDIUM)
   MSGAGE(0)                               QTIME( , )
2 MQSC commands read.
No commands have a syntax error.
All valid MQSC commands were processed.
"""
        section = parse_info(lines, chr(10))
        parsed = parse_runmqsc_display_output(section, "QUEUE")  # pylint: disable=undefined-variable
        assert 2 + 2 == len(parsed)

        assert parsed['FOO.BAR']['STATUS'] == 'ENDED UNEXPECTEDLY'
        assert parsed['MY.TEST']['STATUS'] == 'RUNNING'
        assert parsed['FOO.BAR']['NOW'] == '2020-04-03T17:27:02+0200'
        assert parsed['MY.TEST']['NOW'] == '2019-04-03T17:27:02+0200'

        attrs = parsed['MY.TEST:OTHER.LARGE.INPUT.TEST.FOR.CHECKMK']
        assert attrs['CURDEPTH'] == '1400'
        assert attrs['LGETDATE'] == '2017-03-09'
        assert attrs['LGETTIME'] == '08.49.13'
        assert attrs['CURDEPTH'] == '1400'
        assert attrs['MAXDEPTH'] == '200000'
        assert attrs['MSGAGE'] == '2201'

    def test_multiple_queue_managers(self):
        lines = """\
QMNAME(QM.ONE)                                            STATUS(RUNNING) NOW(2020-04-03T17:27:02+0200)
5724-H72 (C) Copyright IBM Corp. 1994, 2011.  ALL RIGHTS RESERVED.
Starting MQSC for queue manager QM.ONE.


AMQ8409: Display Queue details.
   QUEUE(MY.QUEUE)
   TYPE(QLOCAL)                            MAXDEPTH(100000)
   MAXMSGL(50000)
AMQ8450: Display queue status details.
   QUEUE(MY.QUEUE)
   TYPE(QUEUE)                             CURDEPTH(0)
   IPPROCS(0)                              LGETDATE( )
   LGETTIME( )                             LPUTDATE( )
   LPUTTIME( )                             MEDIALOG( )
   MONQ(MEDIUM)                            MSGAGE(0)
   OPPROCS(0)                              QTIME( , )
   UNCOM(NO)
2 MQSC commands read.
No commands have a syntax error.
All valid MQSC commands were processed.
QMNAME(QM.TWO)                                            STATUS(RUNNING) NOW(2020-04-03T17:27:02+0200)
5724-H72 (C) Copyright IBM Corp. 1994, 2011.  ALL RIGHTS RESERVED.
Starting MQSC for queue manager QM.TWO.


AMQ8409: Display Queue details.
   QUEUE(MY.QUEUE)
   TYPE(QLOCAL)                            MAXDEPTH(100000)
   MAXMSGL(50000)
AMQ8450: Display queue status details.
   QUEUE(MY.QUEUE)
   TYPE(QUEUE)                             CURDEPTH(0)
   IPPROCS(0)                              LGETDATE( )
   LGETTIME( )                             LPUTDATE( )
   LPUTTIME( )                             MEDIALOG( )
   MONQ(MEDIUM)                            MSGAGE(0)
   OPPROCS(0)                              QTIME( , )
   UNCOM(NO)
2 MQSC commands read.
No commands have a syntax error.
All valid MQSC commands were processed.
"""
        section = parse_info(lines, chr(10))
        parsed = parse_runmqsc_display_output(section, "QUEUE")  # pylint: disable=undefined-variable
        assert "QM.ONE:MY.QUEUE" in parsed
        assert "QM.TWO:MY.QUEUE" in parsed
        assert len(parsed["QM.ONE:MY.QUEUE"]) == 16
        assert len(parsed["QM.TWO:MY.QUEUE"]) == 16

    def test_empty_value_for_msgage(self):
        lines = """\
QMNAME(MY.TEST)                                           STATUS(RUNNING) NOW(2020-04-03T17:27:02+0200)
5724-H72 (C) Copyright IBM Corp. 1994, 2015.
Starting MQSC for queue manager MY.TEST.


AMQ8409: Display Queue details.
   QUEUE(MY.QUEUE)
   TYPE(QLOCAL)                            MAXDEPTH(5000)
AMQ8450: Display queue status details.
   QUEUE(MY.QUEUE)                         TYPE(QUEUE)
   CURDEPTH(0)                             IPPROCS(2)
   LGETDATE( )                             LGETTIME( )
   LPUTDATE( )                             LPUTTIME( )
   MEDIALOG( )                             MONQ(OFF)
   MSGAGE( )                               OPPROCS(0)
   QTIME( , )                              UNCOM(NO)
2 MQSC commands read.
No commands have a syntax error.
All valid MQSC commands were processed.
"""
        section = parse_info(lines, chr(10))
        parsed = parse_runmqsc_display_output(section, "QUEUE")  # pylint: disable=undefined-variable
        attrs = parsed['MY.TEST:MY.QUEUE']
        assert attrs['IPPROCS'] == '2'
        assert attrs['MSGAGE'] == ''

    def test_no_channel_status_of_inactive_channels(self):
        lines = """\
QMNAME(MY.TEST)                                           STATUS(RUNNING) NOW(2020-04-03T17:27:02+0200)
5724-H72 (C) Copyright IBM Corp. 1994, 2015.
Starting MQSC for queue manager MY.TEST.

AMQ8414: Display Channel details.
   CHANNEL(HERE.TO.THERE.TWO)              CHLTYPE(SDR)
   XMITQ(HERE.TO.THERE.TWO.XMIT)
AMQ8420: Channel Status not found.
2 MQSC commands read.
No commands have a syntax error.
One valid MQSC command could not be processed.
"""
        section = parse_info(lines, chr(10))
        parsed = parse_runmqsc_display_output(section, "CHANNEL")  # pylint: disable=undefined-variable
        assert 'MY.TEST:HERE.TO.THERE.TWO' in parsed
        assert 'STATUS' not in parsed['MY.TEST:HERE.TO.THERE.TWO']

    def test_mq9_includes_severity_in_message_code(self):
        lines = """\
QMNAME(MY.TEST)                                           STATUS(RUNNING) NOW(2020-04-03T17:27:02+0200)
5724-H72 (C) Copyright IBM Corp. 1994, 2018.
Starting MQSC for queue manager MY.TEST.


AMQ8414I: Display Channel details.
   CHANNEL(YYYYYYYYYY.SVRCONN)             CHLTYPE(SVRCONN)
AMQ8414I: Display Channel details.
   CHANNEL(XXX.XXXX.XXX.SVRCONN)           CHLTYPE(SVRCONN)
AMQ8417I: Display Channel Status details.
   CHANNEL(YYYYYYYYYY.SVRCONN)             CHLTYPE(SVRCONN)
   CONNAME(77.88.0.130)                    CURRENT
   STATUS(RUNNING)                         SUBSTATE(RECEIVE)
AMQ8417I: Display Channel Status details.
   CHANNEL(YYYYYYYYYY.SVRCONN)             CHLTYPE(SVRCONN)
   CONNAME(77.88.0.130)                    CURRENT
   STATUS(RUNNING)                         SUBSTATE(RECEIVE)
AMQ8417I: Display Channel Status details.
   CHANNEL(XXX.XXXX.XXX.SVRCONN)           CHLTYPE(SVRCONN)
   CONNAME(77.88.0.122)                    CURRENT
   STATUS(RUNNING)                         SUBSTATE(MQGET)
AMQ8417I: Display Channel Status details.
   CHANNEL(XXX.XXXX.XXX.SVRCONN)           CHLTYPE(SVRCONN)
   CONNAME(77.88.0.121)                    CURRENT
   STATUS(RUNNING)                         SUBSTATE(MQGET)
AMQ8417I: Display Channel Status details.
   CHANNEL(XXX.XXXX.XXX.SVRCONN)           CHLTYPE(SVRCONN)
   CONNAME(77.88.0.120)                    CURRENT
   STATUS(RUNNING)                         SUBSTATE(MQGET)
"""
        section = parse_info(lines, chr(10))
        parsed = parse_runmqsc_display_output(section, "CHANNEL")  # pylint: disable=undefined-variable

        attrs = parsed['MY.TEST']
        assert attrs['STATUS'] == 'RUNNING'

        attrs = parsed['MY.TEST:YYYYYYYYYY.SVRCONN']
        assert attrs['STATUS'] == 'RUNNING'

        attrs = parsed['MY.TEST:XXX.XXXX.XXX.SVRCONN']
        assert attrs['STATUS'] == 'RUNNING'

        assert len(parsed) == 3


class TestServiceVanished:
    def test_not_vanished(self):
        parsed = {
            'QM1': {
                'STATUS': 'RUNNING'
            },
            'QM1:QUEUE1': {
                'CURDEPTH': '0'
            },
        }
        assert is_ibm_mq_service_vanished('QM1:QUEUE1', parsed) is False  # pylint: disable=undefined-variable

    def test_vanished_for_running_qmgr(self):
        parsed = {
            'QM1': {
                'STATUS': 'RUNNING'
            },
            'QM1:QUEUE1': {
                'CURDEPTH': '0'
            },
        }
        assert is_ibm_mq_service_vanished('QM1:VANISHED', parsed) is True  # pylint: disable=undefined-variable

    def test_stale_for_not_running_qmgr(self):
        parsed = {'QM1': {'STATUS': 'ENDED NORMALLY'}}
        with pytest.raises(MKCounterWrapped, match=r"^Stale because .* ENDED NORMALLY"):
            is_ibm_mq_service_vanished('QM1:QUEUE1', parsed)  # pylint: disable=undefined-variable


class TestCheckVersion:
    def test_specific(self):
        params = {'version': ('specific', '2.1.0')}
        actual = ibm_mq_check_version('2.1.0', params, 'MyLabel')  # pylint: disable=undefined-variable
        expected = (0, 'MyLabel: 2.1.0')
        assert expected == actual

        params = {'version': ('specific', '2.0')}
        actual = ibm_mq_check_version('2.1.0', params, 'MyLabel')  # pylint: disable=undefined-variable
        expected = (2, 'MyLabel: 2.1.0 (should be 2.0)')
        assert expected == actual

    def test_at_least(self):
        params = {'version': ('at_least', '2.0')}
        actual = ibm_mq_check_version('2.1.0', params, 'MyLabel')  # pylint: disable=undefined-variable
        expected = (0, 'MyLabel: 2.1.0')
        assert expected == actual

        params = {'version': ('at_least', '2.2')}
        actual = ibm_mq_check_version('2.1.0', params, 'MyLabel')  # pylint: disable=undefined-variable
        expected = (2, 'MyLabel: 2.1.0 (should be at least 2.2)')
        assert expected == actual

        params = {'version': ('at_least', '0.1.0')}
        actual = ibm_mq_check_version('1.0.0', params, 'MyLabel')  # pylint: disable=undefined-variable
        expected = (0, 'MyLabel: 1.0.0')
        assert expected == actual

        params = {'version': ('at_least', '8.0.0.1')}
        actual = ibm_mq_check_version('9.0.0.0', params, 'MyLabel')  # pylint: disable=undefined-variable
        expected = (0, 'MyLabel: 9.0.0.0')
        assert expected == actual

    def test_unparseable(self):
        const_error = "Only characters 0-9 and . are allowed for a version."

        params = {'version': ('specific', '2.a')}
        actual = ibm_mq_check_version('2.1.0', params, 'MyLabel')  # pylint: disable=undefined-variable
        expected = (3, "Can not compare 2.1.0 and 2.a. " + const_error)
        assert expected == actual

        params = {'version': ('specific', '2.2')}
        actual = ibm_mq_check_version('2.x', params, 'MyLabel')  # pylint: disable=undefined-variable
        expected = (3, "Can not compare 2.x and 2.2. " + const_error)
        assert expected == actual

    def test_unparseable_without_wato_rule(self):
        params = {}
        actual = ibm_mq_check_version('2.x', params, 'MyLabel')  # pylint: disable=undefined-variable
        expected = (0, "MyLabel: 2.x")
        assert expected == actual

    def test_no_version(self):
        params = {}
        actual = ibm_mq_check_version(None, params, 'MyLabel')  # pylint: disable=undefined-variable
        expected = (3, "MyLabel: None (no agent info)")
        assert expected == actual
