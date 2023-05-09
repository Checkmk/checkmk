#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.ntp import parse_ntp, Peer


def test_parse_ntp():
    assert parse_ntp([
        ['%', 'remote', 'refid', 'st', 't', 'when', 'poll', 'reach', 'delay', 'offset', 'jitter'],
        ['=', '============================================================================='],
        ['+', '127.0.0.1', '.PTB.', '1', 'u', '72', '256', '377', '16.199', '0.623', '1.533'],
        ['*', '127.0.0.2', '.PTB.', '1', 'u', '92', '256', '377', '15.515', '0.587', '1.439'],
        ['+', '127.0.0.3', '.PTB.', '1', 'u', '230', '256', '377', '15.837', '0.490', '1.035'],
    ]) == {
        '127.0.0.1': Peer(
            statecode='+',
            name='127.0.0.1',
            refid='.PTB.',
            stratum=1,
            when=72,
            reach='377',
            offset=0.623,
            jitter=1.533,
        ),
        '127.0.0.2': Peer(
            statecode='*',
            name='127.0.0.2',
            refid='.PTB.',
            stratum=1,
            when=92,
            reach='377',
            offset=0.587,
            jitter=1.439,
        ),
        None: Peer(
            statecode='*',
            name='127.0.0.2',
            refid='.PTB.',
            stratum=1,
            when=92,
            reach='377',
            offset=0.587,
            jitter=1.439,
        ),
        '127.0.0.3': Peer(
            statecode='+',
            name='127.0.0.3',
            refid='.PTB.',
            stratum=1,
            when=230,
            reach='377',
            offset=0.49,
            jitter=1.035,
        ),
    }
