# encoding: utf-8

import pytest

from cmk.special_agents.agent_aws import (
    AWSConfig,
    AWSColleagueContents,
    ELBLabels,
)

#TODO what about enums?
#TODO modifiy AWSConfig

#   .--instances-----------------------------------------------------------.
#   |              _           _                                           |
#   |             (_)_ __  ___| |_ __ _ _ __   ___ ___  ___                |
#   |             | | '_ \/ __| __/ _` | '_ \ / __/ _ \/ __|               |
#   |             | | | | \__ \ || (_| | | | | (_|  __/\__ \               |
#   |             |_|_| |_|___/\__\__,_|_| |_|\___\___||___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'

lb1 = {
    'LoadBalancerName': 'string1',
    'DNSName': 'string1',
    'CanonicalHostedZoneName': 'string1',
    'CanonicalHostedZoneNameID': 'string1',
    'ListenerDescriptions': [{
        'Listener': {
            'Protocol': 'string1',
            'LoadBalancerPort': 123,
            'InstanceProtocol': 'string1',
            'InstancePort': 123,
            'SSLCertificateId': 'string1'
        },
        'PolicyNames': ['string1',]
    },],
    'Policies': {
        'AppCookieStickinessPolicies': [{
            'PolicyName': 'string1',
            'CookieName': 'string1'
        },],
        'LBCookieStickinessPolicies': [{
            'PolicyName': 'string1',
            'CookieExpirationPeriod': 123
        },],
        'OtherPolicies': ['string1',]
    },
    'BackendServerDescriptions': [{
        'InstancePort': 123,
        'PolicyNames': ['string1',]
    },],
    'AvailabilityZones': ['string1',],
    'Subnets': ['string1',],
    'VPCId': 'string1',
    'Instances': [{
        'InstanceId': 'string1'
    },],
    'HealthCheck': {
        'Target': 'string1',
        'Interval': 123,
        'Timeout': 123,
        'UnhealthyThreshold': 123,
        'HealthyThreshold': 123
    },
    'SourceSecurityGroup': {
        'OwnerAlias': 'string1',
        'GroupName': 'string1'
    },
    'SecurityGroups': ['string1',],
    'CreatedTime': "1970-01-01",
    'Scheme': 'string1',
    'TagDescriptions': [{
        'Key': 'key-string1',
        'Value': 'value- string1',
    }],
}

lb2 = {
    'LoadBalancerName': 'string2',
    'DNSName': 'string2',
    'CanonicalHostedZoneName': 'string2',
    'CanonicalHostedZoneNameID': 'string2',
    'ListenerDescriptions': [{
        'Listener': {
            'Protocol': 'string2',
            'LoadBalancerPort': 123,
            'InstanceProtocol': 'string2',
            'InstancePort': 123,
            'SSLCertificateId': 'string2'
        },
        'PolicyNames': ['string2',]
    },],
    'Policies': {
        'AppCookieStickinessPolicies': [{
            'PolicyName': 'string2',
            'CookieName': 'string2'
        },],
        'LBCookieStickinessPolicies': [{
            'PolicyName': 'string2',
            'CookieExpirationPeriod': 123
        },],
        'OtherPolicies': ['string2',]
    },
    'BackendServerDescriptions': [{
        'InstancePort': 123,
        'PolicyNames': ['string2',]
    },],
    'AvailabilityZones': ['string2',],
    'Subnets': ['string2',],
    'VPCId': 'string2',
    'Instances': [{
        'InstanceId': 'string2'
    },],
    'HealthCheck': {
        'Target': 'string2',
        'Interval': 123,
        'Timeout': 123,
        'UnhealthyThreshold': 123,
        'HealthyThreshold': 123
    },
    'SourceSecurityGroup': {
        'OwnerAlias': 'string2',
        'GroupName': 'string2'
    },
    'SecurityGroups': ['string2',],
    'CreatedTime': "1970-01-01",
    'Scheme': 'string2',
    'TagDescriptions': [{
        'Key': 'key-string21',
        'Value': 'value- string21',
    }, {
        'Key': 'key-string22',
        'Value': 'value- string22',
    }],
}

lb3 = {
    'LoadBalancerName': 'string3',
    'DNSName': 'string3',
    'CanonicalHostedZoneName': 'string3',
    'CanonicalHostedZoneNameID': 'string3',
    'ListenerDescriptions': [{
        'Listener': {
            'Protocol': 'string3',
            'LoadBalancerPort': 123,
            'InstanceProtocol': 'string3',
            'InstancePort': 123,
            'SSLCertificateId': 'string3'
        },
        'PolicyNames': ['string3',]
    },],
    'Policies': {
        'AppCookieStickinessPolicies': [{
            'PolicyName': 'string3',
            'CookieName': 'string3'
        },],
        'LBCookieStickinessPolicies': [{
            'PolicyName': 'string3',
            'CookieExpirationPeriod': 123
        },],
        'OtherPolicies': ['string3',]
    },
    'BackendServerDescriptions': [{
        'InstancePort': 123,
        'PolicyNames': ['string3',]
    },],
    'AvailabilityZones': ['string3',],
    'Subnets': ['string3',],
    'VPCId': 'string3',
    'Instances': [{
        'InstanceId': 'string3'
    },],
    'HealthCheck': {
        'Target': 'string3',
        'Interval': 123,
        'Timeout': 123,
        'UnhealthyThreshold': 123,
        'HealthyThreshold': 123
    },
    'SourceSecurityGroup': {
        'OwnerAlias': 'string3',
        'GroupName': 'string3'
    },
    'SecurityGroups': ['string3',],
    'CreatedTime': "1970-01-01",
    'Scheme': 'string3',
}

#.
#   .--fake client---------------------------------------------------------.
#   |             __       _               _ _            _                |
#   |            / _| __ _| | _____    ___| (_) ___ _ __ | |_              |
#   |           | |_ / _` | |/ / _ \  / __| | |/ _ \ '_ \| __|             |
#   |           |  _| (_| |   <  __/ | (__| | |  __/ | | | |_              |
#   |           |_|  \__,_|_|\_\___|  \___|_|_|\___|_| |_|\__|             |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class FakeELBClient(object):
    pass


#.


@pytest.mark.parametrize("instances,expected_result_len", [
    ([], 0),
    ([lb1], 1),
    ([lb1, lb2], 2),
    ([lb1, lb2, lb3], 2),
])
def test_agent_aws_elb_labels(instances, expected_result_len):
    section = ELBLabels(FakeELBClient(), 'region', AWSConfig('hostname', (None, None)))
    #TODO change in the future
    # At the moment, we simulate received results for simplicity:
    # In the agent_aws there are connected sections like
    # AWSLimits -> AWSSummary -> AWSLabels
    section._received_results = {
        'elb_summary': AWSColleagueContents({inst['DNSName']: inst for inst in instances}, 0.0),
    }

    results = section.run().results
    assert expected_result_len == len(results)

    for result in results:
        assert result.piggyback_hostname != 'string3'
