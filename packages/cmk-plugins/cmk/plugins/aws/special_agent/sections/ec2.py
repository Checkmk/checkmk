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

from collections.abc import Mapping, Sequence
from typing import assert_never, override

from botocore.client import BaseClient
from pydantic import BaseModel, Field

from cmk.plugins.aws.constants import (
    AWS_EC2_INST_FAMILIES,
    AWS_EC2_INST_TYPES,
    AWS_EC2_LIMITS_DEFAULT,
    AWS_EC2_LIMITS_SPECIAL,
)

from ..config import AWSConfig, LOGGER, NamingConvention
from .core import (
    AWSColleagueContents,
    AWSComputedContent,
    AWSLimit,
    AWSRawContent,
    AWSSection,
    AWSSectionCloudwatch,
    AWSSectionLabels,
    AWSSectionLimits,
    AWSSectionResult,
    chunks,
    Metrics,
    ResultDistributor,
)


class Instance(BaseModel):
    private_ip_address: str | None = Field(None, alias="PrivateIpAddress")
    private_dns_name: str | None = Field(None, alias="PrivateDnsName")
    instance_id: str = Field(..., alias="InstanceId")


def _get_ec2_piggyback_hostname(
    piggyback_naming_convention: NamingConvention, inst: Mapping[str, object], region: str
) -> str | None:
    # PrivateIpAddress and InstanceId is available although the instance is stopped
    # When we terminate an instance, the instance gets the state "terminated":
    # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-lifecycle.html
    # The instance remains in this state about 60 minutes, after 60 minutes the
    # instance is no longer visible in the console.
    # In this case we do not deliever any data for this piggybacked host such that
    # the services go stable and Check_MK service reports "CRIT - Got not information".
    parsed_instance = Instance.model_validate(inst)
    match piggyback_naming_convention:
        case NamingConvention.private_dns_name:
            return parsed_instance.private_dns_name
        case NamingConvention.ip_region_instance:
            if parsed_instance.private_ip_address and parsed_instance.instance_id:
                return (
                    f"{parsed_instance.private_ip_address}-{region}-{parsed_instance.instance_id}"
                )
            return None
        case _:
            assert_never(piggyback_naming_convention)


