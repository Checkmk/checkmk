#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from argparse import Namespace as Args
from collections.abc import Collection, Mapping, Sequence
from typing import Protocol

import pytest

from cmk.plugins.aws_v2.special_agent.config import (
    AWSConfig,
    NamingConvention,
    OverallTags,
    TagsImportPatternOption,
    TagsOption,
)
from cmk.plugins.aws_v2.special_agent.hosts import TargetHost
from cmk.plugins.aws_v2.special_agent.sections.core import ResultDistributor
from cmk.plugins.aws_v2.special_agent.sections.ec2 import (
    EC2,
    EC2Limits,
    EC2SecurityGroups,
    EC2Summary,
)

from .agent_aws_fake_clients import (
    EC2DescribeAddressesIB,
    EC2DescribeInstancesIB,
    EC2DescribeNetworkInterfacesIB,
    EC2DescribeReservedInstancesIB,
    EC2DescribeSecurityGroupsIB,
    EC2DescribeSpotFleetRequestsIB,
    EC2DescribeSpotInstanceRequestsIB,
    FakeCloudwatchClient,
    FakeServiceQuotasClient,
)

ACCOUNT_HOST = TargetHost("123456789012")


class FakeEC2Client:
    def __init__(
        self,
        skip_entities: Mapping[str, Collection[str]] | None = None,
        name_tags: Mapping[str, str] | None = None,
    ) -> None:
        self._skip_entities: Mapping[str, Collection[str]] = skip_entities if skip_entities else {}
        # The Name tag of some instances, by instance ID.
        self._name_tags: Mapping[str, str] = name_tags or {}

    def describe_instances(
        self,
        InstanceIds: object = None,  # noqa: ARG002
        Filters: object = None,  # noqa: ARG002
    ) -> Mapping[str, object]:
        instances = EC2DescribeInstancesIB.create_instances(
            amount=3, skip_entities=self._skip_entities.get("Instances")
        )

        for instance in instances:
            if instance["InstanceId"] == "InstanceId-0":
                continue
            instance["Tags"] = []
        for instance in instances:
            if (name := self._name_tags.get(instance["InstanceId"])) is not None:
                instance["Tags"] = [*instance["Tags"], {"Key": "Name", "Value": name}]

        return {
            "Reservations": [
                {
                    "Groups": [
                        {"GroupName": "string", "GroupId": "string"},
                    ],
                    "Instances": instances,
                    "OwnerId": "string",
                    "RequesterId": "string",
                    "ReservationId": "string",
                },
            ],
            "NextToken": "string",
        }

    def describe_reserved_instances(self) -> Mapping[str, object]:
        return {
            "ReservedInstances": EC2DescribeReservedInstancesIB.create_instances(
                amount=3,
                skip_entities=self._skip_entities.get("ReservedInstances", []),
            ),
        }

    def describe_addresses(self) -> Mapping[str, object]:
        return {
            "Addresses": EC2DescribeAddressesIB.create_instances(amount=3),
        }

    def describe_security_groups(
        self,
        InstanceIds: object = None,  # noqa: ARG002
        Filters: object = None,  # noqa: ARG002
    ) -> Mapping[str, object]:
        return {
            "SecurityGroups": EC2DescribeSecurityGroupsIB.create_instances(amount=3),
            "NextToken": "string",
        }

    def describe_network_interfaces(self) -> Mapping[str, object]:
        return {
            "NetworkInterfaces": EC2DescribeNetworkInterfacesIB.create_instances(amount=3),
            "NextToken": "string",
        }

    def describe_spot_instance_requests(self) -> Mapping[str, object]:
        return {
            "SpotInstanceRequests": EC2DescribeSpotInstanceRequestsIB.create_instances(amount=3),
            "NextToken": "string",
        }

    def describe_spot_fleet_requests(self) -> Mapping[str, object]:
        return {
            "SpotFleetRequestConfigs": EC2DescribeSpotFleetRequestsIB.create_instances(amount=3),
            "NextToken": "string",
        }


