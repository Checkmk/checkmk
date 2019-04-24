# encoding: utf-8

import pytest
from agent_aws_fake_clients import (
    FakeCloudwatchClient,)

from cmk.special_agents.agent_aws import (
    AWSConfig,
    ResultDistributor,
    ELBLimits,
    ELBSummaryGeneric,
    ELBLabelsGeneric,
    ELBHealth,
    ELB,
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

elb_lb1 = {
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

elb_lb2 = {
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

elb_lb3 = {
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

elbv2_lb1 = {
    'LoadBalancerArn': 'string1',
    'DNSName': 'string1',
    'CanonicalHostedZoneId': 'string1',
    'CreatedTime': "1970-01-01",
    'LoadBalancerName': 'string1',
    'Scheme': "'internet-facing'|'internal'",
    'VpcId': 'string1',
    'State': {
        'Code': "'active'|'provisioning'|'active_impaired'|'failed'",
        'Reason': 'string1'
    },
    'Type': "'application'|'network'",
    'AvailabilityZones': [{
        'ZoneName': 'string1',
        'SubnetId': 'string1',
        'LoadBalancerAddresses': [{
            'IpAddress': 'string1',
            'AllocationId': 'string1'
        },]
    },],
    'SecurityGroups': ['string1',],
    'IpAddressType': "'ipv4'|'dualstack'",
    'TagDescriptions': [{
        'Key': 'key-string1',
        'Value': 'value- string1',
    }],
}

elbv2_lb2 = {
    'LoadBalancerArn': 'string2',
    'DNSName': 'string2',
    'CanonicalHostedZoneId': 'string2',
    'CreatedTime': "1970-01-01",
    'LoadBalancerName': 'string2',
    'Scheme': "'internet-facing'|'internal'",
    'VpcId': 'string2',
    'State': {
        'Code': "'active'|'provisioning'|'active_impaired'|'failed'",
        'Reason': 'string2'
    },
    'Type': "'application'|'network'",
    'AvailabilityZones': [{
        'ZoneName': 'string2',
        'SubnetId': 'string2',
        'LoadBalancerAddresses': [{
            'IpAddress': 'string2',
            'AllocationId': 'string2'
        },]
    },],
    'SecurityGroups': ['string2',],
    'IpAddressType': "'ipv4'|'dualstack'",
    'TagDescriptions': [{
        'Key': 'key-string21',
        'Value': 'value- string21',
    }, {
        'Key': 'key-string22',
        'Value': 'value- string22',
    }],
}

elbv2_lb3 = {
    'LoadBalancerArn': 'string3',
    'DNSName': 'string3',
    'CanonicalHostedZoneId': 'string3',
    'CreatedTime': "1970-01-01",
    'LoadBalancerName': 'string3',
    'Scheme': "'internet-facing'|'internal'",
    'VpcId': 'string3',
    'State': {
        'Code': "'active'|'provisioning'|'active_impaired'|'failed'",
        'Reason': 'string3'
    },
    'Type': "'application'|'network'",
    'AvailabilityZones': [{
        'ZoneName': 'string3',
        'SubnetId': 'string3',
        'LoadBalancerAddresses': [{
            'IpAddress': 'string3',
            'AllocationId': 'string3'
        },]
    },],
    'SecurityGroups': ['string3',],
    'IpAddressType': "'ipv4'|'dualstack'",
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
    def describe_load_balancers(self, LoadBalancerNames=None):
        return {'LoadBalancerDescriptions': [elb_lb1, elb_lb2, elb_lb3], 'NextMarker': 'string'}

    def describe_account_limits(self):
        return {
            'Limits': [
                {
                    'Name': 'classic-load-balancers',
                    'Max': 10,
                },
                {
                    'Name': 'classic-listeners',
                    'Max': 10,
                },
                {
                    'Name': 'classic-registered-instances',
                    'Max': 10,
                },
            ],
            'NextMarker': 'string'
        }

    def describe_tags(self, LoadBalancerNames=None):
        tag_descrs = []
        for lb_name, lb_tags in [
            ('string1', [{
                'Key': 'key-string',
                'Value': 'value-string1',
            }]),
            ('string2', [{
                'Key': 'key-string',
                'Value': 'value-string21',
            }, {
                'Key': 'key-string22',
                'Value': 'value-string22',
            }]),
        ]:
            if not LoadBalancerNames or lb_name in LoadBalancerNames:
                tag_descrs.append({'LoadBalancerName': lb_name, 'Tags': lb_tags})
        return {'TagDescriptions': tag_descrs}

    def describe_instance_health(self, LoadBalancerName=None):
        return {
            'InstanceStates': [{
                'InstanceId': 'string',
                'State': 'string',
                'ReasonCode': 'string',
                'Description': 'string'
            },]
        }


class FakeELBv2Client(object):
    def describe_load_balancers(self, Names=None):
        return {
            'LoadBalancerDescriptions': [elbv2_lb1, elbv2_lb2, elbv2_lb3],
            'NextMarker': 'string'
        }


#.


@pytest.mark.parametrize("tags,found_instances,found_instances_with_labels", [
    ((None, None), ['string1', 'string2', 'string3'], ['string1', 'string2']),
    (([['FOO']], [['BAR']]), [], []),
    (([['key-string']], [['value-string1']]), ['string1'], ['string1']),
    (([['key-string']], [['value-string1', 'value-string21']]), ['string1', 'string2'],
     ['string1', 'string2']),
])
def test_agent_aws_elb_result_distribution(tags, found_instances, found_instances_with_labels):
    region = 'region'
    config = AWSConfig('hostname', (None, None))
    config.add_single_service_config('elb_names', None)
    config.add_service_tags('elb_tags', tags)

    fake_elb_client = FakeELBClient()
    fake_cloudwatch_client = FakeCloudwatchClient()

    elb_limits_distributor = ResultDistributor()
    elb_summary_distributor = ResultDistributor()

    elb_limits = ELBLimits(fake_elb_client, region, config, elb_limits_distributor)
    elb_summary = ELBSummaryGeneric(
        fake_elb_client, region, config, elb_summary_distributor, resource='elb')
    elb_labels = ELBLabelsGeneric(fake_elb_client, region, config, resource='elb')
    elb_health = ELBHealth(fake_elb_client, region, config)
    elb = ELB(fake_cloudwatch_client, region, config)

    elb_limits_distributor.add(elb_summary)
    elb_summary_distributor.add(elb_labels)
    elb_summary_distributor.add(elb_health)
    elb_summary_distributor.add(elb)

    elb_limits_results = elb_limits.run().results
    elb_summary_results = elb_summary.run().results
    elb_labels_results = elb_labels.run().results
    elb_health_results = elb_health.run().results
    elb_results = elb.run().results

    #--ELBLimits------------------------------------------------------------
    assert elb_limits.interval == 300
    assert elb_limits.name == "elb_limits"
    assert len(elb_limits_results) == 4
    for result in elb_limits_results:
        if result.piggyback_hostname == '':
            assert len(result.content) == 1
        else:
            assert len(result.content) == 2

    #--ELBSummary-----------------------------------------------------------
    assert elb_summary.interval == 300
    assert elb_summary.name == "elb_summary"

    if found_instances:
        assert len(elb_summary_results) == 1
        elb_summary_result = elb_summary_results[0]
        assert elb_summary_result.piggyback_hostname == ''
        assert len(elb_summary_result.content) == len(found_instances)

    else:
        assert len(elb_summary_results) == 0

    #--ELBLabels------------------------------------------------------------
    assert elb_labels.interval == 300
    assert elb_labels.name == "labels"
    assert len(elb_labels_results) == len(found_instances_with_labels)
    for result in elb_labels_results:
        assert result.piggyback_hostname in found_instances_with_labels

    #--ELBHealth------------------------------------------------------------
    assert elb_health.interval == 300
    assert elb_health.name == "elb_health"
    assert len(elb_health_results) == len(found_instances)
    for result in elb_health_results:
        assert result.piggyback_hostname in found_instances

    #--ELB------------------------------------------------------------------
    assert elb.interval == 300
    assert elb.name == "elb"
    assert len(elb_results) == len(found_instances)
    for result in elb_results:
        assert result.piggyback_hostname in found_instances
        # 13 metrics
        assert len(result.content) == 13
