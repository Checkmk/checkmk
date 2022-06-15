#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'aws_wafv2_web_acl'

info = [['[{"Id":', '"id_0_AllowedRequests",', '"Label":', '"joerg-herbel-acl_eu-central-1",',
         '"Timestamps":', '["2020-04-28', '08:45:00+00:00"],', '"Values":', '[[11.0,', '600]],',
         '"StatusCode":', '"Complete"},', '{"Id":', '"id_0_BlockedRequests",', '"Label":',
         '"joerg-herbel-acl_eu-central-1",', '"Timestamps":', '["2020-04-28', '08:45:00+00:00"],',
         '"Values":', '[[9.0,', '600]],', '"StatusCode":', '"Complete"}]']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {'allowed_requests_perc': (10.0, 20.0), 'blocked_requests_perc': (10.0, 20.0)},
            [
                (0, 'Total requests: 0.033/s',
                 [('aws_wafv2_requests_rate', 0.03333333333333333, None, None)]),
                (0, 'Allowed requests: 0.018/s',
                 [('aws_wafv2_allowed_requests_rate', 0.018333333333333333, None, None)]),
                (2, 'Percentage allowed requests: 55.00% (warn/crit at 10.00%/20.00%)',
                 [('aws_wafv2_allowed_requests_perc', 55.0, 10.0, 20.0)]),
                (0, 'Blocked requests: 0.015/s',
                 [('aws_wafv2_blocked_requests_rate', 0.015, None, None)]),
                (2, 'Percentage blocked requests: 45.00% (warn/crit at 10.00%/20.00%)',
                 [('aws_wafv2_blocked_requests_perc', 45.0, 10.0, 20.0)]),

            ]
        )
    ]
}