EC2SectionsOut = tuple[EC2Limits, EC2Summary, EC2SecurityGroups, EC2]


class EC2Sections(Protocol):
    def __call__(
        self,
        names: object | None = None,
        tags: OverallTags = (None, None),
        skip_entities: Mapping[str, Collection[str]] | None = None,
        tag_import: TagsOption = TagsImportPatternOption.import_all,
        naming_convention: NamingConvention = NamingConvention.ip_region_instance,
        name_tags: Mapping[str, str] | None = None,
    ) -> EC2SectionsOut: ...


@pytest.fixture()
def get_ec2_sections() -> EC2Sections:
    def _create_ec2_sections(
        names: object | None = None,
        tags: OverallTags = (None, None),
        skip_entities: Mapping[str, Collection[str]] | None = None,
        tag_import: TagsOption = TagsImportPatternOption.import_all,
        naming_convention: NamingConvention = NamingConvention.ip_region_instance,
        name_tags: Mapping[str, str] | None = None,
    ) -> EC2SectionsOut:
        region = "region"
        config = AWSConfig("hostname", Args(), ([], []), naming_convention, tag_import).for_account(
            "123456789012"
        )
        config.add_single_service_config("ec2_names", names)
        config.add_service_tags("ec2_tags", tags)
        fake_ec2_client = FakeEC2Client(skip_entities, name_tags)
        fake_cloudwatch_client = FakeCloudwatchClient()
        fake_service_quotas_client = FakeServiceQuotasClient()

        distributor = ResultDistributor()

        # TODO: FakeEC2Client shoud actually subclass EC2Client, etc.
        ec2_limits = EC2Limits(
            fake_ec2_client,
            region,
            config,
            distributor,
            fake_service_quotas_client,
        )
        ec2_summary = EC2Summary(fake_ec2_client, region, config, distributor)
        ec2_security_groups = EC2SecurityGroups(fake_ec2_client, region, config)
        ec2 = EC2(fake_cloudwatch_client, region, config)

        distributor.add(ec2_limits.name, ec2_summary)
        distributor.add(ec2_summary.name, ec2_security_groups)
        distributor.add(ec2_summary.name, ec2)
        return ec2_limits, ec2_summary, ec2_security_groups, ec2

    return _create_ec2_sections


ec2_params = [
    (None, (None, None), 3),
    (None, (["Key-0"], ["Value-0"]), 1),
    (None, (["Key-X"], ["Value-0"]), 0),
    (None, (["Key-0"], ["Value-X"]), 0),
    (None, (["Key-0"], ["Value-1"]), 0),
    (None, (["Key-1", "Key-1"], ["Value-0", "Value-1"]), 1),
    (None, (["Key-0", "Key-0"], ["Value-0", "Value-1"]), 1),
    (["InstanceId-0"], (None, None), 1),
    (["InstanceId-0", "Foo", "Bar"], (None, None), 1),
    (["InstanceId-0", "InstanceId-1"], (None, None), 2),
    (["InstanceId-0", "InstanceId-1", "Foo", "Bar"], (None, None), 2),
    (["InstanceId-0", "InstanceId-1", "InstanceId-2"], (None, None), 3),
    (["InstanceId-0", "InstanceId-1", "InstanceId-2", "Foo", "Bar"], (None, None), 3),
    (["Foo", "Bar"], (None, None), 0),
]


