#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from argparse import Namespace as Args
from collections.abc import Sequence
from typing import Protocol

import pytest

from cmk.plugins.aws.special_agent.agent_aws import (
    AWSConfig,
    EBS,
    EBSLimits,
    EBSSummary,
    EC2Summary,
    NamingConvention,
    OverallTags,
    ResultDistributor,
    TagsImportPatternOption,
    TagsOption,
)

from .agent_aws_fake_clients import (
    EC2DescribeInstancesIB,
    EC2DescribeSnapshotsIB,
    EC2DescribeVolumesIB,
    EC2DescribeVolumeStatusIB,
    FakeCloudwatchClient,
)


class FakeEC2Client:
    def describe_instances(self, Filters=None, InstanceIds=None):
        return {
            "Reservations": [
                {
                    "Groups": [
                        {"GroupName": "string", "GroupId": "string"},
                    ],
                    "Instances": EC2DescribeInstancesIB.create_instances(amount=2),
                    "OwnerId": "string",
                    "RequesterId": "string",
                    "ReservationId": "string",
                },
            ],
            "NextToken": "string",
        }

    def describe_snapshots(self, OwnerIds=None):
        return {
            "Snapshots": EC2DescribeSnapshotsIB.create_instances(amount=3),
            "NextToken": "string",
        }

    def describe_volumes(self, VolumeIds=None, Filters=None):
        return {
            "Volumes": EC2DescribeVolumesIB.create_instances(amount=3),
            "NextToken": "string",
        }

    def describe_volume_status(self, VolumeIds=None, Filters=None):
        return {
            "VolumeStatuses": EC2DescribeVolumeStatusIB.create_instances(amount=3),
            "NextToken": "string",
        }


EBSectionsOut = tuple[EC2Summary, EBSLimits, EBSSummary, EBS]


class EBSSections(Protocol):
    def __call__(
        self,
        names: object | None,
        tags: OverallTags,
        tag_import: TagsOption = TagsImportPatternOption.import_all,
    ) -> EBSectionsOut: ...


@pytest.fixture()
def get_ebs_sections() -> EBSSections:
    def _create_ebs_sections(
        names: object | None,
        tags: OverallTags,
        tag_import: TagsOption = TagsImportPatternOption.import_all,
    ) -> EBSectionsOut:
        region = "region"
        config = AWSConfig(
            "hostname", Args(), ([], []), NamingConvention.ip_region_instance, tag_import
        )
        config.add_single_service_config("ebs_names", names)
        config.add_service_tags("ebs_tags", tags)
        config.add_single_service_config("ec2_names", None)
        config.add_service_tags("ec2_tags", ([], []))

        fake_ec2_client = FakeEC2Client()
        fake_cloudwatch_client = FakeCloudwatchClient()

        distributor = ResultDistributor()

        # TODO: FakeEC2Client shoud actually subclass EC2Client, etc.
        ec2_summary = EC2Summary(fake_ec2_client, region, config, distributor)  # type: ignore[arg-type]
        ebs_limits = EBSLimits(fake_ec2_client, region, config, distributor)  # type: ignore[arg-type]
        ebs_summary = EBSSummary(fake_ec2_client, region, config, distributor)  # type: ignore[arg-type]
        ebs = EBS(fake_cloudwatch_client, region, config)  # type: ignore[arg-type]

        distributor.add(ec2_summary.name, ebs_summary)
        distributor.add(ebs_limits.name, ebs_summary)
        distributor.add(ebs_summary.name, ebs)
        return ec2_summary, ebs_limits, ebs_summary, ebs

    return _create_ebs_sections


ebs_params = [
    (None, (None, None), 3),
    (None, ([["Key-0"]], [["Value-0"]]), 3),
    (None, ([["Key-0"]], [["Value-X"]]), 0),
    (None, ([["Key-X"]], [["Value-X"]]), 0),
    (None, ([["Key-0"]], [["Value-0", "Value-X"]]), 3),
    (["VolumeId-0"], (None, None), 1),
    (["VolumeId-0", "VolumeId-1"], (None, None), 2),
    (["VolumeId-0", "Foobar"], (None, None), 1),
    (["VolumeId-0", "VolumeId-1", "Foobar"], (None, None), 2),
    (["Foo", "Bar"], (None, None), 0),
]


