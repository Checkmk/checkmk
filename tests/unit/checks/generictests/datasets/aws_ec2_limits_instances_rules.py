#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "aws_ec2_limits"

info = [
    [
        '[["running_ondemand_instances_t2.medium",',
        '"Running',
        "On-Demand",
        "t2.medium",
        'Instances",',
        "3,",
        "3,",
        '"eu-central-1"],',
        '["running_ondemand_instances_t2.nano",',
        '"Running',
        "On-Demand",
        "t2.nano",
        'Instances",',
        "20,",
        "5,",
        '"eu-central-1"],',
        '["running_ondemand_instances_total",',
        '"Total',
        "Running",
        "On-Demand",
        'Instances",',
        "20,",
        "4,",
        '"eu-central-1"],',
        '["vpc_elastic_ip_addresses",',
        '"VPC',
        "Elastic",
        "IP",
        'Addresses",',
        "5,",
        "0,",
        '"eu-central-1"],',
        '["elastic_ip_addresses",',
        '"Elastic',
        "IP",
        'Addresses",',
        "5,",
        "0,",
        '"eu-central-1"],',
        '["spot_inst_requests",',
        '"Spot',
        "Instance",
        'Requests",',
        "20,",
        "0,",
        '"eu-central-1"],',
        '["active_spot_fleet_requests",',
        '"Active',
        "Spot",
        "Fleet",
        'Requests",',
        "1000,",
        "0,",
        '"eu-central-1"],',
        '["spot_fleet_total_target_capacity",',
        '"Spot',
        "Fleet",
        "Requests",
        "Total",
        "Target",
        'Capacity",',
        "5000,",
        "0,",
        '"eu-central-1"]]',
    ]
]

discovery = {"": [("eu-central-1", {})]}

checks = {
    "": [
        (
            "eu-central-1",
            {
                "spot_fleet_total_target_capacity": (None, 80.0, 90.0),
                "vpc_elastic_ip_addresses": (None, 80.0, 90.0),
                "if_vpc_sec_group": (None, 80.0, 90.0),
                "running_ondemand_instances": [("t2.nano", (6, 80.0, 90.0))],
                "active_spot_fleet_requests": (None, 80.0, 90.0),
                "running_ondemand_instances_total": (None, 80.0, 90.0),
                "vpc_sec_groups": (None, 80.0, 90.0),
                "vpc_sec_group_rules": (None, 80.0, 90.0),
                "spot_inst_requests": (None, 80.0, 90.0),
                "elastic_ip_addresses": (None, 80.0, 90.0),
            },
            [
                (
                    2,
                    "Levels reached: Running On-Demand t2.medium Instances, Running On-Demand "
                    "t2.nano Instances",
                    [
                        ("aws_ec2_running_ondemand_instances_t2.medium", 3, None, None, None, None),
                        ("aws_ec2_running_ondemand_instances_t2.nano", 5, None, None, None, None),
                        ("aws_ec2_running_ondemand_instances_total", 4, None, None, None, None),
                        ("aws_ec2_vpc_elastic_ip_addresses", 0, None, None, None, None),
                        ("aws_ec2_elastic_ip_addresses", 0, None, None, None, None),
                        ("aws_ec2_spot_inst_requests", 0, None, None, None, None),
                        ("aws_ec2_active_spot_fleet_requests", 0, None, None, None, None),
                        ("aws_ec2_spot_fleet_total_target_capacity", 0, None, None, None, None),
                    ],
                ),
                (0, "\nActive Spot Fleet Requests: 0 (of max. 1000)"),
                (0, "\nElastic IP Addresses: 0 (of max. 5)"),
                (2, "\nRunning On-Demand t2.medium Instances: 3 (of max. 3), Usage: 100.00% (warn/crit at 80.00%/90.00%)"),
                (1, "\nRunning On-Demand t2.nano Instances: 5 (of max. 6), Usage: 83.33% (warn/crit at 80.00%/90.00%)"),
                (0, "\nSpot Fleet Requests Total Target Capacity: 0 (of max. 5000)"),
                (0, "\nSpot Instance Requests: 0 (of max. 20)"),
                (0, "\nTotal Running On-Demand Instances: 4 (of max. 20)"),
                (0, "\nVPC Elastic IP Addresses: 0 (of max. 5)"),
            ],
        ),
    ]
}
