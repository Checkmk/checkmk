#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

from collections.abc import Mapping
from typing import override

from botocore.client import BaseClient

from ..config import AWSConfig, LOGGER
from .core import (
    AWSColleagueContents,
    AWSComputedContent,
    AWSLimit,
    AWSRawContent,
    AWSSection,
    AWSSectionCloudwatch,
    AWSSectionLimits,
    AWSSectionResult,
    chunks,
    Metric,
    Metrics,
    ResultDistributor,
)


class EBSLimits(AWSSectionLimits):
    @property
    @override
    def name(self) -> str:
        return "ebs_limits"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    @override
    def get_live_data(self, *args):
        response = self._client.describe_volumes()  # type: ignore[attr-defined]
        volumes = self._get_response_content(response, "Volumes")

        response = self._client.describe_snapshots(OwnerIds=["self"])  # type: ignore[attr-defined]
        snapshots = self._get_response_content(response, "Snapshots")
        return volumes, snapshots

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        volumes, snapshots = raw_content.content

        vol_storage_standard = 0
        vol_storage_io1 = 0
        vol_storage_io2 = 0
        vol_storage_gp2 = 0
        vol_storage_gp3 = 0
        vol_storage_sc1 = 0
        vol_storage_st1 = 0
        vol_iops_io1 = 0
        vol_iops_io2 = 0
        for volume in volumes:
            vol_type = volume["VolumeType"]
            vol_size = volume["Size"]
            if vol_type == "standard":
                vol_storage_standard += vol_size
            elif vol_type == "io1":
                vol_storage_io1 += vol_size
                vol_iops_io1 += volume["Iops"]
            elif vol_type == "io2":
                vol_storage_io2 += vol_size
                vol_iops_io2 += volume["Iops"]
            elif vol_type == "gp2":
                vol_storage_gp2 += vol_size
            elif vol_type == "gp3":
                vol_storage_gp3 += vol_size
            elif vol_type == "sc1":
                vol_storage_sc1 += vol_size
            elif vol_type == "st1":
                vol_storage_st1 += vol_size
            else:
                LOGGER.info(
                    "%(name)s: Unhandled volume type: '%(vol_type)s'",
                    {"name": self.name, "vol_type": vol_type},
                )

        # These are total limits and not instance specific
        # Space values are in TiB.
        # Reference: https://docs.aws.amazon.com/general/latest/gr/ebs-service.html
        self._add_limit(
            "",
            AWSLimit(
                "block_store_snapshots",
                "Block store snapshots",
                100000,
                len(snapshots),
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_space_standard",
                "Magnetic volumes space",
                300,
                vol_storage_standard,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_space_io1",
                "Provisioned IOPS SSD (io1) space",
                300,
                vol_storage_io1,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_iops_io1",
                "Provisioned IOPS SSD (io1) IO operations per second",
                300000,
                vol_storage_io1,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_space_io2",
                "Provisioned IOPS SSD (io2) space",
                20,
                vol_storage_io2,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_iops_io2",
                "Provisioned IOPS SSD (io2) IO operations per second",
                100000,
                vol_storage_io2,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_space_gp2",
                "General Purpose SSD (gp2) space",
                300,
                vol_storage_gp2,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_space_gp3",
                "General Purpose SSD (gp3) space",
                300,
                vol_storage_gp3,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_space_sc1",
                "Cold HDD space",
                300,
                vol_storage_sc1,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_space_st1",
                "Throughput Optimized HDD space",
                300,
                vol_storage_st1,
            ),
        )
        return AWSComputedContent(volumes, raw_content.cache_timestamp)


