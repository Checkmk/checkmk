#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from cmk.base.plugins.agent_based.utils.aws import (
    parse_aws,
    extract_aws_metrics_by_labels,
)


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            [[
                '[{"Id":', '"id_10_CPUCreditUsage",', '"Label":',
                '"172.31.41.207-eu-central-1-i-08363bfeff774e12c",', '"Timestamps":',
                '["2020-12-01', '12:24:00+00:00"],', '"Values":', '[[0.0030055,', 'null]],',
                '"StatusCode":', '"Complete"},', '{"Id":', '"id_10_CPUCreditBalance",', '"Label":',
                '"172.31.41.207-eu-central-1-i-08363bfeff774e12c",', '"Timestamps":',
                '["2020-12-01', '12:24:00+00:00"],', '"Values":', '[[29.5837305,', 'null]],',
                '"StatusCode":', '"Complete"},', '{"Id":', '"id_10_CPUUtilization",', '"Label":',
                '"172.31.41.207-eu-central-1-i-08363bfeff774e12c",', '"Timestamps":',
                '["2020-12-01', '12:24:00+00:00"],', '"Values":', '[[0.0499999999999995,',
                'null]],', '"StatusCode":', '"Complete"},', '{"Id":', '"id_10_DiskReadOps",',
                '"Label":', '"172.31.41.207-eu-central-1-i-08363bfeff774e12c",', '"Timestamps":',
                '["2020-12-01', '12:24:00+00:00"],', '"Values":', '[[0.0,', 'null]],',
                '"StatusCode":', '"Complete"},', '{"Id":', '"id_10_DiskWriteOps",', '"Label":',
                '"172.31.41.207-eu-central-1-i-08363bfeff774e12c",', '"Timestamps":',
                '["2020-12-01', '12:24:00+00:00"],', '"Values":', '[[0.0,', 'null]],',
                '"StatusCode":', '"Complete"},', '{"Id":', '"id_10_DiskReadBytes",', '"Label":',
                '"172.31.41.207-eu-central-1-i-08363bfeff774e12c",', '"Timestamps":',
                '["2020-12-01', '12:24:00+00:00"],', '"Values":', '[[0.0,', 'null]],',
                '"StatusCode":', '"Complete"},', '{"Id":', '"id_10_DiskWriteBytes",', '"Label":',
                '"172.31.41.207-eu-central-1-i-08363bfeff774e12c",', '"Timestamps":',
                '["2020-12-01', '12:24:00+00:00"],', '"Values":', '[[0.0,', 'null]],',
                '"StatusCode":', '"Complete"},', '{"Id":', '"id_10_NetworkIn",', '"Label":',
                '"172.31.41.207-eu-central-1-i-08363bfeff774e12c",', '"Timestamps":',
                '["2020-12-01', '12:24:00+00:00"],', '"Values":', '[[702.2,', 'null]],',
                '"StatusCode":', '"Complete"},', '{"Id":', '"id_10_NetworkOut",', '"Label":',
                '"172.31.41.207-eu-central-1-i-08363bfeff774e12c",', '"Timestamps":',
                '["2020-12-01', '12:24:00+00:00"],', '"Values":', '[[369.0,', 'null]],',
                '"StatusCode":', '"Complete"},', '{"Id":', '"id_10_StatusCheckFailed_Instance",',
                '"Label":', '"172.31.41.207-eu-central-1-i-08363bfeff774e12c",', '"Timestamps":',
                '["2020-12-01', '12:24:00+00:00"],', '"Values":', '[[0.0,', 'null]],',
                '"StatusCode":', '"Complete"},', '{"Id":', '"id_10_StatusCheckFailed_System",',
                '"Label":', '"172.31.41.207-eu-central-1-i-08363bfeff774e12c",', '"Timestamps":',
                '["2020-12-01', '12:24:00+00:00"],', '"Values":', '[[0.0,', 'null]],',
                '"StatusCode":', '"Complete"}]'
            ]],
            [{
                'Id': 'id_10_CPUCreditUsage',
                'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
                'Timestamps': ['2020-12-01 12:24:00+00:00'],
                'Values': [[0.0030055, None]],
                'StatusCode': 'Complete'
            }, {
                'Id': 'id_10_CPUCreditBalance',
                'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
                'Timestamps': ['2020-12-01 12:24:00+00:00'],
                'Values': [[29.5837305, None]],
                'StatusCode': 'Complete'
            }, {
                'Id': 'id_10_CPUUtilization',
                'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
                'Timestamps': ['2020-12-01 12:24:00+00:00'],
                'Values': [[0.0499999999999995, None]],
                'StatusCode': 'Complete'
            }, {
                'Id': 'id_10_DiskReadOps',
                'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
                'Timestamps': ['2020-12-01 12:24:00+00:00'],
                'Values': [[0.0, None]],
                'StatusCode': 'Complete'
            }, {
                'Id': 'id_10_DiskWriteOps',
                'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
                'Timestamps': ['2020-12-01 12:24:00+00:00'],
                'Values': [[0.0, None]],
                'StatusCode': 'Complete'
            }, {
                'Id': 'id_10_DiskReadBytes',
                'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
                'Timestamps': ['2020-12-01 12:24:00+00:00'],
                'Values': [[0.0, None]],
                'StatusCode': 'Complete'
            }, {
                'Id': 'id_10_DiskWriteBytes',
                'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
                'Timestamps': ['2020-12-01 12:24:00+00:00'],
                'Values': [[0.0, None]],
                'StatusCode': 'Complete'
            }, {
                'Id': 'id_10_NetworkIn',
                'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
                'Timestamps': ['2020-12-01 12:24:00+00:00'],
                'Values': [[702.2, None]],
                'StatusCode': 'Complete'
            }, {
                'Id': 'id_10_NetworkOut',
                'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
                'Timestamps': ['2020-12-01 12:24:00+00:00'],
                'Values': [[369.0, None]],
                'StatusCode': 'Complete'
            }, {
                'Id': 'id_10_StatusCheckFailed_Instance',
                'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
                'Timestamps': ['2020-12-01 12:24:00+00:00'],
                'Values': [[0.0, None]],
                'StatusCode': 'Complete'
            }, {
                'Id': 'id_10_StatusCheckFailed_System',
                'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
                'Timestamps': ['2020-12-01 12:24:00+00:00'],
                'Values': [[0.0, None]],
                'StatusCode': 'Complete'
            }],
        ),
        (
            [[
                '[{"Description":', '"Joerg', 'Herbels', 'security', 'group",', '"GroupName":',
                '"joerg.herbel.secgroup",', '"IpPermissions":', '[{"FromPort":', '80,',
                '"IpProtocol":', '"tcp",', '"IpRanges":', '[{"CidrIp":', '"0.0.0.0/0"}],',
                '"Ipv6Ranges":', '[{"CidrIpv6":', '"::/0"}],', '"PrefixListIds":', '[],',
                '"ToPort":', '80,', '"UserIdGroupPairs":', '[{"GroupId":',
                '"sg-06368b02de2a8b850",', '"UserId":', '"710145618630"}]},', '{"FromPort":', '0,',
                '"IpProtocol":', '"tcp",', '"IpRanges":', '[{"CidrIp":', '"0.0.0.0/0"}],',
                '"Ipv6Ranges":', '[],', '"PrefixListIds":', '[],', '"ToPort":', '65535,',
                '"UserIdGroupPairs":', '[]},', '{"FromPort":', '80,', '"IpProtocol":', '"tcp",',
                '"IpRanges":', '[{"CidrIp":', '"0.0.0.0/0"}],', '"Ipv6Ranges":', '[{"CidrIpv6":',
                '"::/0"}],', '"PrefixListIds":', '[],', '"ToPort":', '90,', '"UserIdGroupPairs":',
                '[]},', '{"IpProtocol":', '"-1",', '"IpRanges":', '[],', '"Ipv6Ranges":', '[],',
                '"PrefixListIds":', '[],', '"UserIdGroupPairs":', '[{"GroupId":',
                '"sg-06368b02de2a8b850",', '"UserId":', '"710145618630"}]},', '{"FromPort":', '22,',
                '"IpProtocol":', '"tcp",', '"IpRanges":', '[{"CidrIp":', '"0.0.0.0/0"}],',
                '"Ipv6Ranges":', '[{"CidrIpv6":', '"::/0"}],', '"PrefixListIds":', '[],',
                '"ToPort":', '22,', '"UserIdGroupPairs":', '[]},', '{"FromPort":', '5000,',
                '"IpProtocol":', '"tcp",', '"IpRanges":', '[{"CidrIp":', '"0.0.0.0/0"}],',
                '"Ipv6Ranges":', '[{"CidrIpv6":', '"::/0"}],', '"PrefixListIds":', '[],',
                '"ToPort":', '5000,', '"UserIdGroupPairs":', '[]},', '{"FromPort":', '3389,',
                '"IpProtocol":', '"tcp",', '"IpRanges":', '[{"CidrIp":', '"0.0.0.0/0"}],',
                '"Ipv6Ranges":', '[{"CidrIpv6":', '"::/0"}],', '"PrefixListIds":', '[],',
                '"ToPort":', '3389,', '"UserIdGroupPairs":', '[]}],', '"OwnerId":',
                '"710145618630",', '"GroupId":', '"sg-06368b02de2a8b850",',
                '"IpPermissionsEgress":', '[{"IpProtocol":', '"-1",', '"IpRanges":', '[{"CidrIp":',
                '"0.0.0.0/0"}],', '"Ipv6Ranges":', '[],', '"PrefixListIds":', '[],',
                '"UserIdGroupPairs":', '[]}],', '"VpcId":', '"vpc-dc8ba3b7"}]'
            ]],
            [{
                'Description': 'Joerg Herbels security group',
                'GroupName': 'joerg.herbel.secgroup',
                'IpPermissions': [{
                    'FromPort': 80,
                    'IpProtocol': 'tcp',
                    'IpRanges': [{
                        'CidrIp': '0.0.0.0/0'
                    }],
                    'Ipv6Ranges': [{
                        'CidrIpv6': '::/0'
                    }],
                    'PrefixListIds': [],
                    'ToPort': 80,
                    'UserIdGroupPairs': [{
                        'GroupId': 'sg-06368b02de2a8b850',
                        'UserId': '710145618630'
                    }]
                }, {
                    'FromPort': 0,
                    'IpProtocol': 'tcp',
                    'IpRanges': [{
                        'CidrIp': '0.0.0.0/0'
                    }],
                    'Ipv6Ranges': [],
                    'PrefixListIds': [],
                    'ToPort': 65535,
                    'UserIdGroupPairs': []
                }, {
                    'FromPort': 80,
                    'IpProtocol': 'tcp',
                    'IpRanges': [{
                        'CidrIp': '0.0.0.0/0'
                    }],
                    'Ipv6Ranges': [{
                        'CidrIpv6': '::/0'
                    }],
                    'PrefixListIds': [],
                    'ToPort': 90,
                    'UserIdGroupPairs': []
                }, {
                    'IpProtocol': '-1',
                    'IpRanges': [],
                    'Ipv6Ranges': [],
                    'PrefixListIds': [],
                    'UserIdGroupPairs': [{
                        'GroupId': 'sg-06368b02de2a8b850',
                        'UserId': '710145618630'
                    }]
                }, {
                    'FromPort': 22,
                    'IpProtocol': 'tcp',
                    'IpRanges': [{
                        'CidrIp': '0.0.0.0/0'
                    }],
                    'Ipv6Ranges': [{
                        'CidrIpv6': '::/0'
                    }],
                    'PrefixListIds': [],
                    'ToPort': 22,
                    'UserIdGroupPairs': []
                }, {
                    'FromPort': 5000,
                    'IpProtocol': 'tcp',
                    'IpRanges': [{
                        'CidrIp': '0.0.0.0/0'
                    }],
                    'Ipv6Ranges': [{
                        'CidrIpv6': '::/0'
                    }],
                    'PrefixListIds': [],
                    'ToPort': 5000,
                    'UserIdGroupPairs': []
                }, {
                    'FromPort': 3389,
                    'IpProtocol': 'tcp',
                    'IpRanges': [{
                        'CidrIp': '0.0.0.0/0'
                    }],
                    'Ipv6Ranges': [{
                        'CidrIpv6': '::/0'
                    }],
                    'PrefixListIds': [],
                    'ToPort': 3389,
                    'UserIdGroupPairs': []
                }],
                'OwnerId': '710145618630',
                'GroupId': 'sg-06368b02de2a8b850',
                'IpPermissionsEgress': [{
                    'IpProtocol': '-1',
                    'IpRanges': [{
                        'CidrIp': '0.0.0.0/0'
                    }],
                    'Ipv6Ranges': [],
                    'PrefixListIds': [],
                    'UserIdGroupPairs': []
                }],
                'VpcId': 'vpc-dc8ba3b7'
            }],
        ),
    ],
)
def test_parse_aws(string_table, expected_result):
    assert parse_aws(string_table) == expected_result