class EC2Limits(AWSSectionLimits):
    @property
    @override
    def name(self) -> str:
        return "ec2_limits"

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
        quota_list = list(self._iter_service_quotas("ec2")) + list(self._iter_service_quotas("vpc"))
        quota_dicts = [q.model_dump() for q in quota_list]

        response = self._client.describe_instances()  # type: ignore[attr-defined]
        reservations = self._get_response_content(response, "Reservations")

        response = self._client.describe_reserved_instances()  # type: ignore[attr-defined]
        reserved_instances = self._get_response_content(response, "ReservedInstances")

        response = self._client.describe_addresses()  # type: ignore[attr-defined]
        addresses = self._get_response_content(response, "Addresses")

        response = self._client.describe_security_groups()  # type: ignore[attr-defined]
        security_groups = self._get_response_content(response, "SecurityGroups")

        response = self._client.describe_network_interfaces()  # type: ignore[attr-defined]
        interfaces = self._get_response_content(response, "NetworkInterfaces")

        response = self._client.describe_spot_instance_requests()  # type: ignore[attr-defined]
        spot_inst_requests = self._get_response_content(response, "SpotInstanceRequests")

        response = self._client.describe_spot_fleet_requests()  # type: ignore[attr-defined]
        spot_fleet_requests = self._get_response_content(response, "SpotFleetRequestConfigs")

        return (
            reservations,
            reserved_instances,
            addresses,
            security_groups,
            interfaces,
            spot_inst_requests,
            spot_fleet_requests,
            quota_dicts,
        )

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        (
            reservations,
            reserved_instances,
            addresses,
            security_groups,
            interfaces,
            spot_inst_requests,
            spot_fleet_requests,
            quotas,
        ) = raw_content.content
        instances = {inst["InstanceId"]: inst for res in reservations for inst in res["Instances"]}
        res_instances = {inst["ReservedInstancesId"]: inst for inst in reserved_instances}
        quotas_by_name: dict[str, float] = {q["QuotaName"]: q["Value"] for q in quotas}
        EC2InstFamiliesquotas = {
            name: int(quotas_by_name[name])
            for name in {name.localize(lambda x: x) for name in AWS_EC2_INST_FAMILIES.values()}
            if name in quotas_by_name
        }

        self._add_instance_limits(
            instances, res_instances, spot_inst_requests, EC2InstFamiliesquotas
        )
        self._add_addresses_limits(addresses, quotas_by_name)
        self._add_security_group_limits(security_groups, quotas_by_name)
        self._add_interface_limits(interfaces, quotas_by_name)
        self._add_spot_inst_limits(spot_inst_requests)
        self._add_spot_fleet_limits(spot_fleet_requests)
        return AWSComputedContent(reservations, raw_content.cache_timestamp)

    def _add_instance_limits(
        self,
        instances: Mapping[str, object],
        res_instances: Mapping[str, object],
        spot_inst_requests: Sequence[Mapping[str, object]],
        instance_quotas: Mapping[str, int],
    ) -> None:
        inst_limits = self._get_inst_limits(instances, spot_inst_requests)
        res_limits = self._get_res_inst_limits(res_instances)

        total_ris = 0
        running_ris = 0
        ondemand_limits: dict[str, int] = {}
        # subtract reservations from instance usage
        for inst_az, inst_types in inst_limits.items():
            if inst_az not in res_limits:
                for inst_type, count in inst_types.items():
                    ondemand_limits[inst_type] = ondemand_limits.get(inst_type, 0) + count
                continue

            # else we have reservations for this AZ
            for inst_type, count in inst_types.items():
                if inst_type not in res_limits[inst_az]:
                    # no reservations for this type
                    ondemand_limits[inst_type] = ondemand_limits.get(inst_type, 0) + count
                    continue

                amount_res_inst_type = res_limits[inst_az][inst_type]
                ondemand = count - amount_res_inst_type
                total_ris += amount_res_inst_type
                if count < amount_res_inst_type:
                    running_ris += count
                else:
                    running_ris += amount_res_inst_type
                if ondemand < 0:
                    # we have unused reservations
                    continue
                ondemand_limits[inst_type] = ondemand_limits.get(inst_type, 0) + ondemand

        dflt_ondemand_limit, _reserved_limit1, _spot_limit1 = AWS_EC2_LIMITS_DEFAULT
        total_instances = 0
        for inst_type, count in ondemand_limits.items():
            ondemand_limit, _reserved_limit, _spot_limit = AWS_EC2_LIMITS_SPECIAL.get(
                inst_type, AWS_EC2_LIMITS_DEFAULT
            )
            if inst_type.endswith("_vcpu"):
                # Maybe should raise instead of unknown family
                try:
                    inst_fam_name = AWS_EC2_INST_FAMILIES[inst_type[0]].localize(lambda x: x)
                except KeyError:
                    inst_fam_name = "Unknown Instance Family"
                ondemand_limit = instance_quotas.get(inst_fam_name, ondemand_limit)
                self._add_limit(
                    "",
                    AWSLimit(
                        "running_ondemand_instances_%s" % inst_type.lower(),
                        inst_fam_name + " vCPUs",
                        ondemand_limit,
                        count,
                    ),
                )
                continue

            total_instances += count
            self._add_limit(
                "",
                AWSLimit(
                    "running_ondemand_instances_%s" % inst_type,
                    "Running On-Demand %s Instances" % inst_type,
                    ondemand_limit,
                    count,
                ),
            )
        self._add_limit(
            "",
            AWSLimit(
                "running_ondemand_instances_total",
                "Total Running On-Demand Instances",
                dflt_ondemand_limit,
                total_instances,
            ),
        )

    def _get_inst_limits(self, instances, spot_inst_requests):
        spot_instance_ids = [inst["InstanceId"] for inst in spot_inst_requests]
        inst_limits: dict[str, dict[str, int]] = {}
        for inst_id, inst in instances.items():
            if inst_id in spot_instance_ids:
                continue
            if inst["State"]["Name"] in ["stopped", "terminated"]:
                continue
            inst_type = inst["InstanceType"]
            inst_az = inst["Placement"]["AvailabilityZone"]
            inst_limits.setdefault(inst_az, {})[inst_type] = (
                inst_limits.get(inst_az, {}).get(inst_type, 0) + 1
            )

            vcount = inst["CpuOptions"]["CoreCount"] * inst["CpuOptions"]["ThreadsPerCore"]
            vcpu_family = "%s_vcpu" % (
                inst_type[0] if inst_type[0] in AWS_EC2_INST_FAMILIES else "_"
            )
            inst_limits[inst_az][vcpu_family] = inst_limits[inst_az].get(vcpu_family, 0) + vcount
        return inst_limits

    def _get_res_inst_limits(self, res_instances):
        res_limits: dict[str, dict[str, int]] = {}
        for res_inst in res_instances.values():
            if res_inst["State"] != "active":
                continue
            inst_type = res_inst["InstanceType"]
            if inst_type not in AWS_EC2_INST_TYPES:
                LOGGER.info(
                    "%(name)s: Unknown instance type '%(inst_type)s'",
                    {"name": self.name, "inst_type": inst_type},
                )
                continue

            inst_az = res_inst.get("AvailabilityZone")
            if not inst_az:
                LOGGER.info("AvailabilityZone not available")
                continue
            res_limits.setdefault(inst_az, {})[inst_type] = (
                res_limits.get(inst_az, {}).get(inst_type, 0) + res_inst["InstanceCount"]
            )
        return res_limits

    def _add_addresses_limits(
        self,
        addresses: Sequence[Mapping[str, object]],
        quotas_by_name: Mapping[str, float],
    ) -> None:
        # Global limits
        vpc_addresses = 0
        std_addresses = 0
        for address in addresses:
            domain = address["Domain"]
            if domain == "vpc":
                vpc_addresses += 1
            elif domain == "standard":
                std_addresses += 1
        self._add_limit(
            "",
            AWSLimit(
                "vpc_elastic_ip_addresses",
                "VPC Elastic IP addresses",
                int(quotas_by_name.get("EC2-VPC Elastic IPs", 5)),
                vpc_addresses,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "elastic_ip_addresses",
                "Elastic IP addresses",
                5,
                std_addresses,
            ),
        )

    def _add_security_group_limits(
        self,
        security_groups: Sequence[Mapping],
        quotas_by_name: Mapping[str, float],
    ) -> None:
        self._add_limit(
            "",
            AWSLimit(
                "vpc_sec_groups",
                "VPC security groups",
                int(quotas_by_name.get("VPC security groups per Region", 2500)),
                len(security_groups),
            ),
        )

        for sec_group in security_groups:
            vpc_id = sec_group["VpcId"]
            if not vpc_id:
                continue
            self._add_limit(
                "",
                AWSLimit(
                    "vpc_sec_group_rules",
                    "Rules of VPC security group %s" % sec_group["GroupName"],
                    120,
                    len(sec_group["IpPermissions"]),
                ),
            )

    def _add_interface_limits(
        self,
        interfaces: Sequence[Mapping],
        quotas_by_name: Mapping[str, float],
    ) -> None:
        # since there can also be interfaces which are not attached to an instance, we add these
        # limits to the host running the agent instead of to individual instances
        if_sec_group_limit = int(quotas_by_name.get("Security groups per network interface", 5))
        for iface in interfaces:
            self._add_limit(
                "",
                AWSLimit(
                    "if_vpc_sec_group",
                    "VPC security groups of elastic network interface %s"
                    % iface["NetworkInterfaceId"],
                    if_sec_group_limit,
                    len(iface["Groups"]),
                ),
            )

    def _add_spot_inst_limits(self, spot_inst_requests: Sequence[Mapping[str, object]]) -> None:
        count_spot_inst_reqs = 0
        for spot_inst_req in spot_inst_requests:
            if spot_inst_req["State"] in ["open", "active"]:
                count_spot_inst_reqs += 1
        self._add_limit(
            "",
            AWSLimit(
                "spot_inst_requests",
                "Spot Instance Requests",
                20,
                count_spot_inst_reqs,
            ),
        )

    def _add_spot_fleet_limits(self, spot_fleet_requests: Sequence[Mapping]) -> None:
        active_spot_fleet_requests = 0
        total_target_cap = 0
        for spot_fleet_req in spot_fleet_requests:
            if spot_fleet_req["SpotFleetRequestState"] != "active":
                continue

            active_spot_fleet_requests += 1
            total_target_cap += spot_fleet_req["SpotFleetRequestConfig"]["TargetCapacity"]

        self._add_limit(
            "",
            AWSLimit(
                "active_spot_fleet_requests",
                "Active Spot Fleet Requests",
                1000,
                active_spot_fleet_requests,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "spot_fleet_total_target_capacity",
                "Spot Fleet Requests Total Target Capacity",
                5000,
                total_target_cap,
            ),
        )


