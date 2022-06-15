#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'aws_glacier_limits'


info = [['[["number_of_vaults",',
         '"Vaults",',
         '1000,',
         '0,',
         '"ap-northeast-2"]]'],
        ['[["number_of_vaults",',
         '"Vaults",',
         '1000,',
         '910,',
         '"ca-central-1"]]'],
        ['[["number_of_vaults",',
         '"Vaults",',
         '1000,',
         '2,',
         '"eu-central-1"]]'],
        ['[["number_of_vaults",',
         '"Vaults",',
         '1000,',
         '1001,',
         '"us-east-1"]]']]


discovery = {'': [("ap-northeast-2", {}),
                  ("ca-central-1", {}),
                  ("eu-central-1", {}),
                  ("us-east-1", {})]}


checks = {'': [("ap-northeast-2",
                {'number_of_vaults': (None, 80.0, 90.0)},
                [(0,
                  'No levels reached',
                  [('aws_glacier_number_of_vaults', 0, None, None, None, None)]),
                 (0,
                  '\nVaults: 0 (of max. 1000)')]),
               ("ca-central-1",
                {'number_of_vaults': (None, 80.0, 90.0)},
                [(2,
                  'Levels reached: Vaults',
                  [('aws_glacier_number_of_vaults', 910, None, None, None, None)]),
                 (0,
                  '\nVaults: 910 (of max. 1000), Usage: 91.00% (warn/crit at 80.00%/90.00%)(!!)')]),
               ("eu-central-1",
                {'number_of_vaults': (None, 80.0, 90.0)},
                [(0,
                  'No levels reached',
                  [('aws_glacier_number_of_vaults', 2, None, None, None, None)]),
                 (0,
                  '\nVaults: 2 (of max. 1000)')]),
               ("us-east-1",
                {'number_of_vaults': (None, 80.0, 90.0)},
                [(2,
                  'Levels reached: Vaults',
                  [('aws_glacier_number_of_vaults', 1001, None, None, None, None)]),
                 (0,
                  '\nVaults: 1001 (of max. 1000), Usage: 100.10% (warn/crit at 80.00%/90.00%)(!!)')])
               ]}
