#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#.
#   .--for imports---------------------------------------------------------.
#   |         __              _                            _               |
#   |        / _| ___  _ __  (_)_ __ ___  _ __   ___  _ __| |_ ___         |
#   |       | |_ / _ \| '__| | | '_ ` _ \| '_ \ / _ \| '__| __/ __|        |
#   |       |  _| (_) | |    | | | | | | | |_) | (_) | |  | |_\__ \        |
#   |       |_|  \___/|_|    |_|_| |_| |_| .__/ \___/|_|   \__|___/        |
#   |                                    |_|                               |
#   '----------------------------------------------------------------------'
#   .--regions--------------------------------------------------------------

AWSRegions = [
    ("ap-south-1", "Asia Pacific (Mumbai)"),
    ("ap-northeast-3", "Asia Pacific (Osaka-Local)"),
    ("ap-northeast-2", "Asia Pacific (Seoul)"),
    ("ap-southeast-1", "Asia Pacific (Singapore)"),
    ("ap-southeast-2", "Asia Pacific (Sydney)"),
    ("ap-northeast-1", "Asia Pacific (Tokyo)"),
    ("ca-central-1", "Canada (Central)"),
    ("cn-north-1", "China (Beijing)"),
    ("cn-northwest-1", "China (Ningxia)"),
    ("eu-central-1", "EU (Frankfurt)"),
    ("eu-west-1", "EU (Ireland)"),
    ("eu-west-2", "EU (London)"),
    ("eu-west-3", "EU (Paris)"),
    ("eu-north-1", "EU (Stockholm)"),
    ("sa-east-1", "South America (Sao Paulo)"),
    ("us-east-2", "US East (Ohio)"),
    ("us-east-1", "US East (N. Virginia)"),
    ("us-west-1", "US West (N. California)"),
    ("us-west-2", "US West (Oregon)"),
]

#.
#   .--EC2 instance types---------------------------------------------------
"""
to get all instance types from the API, do something like:

instance_types = []

for region in AWSRegions:

    try:
        session = boto3.session.Session(aws_access_key_id=...,
                                        aws_secret_access_key=...,
                                        region_name=region[0])
        ec2_client = session.client('ec2')

        for page in ec2_client.get_paginator('describe_instance_types').paginate():
            instance_types.extend([instance_descr['InstanceType'] for instance_descr in page['InstanceTypes']])

    except Exception as e:
        pass

instance_types = set(instance_types)
"""

# the first list is the result of the API calls, the second list are instances we had listed before
# (without using the API) and which are not returned by the API, so they can probably be removed

