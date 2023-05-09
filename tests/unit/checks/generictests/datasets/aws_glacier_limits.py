#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'aws_glacier_limits'

info = [['[["number_of_vaults",', '"TITLE",', '10,', '1,', '"REGION"]]']]

discovery = {'': [("REGION", {})]}

checks = {
    '': [
        (
            "REGION", {
                'number_of_vaults': (None, 80.0, 90.0)
            }, [
                (
                    0, 'No levels reached', [
                        (
                            'aws_glacier_number_of_vaults', 1, None, None, None, None
                        )
                    ]
                ), (0, '\nTITLE: 1 (of max. 10)')
            ]
        )
    ]
}