@pytest.mark.parametrize("names,tags,found_ec2", ec2_params)
def test_agent_aws_ec2_limits(
    get_ec2_sections: EC2Sections,
    names: Sequence[str] | None,
    tags: OverallTags,
    found_ec2: int,  # noqa: ARG001
) -> None:
    ec2_limits, _ec2_summary, _ec2_security_groups, _ec2 = get_ec2_sections(names, tags)
    ec2_limits_results = ec2_limits.run().results

    assert ec2_limits.cache_interval == 300
    assert ec2_limits.period == 600
    assert ec2_limits.name == "ec2_limits"
    assert len(ec2_limits_results) == 1

    for result in ec2_limits_results:
        assert result.piggyback_hostname == ACCOUNT_HOST
        for limit in result.content:
            assert limit.key in [
                "vpc_elastic_ip_addresses",
                "elastic_ip_addresses",
                "spot_inst_requests",
                "active_spot_fleet_requests",
                "spot_fleet_total_target_capacity",
                "vpc_sec_group_rules",
                "vpc_sec_groups",
                "if_vpc_sec_group",
            ] or limit.key.startswith("running_ondemand_instances_")


@pytest.mark.parametrize(
    ("key", "expected_limit"),
    [
        pytest.param("vpc_elastic_ip_addresses", 8, id="vpc_eip-from_quota"),
        pytest.param("vpc_sec_groups", 42, id="vpc_sec_groups-from_quota"),
        pytest.param("if_vpc_sec_group", 13, id="if_vpc_sec_group-from_quota"),
        pytest.param("vpc_sec_group_rules", 120, id="vpc_sec_group_rules-default"),
    ],
)
def test_agent_aws_ec2_limits_vpc_limit(
    get_ec2_sections: EC2Sections, key: str, expected_limit: int
) -> None:
    ec2_limits, *_ = get_ec2_sections()
    results = ec2_limits.run().results

    limits_by_key = {limit.key: limit for result in results for limit in result.content}
    assert limits_by_key[key].limit == expected_limit


@pytest.mark.parametrize("names,tags,found_ec2", ec2_params)
def test_agent_aws_ec2_summary(
    get_ec2_sections: EC2Sections,
    names: Sequence[str] | None,
    tags: OverallTags,
    found_ec2: int,
) -> None:
    ec2_limits, ec2_summary, _ec2_security_groups, _ec2 = get_ec2_sections(names, tags)
    _ec2_limits_results = ec2_limits.run().results
    ec2_summary_results = ec2_summary.run().results

    assert ec2_summary.cache_interval == 300
    assert ec2_summary.period == 600
    assert ec2_summary.name == "ec2_summary"

    if found_ec2:
        assert len(ec2_summary_results) == 1

        result = ec2_summary_results[0]
        assert result.piggyback_hostname == ACCOUNT_HOST
        assert len(result.content) == found_ec2

    else:
        assert len(ec2_summary_results) == 0


@pytest.mark.parametrize("names,tags,found_ec2", ec2_params)
def test_agent_aws_ec2_security_groups(
    get_ec2_sections: EC2Sections,
    names: Sequence[str] | None,
    tags: OverallTags,
    found_ec2: int,
) -> None:
    ec2_limits, ec2_summary, ec2_security_groups, _ec2 = get_ec2_sections(names, tags)
    _ec2_limits_results = ec2_limits.run().results
    _ec2_summary_results = ec2_summary.run().results
    ec2_security_groups_results = ec2_security_groups.run().results

    assert ec2_security_groups.cache_interval == 300
    assert ec2_security_groups.period == 600
    assert ec2_security_groups.name == "ec2_security_groups"

    assert len(ec2_security_groups_results) == found_ec2

    for result in ec2_security_groups_results:
        assert result.piggyback_hostname != ACCOUNT_HOST


@pytest.mark.parametrize("names,tags,found_ec2", ec2_params)
def test_agent_aws_ec2(
    get_ec2_sections: EC2Sections,
    names: Sequence[str] | None,
    tags: OverallTags,
    found_ec2: int,
) -> None:
    ec2_limits, ec2_summary, _ec2_security_groups, ec2 = get_ec2_sections(names, tags)
    _ec2_limits_results = ec2_limits.run().results
    _ec2_summary_results = ec2_summary.run().results
    ec2_results = ec2.run().results

    assert ec2.cache_interval == 300
    assert ec2.period == 600
    assert ec2.name == "ec2"

    assert len(ec2_results) == found_ec2

    for result in ec2_results:
        assert result.piggyback_hostname != ACCOUNT_HOST

        # 11 metrics
        assert len(result.content) == 11


