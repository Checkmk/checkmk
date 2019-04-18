# encoding: utf-8

import pytest

from cmk.special_agents.agent_aws import (
    AWSConfig,
    ResultDistributor,
    S3Limits,
    S3Summary,
    S3,
    S3Requests,
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
    def get_metric_data(self, MetricDataQueries, StartTime='START', EndTime='END'):
        results = []
        for query in MetricDataQueries:
            results.append({
                'Id': query['Id'],
                'Label': query['Label'],
                'Timestamps': ["1970-01-01",],
                'Values': [123.0,],
                'StatusCode': "'Complete' | 'InternalError' | 'PartialData'",
                'Messages': [{
                    'Code': 'string1',
                    'Value': 'string1'
                },]
            })
        return {
            'MetricDataResults': results,
            'NextToken': 'string',
            'Messages': [{
                'Code': 'string',
                'Value': 'string'
            },]
        }


class FakeS3Client(object):
    def list_buckets(self):
        buckets = [
            {
                'Name': 'string1',
                'CreationDate': "1970-01-01",
            },
            {
                'Name': 'string2',
                'CreationDate': "1970-01-02",
            },
            {
                'Name': 'string3',
                'CreationDate': "1970-01-03",
            },
            {
                'Name': 'string4',
                'CreationDate': "1970-01-04",
            },
        ]
        return {'Buckets': buckets, 'Owner': {'DisplayName': 'string', 'ID': 'string'}}

    def get_bucket_location(self, Bucket=''):
        return {
            'string1': {
                'LocationConstraint': 'region'
            },
            'string2': {
                'LocationConstraint': 'region'
            },
            'string3': {
                'LocationConstraint': 'region'
            },
            'string4': {
                'LocationConstraint': 'another-region'
            },
        }.get(Bucket)

    def get_bucket_tagging(self, Bucket=''):
        return {
            'string1': {
                'TagSet': [{
                    'Key': 'key-string',
                    'Value': 'val-string-1'
                },],
            },
            'string2': {
                'TagSet': [
                    {
                        'Key': 'key-string',
                        'Value': 'val-string-2'
                    },
                    {
                        'Key': 'key-string-22',
                        'Value': 'val-string-22'
                    },
                ],
            },
            'string3': {},
            'string4': {},
        }.get(Bucket)


#.


@pytest.mark.parametrize("names,tags,amount_buckets", [
    (None, (None, None), 3),
    (['string1'], (None, None), 1),
    (['string1', 'string2'], (None, None), 2),
    (['string1', 'string2', 'string3'], (None, None), 3),
    (['string1', 'string2', 'string3', 'string4'], (None, None), 3),
    (['string1', 'string2', 'string3', 'FOOBAR'], (None, None), 3),
    (None, ([
        ['key-string'],
    ], [
        [
            'val-string-1',
        ],
    ]), 1),
    (None, ([
        ['key-string'],
    ], [
        [
            'val-string-1',
            'val-string-2',
        ],
    ]), 2),
    (None, ([
        ['key-string', 'unknown-tag'],
    ], [
        [
            'val-string-1',
            'val-string-2',
        ],
        [
            'unknown-val',
        ],
    ]), 2),
])
def test_agent_aws_s3_result_distribution(names, tags, amount_buckets):
    region = 'region'
    config = AWSConfig('hostname', (None, None))
    config.add_single_service_config('s3_names', names)
    config.add_service_tags('s3_tags', tags)

    fake_s3_client = FakeS3Client()
    fake_cloudwatch_client = FakeCloudwatchClient()

    s3_limits_distributor = ResultDistributor()
    s3_summary_distributor = ResultDistributor()

    s3_limits = S3Limits(fake_s3_client, region, config, s3_limits_distributor)
    s3_summary = S3Summary(fake_s3_client, region, config, s3_summary_distributor)
    s3 = S3(fake_cloudwatch_client, region, config)
    s3_requests = S3Requests(fake_cloudwatch_client, region, config)

    s3_limits_distributor.add(s3_summary)
    s3_summary_distributor.add(s3)
    s3_summary_distributor.add(s3_requests)

    s3_limits_results = s3_limits.run().results
    s3_summary_results = s3_summary.run().results
    s3_results = s3.run().results
    s3_requests_results = s3_requests.run().results

    #--S3Limits-------------------------------------------------------------
    assert s3_limits.interval == 86400
    assert s3_limits.name == "s3_limits"

    assert len(s3_limits_results) == 1

    s3_limits_result = s3_limits_results[0]
    assert s3_limits_result.piggyback_hostname == ''
    assert len(s3_limits_result.content) == 1

    s3_limits_content = s3_limits_result.content[0]
    assert s3_limits_content.key == 'buckets'
    assert s3_limits_content.title == 'Buckets'
    assert s3_limits_content.limit == 100
    assert s3_limits_content.amount == 4

    #--S3Summary------------------------------------------------------------
    assert s3_summary.interval == 86400
    assert s3_summary.name == "s3_summary"

    assert s3_summary_results == []

    #--S3-------------------------------------------------------------------
    assert s3.interval == 86400
    assert s3.name == "s3"

    assert len(s3_results) == 1

    s3_result = s3_results[0]
    assert s3_result.piggyback_hostname == ''

    # 4 (metrics) * X (buckets) == Y (len results)
    assert len(s3_result.content) == 4 * amount_buckets
    for row in s3_result.content:
        assert row.get('LocationConstraint') == 'region'
        assert 'Tagging' in row

    #--S3Requests-----------------------------------------------------------
    assert s3_requests.interval == 300
    assert s3_requests.name == "s3_requests"

    assert len(s3_requests_results) == 1

    s3_requests_result = s3_requests_results[0]
    assert s3_requests_result.piggyback_hostname == ''

    # 16 (metrics) * X (buckets) == Y (len results)
    assert len(s3_requests_result.content) == 16 * amount_buckets
    for row in s3_requests_result.content:
        assert row.get('LocationConstraint') == 'region'
        assert 'Tagging' in row