AWSEC2InstTypes = [
    'a1.2xlarge', 'a1.4xlarge', 'a1.large', 'a1.medium', 'a1.metal', 'a1.xlarge', 'c1.medium',
    'c1.xlarge', 'c3.2xlarge', 'c3.4xlarge', 'c3.8xlarge', 'c3.large', 'c3.xlarge', 'c4.2xlarge',
    'c4.4xlarge', 'c4.8xlarge', 'c4.large', 'c4.xlarge', 'c5.12xlarge', 'c5.18xlarge',
    'c5.24xlarge', 'c5.2xlarge', 'c5.4xlarge', 'c5.9xlarge', 'c5.large', 'c5.metal', 'c5.xlarge',
    'c5d.12xlarge', 'c5d.18xlarge', 'c5d.24xlarge', 'c5d.2xlarge', 'c5d.4xlarge', 'c5d.9xlarge',
    'c5d.large', 'c5d.metal', 'c5d.xlarge', 'c5n.18xlarge', 'c5n.2xlarge', 'c5n.4xlarge',
    'c5n.9xlarge', 'c5n.large', 'c5n.metal', 'c5n.xlarge', 'cc2.8xlarge', 'd2.2xlarge',
    'd2.4xlarge', 'd2.8xlarge', 'd2.xlarge', 'f1.16xlarge', 'f1.2xlarge', 'f1.4xlarge',
    'g2.2xlarge', 'g2.8xlarge', 'g3.16xlarge', 'g3.4xlarge', 'g3.8xlarge', 'g3s.xlarge',
    'g4dn.12xlarge', 'g4dn.16xlarge', 'g4dn.2xlarge', 'g4dn.4xlarge', 'g4dn.8xlarge', 'g4dn.metal',
    'g4dn.xlarge', 'h1.16xlarge', 'h1.2xlarge', 'h1.4xlarge', 'h1.8xlarge', 'i2.2xlarge',
    'i2.4xlarge', 'i2.8xlarge', 'i2.xlarge', 'i3.16xlarge', 'i3.2xlarge', 'i3.4xlarge',
    'i3.8xlarge', 'i3.large', 'i3.metal', 'i3.xlarge', 'i3en.12xlarge', 'i3en.24xlarge',
    'i3en.2xlarge', 'i3en.3xlarge', 'i3en.6xlarge', 'i3en.large', 'i3en.metal', 'i3en.xlarge',
    'inf1.24xlarge', 'inf1.2xlarge', 'inf1.6xlarge', 'inf1.xlarge', 'm1.large', 'm1.medium',
    'm1.small', 'm1.xlarge', 'm2.2xlarge', 'm2.4xlarge', 'm2.xlarge', 'm3.2xlarge', 'm3.large',
    'm3.medium', 'm3.xlarge', 'm4.10xlarge', 'm4.16xlarge', 'm4.2xlarge', 'm4.4xlarge', 'm4.large',
    'm4.xlarge', 'm5.12xlarge', 'm5.16xlarge', 'm5.24xlarge', 'm5.2xlarge', 'm5.4xlarge',
    'm5.8xlarge', 'm5.large', 'm5.metal', 'm5.xlarge', 'm5a.12xlarge', 'm5a.16xlarge',
    'm5a.24xlarge', 'm5a.2xlarge', 'm5a.4xlarge', 'm5a.8xlarge', 'm5a.large', 'm5a.xlarge',
    'm5ad.12xlarge', 'm5ad.16xlarge', 'm5ad.24xlarge', 'm5ad.2xlarge', 'm5ad.4xlarge',
    'm5ad.8xlarge', 'm5ad.large', 'm5ad.xlarge', 'm5d.12xlarge', 'm5d.16xlarge', 'm5d.24xlarge',
    'm5d.2xlarge', 'm5d.4xlarge', 'm5d.8xlarge', 'm5d.large', 'm5d.metal', 'm5d.xlarge',
    'm5dn.12xlarge', 'm5dn.16xlarge', 'm5dn.24xlarge', 'm5dn.2xlarge', 'm5dn.4xlarge',
    'm5dn.8xlarge', 'm5dn.large', 'm5dn.xlarge', 'm5n.12xlarge', 'm5n.16xlarge', 'm5n.24xlarge',
    'm5n.2xlarge', 'm5n.4xlarge', 'm5n.8xlarge', 'm5n.large', 'm5n.xlarge', 'p2.16xlarge',
    'p2.8xlarge', 'p2.xlarge', 'p3.16xlarge', 'p3.2xlarge', 'p3.8xlarge', 'p3dn.24xlarge',
    'r3.2xlarge', 'r3.4xlarge', 'r3.8xlarge', 'r3.large', 'r3.xlarge', 'r4.16xlarge', 'r4.2xlarge',
    'r4.4xlarge', 'r4.8xlarge', 'r4.large', 'r4.xlarge', 'r5.12xlarge', 'r5.16xlarge',
    'r5.24xlarge', 'r5.2xlarge', 'r5.4xlarge', 'r5.8xlarge', 'r5.large', 'r5.metal', 'r5.xlarge',
    'r5a.12xlarge', 'r5a.16xlarge', 'r5a.24xlarge', 'r5a.2xlarge', 'r5a.4xlarge', 'r5a.8xlarge',
    'r5a.large', 'r5a.xlarge', 'r5ad.12xlarge', 'r5ad.16xlarge', 'r5ad.24xlarge', 'r5ad.2xlarge',
    'r5ad.4xlarge', 'r5ad.8xlarge', 'r5ad.large', 'r5ad.xlarge', 'r5d.12xlarge', 'r5d.16xlarge',
    'r5d.24xlarge', 'r5d.2xlarge', 'r5d.4xlarge', 'r5d.8xlarge', 'r5d.large', 'r5d.metal',
    'r5d.xlarge', 'r5dn.12xlarge', 'r5dn.16xlarge', 'r5dn.24xlarge', 'r5dn.2xlarge', 'r5dn.4xlarge',
    'r5dn.8xlarge', 'r5dn.large', 'r5dn.xlarge', 'r5n.12xlarge', 'r5n.16xlarge', 'r5n.24xlarge',
    'r5n.2xlarge', 'r5n.4xlarge', 'r5n.8xlarge', 'r5n.large', 'r5n.xlarge', 't1.micro',
    't2.2xlarge', 't2.large', 't2.medium', 't2.micro', 't2.nano', 't2.small', 't2.xlarge',
    't3.2xlarge', 't3.large', 't3.medium', 't3.micro', 't3.nano', 't3.small', 't3.xlarge',
    't3a.2xlarge', 't3a.large', 't3a.medium', 't3a.micro', 't3a.nano', 't3a.small', 't3a.xlarge',
    'x1.16xlarge', 'x1.32xlarge', 'x1e.16xlarge', 'x1e.2xlarge', 'x1e.32xlarge', 'x1e.4xlarge',
    'x1e.8xlarge', 'x1e.xlarge', 'z1d.12xlarge', 'z1d.2xlarge', 'z1d.3xlarge', 'z1d.6xlarge',
    'z1d.large', 'z1d.metal', 'z1d.xlarge'
] + ['cr1.8xlarge', 'cc1.4xlarge', 'hi1.4xlarge', 'hs1.8xlarge', 'cg1.4xlarge']