def test_agent_aws_ec2_summary_without_limits(
    get_ec2_sections: EC2Sections,
) -> None:
    _ec2_limits, ec2_summary, _ec2_security_groups, _ec2 = get_ec2_sections()
    ec2_summary_results = ec2_summary.run().results

    assert ec2_summary.cache_interval == 300
    assert ec2_summary.period == 600
    assert ec2_summary.name == "ec2_summary"

    assert len(ec2_summary_results) == 1

    result = ec2_summary_results[0]
    assert result.piggyback_hostname == ACCOUNT_HOST
    assert len(result.content) == 3


def test_agent_aws_ec2_security_groups_without_limits(
    get_ec2_sections: EC2Sections,
) -> None:
    _ec2_limits, ec2_summary, ec2_security_groups, _ec2 = get_ec2_sections()
    _ec2_summary_results = ec2_summary.run().results
    ec2_security_groups_results = ec2_security_groups.run().results

    assert ec2_security_groups.cache_interval == 300
    assert ec2_security_groups.period == 600
    assert ec2_security_groups.name == "ec2_security_groups"

    assert len(ec2_security_groups_results) == 3

    for result in ec2_security_groups_results:
        assert result.piggyback_hostname != ACCOUNT_HOST


def test_agent_aws_ec2_without_limits(get_ec2_sections: EC2Sections) -> None:
    _ec2_limits, ec2_summary, _ec2_security_groups, ec2 = get_ec2_sections()
    _ec2_summary_results = ec2_summary.run().results
    ec2_results = ec2.run().results

    assert ec2.cache_interval == 300
    assert ec2.period == 600
    assert ec2.name == "ec2"

    assert len(ec2_results) == 3

    for result in ec2_results:
        assert result.piggyback_hostname != ACCOUNT_HOST

        # 11 metrics
        assert len(result.content) == 11


def test_agent_aws_ec2_metrics_go_to_ip_region_instance_hosts(
    get_ec2_sections: EC2Sections,
) -> None:
    _ec2_limits, ec2_summary, _ec2_security_groups, ec2 = get_ec2_sections(
        naming_convention=NamingConvention.ip_region_instance
    )
    ec2_summary.run()

    ec2_results = ec2.run().results

    assert sorted(result.piggyback_hostname for result in ec2_results) == [
        "PrivateIpAddress-0-region-InstanceId-0",
        "PrivateIpAddress-1-region-InstanceId-1",
        "PrivateIpAddress-2-region-InstanceId-2",
    ]


def test_agent_aws_ec2_metrics_go_to_private_dns_name_hosts(
    get_ec2_sections: EC2Sections,
) -> None:
    _ec2_limits, ec2_summary, _ec2_security_groups, ec2 = get_ec2_sections(
        naming_convention=NamingConvention.private_dns_name
    )
    ec2_summary.run()

    ec2_results = ec2.run().results

    assert sorted(result.piggyback_hostname for result in ec2_results) == [
        "PrivateDnsName-0",
        "PrivateDnsName-1",
        "PrivateDnsName-2",
    ]


def test_agent_aws_ec2_security_groups_go_to_the_host_of_their_instance(
    get_ec2_sections: EC2Sections,
) -> None:
    _ec2_limits, ec2_summary, ec2_security_groups, _ec2 = get_ec2_sections()
    ec2_summary.run()

    ec2_security_groups_results = ec2_security_groups.run().results

    assert sorted(result.piggyback_hostname for result in ec2_security_groups_results) == [
        "PrivateIpAddress-0-region-InstanceId-0",
        "PrivateIpAddress-1-region-InstanceId-1",
        "PrivateIpAddress-2-region-InstanceId-2",
    ]


