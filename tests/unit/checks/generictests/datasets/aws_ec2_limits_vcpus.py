#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'aws_ec2_limits'

info = [
    [
        '[["running_ondemand_instances_t2.medium",', '"Running',
        'On-Demand', 't2.medium', 'Instances",', '20,', '3,',
        '"eu-central-1"],', '["running_ondemand_instances___vcpu",',
        '"Running', 'On-Demand', 'Standard', '(A,', 'C,', 'D,', 'H,',
        'I,', 'M,', 'R,', 'T,', 'Z)', 'instances', 'vCPUs",', '1152,',
        '8,', '"eu-central-1"],', '["running_ondemand_instances_t2.nano",',
        '"Running', 'On-Demand', 't2.nano', 'Instances",', '20,', '2,',
        '"eu-central-1"],', '["running_ondemand_instances_total",',
        '"Total', 'Running', 'On-Demand', 'Instances",', '20,', '5,',
        '"eu-central-1"],', '["vpc_elastic_ip_addresses",', '"VPC',
        'Elastic', 'IP', 'Addresses",', '5,', '0,', '"eu-central-1"],',
        '["elastic_ip_addresses",', '"Elastic', 'IP', 'Addresses",', '5,',
        '0,', '"eu-central-1"],', '["spot_inst_requests",', '"Spot',
        'Instance', 'Requests",', '20,', '0,', '"eu-central-1"],',
        '["active_spot_fleet_requests",', '"Active', 'Spot', 'Fleet',
        'Requests",', '1000,', '0,', '"eu-central-1"],',
        '["spot_fleet_total_target_capacity",', '"Spot', 'Fleet',
        'Requests', 'Total', 'Target', 'Capacity",', '5000,', '0,',
        '"eu-central-1"]]'
    ]
]

discovery = {'': [("eu-central-1", {})]}

