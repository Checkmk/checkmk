# encoding: utf-8

import pytest

from cmk.special_agents.agent_aws import (
    AWSConfig,
    ResultDistributor,
    CloudwatchAlarmsLimits,
    CloudwatchAlarms,
)

#TODO what about enums?

#   .--fake client---------------------------------------------------------.
#   |             __       _               _ _            _                |
#   |            / _| __ _| | _____    ___| (_) ___ _ __ | |_              |
#   |           | |_ / _` | |/ / _ \  / __| | |/ _ \ '_ \| __|             |
#   |           |  _| (_| |   <  __/ | (__| | |  __/ | | | |_              |
#   |           |_|  \__,_|_|\_\___|  \___|_|_|\___|_| |_|\__|             |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class FakeCloudwatchClient(object):
    def describe_alarms(self, AlarmNames=None):
        alarms = [
            {
                'AlarmName': 'string1',
                'AlarmArn': 'string1',
                'AlarmDescription': 'string1',
                'AlarmConfigurationUpdatedTimestamp': "datetime(2015, 1, 1)",
                'ActionsEnabled': "True|False",
                'OKActions': ['string1',],
                'AlarmActions': ['string1',],
                'InsufficientDataActions': ['string1',],
                'StateValue': "'OK' | 'ALARM' | 'INSUFFICIENT_DATA'",
                'StateReason': 'string1',
                'StateReasonData': 'string1',
                'StateUpdatedTimestamp': "datetime(2015, 1, 1)",
                'MetricName': 'string1',
                'Namespace': 'string1',
                'Statistic': "'SampleCount' | 'Average' | 'Sum' | 'Minimum' | 'Maximum'",
                'ExtendedStatistic': 'string1',
                'Dimensions': [{
                    'Name': 'string1',
                    'Value': 'string1'
                },],
                'Period': 123,
                'Unit': "'Seconds' | 'Microseconds' | 'Milliseconds' | 'Bytes' | 'Kilobytes' |"
                        "'Megabytes' | 'Gigabytes' | 'Terabytes' | 'Bits' | 'Kilobits' |"
                        "'Megabits' | 'Gigabits' | 'Terabits' | 'Percent' | 'Count' |"
                        "'Bytes/Second' | 'Kilobytes/Second' | 'Megabytes/Second' |"
                        "'Gigabytes/Second' | 'Terabytes/Second' | 'Bits/Second' |"
                        "'Kilobits/Second' | 'Megabits/Second' | 'Gigabits/Second' |"
                        "'Terabits/Second' | 'Count/Second' | 'None'",
                'EvaluationPeriods': 123,
                'DatapointsToAlarm': 123,
                'Threshold': 123.0,
                'ComparisonOperator': "'GreaterThanOrEqualToThreshold' | 'GreaterThanThreshold' |"
                                      "'LessThanThreshold' | 'LessThanOrEqualToThreshold'",
                'TreatMissingData': 'string1',
                'EvaluateLowSampleCountPercentile': 'string1',
                'Metrics': [{
                    'Id': 'string1',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'string1',
                            'MetricName': 'string1',
                            'Dimensions': [{
                                'Name': 'string1',
                                'Value': 'string1'
                            },]
                        },
                        'Period': 123,
                        'Stat': 'string1',
                        'Unit': "'Seconds' | 'Microseconds' | 'Milliseconds' | 'Bytes' |"
                                "'Kilobytes' | 'Megabytes' | 'Gigabytes' | 'Terabytes' | 'Bits' |"
                                "'Kilobits' | 'Megabits' | 'Gigabits' | 'Terabits' | 'Percent' |"
                                "'Count' | 'Bytes/Second' | 'Kilobytes/Second' |"
                                "'Megabytes/Second' | 'Gigabytes/Second' | 'Terabytes/Second' |"
                                "'Bits/Second' | 'Kilobits/Second' | 'Megabits/Second' |"
                                "'Gigabits/Second' | 'Terabits/Second' | 'Count/Second' | 'None'"
                    },
                    'Expression': 'string1',
                    'Label': 'string1',
                    'ReturnData': "True|False"
                },]
            },
            {
                'AlarmName': 'string2',
                'AlarmArn': 'string2',
                'AlarmDescription': 'string2',
                'AlarmConfigurationUpdatedTimestamp': "datetime(2015, 1, 1)",
                'ActionsEnabled': "True|False",
                'OKActions': ['string2',],
                'AlarmActions': ['string2',],
                'InsufficientDataActions': ['string2',],
                'StateValue': "'OK' | 'ALARM' | 'INSUFFICIENT_DATA'",
                'StateReason': 'string2',
                'StateReasonData': 'string2',
                'StateUpdatedTimestamp': "datetime(2015, 1, 1)",
                'MetricName': 'string2',
                'Namespace': 'string2',
                'Statistic': "'SampleCount' | 'Average' | 'Sum' | 'Minimum' | 'Maximum'",
                'ExtendedStatistic': 'string2',
                'Dimensions': [{
                    'Name': 'string2',
                    'Value': 'string2'
                },],
                'Period': 123,
                'Unit': "'Seconds' | 'Microseconds' | 'Milliseconds' | 'Bytes' | 'Kilobytes' |"
                        "'Megabytes' | 'Gigabytes' | 'Terabytes' | 'Bits' | 'Kilobits' |"
                        "'Megabits' | 'Gigabits' | 'Terabits' | 'Percent' | 'Count' |"
                        "'Bytes/Second' | 'Kilobytes/Second' | 'Megabytes/Second' |"
                        "'Gigabytes/Second' | 'Terabytes/Second' | 'Bits/Second' |"
                        "'Kilobits/Second' | 'Megabits/Second' | 'Gigabits/Second' |"
                        "'Terabits/Second' | 'Count/Second' | 'None'",
                'EvaluationPeriods': 123,
                'DatapointsToAlarm': 123,
                'Threshold': 123.0,
                'ComparisonOperator': "'GreaterThanOrEqualToThreshold' | 'GreaterThanThreshold' |"
                                      "'LessThanThreshold' | 'LessThanOrEqualToThreshold'",
                'TreatMissingData': 'string2',
                'EvaluateLowSampleCountPercentile': 'string2',
                'Metrics': [{
                    'Id': 'string2',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'string2',
                            'MetricName': 'string2',
                            'Dimensions': [{
                                'Name': 'string2',
                                'Value': 'string2'
                            },]
                        },
                        'Period': 123,
                        'Stat': 'string2',
                        'Unit': "'Seconds' | 'Microseconds' | 'Milliseconds' | 'Bytes' |"
                                "'Kilobytes' | 'Megabytes' | 'Gigabytes' | 'Terabytes' | 'Bits' |"
                                "'Kilobits' | 'Megabits' | 'Gigabits' | 'Terabits' | 'Percent' |"
                                "'Count' | 'Bytes/Second' | 'Kilobytes/Second' |"
                                "'Megabytes/Second' | 'Gigabytes/Second' | 'Terabytes/Second' |"
                                "'Bits/Second' | 'Kilobits/Second' | 'Megabits/Second' |"
                                "'Gigabits/Second' | 'Terabits/Second' | 'Count/Second' | 'None'"
                    },
                    'Expression': 'string2',
                    'Label': 'string2',
                    'ReturnData': "True|False"
                },]
            },
        ]
        if AlarmNames:
            alarms = [alarm for alarm in alarms if alarm['AlarmName'] in AlarmNames]
        return {'MetricAlarms': alarms, 'NextToken': 'string'}