@pytest.mark.parametrize("names,tags,found_ec2", ec2_params)
@pytest.mark.parametrize(
    "skip_entities",
    [
        {"ReservedInstances": ["AvailabilityZone"]},
        {"Instances": ["Tags"]},  # Fix for FEED-6986
    ],
)
def test_agent_aws_ec2_no_crash_when_keys_missing(
    get_ec2_sections: EC2Sections,
    names: Sequence[str] | None,
    tags: OverallTags,
    found_ec2: int,  # noqa: ARG001
    skip_entities: Mapping[str, Collection[str]],
) -> None:
    ec2_limits, ec2_summary, _ec2_security_groups, _ec2 = get_ec2_sections(
        names, tags, skip_entities=skip_entities
    )
    ec2_limits_results = ec2_limits.run().results
    ec2_summary.run()
    assert len(ec2_limits_results) == 1


@pytest.mark.parametrize(
    "tag_import, expected_tags",
    [
        (TagsImportPatternOption.import_all, ["Key-0", "Key-1", "Key-2"]),
        (r".*-1$", ["Key-1"]),
        (TagsImportPatternOption.ignore_all, []),
    ],
)
def test_agent_aws_ec2_filters_labels(
    get_ec2_sections: EC2Sections,
    tag_import: TagsOption,
    expected_tags: Sequence[str],
) -> None:
    _ec2_limits, ec2_summary, _ec2_security_groups, ec2 = get_ec2_sections(
        None, (None, None), tag_import=tag_import
    )
    ec2_summary_results = ec2_summary.run().results
    ec2_results = ec2.run().results

    labels = {result.piggyback_hostname: result.piggyback_host_labels for result in ec2_results}[
        "PrivateIpAddress-0-region-InstanceId-0"
    ]
    assert [key for key in labels if key.startswith("cmk/aws/tag/")] == [
        f"cmk/aws/tag/{tag}" for tag in expected_tags
    ]

    for result in ec2_summary_results:
        assert list(result.content[0]["TagsForCmkLabels"].keys()) == expected_tags


def test_agent_aws_ec2_limits_go_to_the_account_host_of_a_listed_account() -> None:
    config = AWSConfig(
        "hostname", Args(), ([], []), NamingConvention.ip_region_instance
    ).for_account("333333333333")
    config.add_single_service_config("ec2_names", None)
    config.add_service_tags("ec2_tags", (None, None))
    ec2_limits = EC2Limits(
        FakeEC2Client(), "region", config, ResultDistributor(), FakeServiceQuotasClient()
    )

    ec2_limits_results = ec2_limits.run().results

    assert [result.piggyback_hostname for result in ec2_limits_results] == ["333333333333"]


@pytest.mark.parametrize(
    ("name_tags", "expected_name"),
    [
        pytest.param(
            {"InstanceId-0": "web-server"},
            {"cmk/aws/name": "web-server", "cmk/aws/tag/Name": "web-server"},
            id="Name tag",
        ),
        pytest.param({}, {}, id="no Name tag"),
    ],
)
def test_agent_aws_ec2_instance_hosts_get_the_resource_labels(
    get_ec2_sections: EC2Sections,
    name_tags: Mapping[str, str],
    expected_name: Mapping[str, str],
) -> None:
    _ec2_limits, ec2_summary, _ec2_security_groups, ec2 = get_ec2_sections(name_tags=name_tags)
    ec2_summary.run()

    results = ec2.run().results

    host = "PrivateIpAddress-0-region-InstanceId-0"
    assert {result.piggyback_hostname: result.piggyback_host_labels for result in results}[
        host
    ] == {
        "cmk/aws/ec2": "instance",
        "cmk/aws/service": "ec2",
        **expected_name,
        "cmk/aws/resource_id": "InstanceId-0",
        "cmk/aws/region": "region",
        "cmk/aws/tag/Key-0": "Value-0",
        "cmk/aws/tag/Key-1": "Value-1",
        "cmk/aws/tag/Key-2": "Value-2",
    }
