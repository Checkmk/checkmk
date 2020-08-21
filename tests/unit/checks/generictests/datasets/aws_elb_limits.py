#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'aws_elb_limits'

info = [['[["load_balancers",', '"TITLE",', '10,', '1,', '"REGION"]]']]

discovery = {'': [("REGION", {})]}

checks = {
    '': [
        (
            "REGION", {
                'load_balancer_registered_instances': (None, 80.0, 90.0),
                'load_balancer_listeners': (None, 80.0, 90.0),
                'load_balancers': (None, 80.0, 90.0)
            }, [
                (
                    0, 'No levels reached', [
                        (u'aws_elb_load_balancers', 1, None, None, None, None)
                    ]
                ), (0, u'\nTITLE: 1 (of max. 10)')
            ]
        )
    ]
}