#.


@pytest.mark.parametrize("alarm_names,amount_alarms", [
    (None, 2),
    ([], 2),
    (['string1'], 1),
    (['not found'], 1),
    (['string1', 'too many'], 1),
    (['string1', 'string2'], 2),
    (['string1', 'string2', 'too many'], 2),
])
def test_agent_aws_cloudwatch_result_distribution(alarm_names, amount_alarms):
    region = 'region'
    config = AWSConfig('hostname', (None, None))
    config.add_single_service_config('cloudwatch_alarms', alarm_names)

    fake_cloudwatch_client = FakeCloudwatchClient()

    cloudwatch_alarms_limits_distributor = ResultDistributor()

    cloudwatch_alarms_limits = CloudwatchAlarmsLimits(fake_cloudwatch_client, region, config,
                                                      cloudwatch_alarms_limits_distributor)
    cloudwatch_alarms = CloudwatchAlarms(fake_cloudwatch_client, region, config)

    cloudwatch_alarms_limits_distributor.add(cloudwatch_alarms)

    cloudwatch_alarms_limits_results = cloudwatch_alarms_limits.run().results
    cloudwatch_alarms_results = cloudwatch_alarms.run().results

    #--CloudwatchAlarmsLimits-----------------------------------------------
    assert cloudwatch_alarms_limits.interval == 300
    assert cloudwatch_alarms_limits.name == "cloudwatch_alarms_limits"
    assert cloudwatch_alarms.interval == 300
    assert cloudwatch_alarms.name == "cloudwatch_alarms"

    assert len(cloudwatch_alarms_limits_results) == 1
    cloudwatch_alarms_limits_result = cloudwatch_alarms_limits_results[0]
    assert cloudwatch_alarms_limits_result.piggyback_hostname == ''

    assert len(cloudwatch_alarms_limits_result.content) == 1
    cloudwatch_alarms_limits_content = cloudwatch_alarms_limits_result.content[0]
    assert cloudwatch_alarms_limits_content.key == 'cloudwatch_alarms'
    assert cloudwatch_alarms_limits_content.title == 'Cloudwatch Alarms'
    assert cloudwatch_alarms_limits_content.limit == 5000
    assert cloudwatch_alarms_limits_content.amount == 2

    #--CloudwatchAlarms-----------------------------------------------------
    assert len(cloudwatch_alarms_results) == 1
    cloudwatch_alarms_result = cloudwatch_alarms_results[0]
    assert cloudwatch_alarms_result.piggyback_hostname == ''
    assert len(cloudwatch_alarms_result.content) == amount_alarms
