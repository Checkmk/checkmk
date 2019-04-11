# encoding: utf-8

import pytest

from cmk.special_agents.agent_aws import (
    AWSConfig,
    CloudwatchAlarmsLimits,
    CloudwatchAlarms,
)

#TODO what about enums?
#TODO modifiy AWSConfig


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


def test_agent_aws_cloudwatch_alarms_limits():
    section = CloudwatchAlarmsLimits(FakeCloudwatchClient(), 'region',
                                     AWSConfig('hostname', (None, None)))
    results = section.run().results
    assert len(results) == 1

    result = results[0]
    assert result.piggyback_hostname == ''
    assert len(result.content) == 1

    content = result.content[0]
    assert content.key == 'cloudwatch_alarms'
    assert content.title == 'Cloudwatch Alarms'
    assert content.limit == 5000
    assert content.amount == 2


@pytest.mark.parametrize("names,amount_alarms", [
    (None, 2),
    ([], 2),
    (['string1'], 1),
    (['not found'], 1),
    (['string1', 'too many'], 1),
    (['string1', 'string2'], 2),
    (['string1', 'string2', 'too many'], 2),
])
def test_agent_aws_cloudwatch_alarms(names, amount_alarms):
    config = AWSConfig('hostname', (None, None))
    config.add_single_service_config('cloudwatch_alarms', names)
    section = CloudwatchAlarms(FakeCloudwatchClient(), 'region', config)
    results = section.run().results
    assert len(results) == 1

    result = results[0]
    assert result.piggyback_hostname == ''
    assert len(result.content) == amount_alarms
