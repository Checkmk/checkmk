#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'aws_elb'

info = [
    [
        '[{"Id":', '"id_1_RequestCount",', '"Label":',
        '"jh-clb-331570100.eu-central-1.elb.amazonaws.com",', '"Timestamps":',
        '["2020-06-18', '11:37:00+00:00"],', '"Values":', '[[14.0,', '600]],',
        '"StatusCode":', '"Complete"},', '{"Id":', '"id_1_SurgeQueueLength",',
        '"Label":', '"jh-clb-331570100.eu-central-1.elb.amazonaws.com",',
        '"Timestamps":', '["2020-06-18', '11:37:00+00:00"],', '"Values":',
        '[[1.0,', 'null]],', '"StatusCode":', '"Complete"},', '{"Id":',
        '"id_1_SpilloverCount",', '"Label":',
        '"jh-clb-331570100.eu-central-1.elb.amazonaws.com",', '"Timestamps":',
        '[],', '"Values":', '[],', '"StatusCode":', '"Complete"},', '{"Id":',
        '"id_1_Latency",', '"Label":',
        '"jh-clb-331570100.eu-central-1.elb.amazonaws.com",', '"Timestamps":',
        '["2020-06-18', '11:37:00+00:00"],', '"Values":',
        '[[28.426270178386144,', 'null]],', '"StatusCode":', '"Complete"},',
        '{"Id":', '"id_1_HTTPCode_ELB_4XX",', '"Label":',
        '"jh-clb-331570100.eu-central-1.elb.amazonaws.com",', '"Timestamps":',
        '[],', '"Values":', '[],', '"StatusCode":', '"Complete"},', '{"Id":',
        '"id_1_HTTPCode_ELB_5XX",', '"Label":',
        '"jh-clb-331570100.eu-central-1.elb.amazonaws.com",', '"Timestamps":',
        '["2020-06-18', '11:37:00+00:00"],', '"Values":', '[[1.0,', '600]],',
        '"StatusCode":', '"Complete"},', '{"Id":',
        '"id_1_HTTPCode_Backend_2XX",', '"Label":',
        '"jh-clb-331570100.eu-central-1.elb.amazonaws.com",', '"Timestamps":',
        '["2020-06-18', '11:37:00+00:00"],', '"Values":', '[[6.0,', '600]],',
        '"StatusCode":', '"Complete"},', '{"Id":',
        '"id_1_HTTPCode_Backend_3XX",', '"Label":',
        '"jh-clb-331570100.eu-central-1.elb.amazonaws.com",', '"Timestamps":',
        '[],', '"Values":', '[],', '"StatusCode":', '"Complete"},', '{"Id":',
        '"id_1_HTTPCode_Backend_4XX",', '"Label":',
        '"jh-clb-331570100.eu-central-1.elb.amazonaws.com",', '"Timestamps":',
        '[],', '"Values":', '[],', '"StatusCode":', '"Complete"},', '{"Id":',
        '"id_1_HTTPCode_Backend_5XX",', '"Label":',
        '"jh-clb-331570100.eu-central-1.elb.amazonaws.com",', '"Timestamps":',
        '["2020-06-18', '11:37:00+00:00"],', '"Values":', '[[7.0,', '600]],',
        '"StatusCode":', '"Complete"},', '{"Id":', '"id_1_HealthyHostCount",',
        '"Label":', '"jh-clb-331570100.eu-central-1.elb.amazonaws.com",',
        '"Timestamps":', '["2020-06-18', '11:37:00+00:00"],', '"Values":',
        '[[1.0,', 'null]],', '"StatusCode":', '"Complete"},', '{"Id":',
        '"id_1_UnHealthyHostCount",', '"Label":',
        '"jh-clb-331570100.eu-central-1.elb.amazonaws.com",', '"Timestamps":',
        '["2020-06-18', '11:37:00+00:00"],', '"Values":', '[[0.0,', 'null]],',
        '"StatusCode":', '"Complete"},', '{"Id":',
        '"id_1_BackendConnectionErrors",', '"Label":',
        '"jh-clb-331570100.eu-central-1.elb.amazonaws.com",', '"Timestamps":',
        '[],', '"Values":', '[],', '"StatusCode":', '"Complete"}]'
    ]
]

discovery = {
    '': [],
    'latency': [(None, {})],
    'http_elb': [(None, {})],
    'http_backend': [(None, {})],
    'healthy_hosts': [(None, {})],
    'backend_connection_errors': []
}

checks = {
    'latency': [
        (
            None, {}, [
                (
                    0, '28 seconds', [
                        (
                            'aws_load_balancer_latency', 28.426270178386144,
                            None, None, None, None
                        )
                    ]
                )
            ]
        )
    ],
    'http_elb': [
        (
            None, {}, [
                (
                    0, 'Requests: 0.023/s', [
                        (
                            'requests_per_second', 0.023333333333333334, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '4XX-Errors: 0.000/s', [
                        ('aws_http_4xx_rate', 0, None, None, None, None)
                    ]
                ),
                (
                    0, '4XX-Errors of total requests: 0%', [
                        ('aws_http_4xx_perc', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, '5XX-Errors: 0.002/s', [
                        (
                            'aws_http_5xx_rate', 0.0016666666666666668, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '5XX-Errors of total requests: 7.14%', [
                        (
                            'aws_http_5xx_perc', 7.142857142857143, None, None,
                            None, None
                        )
                    ]
                )
            ]
        )
    ],
    'http_backend': [
        (
            None, {}, [
                (
                    0, 'Requests: 0.023/s', [
                        (
                            'requests_per_second', 0.023333333333333334, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '2XX-Errors: 0.010/s', [
                        ('aws_http_2xx_rate', 0.01, None, None, None, None)
                    ]
                ),
                (
                    0, '2XX-Errors of total requests: 42.86%', [
                        (
                            'aws_http_2xx_perc', 42.857142857142854, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '3XX-Errors: 0.000/s', [
                        ('aws_http_3xx_rate', 0, None, None, None, None)
                    ]
                ),
                (
                    0, '3XX-Errors of total requests: 0%', [
                        ('aws_http_3xx_perc', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, '4XX-Errors: 0.000/s', [
                        ('aws_http_4xx_rate', 0, None, None, None, None)
                    ]
                ),
                (
                    0, '4XX-Errors of total requests: 0%', [
                        ('aws_http_4xx_perc', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, '5XX-Errors: 0.012/s', [
                        (
                            'aws_http_5xx_rate', 0.011666666666666667, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '5XX-Errors of total requests: 50.0%', [
                        ('aws_http_5xx_perc', 50.0, None, None, None, None)
                    ]
                )
            ]
        )
    ],
    'healthy_hosts': [
        (
            None, {}, [
                (0, 'Healthy hosts: 1', []), (0, 'Unhealthy hosts: 0', []),
                (0, 'Total: 1', []),
                (
                    0, 'Proportion of healthy hosts: 100%', [
                        (
                            'aws_overall_hosts_health_perc', 100.0, None, None,
                            None, None
                        )
                    ]
                )
            ]
        )
    ]
}