checks = {
    '': [
        (
            "eu-central-1", {
                'vpc_elastic_ip_addresses': (None, 80.0, 90.0),
                'running_ondemand_instances': [
                    ('a1.2xlarge', (None, 80.0, 90.0)),
                    ('a1.4xlarge', (None, 80.0, 90.0)),
                    ('a1.large', (None, 80.0, 90.0)),
                    ('a1.medium', (None, 80.0, 90.0)),
                    ('a1.xlarge', (None, 80.0, 90.0)),
                    ('t2.nano', (None, 80.0, 90.0)),
                    ('t2.micro', (None, 80.0, 90.0)),
                    ('t2.small', (None, 80.0, 90.0)),
                    ('t2.medium', (None, 80.0, 90.0)),
                    ('t2.large', (None, 80.0, 90.0)),
                    ('t2.xlarge', (None, 80.0, 90.0)),
                    ('t2.2xlarge', (None, 80.0, 90.0)),
                    ('t3.nano', (None, 80.0, 90.0)),
                    ('t3.micro', (None, 80.0, 90.0)),
                    ('t3.small', (None, 80.0, 90.0)),
                    ('t3.medium', (None, 80.0, 90.0)),
                    ('t3.large', (None, 80.0, 90.0)),
                    ('t3.xlarge', (None, 80.0, 90.0)),
                    ('t3.2xlarge', (None, 80.0, 90.0)),
                    ('m3.medium', (None, 80.0, 90.0)),
                    ('m3.large', (None, 80.0, 90.0)),
                    ('m3.xlarge', (None, 80.0, 90.0)),
                    ('m3.2xlarge', (None, 80.0, 90.0)),
                    ('m4.large', (None, 80.0, 90.0)),
                    ('m4.xlarge', (None, 80.0, 90.0)),
                    ('m4.2xlarge', (None, 80.0, 90.0)),
                    ('m4.4xlarge', (None, 80.0, 90.0)),
                    ('m4.10xlarge', (None, 80.0, 90.0)),
                    ('m4.16xlarge', (None, 80.0, 90.0)),
                    ('m5.12xlarge', (None, 80.0, 90.0)),
                    ('m5.24xlarge', (None, 80.0, 90.0)),
                    ('m5.2xlarge', (None, 80.0, 90.0)),
                    ('m5.4xlarge', (None, 80.0, 90.0)),
                    ('m5.large', (None, 80.0, 90.0)),
                    ('m5.xlarge', (None, 80.0, 90.0)),
                    ('m5d.12xlarge', (None, 80.0, 90.0)),
                    ('m5d.24xlarge', (None, 80.0, 90.0)),
                    ('m5d.2xlarge', (None, 80.0, 90.0)),
                    ('m5d.4xlarge', (None, 80.0, 90.0)),
                    ('m5d.large', (None, 80.0, 90.0)),
                    ('m5d.xlarge', (None, 80.0, 90.0)),
                    ('m5a.12xlarge', (None, 80.0, 90.0)),
                    ('m5a.24xlarge', (None, 80.0, 90.0)),
                    ('m5a.2xlarge', (None, 80.0, 90.0)),
                    ('m5a.4xlarge', (None, 80.0, 90.0)),
                    ('m5a.large', (None, 80.0, 90.0)),
                    ('m5a.xlarge', (None, 80.0, 90.0)),
                    ('t1.micro', (None, 80.0, 90.0)),
                    ('m1.small', (None, 80.0, 90.0)),
                    ('m1.medium', (None, 80.0, 90.0)),
                    ('m1.large', (None, 80.0, 90.0)),
                    ('m1.xlarge', (None, 80.0, 90.0)),
                    ('r3.2xlarge', (None, 80.0, 90.0)),
                    ('r3.4xlarge', (None, 80.0, 90.0)),
                    ('r3.8xlarge', (None, 80.0, 90.0)),
                    ('r3.large', (None, 80.0, 90.0)),
                    ('r3.xlarge', (None, 80.0, 90.0)),
                    ('r4.2xlarge', (None, 80.0, 90.0)),
                    ('r4.4xlarge', (None, 80.0, 90.0)),
                    ('r4.8xlarge', (None, 80.0, 90.0)),
                    ('r4.16xlarge', (None, 80.0, 90.0)),
                    ('r4.large', (None, 80.0, 90.0)),
                    ('r4.xlarge', (None, 80.0, 90.0)),
                    ('r5.2xlarge', (None, 80.0, 90.0)),
                    ('r5.4xlarge', (None, 80.0, 90.0)),
                    ('r5.8xlarge', (None, 80.0, 90.0)),
                    ('r5.12xlarge', (None, 80.0, 90.0)),
                    ('r5.16xlarge', (None, 80.0, 90.0)),
                    ('r5.24xlarge', (None, 80.0, 90.0)),
                    ('r5.large', (None, 80.0, 90.0)),
                    ('r5.metal', (None, 80.0, 90.0)),
                    ('r5.xlarge', (None, 80.0, 90.0)),
                    ('r5a.12xlarge', (None, 80.0, 90.0)),
                    ('r5a.24xlarge', (None, 80.0, 90.0)),
                    ('r5a.2xlarge', (None, 80.0, 90.0)),
                    ('r5a.4xlarge', (None, 80.0, 90.0)),
                    ('r5a.large', (None, 80.0, 90.0)),
                    ('r5a.xlarge', (None, 80.0, 90.0)),
                    ('r5d.2xlarge', (None, 80.0, 90.0)),
                    ('r5d.4xlarge', (None, 80.0, 90.0)),
                    ('r5d.8xlarge', (None, 80.0, 90.0)),
                    ('r5d.12xlarge', (None, 80.0, 90.0)),
                    ('r5d.16xlarge', (None, 80.0, 90.0)),
                    ('r5d.24xlarge', (None, 80.0, 90.0)),
                    ('r5d.large', (None, 80.0, 90.0)),
                    ('r5d.metal', (None, 80.0, 90.0)),
                    ('r5d.xlarge', (None, 80.0, 90.0)),
                    ('x1.16xlarge', (None, 80.0, 90.0)),
                    ('x1.32xlarge', (None, 80.0, 90.0)),
                    ('x1e.2xlarge', (None, 80.0, 90.0)),
                    ('x1e.4xlarge', (None, 80.0, 90.0)),
                    ('x1e.8xlarge', (None, 80.0, 90.0)),
                    ('x1e.16xlarge', (None, 80.0, 90.0)),
                    ('x1e.32xlarge', (None, 80.0, 90.0)),
                    ('x1e.xlarge', (None, 80.0, 90.0)),
                    ('z1d.2xlarge', (None, 80.0, 90.0)),
                    ('z1d.3xlarge', (None, 80.0, 90.0)),
                    ('z1d.6xlarge', (None, 80.0, 90.0)),
                    ('z1d.12xlarge', (None, 80.0, 90.0)),
                    ('z1d.large', (None, 80.0, 90.0)),
                    ('z1d.xlarge', (None, 80.0, 90.0)),
                    ('m2.xlarge', (None, 80.0, 90.0)),
                    ('m2.2xlarge', (None, 80.0, 90.0)),
                    ('m2.4xlarge', (None, 80.0, 90.0)),
                    ('cr1.8xlarge', (None, 80.0, 90.0)),
                    ('c3.large', (None, 80.0, 90.0)),
                    ('c3.xlarge', (None, 80.0, 90.0)),
                    ('c3.2xlarge', (None, 80.0, 90.0)),
                    ('c3.4xlarge', (None, 80.0, 90.0)),
                    ('c3.8xlarge', (None, 80.0, 90.0)),
                    ('c4.large', (None, 80.0, 90.0)),
                    ('c4.xlarge', (None, 80.0, 90.0)),
                    ('c4.2xlarge', (None, 80.0, 90.0)),
                    ('c4.4xlarge', (None, 80.0, 90.0)),
                    ('c4.8xlarge', (None, 80.0, 90.0)),
                    ('c5.18xlarge', (None, 80.0, 90.0)),
                    ('c5.2xlarge', (None, 80.0, 90.0)),
                    ('c5.4xlarge', (None, 80.0, 90.0)),
                    ('c5.9xlarge', (None, 80.0, 90.0)),
                    ('c5.large', (None, 80.0, 90.0)),
                    ('c5.xlarge', (None, 80.0, 90.0)),
                    ('c5d.18xlarge', (None, 80.0, 90.0)),
                    ('c5d.2xlarge', (None, 80.0, 90.0)),
                    ('c5d.4xlarge', (None, 80.0, 90.0)),
                    ('c5d.9xlarge', (None, 80.0, 90.0)),
                    ('c5d.large', (None, 80.0, 90.0)),
                    ('c5d.xlarge', (None, 80.0, 90.0)),
                    ('c5n.18xlarge', (None, 80.0, 90.0)),
                    ('c5n.2xlarge', (None, 80.0, 90.0)),
                    ('c5n.4xlarge', (None, 80.0, 90.0)),
                    ('c5n.9xlarge', (None, 80.0, 90.0)),
                    ('c5n.large', (None, 80.0, 90.0)),
                    ('c5n.xlarge', (None, 80.0, 90.0)),
                    ('c1.medium', (None, 80.0, 90.0)),
                    ('c1.xlarge', (None, 80.0, 90.0)),
                    ('cc2.8xlarge', (None, 80.0, 90.0)),
                    ('cc1.4xlarge', (None, 80.0, 90.0)),
                    ('f1.4xlarge', (None, 80.0, 90.0)),
                    ('p2.xlarge', (None, 80.0, 90.0)),
                    ('p2.8xlarge', (None, 80.0, 90.0)),
                    ('p2.16xlarge', (None, 80.0, 90.0)),
                    ('p3.16xlarge', (None, 80.0, 90.0)),
                    ('p3.2xlarge', (None, 80.0, 90.0)),
                    ('p3.8xlarge', (None, 80.0, 90.0)),
                    ('p3dn.24xlarge', (None, 80.0, 90.0)),
                    ('i2.xlarge', (None, 80.0, 90.0)),
                    ('i2.2xlarge', (None, 80.0, 90.0)),
                    ('i2.4xlarge', (None, 80.0, 90.0)),
                    ('i2.8xlarge', (None, 80.0, 90.0)),
                    ('i3.large', (None, 80.0, 90.0)),
                    ('i3.xlarge', (None, 80.0, 90.0)),
                    ('i3.2xlarge', (None, 80.0, 90.0)),
                    ('i3.4xlarge', (None, 80.0, 90.0)),
                    ('i3.8xlarge', (None, 80.0, 90.0)),
                    ('i3.16xlarge', (None, 80.0, 90.0)),
                    ('i3.metal', (None, 80.0, 90.0)),
                    ('h1.16xlarge', (None, 80.0, 90.0)),
                    ('h1.2xlarge', (None, 80.0, 90.0)),
                    ('h1.4xlarge', (None, 80.0, 90.0)),
                    ('h1.8xlarge', (None, 80.0, 90.0)),
                    ('hi1.4xlarge', (None, 80.0, 90.0)),
                    ('hs1.8xlarge', (None, 80.0, 90.0)),
                    ('d2.xlarge', (None, 80.0, 90.0)),
                    ('d2.2xlarge', (None, 80.0, 90.0)),
                    ('d2.4xlarge', (None, 80.0, 90.0)),
                    ('d2.8xlarge', (None, 80.0, 90.0)),
                    ('g2.2xlarge', (None, 80.0, 90.0)),
                    ('g2.8xlarge', (None, 80.0, 90.0)),
                    ('g3.16xlarge', (None, 80.0, 90.0)),
                    ('g3.4xlarge', (None, 80.0, 90.0)),
                    ('g3.8xlarge', (None, 80.0, 90.0)),
                    ('g3s.xlarge', (None, 80.0, 90.0)),
                    ('cg1.4xlarge', (None, 80.0, 90.0)),
                    ('f1.2xlarge', (None, 80.0, 90.0)),
                    ('f1.16xlarge', (None, 80.0, 90.0))
                ],
                'active_spot_fleet_requests': (None, 80.0, 90.0),
                'spot_fleet_total_target_capacity': (None, 80.0, 90.0),
                'spot_inst_requests': (None, 80.0, 90.0),
                'if_vpc_sec_group': (None, 80.0, 90.0),
                'vpc_sec_group_rules': (None, 80.0, 90.0),
                'elastic_ip_addresses': (None, 80.0, 90.0),
                'running_ondemand_instances_total': (None, 80.0, 90.0),
                'running_ondemand_instances_vcpus': [
                    ('__vcpu', (None, 80.0, 90.0)),
                    ('p_vcpu', (None, 80.0, 90.0)),
                    ('x_vcpu', (None, 80.0, 90.0)),
                    ('g_vcpu', (None, 80.0, 90.0)),
                    ('f_vcpu', (None, 80.0, 90.0))
                ],
                'vpc_sec_groups': (None, 80.0, 90.0)
            }, [
                (
                    0, 'No levels reached', [
                        (
                            'aws_ec2_running_ondemand_instances_t2.medium', 3,
                            None, None, None, None
                        ),
                        (
                            'aws_ec2_running_ondemand_instances___vcpu', 8,
                            None, None, None, None
                        ),
                        (
                            'aws_ec2_running_ondemand_instances_t2.nano', 2,
                            None, None, None, None
                        ),
                        (
                            'aws_ec2_running_ondemand_instances_total', 5,
                            None, None, None, None
                        ),
                        (
                            'aws_ec2_vpc_elastic_ip_addresses', 0, None, None,
                            None, None
                        ),
                        (
                            'aws_ec2_elastic_ip_addresses', 0, None, None,
                            None, None
                        ),
                        (
                            'aws_ec2_spot_inst_requests', 0, None, None, None,
                            None
                        ),
                        (
                            'aws_ec2_active_spot_fleet_requests', 0, None,
                            None, None, None
                        ),
                        (
                            'aws_ec2_spot_fleet_total_target_capacity', 0,
                            None, None, None, None
                        )
                    ]
                ),
                (
                    0,
                    '\nActive Spot Fleet Requests: 0 (of max. 1000)\nElastic IP Addresses: 0 (of '
                    'max. 5)\nRunning On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances '
                    'vCPUs: 8 (of max. 1152)\nRunning On-Demand t2.medium Instances: 3 (of max. '
                    '20)\nRunning On-Demand t2.nano Instances: 2 (of max. 20)\nSpot Fleet Requests '
                    'Total Target Capacity: 0 (of max. 5000)\nSpot Instance Requests: 0 (of max. '
                    '20)\nTotal Running On-Demand Instances: 5 (of max. 20)\nVPC Elastic IP '
                    'Addresses: 0 (of max. 5)'
                )
            ]
        ),
        (
            "eu-central-1", {
                'vpc_elastic_ip_addresses': (None, 80.0, 90.0),
                'running_ondemand_instances': [
                    ('t2.nano', (10, 80.0, 90.0)),
                    ('t2.medium', (10, 80.0, 90.0))
                ],
                'active_spot_fleet_requests': (None, 80.0, 90.0),
                'spot_fleet_total_target_capacity': (None, 80.0, 90.0),
                'elastic_ip_addresses': (None, 80.0, 90.0),
                'if_vpc_sec_group': (None, 80.0, 90.0),
                'vpc_sec_group_rules': (None, 80.0, 90.0),
                'spot_inst_requests': (None, 80.0, 90.0),
                'running_ondemand_instances_total': (None, 80.0, 90.0),
                'running_ondemand_instances_vcpus':
                [('__vcpu', (10, 50.0, 70.0))],
                'vpc_sec_groups': (None, 80.0, 90.0)
            }, [
                (
                    2,
                    'Levels reached: Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) '
                    'instances vCPUs',
                    [
                        (
                            'aws_ec2_running_ondemand_instances_t2.medium', 3,
                            None, None, None, None
                        ),
                        (
                            'aws_ec2_running_ondemand_instances___vcpu', 8,
                            None, None, None, None
                        ),
                        (
                            'aws_ec2_running_ondemand_instances_t2.nano', 2,
                            None, None, None, None
                        ),
                        (
                            'aws_ec2_running_ondemand_instances_total', 5,
                            None, None, None, None
                        ),
                        (
                            'aws_ec2_vpc_elastic_ip_addresses', 0, None, None,
                            None, None
                        ),
                        (
                            'aws_ec2_elastic_ip_addresses', 0, None, None,
                            None, None
                        ),
                        (
                            'aws_ec2_spot_inst_requests', 0, None, None, None,
                            None
                        ),
                        (
                            'aws_ec2_active_spot_fleet_requests', 0, None,
                            None, None, None
                        ),
                        (
                            'aws_ec2_spot_fleet_total_target_capacity', 0,
                            None, None, None, None
                        )
                    ]
                ),
                (
                    0,
                    '\nActive Spot Fleet Requests: 0 (of max. 1000)\nElastic IP Addresses: 0 (of '
                    'max. 5)\nRunning On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances '
                    'vCPUs: 8 (of max. 10), Usage: 80.00% (warn/crit at 50.00%/70.00%)(!!)\nRunning '
                    'On-Demand t2.medium Instances: 3 (of max. 10)\nRunning On-Demand t2.nano '
                    'Instances: 2 (of max. 10)\nSpot Fleet Requests Total Target Capacity: 0 (of '
                    'max. 5000)\nSpot Instance Requests: 0 (of max. 20)\nTotal Running On-Demand '
                    'Instances: 5 (of max. 20)\nVPC Elastic IP Addresses: 0 (of max. 5)'
                )
            ]
        )
    ]
}
