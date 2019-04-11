# encoding: utf-8

import pytest

from cmk.special_agents.agent_aws import (
    _get_ec2_piggyback_hostname,
    AWSConfig,
    AWSColleagueContents,
    EC2Labels,
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

inst1 = {
    'AmiLaunchIndex': 123,
    'ImageId': 'string1',
    'InstanceId': 'string1',
    'InstanceType':
        "'t1.micro' | 't2.nano' | 't2.micro' | 't2.small' | 't2.medium' | 't2.large' |"
        "'t2.xlarge' | 't2.2xlarge' | 't3.nano' | 't3.micro' | 't3.small' | 't3.medium' |"
        "'t3.large' | 't3.xlarge' | 't3.2xlarge' | 'm1.small' | 'm1.medium' |"
        "'m1.large' | 'm1.xlarge' | 'm3.medium' | 'm3.large' | 'm3.xlarge' |"
        "'m3.2xlarge' | 'm4.large' | 'm4.xlarge' | 'm4.2xlarge' |"
        "'m4.4xlarge' | 'm4.10xlarge' | 'm4.16xlarge' | 'm2.xlarge' | 'm2.2xlarge' |"
        "'m2.4xlarge' | 'cr1.8xlarge' | 'r3.large' | 'r3.xlarge' | 'r3.2xlarge' |"
        "'r3.4xlarge' | 'r3.8xlarge' | 'r4.large' | 'r4.xlarge' | 'r4.2xlarge' |"
        "'r4.4xlarge' | 'r4.8xlarge' | 'r4.16xlarge' | 'r5.large' | 'r5.xlarge' |"
        "'r5.2xlarge' | 'r5.4xlarge' | 'r5.12xlarge' | 'r5.24xlarge' | 'r5.metal' |"
        "'r5a.large' | 'r5a.xlarge' | 'r5a.2xlarge' | 'r5a.4xlarge' | 'r5a.12xlarge' |"
        "'r5a.24xlarge' | 'r5d.large' | 'r5d.xlarge' | 'r5d.2xlarge' | 'r5d.4xlarge' |"
        "'r5d.12xlarge' | 'r5d.24xlarge' | 'r5d.metal' | 'r5ad.large' | 'r5ad.xlarge' |"
        "'r5ad.2xlarge' | 'r5ad.4xlarge' | 'r5ad.8xlarge' | 'r5ad.12xlarge' |"
        "'r5ad.16xlarge' | 'r5ad.24xlarge' | 'x1.16xlarge' | 'x1.32xlarge' |"
        "'x1e.xlarge' | 'x1e.2xlarge' | 'x1e.4xlarge' | 'x1e.8xlarge' | 'x1e.16xlarge' |"
        "'x1e.32xlarge' | 'i2.xlarge' | 'i2.2xlarge' | 'i2.4xlarge' | 'i2.8xlarge' |"
        "'i3.large' | 'i3.xlarge' | 'i3.2xlarge' | 'i3.4xlarge' | 'i3.8xlarge' |"
        "'i3.16xlarge' | 'i3.metal' | 'hi1.4xlarge' | 'hs1.8xlarge' | 'c1.medium' |"
        "'c1.xlarge' | 'c3.large' | 'c3.xlarge' | 'c3.2xlarge' | 'c3.4xlarge' |"
        "'c3.8xlarge' | 'c4.large' | 'c4.xlarge' | 'c4.2xlarge' | 'c4.4xlarge' |"
        "'c4.8xlarge' | 'c5.large' | 'c5.xlarge' | 'c5.2xlarge' | 'c5.4xlarge' |"
        "'c5.9xlarge' | 'c5.18xlarge' | 'c5d.large' | 'c5d.xlarge' | 'c5d.2xlarge' |"
        "'c5d.4xlarge' | 'c5d.9xlarge' | 'c5d.18xlarge' | 'c5n.large' | 'c5n.xlarge' |"
        "'c5n.2xlarge' | 'c5n.4xlarge' | 'c5n.9xlarge' | 'c5n.18xlarge' | 'cc1.4xlarge' |"
        "'cc2.8xlarge' | 'g2.2xlarge' | 'g2.8xlarge' | 'g3.4xlarge' | 'g3.8xlarge' |"
        "'g3.16xlarge' | 'g3s.xlarge' | 'cg1.4xlarge' | 'p2.xlarge' | 'p2.8xlarge' |"
        "'p2.16xlarge' | 'p3.2xlarge' | 'p3.8xlarge' | 'p3.16xlarge' | 'p3dn.24xlarge' |"
        "'d2.xlarge' | 'd2.2xlarge' | 'd2.4xlarge' | 'd2.8xlarge' | 'f1.2xlarge' |"
        "'f1.4xlarge' | 'f1.16xlarge' | 'm5.large' | 'm5.xlarge' | 'm5.2xlarge' |"
        "'m5.4xlarge' | 'm5.12xlarge' | 'm5.24xlarge' | 'm5.metal' | 'm5a.large' |"
        "'m5a.xlarge' | 'm5a.2xlarge' | 'm5a.4xlarge' | 'm5a.12xlarge' | 'm5a.24xlarge' |"
        "'m5d.large' | 'm5d.xlarge' | 'm5d.2xlarge' | 'm5d.4xlarge' | 'm5d.12xlarge' |"
        "'m5d.24xlarge' | 'm5d.metal' | 'm5ad.large' | 'm5ad.xlarge' | 'm5ad.2xlarge' |"
        "'m5ad.4xlarge' | 'm5ad.8xlarge' | 'm5ad.12xlarge' | 'm5ad.16xlarge' |"
        "'m5ad.24xlarge' | 'h1.2xlarge' | 'h1.4xlarge' | 'h1.8xlarge' | 'h1.16xlarge' |"
        "'z1d.large' | 'z1d.xlarge' | 'z1d.2xlarge' | 'z1d.3xlarge' | 'z1d.6xlarge' |"
        "'z1d.12xlarge' | 'z1d.metal' | 'u-6tb1.metal' | 'u-9tb1.metal' | 'u-12tb1.metal'"
        "| 'a1.medium' | 'a1.large' | 'a1.xlarge' | 'a1.2xlarge' | 'a1.4xlarge'",
    'KernelId': 'string1',
    'KeyName': 'string1',
    'LaunchTime': "1970-01-01",
    'Monitoring': {
        'State': "'disabled' | 'disabling' | 'enabled' | 'pending'"
    },
    'Placement': {
        'AvailabilityZone': 'string1',
        'Affinity': 'string1',
        'GroupName': 'string1',
        'PartitionNumber': 123,
        'HostId': 'string1',
        'Tenancy': "'default' | 'dedicated' | 'host'",
        'SpreadDomain': 'string1'
    },
    'Platform': 'Windows',
    'PrivateDnsName': 'string1',
    'PrivateIpAddress': 'string1',
    'ProductCodes': [{
        'ProductCodeId': 'string1',
        'ProductCodeType': "'devpay' | 'marketplace'"
    },],
    'PublicDnsName': 'string1',
    'PublicIpAddress': 'string1',
    'RamdiskId': 'string1',
    'State': {
        'Code': 123,
        'Name': "'pending' | 'running' | 'shutting-down' | 'terminated' | 'stopping' |"
                "'stopped'"
    },
    'StateTransitionReason': 'string1',
    'SubnetId': 'string1',
    'VpcId': 'string1',
    'Architecture': "'i386' | 'x86_64' | 'arm64'",
    'BlockDeviceMappings': [{
        'DeviceName': 'string1',
        'Ebs': {
            'AttachTime': "1970-01-01",
            'DeleteOnTermination': "True | False",
            'Status': "'attaching' | 'attached' | 'detaching' | 'detached'",
            'VolumeId': 'string1'
        }
    },],
    'ClientToken': 'string1',
    'EbsOptimized': "True | False",
    'EnaSupport': "True | False",
    'Hypervisor': "'ovm' | 'xen'",
    'IamInstanceProfile': {
        'Arn': 'string1',
        'Id': 'string1'
    },
    'InstanceLifecycle': "'spot' | 'scheduled'",
    'ElasticGpuAssociations': [{
        'ElasticGpuId': 'string1',
        'ElasticGpuAssociationId': 'string1',
        'ElasticGpuAssociationState': 'string1',
        'ElasticGpuAssociationTime': 'string1'
    },],
    'ElasticInferenceAcceleratorAssociations': [{
        'ElasticInferenceAcceleratorArn': 'string1',
        'ElasticInferenceAcceleratorAssociationId': 'string1',
        'ElasticInferenceAcceleratorAssociationState': 'string1',
        'ElasticInferenceAcceleratorAssociationTime': "1970-01-01"
    },],
    'NetworkInterfaces': [{
        'Association': {
            'IpOwnerId': 'string1',
            'PublicDnsName': 'string1',
            'PublicIp': 'string1'
        },
        'Attachment': {
            'AttachTime': "1970-01-01",
            'AttachmentId': 'string1',
            'DeleteOnTermination': "True | False",
            'DeviceIndex': 123,
            'Status': "'attaching' | 'attached' | 'detaching' | 'detached'"
        },
        'Description': 'string1',
        'Groups': [{
            'GroupName': 'string1',
            'GroupId': 'string1'
        },],
        'Ipv6Addresses': [{
            'Ipv6Address': 'string1'
        },],
        'MacAddress': 'string1',
        'NetworkInterfaceId': 'string1',
        'OwnerId': 'string1',
        'PrivateDnsName': 'string1',
        'PrivateIpAddress': 'string1',
        'PrivateIpAddresses': [{
            'Association': {
                'IpOwnerId': 'string1',
                'PublicDnsName': 'string1',
                'PublicIp': 'string1'
            },
            'Primary': "True | False",
            'PrivateDnsName': 'string1',
            'PrivateIpAddress': 'string1'
        },],
        'SourceDestCheck': "True | False",
        'Status': "'available' | 'associated' | 'attaching' | 'in-use' | 'detaching'",
        'SubnetId': 'string1',
        'VpcId': 'string1'
    },],
    'RootDeviceName': 'string1',
    'RootDeviceType': "'ebs' | 'instance-store'",
    'SecurityGroups': [{
        'GroupName': 'string1',
        'GroupId': 'string1'
    },],
    'SourceDestCheck': "True | False",
    'SpotInstanceRequestId': 'string1',
    'SriovNetSupport': 'string1',
    'StateReason': {
        'Code': 'string1',
        'Message': 'string1'
    },
    'Tags': [{
        'Key': 'string1',
        'Value': 'string1'
    },],
    'VirtualizationType': "'hvm' | 'paravirtual'",
    'CpuOptions': {
        'CoreCount': 123,
        'ThreadsPerCore': 123
    },
    'CapacityReservationId': 'string1',
    'CapacityReservationSpecification': {
        'CapacityReservationPreference': "'open' | 'none'",
        'CapacityReservationTarget': {
            'CapacityReservationId': 'string1'
        }
    },
    'HibernationOptions': {
        'Configured': "True | False"
    },
    'Licenses': [{
        'LicenseConfigurationArn': 'string1'
    },]
}

inst2 = {
    'AmiLaunchIndex': 123,
    'ImageId': 'string2',
    'InstanceId': 'string2',
    'InstanceType':
        "'t1.micro' | 't2.nano' | 't2.micro' | 't2.small' | 't2.medium' | 't2.large' |"
        "'t2.xlarge' | 't2.2xlarge' | 't3.nano' | 't3.micro' | 't3.small' | 't3.medium' |"
        "'t3.large' | 't3.xlarge' | 't3.2xlarge' | 'm1.small' | 'm1.medium' |"
        "'m1.large' | 'm1.xlarge' | 'm3.medium' | 'm3.large' | 'm3.xlarge' |"
        "'m3.2xlarge' | 'm4.large' | 'm4.xlarge' | 'm4.2xlarge' |"
        "'m4.4xlarge' | 'm4.10xlarge' | 'm4.16xlarge' | 'm2.xlarge' | 'm2.2xlarge' |"
        "'m2.4xlarge' | 'cr1.8xlarge' | 'r3.large' | 'r3.xlarge' | 'r3.2xlarge' |"
        "'r3.4xlarge' | 'r3.8xlarge' | 'r4.large' | 'r4.xlarge' | 'r4.2xlarge' |"
        "'r4.4xlarge' | 'r4.8xlarge' | 'r4.16xlarge' | 'r5.large' | 'r5.xlarge' |"
        "'r5.2xlarge' | 'r5.4xlarge' | 'r5.12xlarge' | 'r5.24xlarge' | 'r5.metal' |"
        "'r5a.large' | 'r5a.xlarge' | 'r5a.2xlarge' | 'r5a.4xlarge' | 'r5a.12xlarge' |"
        "'r5a.24xlarge' | 'r5d.large' | 'r5d.xlarge' | 'r5d.2xlarge' | 'r5d.4xlarge' |"
        "'r5d.12xlarge' | 'r5d.24xlarge' | 'r5d.metal' | 'r5ad.large' | 'r5ad.xlarge' |"
        "'r5ad.2xlarge' | 'r5ad.4xlarge' | 'r5ad.8xlarge' | 'r5ad.12xlarge' |"
        "'r5ad.16xlarge' | 'r5ad.24xlarge' | 'x1.16xlarge' | 'x1.32xlarge' |"
        "'x1e.xlarge' | 'x1e.2xlarge' | 'x1e.4xlarge' | 'x1e.8xlarge' | 'x1e.16xlarge' |"
        "'x1e.32xlarge' | 'i2.xlarge' | 'i2.2xlarge' | 'i2.4xlarge' | 'i2.8xlarge' |"
        "'i3.large' | 'i3.xlarge' | 'i3.2xlarge' | 'i3.4xlarge' | 'i3.8xlarge' |"
        "'i3.16xlarge' | 'i3.metal' | 'hi1.4xlarge' | 'hs1.8xlarge' | 'c1.medium' |"
        "'c1.xlarge' | 'c3.large' | 'c3.xlarge' | 'c3.2xlarge' | 'c3.4xlarge' |"
        "'c3.8xlarge' | 'c4.large' | 'c4.xlarge' | 'c4.2xlarge' | 'c4.4xlarge' |"
        "'c4.8xlarge' | 'c5.large' | 'c5.xlarge' | 'c5.2xlarge' | 'c5.4xlarge' |"
        "'c5.9xlarge' | 'c5.18xlarge' | 'c5d.large' | 'c5d.xlarge' | 'c5d.2xlarge' |"
        "'c5d.4xlarge' | 'c5d.9xlarge' | 'c5d.18xlarge' | 'c5n.large' | 'c5n.xlarge' |"
        "'c5n.2xlarge' | 'c5n.4xlarge' | 'c5n.9xlarge' | 'c5n.18xlarge' | 'cc1.4xlarge' |"
        "'cc2.8xlarge' | 'g2.2xlarge' | 'g2.8xlarge' | 'g3.4xlarge' | 'g3.8xlarge' |"
        "'g3.16xlarge' | 'g3s.xlarge' | 'cg1.4xlarge' | 'p2.xlarge' | 'p2.8xlarge' |"
        "'p2.16xlarge' | 'p3.2xlarge' | 'p3.8xlarge' | 'p3.16xlarge' | 'p3dn.24xlarge' |"
        "'d2.xlarge' | 'd2.2xlarge' | 'd2.4xlarge' | 'd2.8xlarge' | 'f1.2xlarge' |"
        "'f1.4xlarge' | 'f1.16xlarge' | 'm5.large' | 'm5.xlarge' | 'm5.2xlarge' |"
        "'m5.4xlarge' | 'm5.12xlarge' | 'm5.24xlarge' | 'm5.metal' | 'm5a.large' |"
        "'m5a.xlarge' | 'm5a.2xlarge' | 'm5a.4xlarge' | 'm5a.12xlarge' | 'm5a.24xlarge' |"
        "'m5d.large' | 'm5d.xlarge' | 'm5d.2xlarge' | 'm5d.4xlarge' | 'm5d.12xlarge' |"
        "'m5d.24xlarge' | 'm5d.metal' | 'm5ad.large' | 'm5ad.xlarge' | 'm5ad.2xlarge' |"
        "'m5ad.4xlarge' | 'm5ad.8xlarge' | 'm5ad.12xlarge' | 'm5ad.16xlarge' |"
        "'m5ad.24xlarge' | 'h1.2xlarge' | 'h1.4xlarge' | 'h1.8xlarge' | 'h1.16xlarge' |"
        "'z1d.large' | 'z1d.xlarge' | 'z1d.2xlarge' | 'z1d.3xlarge' | 'z1d.6xlarge' |"
        "'z1d.12xlarge' | 'z1d.metal' | 'u-6tb1.metal' | 'u-9tb1.metal' | 'u-12tb1.metal'"
        "| 'a1.medium' | 'a1.large' | 'a1.xlarge' | 'a1.2xlarge' | 'a1.4xlarge'",
    'KernelId': 'string2',
    'KeyName': 'string2',
    'LaunchTime': "1970-01-01",
    'Monitoring': {
        'State': "'disabled' | 'disabling' | 'enabled' | 'pending'"
    },
    'Placement': {
        'AvailabilityZone': 'string2',
        'Affinity': 'string2',
        'GroupName': 'string2',
        'PartitionNumber': 123,
        'HostId': 'string2',
        'Tenancy': "'default' | 'dedicated' | 'host'",
        'SpreadDomain': 'string2'
    },
    'Platform': 'Windows',
    'PrivateDnsName': 'string2',
    'PrivateIpAddress': 'string2',
    'ProductCodes': [{
        'ProductCodeId': 'string2',
        'ProductCodeType': "'devpay' | 'marketplace'"
    },],
    'PublicDnsName': 'string2',
    'PublicIpAddress': 'string2',
    'RamdiskId': 'string2',
    'State': {
        'Code': 123,
        'Name': "'pending' | 'running' | 'shutting-down' | 'terminated' | 'stopping' |"
                "'stopped'"
    },
    'StateTransitionReason': 'string2',
    'SubnetId': 'string2',
    'VpcId': 'string2',
    'Architecture': "'i386' | 'x86_64' | 'arm64'",
    'BlockDeviceMappings': [{
        'DeviceName': 'string2',
        'Ebs': {
            'AttachTime': "1970-01-01",
            'DeleteOnTermination': "True | False",
            'Status': "'attaching' | 'attached' | 'detaching' | 'detached'",
            'VolumeId': 'string2'
        }
    },],
    'ClientToken': 'string2',
    'EbsOptimized': "True | False",
    'EnaSupport': "True | False",
    'Hypervisor': "'ovm' | 'xen'",
    'IamInstanceProfile': {
        'Arn': 'string2',
        'Id': 'string2'
    },
    'InstanceLifecycle': "'spot' | 'scheduled'",
    'ElasticGpuAssociations': [{
        'ElasticGpuId': 'string2',
        'ElasticGpuAssociationId': 'string2',
        'ElasticGpuAssociationState': 'string2',
        'ElasticGpuAssociationTime': 'string2'
    },],
    'ElasticInferenceAcceleratorAssociations': [{
        'ElasticInferenceAcceleratorArn': 'string2',
        'ElasticInferenceAcceleratorAssociationId': 'string2',
        'ElasticInferenceAcceleratorAssociationState': 'string2',
        'ElasticInferenceAcceleratorAssociationTime': "1970-01-01"
    },],
    'NetworkInterfaces': [{
        'Association': {
            'IpOwnerId': 'string2',
            'PublicDnsName': 'string2',
            'PublicIp': 'string2'
        },
        'Attachment': {
            'AttachTime': "1970-01-01",
            'AttachmentId': 'string2',
            'DeleteOnTermination': "True | False",
            'DeviceIndex': 123,
            'Status': "'attaching' | 'attached' | 'detaching' | 'detached'"
        },
        'Description': 'string2',
        'Groups': [{
            'GroupName': 'string2',
            'GroupId': 'string2'
        },],
        'Ipv6Addresses': [{
            'Ipv6Address': 'string2'
        },],
        'MacAddress': 'string2',
        'NetworkInterfaceId': 'string2',
        'OwnerId': 'string2',
        'PrivateDnsName': 'string2',
        'PrivateIpAddress': 'string2',
        'PrivateIpAddresses': [{
            'Association': {
                'IpOwnerId': 'string2',
                'PublicDnsName': 'string2',
                'PublicIp': 'string2'
            },
            'Primary': "True | False",
            'PrivateDnsName': 'string2',
            'PrivateIpAddress': 'string2'
        },],
        'SourceDestCheck': "True | False",
        'Status': "'available' | 'associated' | 'attaching' | 'in-use' | 'detaching'",
        'SubnetId': 'string2',
        'VpcId': 'string2'
    },],
    'RootDeviceName': 'string2',
    'RootDeviceType': "'ebs' | 'instance-store'",
    'SecurityGroups': [{
        'GroupName': 'string2',
        'GroupId': 'string2'
    },],
    'SourceDestCheck': "True | False",
    'SpotInstanceRequestId': 'string2',
    'SriovNetSupport': 'string2',
    'StateReason': {
        'Code': 'string2',
        'Message': 'string2'
    },
    'Tags': [{
        'Key': 'string2',
        'Value': 'string2'
    },],
    'VirtualizationType': "'hvm' | 'paravirtual'",
    'CpuOptions': {
        'CoreCount': 123,
        'ThreadsPerCore': 123
    },
    'CapacityReservationId': 'string2',
    'CapacityReservationSpecification': {
        'CapacityReservationPreference': "'open' | 'none'",
        'CapacityReservationTarget': {
            'CapacityReservationId': 'string2'
        }
    },
    'HibernationOptions': {
        'Configured': "True | False"
    },
    'Licenses': [{
        'LicenseConfigurationArn': 'string2'
    },]
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


class FakeEC2Client(object):
    def describe_tags(self, Filters=None):
        tags = [
            {
                'Key': 'key-string1',
                'ResourceId': 'string1',
                'ResourceType': "'client-vpn-endpoint' | 'customer-gateway' | 'dedicated-host' |"
                                "'dhcp-options' | 'elastic-ip' | 'fleet' | 'fpga-image' |"
                                "'host-reservation' | 'image' | 'instance' | 'internet-gateway' |"
                                "'launch-template' | 'natgateway' | 'network-acl' |"
                                "'network-interface' | 'reserved-instances' | 'route-table' |"
                                "'security-group' | 'snapshot' | 'spot-instances-request' |"
                                "'subnet' | 'transit-gateway' | 'transit-gateway-attachment' |"
                                "'transit-gateway-route-table' | 'volume' | 'vpc' |"
                                "'vpc-peering-connection' | 'vpn-connection' | 'vpn-gateway'",
                'Value': 'value-string1'
            },
            {
                'Key': 'key-string21',
                'ResourceId': 'string2',
                'ResourceType': "'client-vpn-endpoint' | 'customer-gateway' | 'dedicated-host' |"
                                "'dhcp-options' | 'elastic-ip' | 'fleet' | 'fpga-image' |"
                                "'host-reservation' | 'image' | 'instance' | 'internet-gateway' |"
                                "'launch-template' | 'natgateway' | 'network-acl' |"
                                "'network-interface' | 'reserved-instances' | 'route-table' |"
                                "'security-group' | 'snapshot' | 'spot-instances-request' |"
                                "'subnet' | 'transit-gateway' | 'transit-gateway-attachment' |"
                                "'transit-gateway-route-table' | 'volume' | 'vpc' |"
                                "'vpc-peering-connection' | 'vpn-connection' | 'vpn-gateway'",
                'Value': 'value-string21'
            },
            {
                'Key': 'key-string22',
                'ResourceId': 'string2',
                'ResourceType': "'client-vpn-endpoint' | 'customer-gateway' | 'dedicated-host' |"
                                "'dhcp-options' | 'elastic-ip' | 'fleet' | 'fpga-image' |"
                                "'host-reservation' | 'image' | 'instance' | 'internet-gateway' |"
                                "'launch-template' | 'natgateway' | 'network-acl' |"
                                "'network-interface' | 'reserved-instances' | 'route-table' |"
                                "'security-group' | 'snapshot' | 'spot-instances-request' |"
                                "'subnet' | 'transit-gateway' | 'transit-gateway-attachment' |"
                                "'transit-gateway-route-table' | 'volume' | 'vpc' |"
                                "'vpc-peering-connection' | 'vpn-connection' | 'vpn-gateway'",
                'Value': 'value-string22'
            },
        ]
        if Filters:
            for filter_ in Filters:
                if filter_['Name']:
                    pass
        return {
            'NextToken': 'string',
            'Tags': tags,
        }


#.


@pytest.mark.parametrize("instances,len_results,expected_results", [
    ([], 0, {
        'string1-region-string1': None
    }),
    ([inst1], 1, {
        'string1-region-string1': {
            'key-string1': 'value-string1'
        }
    }),
    ([inst1, inst2], 2, {
        'string1-region-string1': {
            'key-string1': 'value-string1'
        },
        'string2-region-string2': {
            'key-string21': 'value-string21',
            'key-string22': 'value-string22',
        },
    }),
])
def test_agent_aws_ec2_labels(instances, len_results, expected_results):
    section = EC2Labels(FakeEC2Client(), 'region', AWSConfig('hostname', (None, None)))
    #TODO change in the future
    # At the moment, we simulate received results for simplicity:
    # In the agent_aws there are connected sections like
    # AWSLimits -> AWSSummary -> AWSLabels
    section._received_results = {
        'ec2_summary': AWSColleagueContents(
            {_get_ec2_piggyback_hostname(inst, 'region'): inst for inst in instances}, 0.0),
    }

    results = section.run().results
    assert len(results) == len_results

    for result in results:
        assert result.piggyback_hostname in expected_results
        assert result.content == expected_results[result.piggyback_hostname]
