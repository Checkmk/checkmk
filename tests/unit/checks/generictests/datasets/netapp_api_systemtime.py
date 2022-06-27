#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable

from typing import Any, Dict, List, Tuple

checkname = 'netapp_api_systemtime'

info = [['FAS8020-2', '1498108660', '1498108660']]

discovery: Dict[str, List[Tuple[str, Dict[Any, Any]]]] = {'': [('FAS8020-2', {})]}

checks: Dict[str, List[Tuple[str, Dict[Any, Any], List[Tuple[int, str, List[Tuple[str, int, Any, Any, Any, Any]]]]]]] = {
    '': [
        (
            'FAS8020-2', {}, [
                (
                    0,
                    'System time: 2017-06-22 07:17:40',
                    []
                ),
                (
                    0,
                    'Time difference: 0 seconds',
                    [('time_difference', 0, None, None, None, None)]
                ),
            ]
        )
    ]
}