@pytest.mark.parametrize("names,tags,found_ebs", ebs_params)
def test_agent_aws_ebs_limits(
    get_ebs_sections: EBSSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    found_ebs: int,
) -> None:
    ec2_summary, ebs_limits, _ebs_summary, _ebs = get_ebs_sections(names, tags)
    _ec2_summary_results = ec2_summary.run().results
    ebs_limits_results = ebs_limits.run().results

    assert ebs_limits.cache_interval == 300
    assert ebs_limits.period == 600
    assert ebs_limits.name == "ebs_limits"

    assert len(ebs_limits_results) == 1

    ebs_limits_result = ebs_limits_results[0]
    assert ebs_limits_result.piggyback_hostname == ""
    assert len(ebs_limits_result.content) == 10

    for limit in ebs_limits_result.content:
        assert limit.key in [
            "block_store_snapshots",
            "block_store_space_standard",
            "block_store_space_io1",
            "block_store_iops_io1",
            "block_store_space_io2",
            "block_store_iops_io2",
            "block_store_space_gp2",
            "block_store_space_gp3",
            "block_store_space_sc1",
            "block_store_space_st1",
        ]


@pytest.mark.parametrize("names,tags,found_ebs", ebs_params)
def test_agent_aws_ebs_summary(
    get_ebs_sections: EBSSections,
    names: list[str] | None,
    tags: OverallTags,
    found_ebs: int,
) -> None:
    ec2_summary, ebs_limits, ebs_summary, _ebs = get_ebs_sections(names, tags)
    _ec2_summary_results = ec2_summary.run().results
    _ebs_limits_results = ebs_limits.run().results
    ebs_summary_results = ebs_summary.run().results

    assert ebs_summary.cache_interval == 300
    assert ebs_summary.period == 600
    assert ebs_summary.name == "ebs_summary"

    assert len(ebs_summary_results) == found_ebs


@pytest.mark.parametrize("names,tags,found_ebs", ebs_params)
def test_agent_aws_ebs(
    get_ebs_sections: EBSSections,
    names: list[str] | None,
    tags: OverallTags,
    found_ebs: int,
) -> None:
    ec2_summary, ebs_limits, ebs_summary, ebs = get_ebs_sections(names, tags)
    _ec2_summary_results = ec2_summary.run().results
    _ebs_limits_results = ebs_limits.run().results
    _ebs_summary_results = ebs_summary.run().results
    ebs_results = ebs.run().results

    assert ebs.cache_interval == 300
    assert ebs.period == 600
    assert ebs.name == "ebs"

    assert len(ebs_results) == found_ebs

    for result in ebs_results:
        # Y (len results) == 6 (metrics) * X (buckets)
        # But: 5 metrics for all volume types
        assert len(result.content) >= 5


def test_agent_aws_ebs_summary_without_limits(
    get_ebs_sections: EBSSections,
) -> None:
    ec2_summary, _ebs_limits, ebs_summary, _ebs = get_ebs_sections(None, (None, None))
    _ec2_summary_results = ec2_summary.run().results
    ebs_summary_results = ebs_summary.run().results

    assert ebs_summary.cache_interval == 300
    assert ebs_summary.period == 600
    assert ebs_summary.name == "ebs_summary"

    assert len(ebs_summary_results) == 3


def test_agent_aws_ebs_without_limits(get_ebs_sections: EBSSections) -> None:
    ec2_summary, _ebs_limits, ebs_summary, ebs = get_ebs_sections(None, (None, None))
    _ec2_summary_results = ec2_summary.run().results
    _ebs_summary_results = ebs_summary.run().results
    ebs_results = ebs.run().results

    assert ebs.cache_interval == 300
    assert ebs.period == 600
    assert ebs.name == "ebs"

    assert len(ebs_results) == 3

    for result in ebs_results:
        # Y (len results) == 6 (metrics) * X (buckets)
        # But: 5 metrics for all volume types
        assert len(result.content) >= 5


@pytest.mark.parametrize(
    "tag_import, expected_tags",
    [
        (TagsImportPatternOption.import_all, ["Key-0", "Key-1", "Key-2"]),
        (r".*-1$", ["Key-1"]),
        (TagsImportPatternOption.ignore_all, []),
    ],
)
def test_agent_aws_ebs_filters_tags(
    get_ebs_sections: EBSSections,
    tag_import: TagsOption,
    expected_tags: Sequence[str],
) -> None:
    _ec2_summary, _ebs_limits, ebs_summary, _ebs = get_ebs_sections(None, (None, None), tag_import)
    ebs_summary_results = ebs_summary.run().results
    ebs_summary_result = ebs_summary_results[0]

    for result in ebs_summary_result.content:
        assert list(result["TagsForCmkLabels"].keys()) == expected_tags
