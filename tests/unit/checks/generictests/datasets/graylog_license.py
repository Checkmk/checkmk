#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'graylog_license'

freeze_time = '2019-11-08T08:56:00'

info = [
    [
        u'{"status": [{"violated": true,"expired": false,"expiration_upcoming": false,"expired_since": "PT0S","expires_in": "PT550H17.849S","trial": true,"license": {"version": 2,"id": "*********************************","issuer": "Graylog, Inc.","subject": "/license/enterprise","audience": {"company": "MYCOMPANY","name": "****************************","email": "*******************************"},"issue_date": "2019-09-23T05:00:00Z","expiration_date": "2019-10-24T04:59:59Z","not_before_date": "2019-09-23T05:00:00Z","trial": true,"enterprise": {"cluster_ids": ["***********************************************"],"number_of_nodes": 2147483647,"require_remote_check": true,"allowed_remote_check_failures": 120,"traffic_limit": 5368709120,"traffic_check_range": "PT720H","allowed_traffic_violations": 5,"expiration_warning_range": "PT240H"},"expired": false},"traffic_exceeded": false,"cluster_not_covered": false,"nodes_exceeded": false,"remote_checks_failed": true,"valid": false}]}'
    ]
]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'no_enterprise': 0,
                'violated': 2,
                'valid': 2,
                'cluster_not_covered': 1,
                'traffic_exceeded': 1,
                'nodes_exceeded': 1,
                'expired': 2,
                'remote_checks_failed': 1
            }, [
                (0, 'Is expired: no', []), (2, 'Is violated: yes', []),
                (2, 'Is valid: no', []), (0, 'Traffic is exceeded: no', []),
                (0, 'Cluster is not covered: no', []),
                (0, 'Nodes exceeded: no', []),
                (1, 'Remote checks failed: yes', []),
                (0, 'Traffic limit: 5.00 GB', []),
                (0, 'Expires in: -15 days 3 hours', []),
                (0, 'Subject: /license/enterprise', []), (0, 'Trial: yes', []),
                (0, 'Requires remote checks: yes', [])
            ]
        )
    ]
}