AWSEC2InstFamilies = {
    'f': 'Running On-Demand F instances',
    'g': 'Running On-Demand G instances',
    'inf': 'Running On-Demand Inf instances',
    'p': 'Running On-Demand P instances',
    'x': 'Running On-Demand X instances',
    '_': 'Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances'
}

# (On-Demand, Reserved, Spot)
AWSEC2LimitsDefault = (20, 20, 5)

AWSEC2LimitsSpecial = {
    'c4.4xlarge': (10, 20, 5),
    'c4.8xlarge': (5, 20, 5),
    'c5.4xlarge': (10, 20, 5),
    'c5.9xlarge': (5, 20, 5),
    'c5.18xlarge': (5, 20, 5),
    'cg1.4xlarge': (2, 20, 5),
    'cr1.8xlarge': (2, 20, 5),
    'd2.4xlarge': (10, 20, 5),
    'd2.8xlarge': (5, 20, 5),
    'g2.2xlarge': (5, 20, 5),
    'g2.8xlarge': (2, 20, 5),
    'g3.4xlarge': (1, 20, 5),
    'g3.8xlarge': (1, 20, 5),
    'g3.16xlarge': (1, 20, 5),
    'h1.8xlarge': (10, 20, 5),
    'h1.16xlarge': (5, 20, 5),
    'hi1.4xlarge': (2, 20, 5),
    'hs1.8xlarge': (2, 20, 0),
    'i2.2xlarge': (8, 20, 0),
    'i2.4xlarge': (4, 20, 0),
    'i2.8xlarge': (2, 20, 0),
    'i2.xlarge': (8, 20, 0),
    'i3.2xlarge': (2, 20, 0),
    'i3.4xlarge': (2, 20, 0),
    'i3.8xlarge': (2, 20, 0),
    'i3.16xlarge': (2, 20, 0),
    'i3.large': (2, 20, 0),
    'i3.xlarge': (2, 20, 0),
    'm4.4xlarge': (10, 20, 5),
    'm4.10xlarge': (5, 20, 5),
    'm4.16xlarge': (5, 20, 5),
    'm5.4xlarge': (10, 20, 5),
    'm5.12xlarge': (5, 20, 5),
    'm5.24xlarge': (5, 20, 5),
    'p2.8xlarge': (1, 20, 5),
    'p2.16xlarge': (1, 20, 5),
    'p2.xlarge': (1, 20, 5),
    'p3.2xlarge': (1, 20, 5),
    'p3.8xlarge': (1, 20, 5),
    'p3.16xlarge': (1, 20, 5),
    'p3dn.24xlarge': (1, 20, 5),
    'r3.4xlarge': (10, 20, 5),
    'r3.8xlarge': (5, 20, 5),
    'r4.4xlarge': (10, 20, 5),
    'r4.8xlarge': (5, 20, 5),
    'r4.16xlarge': (1, 20, 5),
    'f_vcpu': (128, None, None),
    'g_vcpu': (128, None, None),
    'inf_vcpu': (128, None, None),
    'p_vcpu': (128, None, None),
    'x_vcpu': (128, None, None),
    '__vcpu': (1152, None, None),
}
