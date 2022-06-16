#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'aws_ebs_limits'

info = [['[["block_store_snapshots",', '"TITLE",', '10,', '1,', '"REGION"]]']]

discovery = {'': [("REGION", {})]}

checks = {
    '': [
        (
            "REGION", {
                'block_store_space_gp2': (None, 80.0, 90.0),
                'block_store_space_gp3': (None, 80.0, 90.0),
                'block_store_space_sc1': (None, 80.0, 90.0),
                'block_store_space_st1': (None, 80.0, 90.0),
                'block_store_snapshots': (None, 80.0, 90.0),
                'block_store_iops_io1': (None, 80.0, 90.0),
                'block_store_iops_io2': (None, 80.0, 90.0),
                'block_store_space_standard': (None, 80.0, 90.0),
                'block_store_space_io1': (None, 80.0, 90.0),
                'block_store_space_io2': (None, 80.0, 90.0),
            }, [
                (
                    0, 'No levels reached', [
                        (
                            'aws_ebs_block_store_snapshots', 1, None, None,
                            None, None
                        )
                    ]
                ), (0, '\nTITLE: 1 (of max. 10)', [])
            ]
        )
    ]
}