@pytest.mark.parametrize(
    "expected_metric_names, section, expected_result",
    [(
        [
            'CPUCreditUsage', 'CPUCreditBalance', 'CPUUtilization', 'DiskReadOps', 'DiskWriteOps',
            'DiskReadBytes', 'DiskWriteBytes', 'NetworkIn', 'NetworkOut',
            'StatusCheckFailed_Instance', 'StatusCheckFailed_System'
        ],
        [{
            'Id': 'id_10_CPUCreditUsage',
            'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
            'Timestamps': ['2020-12-01 12:45:00+00:00'],
            'Values': [[0.0021155, None]],
            'StatusCode': 'Complete'
        }, {
            'Id': 'id_10_CPUCreditBalance',
            'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
            'Timestamps': ['2020-12-01 12:45:00+00:00'],
            'Values': [[31.5750585, None]],
            'StatusCode': 'Complete'
        }, {
            'Id': 'id_10_CPUUtilization',
            'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
            'Timestamps': ['2020-12-01 12:45:00+00:00'],
            'Values': [[0.0322580645161318, None]],
            'StatusCode': 'Complete'
        }, {
            'Id': 'id_10_DiskReadOps',
            'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
            'Timestamps': ['2020-12-01 12:45:00+00:00'],
            'Values': [[0.0, None]],
            'StatusCode': 'Complete'
        }, {
            'Id': 'id_10_DiskWriteOps',
            'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
            'Timestamps': ['2020-12-01 12:45:00+00:00'],
            'Values': [[0.0, None]],
            'StatusCode': 'Complete'
        }, {
            'Id': 'id_10_DiskReadBytes',
            'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
            'Timestamps': ['2020-12-01 12:45:00+00:00'],
            'Values': [[0.0, None]],
            'StatusCode': 'Complete'
        }, {
            'Id': 'id_10_DiskWriteBytes',
            'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
            'Timestamps': ['2020-12-01 12:45:00+00:00'],
            'Values': [[0.0, None]],
            'StatusCode': 'Complete'
        }, {
            'Id': 'id_10_NetworkIn',
            'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
            'Timestamps': ['2020-12-01 12:45:00+00:00'],
            'Values': [[840.4, None]],
            'StatusCode': 'Complete'
        }, {
            'Id': 'id_10_NetworkOut',
            'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
            'Timestamps': ['2020-12-01 12:45:00+00:00'],
            'Values': [[466.0, None]],
            'StatusCode': 'Complete'
        }, {
            'Id': 'id_10_StatusCheckFailed_Instance',
            'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
            'Timestamps': ['2020-12-01 12:45:00+00:00'],
            'Values': [[0.0, None]],
            'StatusCode': 'Complete'
        }, {
            'Id': 'id_10_StatusCheckFailed_System',
            'Label': '172.31.41.207-eu-central-1-i-08363bfeff774e12c',
            'Timestamps': ['2020-12-01 12:45:00+00:00'],
            'Values': [[0.0, None]],
            'StatusCode': 'Complete'
        }],
        {
            '172.31.41.207-eu-central-1-i-08363bfeff774e12c': {
                'CPUCreditUsage': 0.0021155,
                'CPUCreditBalance': 31.5750585,
                'CPUUtilization': 0.0322580645161318,
                'DiskReadOps': 0.0,
                'DiskWriteOps': 0.0,
                'DiskReadBytes': 0.0,
                'DiskWriteBytes': 0.0,
                'NetworkIn': 840.4,
                'NetworkOut': 466.0,
                'StatusCheckFailed_Instance': 0.0,
                'StatusCheckFailed_System': 0.0
            }
        },
    )],
)
def test_extract_aws_metrics_by_labels(expected_metric_names, section, expected_result):
    assert extract_aws_metrics_by_labels(expected_metric_names, section) == expected_result