class EBSSummary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["ebs_names"]
        self._tags = self._config.service_config["ebs_tags"]

    @property
    @override
    def name(self) -> str:
        return "ebs_summary"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("ebs_limits")
        volumes = []
        max_cache_timestamp = 0.0
        if colleague and colleague.content:
            max_cache_timestamp = max(max_cache_timestamp, colleague.cache_timestamp)
            volumes = colleague.content

        colleague = self._received_results.get("ec2_summary")
        instances = {}
        if colleague and colleague.content:
            max_cache_timestamp = max(max_cache_timestamp, colleague.cache_timestamp)
            instances = colleague.content

        return AWSColleagueContents((volumes, instances), max_cache_timestamp)

    @override
    def get_live_data(self, *args: AWSColleagueContents) -> Mapping[str, Mapping[str, object]]:
        (colleague_contents,) = args
        col_volumes, _col_instances = colleague_contents.content
        if self._tags is None and self._names is not None:
            volumes = self._fetch_volumes_filtered_by_names(col_volumes)
        elif self._tags is not None:
            volumes = self._fetch_volumes_filtered_by_tags(col_volumes)
        else:
            volumes = self._fetch_volumes_without_filter(col_volumes)

        formatted_volumes = {v["VolumeId"]: v for v in volumes}
        for vol_id, vol in formatted_volumes.items():
            response = self._client.describe_volume_status(VolumeIds=[vol_id])  # type: ignore[attr-defined]
            for state in self._get_response_content(response, "VolumeStatuses"):
                if state["VolumeId"] == vol_id:
                    vol.setdefault("VolumeStatus", state["VolumeStatus"])
        return formatted_volumes

    def _fetch_volumes_filtered_by_names(self, col_volumes):
        if col_volumes:
            return [v for v in col_volumes if v["VolumeId"] in self._names]
        response = self._client.describe_volumes(VolumeIds=self._names)  # type: ignore[attr-defined]
        return self._get_response_content(response, "Volumes")

    def _fetch_volumes_filtered_by_tags(self, col_volumes):
        if col_volumes:
            tags = self.prepare_tags_for_api_response(self._tags)
            if tags:
                return [v for v in col_volumes for tag in v.get("Tags", []) if tag in tags]

        volumes = []
        for chunk in chunks(self._tags, length=200):
            # EC2 FilterLimitExceeded: The maximum number of filter values
            # specified on a single call is 200
            response = self._client.describe_volumes(Filters=chunk)  # type: ignore[attr-defined]
            volumes.extend(self._get_response_content(response, "Volumes"))
        return volumes

    def _fetch_volumes_without_filter(self, col_volumes):
        if col_volumes:
            return col_volumes
        response = self._client.describe_volumes()  # type: ignore[attr-defined]
        return self._get_response_content(response, "Volumes")

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        _col_volumes, col_instances = colleague_contents.content
        instance_name_mapping = {v["InstanceId"]: k for k, v in col_instances.items()}

        content_by_piggyback_hosts: dict[str, list[str]] = {}
        for vol in raw_content.content.values():
            vol["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(vol.get("Tags", []))

            instance_names = []
            for attachment in vol["Attachments"]:
                # Just for security
                if vol["VolumeId"] != attachment["VolumeId"]:
                    continue
                instance_name = instance_name_mapping.get(attachment["InstanceId"])
                if instance_name is None:
                    instance_name = ""
                instance_names.append(instance_name)

            # Should be attached to max. one instance
            for instance_name in instance_names:
                content_by_piggyback_hosts.setdefault(instance_name, [])
                content_by_piggyback_hosts[instance_name].append(vol)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


class EBS(AWSSectionCloudwatch):
    @property
    @override
    def name(self) -> str:
        return "ebs"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("ebs_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(
                [
                    (instance_name, row["VolumeId"], row["VolumeType"])
                    for instance_name, rows in colleague.content.items()
                    for row in rows
                ],
                colleague.cache_timestamp,
            )
        return AWSColleagueContents([], 0.0)

    @override
    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        muv: list[tuple[str, str, list[str]]] = [
            ("VolumeReadOps", "Count", []),
            ("VolumeWriteOps", "Count", []),
            ("VolumeReadBytes", "Bytes", []),
            ("VolumeWriteBytes", "Bytes", []),
            ("VolumeQueueLength", "Count", []),
            ("BurstBalance", "Percent", ["gp2", "st1", "sc1"]),
            # ("VolumeThroughputPercentage", "Percent", ["io1"]),
            # ("VolumeConsumedReadWriteOps", "Count", ["io1"]),
            # ("VolumeTotalReadTime", "Seconds", []),
            # ("VolumeTotalWriteTime", "Seconds", []),
            # ("VolumeIdleTime", "Seconds", []),
            # ("VolumeStatus", None, []),
            # ("IOPerformance", None, ["io1"]),
        ]
        metrics: Metrics = []
        for idx, (instance_name, volume_name, volume_type) in enumerate(colleague_contents.content):
            for metric_name, unit, volume_types in muv:
                if volume_types and volume_type not in volume_types:
                    continue
                metric: Metric = {
                    "Id": self._create_id_for_metric_data_query(idx, metric_name),
                    "Label": instance_name,
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/EBS",
                            "MetricName": metric_name,
                            "Dimensions": [
                                {
                                    "Name": "VolumeID",
                                    "Value": volume_name,
                                }
                            ],
                        },
                        "Period": self.period,
                        "Stat": "Average",
                    },
                }
                if unit:
                    metric["MetricStat"]["Unit"] = unit
                metrics.append(metric)
        return metrics

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, list[str]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]
