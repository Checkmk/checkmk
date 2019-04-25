# encoding: utf-8

import pytest
from agent_aws_fake_clients import (
    FakeCloudwatchClient,)

from cmk.special_agents.agent_aws import (
    _get_ec2_piggyback_hostname,
    AWSColleagueContents,
    AWSEC2InstTypes,
    AWSConfig,
    ResultDistributor,
    EC2Limits,
    EC2Summary,
    EC2Labels,
    EC2SecurityGroups,
    EC2,
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
    'InstanceType': "'%s'" % "'|'".join(AWSEC2InstTypes),
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
    'InstanceType': "'%s'" % "'|'".join(AWSEC2InstTypes),
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
    def describe_instances(self, InstanceIds=None, Filters=None):
        return {
            'Reservations': [{
                'Groups': [{
                    'GroupName': 'string',
                    'GroupId': 'string'
                },],
                'Instances': [inst1, inst2],
                'OwnerId': 'string',
                'RequesterId': 'string',
                'ReservationId': 'string'
            },],
            'NextToken': 'string'
        }

    def describe_reserved_instances(self):
        return {
            'ReservedInstances': [{
                'AvailabilityZone': 'string',
                'Duration': 123,
                'End': "1970-01-02",
                'FixedPrice': "",
                'InstanceCount': 123,
                'InstanceType': "'%s'" % "'|'".join(AWSEC2InstTypes),
                'ProductDescription': "'Linux/UNIX'|'Linux/UNIX (Amazon VPC)'|'Windows'|'Windows (Amazon VPC)'",
                'ReservedInstancesId': 'string',
                'Start': "1970-01-01",
                'State': "'payment-pending'|'active'|'payment-failed'|'retired'",
                'UsagePrice': "",
                'CurrencyCode': 'USD',
                'InstanceTenancy': "'default'|'dedicated'|'host'",
                'OfferingClass': "'standard'|'convertible'",
                'OfferingType':
                    "'Heavy Utilization'|'Medium Utilization'|'Light Utilization'|'No Upfront'|"
                    "'Partial Upfront'|'All Upfront'",
                'RecurringCharges': [{
                    'Amount': 123.0,
                    'Frequency': 'Hourly'
                },],
                'Scope': "'Availability Zone'|'Region'",
                'Tags': [{
                    'Key': 'string',
                    'Value': 'string'
                },]
            },]
        }

    def describe_addresses(self):
        return {
            'Addresses': [{
                'InstanceId': 'string',
                'PublicIp': 'string',
                'AllocationId': 'string',
                'AssociationId': 'string',
                'Domain': "'vpc'|'standard'",
                'NetworkInterfaceId': 'string',
                'NetworkInterfaceOwnerId': 'string',
                'PrivateIpAddress': 'string',
                'Tags': [{
                    'Key': 'string',
                    'Value': 'string'
                },],
                'PublicIpv4Pool': 'string'
            },]
        }

    def describe_security_groups(self):
        return {
            'SecurityGroups': [{
                'Description': 'string',
                'GroupName': 'string',
                'IpPermissions': [{
                    'FromPort': 123,
                    'IpProtocol': 'string',
                    'IpRanges': [{
                        'CidrIp': 'string',
                        'Description': 'string'
                    },],
                    'Ipv6Ranges': [{
                        'CidrIpv6': 'string',
                        'Description': 'string'
                    },],
                    'PrefixListIds': [{
                        'Description': 'string',
                        'PrefixListId': 'string'
                    },],
                    'ToPort': 123,
                    'UserIdGroupPairs': [{
                        'Description': 'string',
                        'GroupId': 'string',
                        'GroupName': 'string',
                        'PeeringStatus': 'string',
                        'UserId': 'string',
                        'VpcId': 'string',
                        'VpcPeeringConnectionId': 'string'
                    },]
                },],
                'OwnerId': 'string',
                'GroupId': 'string',
                'IpPermissionsEgress': [{
                    'FromPort': 123,
                    'IpProtocol': 'string',
                    'IpRanges': [{
                        'CidrIp': 'string',
                        'Description': 'string'
                    },],
                    'Ipv6Ranges': [{
                        'CidrIpv6': 'string',
                        'Description': 'string'
                    },],
                    'PrefixListIds': [{
                        'Description': 'string',
                        'PrefixListId': 'string'
                    },],
                    'ToPort': 123,
                    'UserIdGroupPairs': [{
                        'Description': 'string',
                        'GroupId': 'string',
                        'GroupName': 'string',
                        'PeeringStatus': 'string',
                        'UserId': 'string',
                        'VpcId': 'string',
                        'VpcPeeringConnectionId': 'string'
                    },]
                },],
                'Tags': [{
                    'Key': 'string',
                    'Value': 'string'
                },],
                'VpcId': 'string'
            },],
            'NextToken': 'string'
        }

    def describe_network_interfaces(self):
        return {
            'NetworkInterfaces': [{
                'Association': {
                    'AllocationId': 'string',
                    'AssociationId': 'string',
                    'IpOwnerId': 'string',
                    'PublicDnsName': 'string',
                    'PublicIp': 'string'
                },
                'Attachment': {
                    'AttachTime': "19070-01-01",
                    'AttachmentId': 'string',
                    'DeleteOnTermination': "True|False",
                    'DeviceIndex': 123,
                    'InstanceId': 'string',
                    'InstanceOwnerId': 'string',
                    'Status': "'attaching'|'attached'|'detaching'|'detached'"
                },
                'AvailabilityZone': 'string',
                'Description': 'string',
                'Groups': [{
                    'GroupName': 'string',
                    'GroupId': 'string'
                },],
                'InterfaceType': "'interface'|'natGateway'",
                'Ipv6Addresses': [{
                    'Ipv6Address': 'string'
                },],
                'MacAddress': 'string',
                'NetworkInterfaceId': 'string',
                'OwnerId': 'string',
                'PrivateDnsName': 'string',
                'PrivateIpAddress': 'string',
                'PrivateIpAddresses': [{
                    'Association': {
                        'AllocationId': 'string',
                        'AssociationId': 'string',
                        'IpOwnerId': 'string',
                        'PublicDnsName': 'string',
                        'PublicIp': 'string'
                    },
                    'Primary': "True|False",
                    'PrivateDnsName': 'string',
                    'PrivateIpAddress': 'string'
                },],
                'RequesterId': 'string',
                'RequesterManaged': "True|False",
                'SourceDestCheck': "True|False",
                'Status': "'available'|'associated'|'attaching'|'in-use'|'detaching'",
                'SubnetId': 'string',
                'TagSet': [{
                    'Key': 'string',
                    'Value': 'string'
                },],
                'VpcId': 'string'
            },],
            'NextToken': 'string'
        }

    def describe_spot_instance_requests(self):
        return {
            'SpotInstanceRequests': [{
                'ActualBlockHourlyPrice': 'string',
                'AvailabilityZoneGroup': 'string',
                'BlockDurationMinutes': 123,
                'CreateTime': "1970-01-01",
                'Fault': {
                    'Code': 'string',
                    'Message': 'string'
                },
                'InstanceId': 'string',
                'LaunchGroup': 'string',
                'LaunchSpecification': {
                    'UserData': 'string',
                    'SecurityGroups': [{
                        'GroupName': 'string',
                        'GroupId': 'string'
                    },],
                    'AddressingType': 'string',
                    'BlockDeviceMappings': [{
                        'DeviceName': 'string',
                        'VirtualName': 'string',
                        'Ebs': {
                            'DeleteOnTermination': "True|False",
                            'Iops': 123,
                            'SnapshotId': 'string',
                            'VolumeSize': 123,
                            'VolumeType': "'standard'|'io1'|'gp2'|'sc1'|'st1'",
                            'Encrypted': "True|False",
                            'KmsKeyId': 'string'
                        },
                        'NoDevice': 'string'
                    },],
                    'EbsOptimized': "True|False",
                    'IamInstanceProfile': {
                        'Arn': 'string',
                        'Name': 'string'
                    },
                    'ImageId': 'string',
                    'InstanceType': "'%s'" % "'|'".join(AWSEC2InstTypes),
                    'KernelId': 'string',
                    'KeyName': 'string',
                    'NetworkInterfaces': [{
                        'AssociatePublicIpAddress': "True|False",
                        'DeleteOnTermination': "True|False",
                        'Description': 'string',
                        'DeviceIndex': 123,
                        'Groups': ['string',],
                        'Ipv6AddressCount': 123,
                        'Ipv6Addresses': [{
                            'Ipv6Address': 'string'
                        },],
                        'NetworkInterfaceId': 'string',
                        'PrivateIpAddress': 'string',
                        'PrivateIpAddresses': [{
                            'Primary': "True|False",
                            'PrivateIpAddress': 'string'
                        },],
                        'SecondaryPrivateIpAddressCount': 123,
                        'SubnetId': 'string'
                    },],
                    'Placement': {
                        'AvailabilityZone': 'string',
                        'GroupName': 'string',
                        'Tenancy': "'default'|'dedicated'|'host'"
                    },
                    'RamdiskId': 'string',
                    'SubnetId': 'string',
                    'Monitoring': {
                        'Enabled': "True|False"
                    }
                },
                'LaunchedAvailabilityZone': 'string',
                'ProductDescription': "'Linux/UNIX'|'Linux/UNIX (Amazon VPC)'|'Windows'|'Windows (Amazon VPC)'",
                'SpotInstanceRequestId': 'string',
                'SpotPrice': 'string',
                'State': "'open'|'active'|'closed'|'cancelled'|'failed'",
                'Status': {
                    'Code': 'string',
                    'Message': 'string',
                    'UpdateTime': "1970-01-01",
                },
                'Tags': [{
                    'Key': 'string',
                    'Value': 'string'
                },],
                'Type': "'one-time' | 'persistent'",
                'ValidFrom': "1970-01-01",
                'ValidUntil': "1970-01-01",
                'InstanceInterruptionBehavior': "'hibernate'|'stop'|'terminate'"
            },],
            'NextToken': 'string'
        }

    def describe_spot_fleet_requests(self):
        return {
            'NextToken': 'string',
            'SpotFleetRequestConfigs': [{
                'ActivityStatus': "'error'|'pending_fulfillment'|'pending_termination'|'fulfilled'",
                'CreateTime': "1970-01-01",
                'SpotFleetRequestConfig': {
                    'AllocationStrategy': "'lowestPrice'|'diversified'",
                    'OnDemandAllocationStrategy': "'lowestPrice'|'prioritized'",
                    'ClientToken': 'string',
                    'ExcessCapacityTerminationPolicy': "'noTermination'|'default'",
                    'FulfilledCapacity': 123.0,
                    'OnDemandFulfilledCapacity': 123.0,
                    'IamFleetRole': 'string',
                    'LaunchSpecifications': [{
                        'SecurityGroups': [{
                            'GroupName': 'string',
                            'GroupId': 'string'
                        },],
                        'AddressingType': 'string',
                        'BlockDeviceMappings': [{
                            'DeviceName': 'string',
                            'VirtualName': 'string',
                            'Ebs': {
                                'DeleteOnTermination': "True|False",
                                'Iops': 123,
                                'SnapshotId': 'string',
                                'VolumeSize': 123,
                                'VolumeType': "'standard'|'io1'|'gp2'|'sc1'|'st1'",
                                'Encrypted': "True|False",
                                'KmsKeyId': 'string'
                            },
                            'NoDevice': 'string'
                        },],
                        'EbsOptimized': "True|False",
                        'IamInstanceProfile': {
                            'Arn': 'string',
                            'Name': 'string'
                        },
                        'ImageId': 'string',
                        'InstanceType': "'%s'" % "'|'".join(AWSEC2InstTypes),
                        'KernelId': 'string',
                        'KeyName': 'string',
                        'Monitoring': {
                            'Enabled': "True|False"
                        },
                        'NetworkInterfaces': [{
                            'AssociatePublicIpAddress': "True|False",
                            'DeleteOnTermination': "True|False",
                            'Description': 'string',
                            'DeviceIndex': 123,
                            'Groups': ['string',],
                            'Ipv6AddressCount': 123,
                            'Ipv6Addresses': [{
                                'Ipv6Address': 'string'
                            },],
                            'NetworkInterfaceId': 'string',
                            'PrivateIpAddress': 'string',
                            'PrivateIpAddresses': [{
                                'Primary': "True|False",
                                'PrivateIpAddress': 'string'
                            },],
                            'SecondaryPrivateIpAddressCount': 123,
                            'SubnetId': 'string'
                        },],
                        'Placement': {
                            'AvailabilityZone': 'string',
                            'GroupName': 'string',
                            'Tenancy': "'default'|'dedicated'|'host'"
                        },
                        'RamdiskId': 'string',
                        'SpotPrice': 'string',
                        'SubnetId': 'string',
                        'UserData': 'string',
                        'WeightedCapacity': 123.0,
                        'TagSpecifications': [{
                            'ResourceType':
                                "'client-vpn-endpoint'|'customer-gateway'|'dedicated-host'|"
                                "'dhcp-options'|'elastic-ip'|'fleet'|'fpga-image'|"
                                "'host-reservation'|'image'|'instance'|'internet-gateway'|"
                                "'launch-template'|'natgateway'|'network-acl'|"
                                "'network-interface'|'reserved-instances'|'route-table'|"
                                "'security-group'|'snapshot'|'spot-instances-request'|"
                                "'subnet'|'transit-gateway'|'transit-gateway-attachment'|"
                                "'transit-gateway-route-table'|'volume'|'vpc'|"
                                "'vpc-peering-connection'|'vpn-connection'|'vpn-gateway'",
                            'Tags': [{
                                'Key': 'string',
                                'Value': 'string'
                            },]
                        },]
                    },],
                    'LaunchTemplateConfigs': [{
                        'LaunchTemplateSpecification': {
                            'LaunchTemplateId': 'string',
                            'LaunchTemplateName': 'string',
                            'Version': 'string'
                        },
                        'Overrides': [{
                            'InstanceType': "'%s'" % "'|'".join(AWSEC2InstTypes),
                            'SpotPrice': 'string',
                            'SubnetId': 'string',
                            'AvailabilityZone': 'string',
                            'WeightedCapacity': 123.0,
                            'Priority': 123.0
                        },]
                    },],
                    'SpotPrice': 'string',
                    'TargetCapacity': 123,
                    'OnDemandTargetCapacity': 123,
                    'TerminateInstancesWithExpiration': "True|False",
                    'Type': "'request'|'maintain'|'instant'",
                    'ValidFrom': "1970-01-01",
                    'ValidUntil': "1970-01-01",
                    'ReplaceUnhealthyInstances': "True|False",
                    'InstanceInterruptionBehavior': "'hibernate'|'stop'|'terminate'",
                    'LoadBalancersConfig': {
                        'ClassicLoadBalancersConfig': {
                            'ClassicLoadBalancers': [{
                                'Name': 'string'
                            },]
                        },
                        'TargetGroupsConfig': {
                            'TargetGroups': [{
                                'Arn': 'string'
                            },]
                        }
                    },
                    'InstancePoolsToUseCount': 123
                },
                'SpotFleetRequestId': 'string',
                'SpotFleetRequestState': "'submitted'|'active'|'cancelled'|'failed'|'cancelled_running'|'cancelled_terminating'|'modifying'"
            },]
        }

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


def test_agent_aws_ec2_result_distribution():
    region = 'region'
    config = AWSConfig('hostname', (None, None))
    config.add_single_service_config('ec2_names', None)
    config.add_service_tags('ec2_tags', (None, None))

    fake_ec2_client = FakeEC2Client()
    fake_cloudwatch_client = FakeCloudwatchClient()

    ec2_limits_distributor = ResultDistributor()
    ec2_summary_distributor = ResultDistributor()

    ec2_limits = EC2Limits(fake_ec2_client, region, config, ec2_limits_distributor)
    ec2_summary = EC2Summary(fake_ec2_client, region, config, ec2_summary_distributor)
    ec2_labels = EC2Labels(fake_ec2_client, region, config)
    ec2_security_groups = EC2SecurityGroups(fake_ec2_client, region, config)
    ec2 = EC2(fake_cloudwatch_client, region, config)

    ec2_limits_distributor.add(ec2_summary)
    ec2_summary_distributor.add(ec2_labels)
    ec2_summary_distributor.add(ec2_security_groups)
    ec2_summary_distributor.add(ec2)

    _ec2_limits_results = ec2_limits.run().results
    _ec2_summary_results = ec2_summary.run().results
    _ec2_labels_results = ec2_labels.run().results
    _ec2_security_groups_results = ec2_security_groups.run().results
    _ec2_results = ec2.run().results

    #--EC2Limits------------------------------------------------------------
    assert ec2_limits.interval == 300
    assert ec2_limits.name == "ec2_limits"

    #--EC2Summary-----------------------------------------------------------
    assert ec2_summary.interval == 300
    assert ec2_summary.name == "ec2_summary"

    #--EC2Labels------------------------------------------------------------
    assert ec2_labels.interval == 300
    assert ec2_labels.name == "ec2_labels"

    #--EC2SecurityGroups----------------------------------------------------
    assert ec2_security_groups.interval == 300
    assert ec2_security_groups.name == "ec2_security_groups"

    #--EC2------------------------------------------------------------------
    assert ec2.interval == 300
    assert ec2.name == "ec2"
