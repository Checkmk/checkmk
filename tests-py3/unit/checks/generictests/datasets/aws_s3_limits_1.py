#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'aws_s3_limits'

info = [['[["buckets",', '"TITLE",', '10,', '1]]']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'buckets': (None, 80.0, 90.0)
            }, [
                (
                    0, 'No levels reached', [
                        (u'aws_s3_buckets', 1, None, None, None, None)
                    ]
                ), (0, u'\nTITLE: 1 (of max. 10)', [])
            ]
        )
    ]
}