class EC2Summary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["ec2_names"]
        self._tags = self._config.service_config["ec2_tags"]

    @property
    @override
    def name(self) -> str:
        return "ec2_summary"

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
        colleague = self._received_results.get("ec2_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    @override
    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping[str, object]] | None:
        (colleague_contents,) = args
        if self._tags is None and self._names is not None:
            return self._fetch_instances_filtered_by_names(colleague_contents.content)
        if self._tags is not None:
            return self._fetch_instances_filtered_by_tags(colleague_contents.content)

        return self._fetch_instances_without_filter()

    def _fetch_instances_filtered_by_names(
        self, col_reservations: Sequence[dict]
    ) -> Sequence[Mapping[str, object]]:
        if col_reservations:
            instances = [
                inst
                for res in col_reservations
                for inst in res["Instances"]
                if inst["InstanceId"] in self._names
            ]
        else:
            response = self._client.describe_instances(InstanceIds=self._names)  # type: ignore[attr-defined]
            instances = [
                inst
                for res in self._get_response_content(response, "Reservations")
                for inst in res["Instances"]
            ]
        return instances

    def _fetch_instances_filtered_by_tags(
        self, col_reservations: list
    ) -> list[Mapping[str, object]] | None:
        if col_reservations:
            tags = self.prepare_tags_for_api_response(self._tags)
            return (
                [
                    inst
                    for res in col_reservations
                    for inst in res["Instances"]
                    for tag in inst.get("Tags", [])
                    if tag in tags
                ]
                if tags
                else None
            )

        instances = []
        for chunk in chunks(self._tags, length=200):
            # EC2 FilterLimitExceeded: The maximum number of filter values
            # specified on a single call is 200
            response = self._client.describe_instances(Filters=chunk)  # type: ignore[attr-defined]
            instances.extend(
                [
                    inst
                    for res in self._get_response_content(response, "Reservations")
                    for inst in res["Instances"]
                ]
            )
        return instances

    def _fetch_instances_without_filter(self) -> Sequence[Mapping[str, object]]:
        response = self._client.describe_instances()  # type: ignore[attr-defined]
        return [
            inst
            for res in self._get_response_content(response, "Reservations")
            for inst in res["Instances"]
        ]

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(
            self._format_instances(raw_content.content), raw_content.cache_timestamp
        )

    def _format_instances(self, instances):
        formatted_instances = {}
        for inst in instances:
            inst_id = _get_ec2_piggyback_hostname(
                self._config.piggyback_naming_convention, inst, self._region
            )
            if inst_id:
                inst["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(inst.get("Tags", []))
                formatted_instances[inst_id] = inst
        return formatted_instances

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", list(computed_content.content.values()))]


class EC2Labels(AWSSectionLabels):
    @property
    @override
    def name(self) -> str:
        return "ec2_labels"

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
        colleague = self._received_results.get("ec2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping[str, str]] | None:
        (colleague_contents,) = args
        return colleague_contents.content

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(
            {
                ec2_instance_id: inst.get("TagsForCmkLabels", [])
                for ec2_instance_id, inst in raw_content.content.items()
                if inst.get("TagsForCmkLabels")
            },
            raw_content.cache_timestamp,
        )


class EC2SecurityGroups(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["ec2_names"]
        self._tags = self._config.service_config["ec2_tags"]

    @property
    @override
    def name(self) -> str:
        return "ec2_security_groups"

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
        colleague = self._received_results.get("ec2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
    def get_live_data(self, *args):
        sec_groups = self._describe_security_groups()
        return {group["GroupId"]: group for group in sec_groups}

    def _describe_security_groups(self):
        if self._names is not None:
            response = self._client.describe_security_groups(InstanceIds=self._names)  # type: ignore[attr-defined]
            return self._get_response_content(response, "SecurityGroups")

        if self._tags is not None:
            sec_groups = []
            for chunk in chunks(self._tags, length=200):
                # EC2 FilterLimitExceeded: The maximum number of filter values
                # specified on a single call is 200
                response = self._client.describe_security_groups(Filters=chunk)  # type: ignore[attr-defined]
                sec_groups.extend(self._get_response_content(response, "SecurityGroups"))
            return sec_groups

        response = self._client.describe_security_groups()  # type: ignore[attr-defined]
        return self._get_response_content(response, "SecurityGroups")

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, list[str]] = {}
        for instance_name, instance in colleague_contents.content.items():
            for security_group_from_instance in instance.get("SecurityGroups", []):
                security_group = raw_content.content.get(security_group_from_instance["GroupId"])
                if security_group is None:
                    continue
                content_by_piggyback_hosts.setdefault(instance_name, []).append(security_group)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


class EC2(AWSSectionCloudwatch):
    @property
    @override
    def name(self) -> str:
        return "ec2"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @property
    def host_labels(self) -> Mapping[str, str]:
        return {"cmk/aws/ec2": "instance"}

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("ec2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        metrics: Metrics = []
        for idx, (instance_name, instance) in enumerate(colleague_contents.content.items()):
            instance_id = instance["InstanceId"]
            for metric_name, unit in [
                ("CPUCreditUsage", "Count"),
                ("CPUCreditBalance", "Count"),
                ("CPUUtilization", "Percent"),
                ("DiskReadOps", "Count"),
                ("DiskWriteOps", "Count"),
                ("DiskReadBytes", "Bytes"),
                ("DiskWriteBytes", "Bytes"),
                ("NetworkIn", "Bytes"),
                ("NetworkOut", "Bytes"),
                ("StatusCheckFailed_Instance", "Count"),
                ("StatusCheckFailed_System", "Count"),
            ]:
                metrics.append(
                    {
                        "Id": self._create_id_for_metric_data_query(idx, metric_name),
                        "Label": instance_name,
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/EC2",
                                "MetricName": metric_name,
                                "Dimensions": [
                                    {
                                        "Name": "InstanceId",
                                        "Value": instance_id,
                                    }
                                ],
                            },
                            "Period": self.period,
                            "Stat": "Average",
                            "Unit": unit,
                        },
                    }
                )
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
            AWSSectionResult(piggyback_hostname, rows, self.host_labels)
            for piggyback_hostname, rows in computed_content.content.items()
        ]
