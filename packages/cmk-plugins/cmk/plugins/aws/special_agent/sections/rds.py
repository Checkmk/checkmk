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

from ..config import AWSConfig, LOGGER, Tags
from .core import (
    AWSColleagueContents,
    AWSComputedContent,
    AWSLimit,
    AWSRawContent,
    AWSSection,
    AWSSectionCloudwatch,
    AWSSectionLimits,
    AWSSectionResult,
    Metric,
    Metrics,
    ResultDistributor,
)

AWSRDSLimitNameMap: Mapping[str, tuple[str, str]] = {
    "DBClusters": ("db_clusters", "DB clusters"),
    "DBClusterParameterGroups": ("db_cluster_parameter_groups", "DB cluster parameter groups"),
    "DBInstances": ("db_instances", "DB instances"),
    "EventSubscriptions": ("event_subscriptions", "Event subscriptions"),
    "ManualSnapshots": ("manual_snapshots", "Manual snapshots"),
    "OptionGroups": ("option_groups", "Option groups"),
    "DBParameterGroups": ("db_parameter_groups", "DB parameter groups"),
    "ReadReplicasPerMaster": ("read_replica_per_master", "Read replica per master"),
    "ReservedDBInstances": ("reserved_db_instances", "Reserved DB instances"),
    "DBSecurityGroups": ("db_security_groups", "DB security groups"),
    "DBSubnetGroups": ("db_subnet_groups", "DB subnet groups"),
    "SubnetsPerDBSubnetGroup": ("subnet_per_db_subnet_groups", "Subnet per DB subnet groups"),
    "AllocatedStorage": ("allocated_storage", "Allocated storage"),
    "AuthorizationsPerDBSecurityGroup": (
        "auths_per_db_security_groups",
        "Authorizations per DB security group",
    ),
    "DBClusterRoles": ("db_cluster_roles", "DB cluster roles"),
}


class RDSLimits(AWSSectionLimits):
    @property
    @override
    def name(self) -> str:
        return "rds_limits"

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
        """
        AWS/RDS API method 'describe_account_attributes' already sends
        limit and usage values.
        """
        response = self._client.describe_account_attributes()  # type: ignore[attr-defined]
        return self._get_response_content(response, "AccountQuotas")

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        for limit in raw_content.content:
            quota_name = limit["AccountQuotaName"]
            key, title = AWSRDSLimitNameMap.get(quota_name, (None, None))
            if key is None or title is None:
                LOGGER.info(
                    "%(name)s: Unhandled account quota name: '%(quota_name)s'",
                    {"name": self.name, "quota_name": quota_name},
                )
                continue
            self._add_limit(
                "",
                AWSLimit(
                    key,
                    title,
                    int(limit["Max"]),
                    int(limit["Used"]),
                ),
            )
        return AWSComputedContent(None, 0.0)


class RDSSummary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["rds_names"]
        self._tags = self.prepare_tags_for_api_response(self._config.service_config["rds_tags"])

    @property
    @override
    def name(self) -> str:
        return "rds_summary"

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
        db_instances = []

        for instance in self._describe_db_instances():
            tags = self._get_instance_tags(instance["DBInstanceArn"])
            if self._matches_tag_conditions(tags):
                instance["Region"] = self._region
                instance["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(tags)
                db_instances.append(instance)

        return db_instances

    def _describe_db_instances(self):
        instances = []

        if self._names is None:
            for page in self._client.get_paginator("describe_db_instances").paginate():
                instances.extend(self._get_response_content(page, "DBInstances"))
            return instances

        for name in self._names:
            try:
                for page in self._client.get_paginator("describe_db_instances").paginate(
                    DBInstanceIdentifier=name
                ):
                    instances.extend(self._get_response_content(page, "DBInstances"))
            # NOTE: The suppression below is needed because of BaseClientExceptions.__getattr__ magic.
            except self._client.exceptions.DBInstanceNotFoundFault:  # type: ignore[misc]
                pass

        return instances

    def _get_instance_tags(self, instance_arn: str) -> Tags:
        # list_tags_for_resource cannot be paginated
        return self._get_response_content(
            self._client.list_tags_for_resource(ResourceName=instance_arn),  # type: ignore[attr-defined]
            "TagList",
        )

    def _matches_tag_conditions(self, tagging: Tags) -> bool:
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        return any(tag in self._tags for tag in tagging)

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(
            {instance["DBInstanceIdentifier"]: instance for instance in raw_content.content},
            raw_content.cache_timestamp,
        )

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", list(computed_content.content.values()))]


class RDS(AWSSectionCloudwatch):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._separator = " "

    @property
    @override
    def name(self) -> str:
        return "rds"

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
        colleague = self._received_results.get("rds_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        # the documentation
        # https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/MonitoringOverview.html
        # seems to be partially wrong: FailedSQLServerAgentJobsCount has to be queried in Counts
        # (instead of Count/Minute) and OldestReplicationSlotLag, ReplicationSlotDiskUsage and
        # TransactionLogsDiskUsage have to be queried in Bytes (instead of Megabytes)
        metrics: Metrics = []
        for idx, (instance_id, instance) in enumerate(colleague_contents.content.items()):
            for metric_name, stat, unit in [
                ("BinLogDiskUsage", "Average", "Bytes"),
                ("BurstBalance", "Average", "Percent"),
                ("CPUUtilization", "Average", "Percent"),
                ("CPUCreditUsage", "Average", "Count"),
                ("CPUCreditBalance", "Average", "Count"),
                ("DatabaseConnections", "Average", "Count"),
                ("DiskQueueDepth", "Average", "Count"),
                ("FailedSQLServerAgentJobsCount", "Sum", "Count"),
                ("NetworkReceiveThroughput", "Average", "Bytes/Second"),
                ("NetworkTransmitThroughput", "Average", "Bytes/Second"),
                ("OldestReplicationSlotLag", "Average", "Bytes"),
                ("ReadIOPS", "Average", "Count/Second"),
                ("ReadLatency", "Average", "Seconds"),
                ("ReadThroughput", "Average", "Bytes/Second"),
                ("ReplicaLag", "Average", "Seconds"),
                ("ReplicationSlotDiskUsage", "Average", "Bytes"),
                ("TransactionLogsDiskUsage", "Average", "Bytes"),
                ("TransactionLogsGeneration", "Average", "Bytes/Second"),
                ("WriteIOPS", "Average", "Count/Second"),
                ("WriteLatency", "Average", "Seconds"),
                ("WriteThroughput", "Average", "Bytes/Second"),
                # ("FreeableMemory", "Bytes"),
                # ("SwapUsage", "Bytes"),
                # ("FreeStorageSpace", "Bytes"),
                # ("MaximumUsedTransactionIDs", "Count"),
            ]:
                metric: Metric = {
                    "Id": self._create_id_for_metric_data_query(idx, metric_name),
                    "Label": instance_id + self._separator + instance["Region"],
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/RDS",
                            "MetricName": metric_name,
                            "Dimensions": [
                                {
                                    "Name": "DBInstanceIdentifier",
                                    "Value": instance_id,
                                }
                            ],
                        },
                        "Period": self.period,
                        "Stat": stat,
                        "Unit": unit,
                    },
                }
                metrics.append(metric)
        return metrics

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        for row in raw_content.content:
            instance_id = row["Label"].split(self._separator)[0]
            row.update(colleague_contents.content.get(instance_id, {}))
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]
