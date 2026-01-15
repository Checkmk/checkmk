#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import AfterValidator, WithJsonSchema

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition
from cmk.gui.fields.utils import edition_field_description
from cmk.gui.openapi.api_endpoints.models.attributes import (
    FolderCustomHostAttributesAndTagGroupsModel,
    HostContactGroupModel,
    HostLabels,
    IPMIParametersModel,
    LockedByModel,
    MetaDataModel,
    MetricsAssociationAttributeFilterModel,
    MetricsAssociationAttributeFiltersModel,
    MetricsAssociationEnabledModel,
    MetricsAssociationModel,
    NetworkScanModel,
    NetworkScanResultModel,
    SNMPCredentialsConverter,
    SNMPCredentialsModel,
)
from cmk.gui.openapi.endpoints._common.host_attribute_schemas import built_in_tag_group_config
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.converter import (
    HostAddressConverter,
    HostConverter,
    TypedPlainValidator,
)
from cmk.gui.openapi.framework.model.restrict_editions import RestrictEditions
from cmk.gui.watolib.builtin_attributes import HostAttributeLabels, HostAttributeWaitingForDiscovery
from cmk.gui.watolib.host_attributes import (
    HostAttributes,
    MetricsAssociationAttributeFilter,
    MetricsAssociationAttributeFilters,
    MetricsAssociationEnabled,
)
from cmk.utils.agent_registration import HostAgentConnectionMode
from cmk.utils.tags import TagGroupID

HostNameOrIPv4 = Annotated[
    HostAddress,
    TypedPlainValidator(str, HostAddressConverter(allow_ipv6=False)),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]
HostNameOrIPv6 = Annotated[
    HostAddress,
    TypedPlainValidator(str, HostAddressConverter(allow_ipv4=False)),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]


def _validate_tag_id(tag_id: str, built_in_tag_group_id: TagGroupID) -> str:
    tag_group = built_in_tag_group_config.get_tag_group(built_in_tag_group_id)
    assert tag_group is not None

    if tag_id not in [
        None if _tag_id is None else str(_tag_id) for _tag_id in tag_group.get_tag_ids()
    ]:
        raise ValueError(f"Tag ID '{tag_id}' is not valid for tag group '{built_in_tag_group_id}'.")

    return tag_id


@api_model(slots=False)
class BaseHostTagGroupModel:
    tag_address_family: (
        Annotated[
            Literal["ip-v4-only", "ip-v6-only", "ip-v4v6", "no-ip"],
            AfterValidator(lambda v: _validate_tag_id(v, TagGroupID("address_family"))),
        ]
        | ApiOmitted
    ) = api_field(
        description="The IP address family of the host.",
        example="ip-v4-only",
        default_factory=ApiOmitted,
    )

    tag_agent: (
        Annotated[
            Literal["cmk-agent", "all-agents", "special-agents", "no-agent"],
            AfterValidator(lambda v: _validate_tag_id(v, TagGroupID("agent"))),
        ]
        | ApiOmitted
    ) = api_field(
        description="Agent and API integrations", example="cmk-agent", default_factory=ApiOmitted
    )

    tag_snmp_ds: (
        Annotated[
            Literal["no-snmp", "snmp-v2", "snmp-v1"],
            AfterValidator(lambda v: _validate_tag_id(v, TagGroupID("snmp_ds"))),
        ]
        | ApiOmitted
    ) = api_field(
        description="The SNMP data source of the host.",
        example="snmp-v2",
        default_factory=ApiOmitted,
    )

    tag_piggyback: (
        Annotated[
            Literal["auto-piggyback", "piggyback", "no-piggyback"],
            AfterValidator(lambda v: _validate_tag_id(v, TagGroupID("piggyback"))),
        ]
        | ApiOmitted
    ) = api_field(
        description="Use piggyback data for this host.",
        example="piggyback",
        default_factory=ApiOmitted,
    )


@api_model(slots=False)
class BaseHostAttributeModel:
    alias: str | ApiOmitted = api_field(
        description="Add a comment or describe this host", default_factory=ApiOmitted
    )

    site: SiteId | ApiOmitted = api_field(
        description="The site that should monitor this host.", default_factory=ApiOmitted
    )

    parents: (
        Sequence[
            Annotated[
                HostName,
                TypedPlainValidator(str, HostConverter.host_name),
                WithJsonSchema({"type": "string"}, mode="serialization"),
            ]
        ]
        | ApiOmitted
    ) = api_field(description="A list of parents of this host.", default_factory=ApiOmitted)

    contactgroups: HostContactGroupModel | ApiOmitted = api_field(
        description="Only members of the contact groups listed here have Setup permission for the host/folder. Optionally, you can make these contact groups automatically monitor contacts. The assignment of hosts to contact groups can also be defined by rules.",
        default_factory=ApiOmitted,
    )

    ipaddress: HostNameOrIPv4 | ApiOmitted = api_field(
        description="An IPv4 address.", default_factory=ApiOmitted
    )

    ipv6address: HostNameOrIPv6 | ApiOmitted = api_field(
        description="An IPv6 address.", default_factory=ApiOmitted
    )

    additional_ipv4addresses: Sequence[HostNameOrIPv4] | ApiOmitted = api_field(
        description="A list of IPv4 addresses.", default_factory=ApiOmitted
    )

    additional_ipv6addresses: Sequence[HostNameOrIPv6] | ApiOmitted = api_field(
        description="A list of IPv6 addresses.", default_factory=ApiOmitted
    )

    bake_agent_package: Annotated[
        bool | ApiOmitted, RestrictEditions(excluded_editions={Edition.COMMUNITY})
    ] = api_field(
        description=edition_field_description(
            "Bake agent packages for this folder even if it is empty.",
            excluded_editions={Edition.COMMUNITY},
        ),
        default_factory=ApiOmitted,
    )
    cmk_agent_connection: Annotated[
        Literal["push-agent", "pull-agent"] | ApiOmitted,
        RestrictEditions(
            supported_editions={
                Edition.ULTIMATEMT,
                Edition.ULTIMATE,
                Edition.CLOUD,
            }
        ),
    ] = api_field(
        description=edition_field_description(
            "This configures the communication direction of this host.\n"
            f" * `{HostAgentConnectionMode.PULL.value}` (default) - The server will try to contact the monitored host and pull the data by initializing a TCP connection\n"
            f" * `{HostAgentConnectionMode.PUSH.value}` - the host is expected to send the data to the monitoring server without being triggered\n",
            supported_editions={
                Edition.ULTIMATEMT,
                Edition.ULTIMATE,
                Edition.CLOUD,
            },
        ),
        default_factory=ApiOmitted,
    )

    snmp_community: SNMPCredentialsModel | ApiOmitted = api_field(
        description="The SNMP access configuration. A configured SNMP v1/v2 community here will have precedence over any configured SNMP community rule. For this attribute to take effect, the attribute `tag_snmp_ds` needs to be set first.",
        default_factory=ApiOmitted,
    )

    metrics_association: Annotated[
        MetricsAssociationModel | ApiOmitted,
        RestrictEditions(supported_editions={Edition.ULTIMATE, Edition.ULTIMATEMT, Edition.CLOUD}),
    ] = api_field(
        description="Configuration for associating OpenTelemetry metrics with this host.",
        default_factory=ApiOmitted,
    )

    labels: HostLabels | ApiOmitted = api_field(
        description=f"{HostAttributeLabels().help()} The key is the host label key.",
        default_factory=ApiOmitted,
    )

    waiting_for_discovery: bool | ApiOmitted = api_field(
        description=HostAttributeWaitingForDiscovery()._help_text(),
        default_factory=ApiOmitted,
    )

    network_scan: NetworkScanModel | ApiOmitted = api_field(
        description="Configuration for automatic network scan. Pings will be sent to each IP address in the configured ranges to check if a host is up or down. Each found host will be added to the folder by its host name (if possible) or IP address.",
        default_factory=ApiOmitted,
    )

    management_protocol: Literal["none", "snmp", "ipmi"] | ApiOmitted = api_field(
        description="The protocol used to connect to the management board. Valid options are: 'none' - No management board, 'snmp' - Connect using SNMP, 'ipmi' - Connect using IPMI",
        default_factory=ApiOmitted,
    )

    management_address: (
        Annotated[
            HostAddress,
            TypedPlainValidator(str, HostAddressConverter()),
            WithJsonSchema({"type": "string"}, mode="serialization"),
        ]
        | ApiOmitted
    ) = api_field(
        description="Address (IPv4, IPv6 or host name) under which the management board can be reached.",
        default_factory=ApiOmitted,
    )

    management_snmp_community: SNMPCredentialsModel | ApiOmitted = api_field(
        description="SNMP credentials", default_factory=ApiOmitted
    )

    management_ipmi_credentials: IPMIParametersModel | ApiOmitted = api_field(
        description="IPMI credentials", default_factory=ApiOmitted
    )

    locked_by: LockedByModel | ApiOmitted = api_field(
        description="Identity of the entity which locked the locked_attributes. The identity is built out of the Site ID, the program name and the connection ID.",
        default_factory=ApiOmitted,
    )

    locked_attributes: list[str] | ApiOmitted = api_field(
        description="Name of host attributes which are locked in the UI.",
        default_factory=ApiOmitted,
    )

    inventory_failed: bool | ApiOmitted = api_field(
        description="Whether or not the last bulk discovery failed. It is set to True once it fails and unset in case a later discovery succeeds.",
        default_factory=ApiOmitted,
    )

    @staticmethod
    def snmp_community_from_internal(value: str | tuple) -> SNMPCredentialsModel:
        return SNMPCredentialsConverter.from_internal(value)

    @staticmethod
    def snmp_community_to_internal(value: SNMPCredentialsModel) -> str | tuple:
        return SNMPCredentialsConverter.to_internal(value)

    @staticmethod
    def management_protocol_from_internal(
        value: Literal["none", "snmp", "ipmi"] | None,
    ) -> Literal["none", "snmp", "ipmi"]:
        if value is None:
            return "none"
        return value

    @staticmethod
    def management_protocol_to_internal(
        value: Literal["none", "snmp", "ipmi"],
    ) -> Literal["snmp", "ipmi"] | None:
        if value == "none":
            return None
        return value


@api_model
class HostViewAttributeModel(
    BaseHostAttributeModel, BaseHostTagGroupModel, FolderCustomHostAttributesAndTagGroupsModel
):
    network_scan_result: NetworkScanResultModel | ApiOmitted = api_field(
        description="Read only access to the network scan result", default_factory=ApiOmitted
    )
    meta_data: MetaDataModel | ApiOmitted = api_field(
        description="Read only access to configured metadata.", default_factory=ApiOmitted
    )

    @staticmethod
    def from_internal(
        value: HostAttributes, static_attributes: set[str]
    ) -> "HostViewAttributeModel":
        return HostViewAttributeModel(
            alias=value.get("alias", ApiOmitted()),
            site=value.get("site", ApiOmitted()),
            meta_data=MetaDataModel.from_internal(value["meta_data"])
            if "meta_data" in value
            else ApiOmitted(),
            network_scan_result=NetworkScanResultModel.from_internal(value["network_scan_result"])
            if "network_scan_result" in value
            else ApiOmitted(),
            parents=value["parents"] if "parents" in value else ApiOmitted(),
            contactgroups=HostContactGroupModel.from_internal(value["contactgroups"])
            if "contactgroups" in value
            else ApiOmitted(),
            ipaddress=value.get("ipaddress", ApiOmitted()),
            ipv6address=value.get("ipv6address", ApiOmitted()),
            additional_ipv4addresses=value.get("additional_ipv4addresses", ApiOmitted()),
            additional_ipv6addresses=value.get("additional_ipv6addresses", ApiOmitted()),
            bake_agent_package=value.get("bake_agent_package", ApiOmitted()),
            cmk_agent_connection=value.get("cmk_agent_connection", ApiOmitted()),
            snmp_community=BaseHostAttributeModel.snmp_community_from_internal(
                value["snmp_community"]
            )
            if "snmp_community" in value
            else ApiOmitted(),
            metrics_association=(
                "disabled"
                if metrics_assoc[0] == "disabled"
                else MetricsAssociationEnabledModel(
                    attribute_filters=MetricsAssociationAttributeFiltersModel(
                        resource_attributes=[
                            MetricsAssociationAttributeFilterModel(
                                key=attribute_filter["key"],
                                value=attribute_filter["value"],
                            )
                            for attribute_filter in metrics_assoc[1]["attribute_filters"][
                                "resource_attributes"
                            ]
                        ],
                        scope_attributes=[
                            MetricsAssociationAttributeFilterModel(
                                key=attribute_filter["key"],
                                value=attribute_filter["value"],
                            )
                            for attribute_filter in metrics_assoc[1]["attribute_filters"][
                                "scope_attributes"
                            ]
                        ],
                        data_point_attributes=[
                            MetricsAssociationAttributeFilterModel(
                                key=attribute_filter["key"],
                                value=attribute_filter["value"],
                            )
                            for attribute_filter in metrics_assoc[1]["attribute_filters"][
                                "data_point_attributes"
                            ]
                        ],
                    ),
                    host_name_resource_attribute_key=metrics_assoc[1][
                        "host_name_resource_attribute_key"
                    ],
                )
            )
            if (metrics_assoc := value.get("metrics_association"))
            else ApiOmitted(),
            labels=dict(value["labels"]) if "labels" in value else ApiOmitted(),
            waiting_for_discovery=value.get("waiting_for_discovery", ApiOmitted()),
            network_scan=NetworkScanModel.from_internal(value["network_scan"])
            if "network_scan" in value
            else ApiOmitted(),
            management_protocol=BaseHostAttributeModel.management_protocol_from_internal(
                value["management_protocol"]
            )
            if "management_protocol" in value
            else ApiOmitted(),
            management_address=value.get("management_address", ApiOmitted()),
            management_snmp_community=SNMPCredentialsConverter.from_internal(
                value["management_snmp_community"]
            )
            if "management_snmp_community" in value
            else ApiOmitted(),
            management_ipmi_credentials=IPMIParametersModel.from_internal(
                value["management_ipmi_credentials"]
            )
            if "management_ipmi_credentials" in value
            else ApiOmitted(),
            tag_agent=value.get("tag_agent", ApiOmitted()),
            tag_piggyback=value.get("tag_piggyback", ApiOmitted()),
            tag_snmp_ds=value.get("tag_snmp_ds", ApiOmitted()),
            tag_address_family=value.get("tag_address_family", ApiOmitted()),
            locked_attributes=(
                list(value["locked_attributes"]) if "locked_attributes" in value else ApiOmitted()
            ),
            locked_by=(
                LockedByModel.from_internal(value["locked_by"])
                if "locked_by" in value
                else ApiOmitted()
            ),
            dynamic_fields={
                k: v
                for k, v in value.items()
                if (k not in static_attributes or k == "tag_criticality") and isinstance(v, str)
            },
        )


@api_model
class HostUpdateAttributeModel(
    BaseHostAttributeModel, BaseHostTagGroupModel, FolderCustomHostAttributesAndTagGroupsModel
):
    def to_internal(self) -> HostAttributes:
        attributes = HostAttributes()
        if not isinstance(self.alias, ApiOmitted):
            attributes["alias"] = self.alias
        if not isinstance(self.site, ApiOmitted):
            attributes["site"] = self.site
        if not isinstance(self.parents, ApiOmitted):
            attributes["parents"] = self.parents
        if not isinstance(self.contactgroups, ApiOmitted):
            attributes["contactgroups"] = self.contactgroups.to_internal()
        if not isinstance(self.ipaddress, ApiOmitted):
            attributes["ipaddress"] = self.ipaddress
        if not isinstance(self.ipv6address, ApiOmitted):
            attributes["ipv6address"] = self.ipv6address
        if not isinstance(self.additional_ipv4addresses, ApiOmitted):
            attributes["additional_ipv4addresses"] = self.additional_ipv4addresses
        if not isinstance(self.additional_ipv6addresses, ApiOmitted):
            attributes["additional_ipv6addresses"] = self.additional_ipv6addresses
        if not isinstance(self.bake_agent_package, ApiOmitted):
            attributes["bake_agent_package"] = self.bake_agent_package
        if not isinstance(self.cmk_agent_connection, ApiOmitted):
            attributes["cmk_agent_connection"] = self.cmk_agent_connection
        if not isinstance(self.snmp_community, ApiOmitted):
            attributes["snmp_community"] = self.snmp_community_to_internal(self.snmp_community)
        if not isinstance(self.metrics_association, ApiOmitted):
            attributes["metrics_association"] = (
                ("disabled", None)
                if self.metrics_association == "disabled"
                else (
                    "enabled",
                    MetricsAssociationEnabled(
                        attribute_filters=MetricsAssociationAttributeFilters(
                            resource_attributes=[
                                MetricsAssociationAttributeFilter(
                                    key=attribute_filter.key,
                                    value=attribute_filter.value,
                                )
                                for attribute_filter in self.metrics_association.attribute_filters.resource_attributes
                            ],
                            scope_attributes=[
                                MetricsAssociationAttributeFilter(
                                    key=attribute_filter.key,
                                    value=attribute_filter.value,
                                )
                                for attribute_filter in self.metrics_association.attribute_filters.scope_attributes
                            ],
                            data_point_attributes=[
                                MetricsAssociationAttributeFilter(
                                    key=attribute_filter.key,
                                    value=attribute_filter.value,
                                )
                                for attribute_filter in self.metrics_association.attribute_filters.data_point_attributes
                            ],
                        ),
                        host_name_resource_attribute_key=self.metrics_association.host_name_resource_attribute_key,
                    ),
                )
            )
        if not isinstance(self.labels, ApiOmitted):
            attributes["labels"] = self.labels
        if not isinstance(self.waiting_for_discovery, ApiOmitted):
            attributes["waiting_for_discovery"] = self.waiting_for_discovery
        if not isinstance(self.network_scan, ApiOmitted):
            attributes["network_scan"] = self.network_scan.to_internal()
        if not isinstance(self.management_protocol, ApiOmitted):
            attributes["management_protocol"] = self.management_protocol_to_internal(
                self.management_protocol
            )
        if not isinstance(self.management_address, ApiOmitted):
            attributes["management_address"] = self.management_address
        if not isinstance(self.management_snmp_community, ApiOmitted):
            attributes["management_snmp_community"] = self.snmp_community_to_internal(
                self.management_snmp_community
            )
        if not isinstance(self.management_ipmi_credentials, ApiOmitted):
            attributes["management_ipmi_credentials"] = (
                self.management_ipmi_credentials.to_internal()
            )
        if not isinstance(self.tag_agent, ApiOmitted):
            attributes["tag_agent"] = self.tag_agent
        if not isinstance(self.tag_piggyback, ApiOmitted):
            attributes["tag_piggyback"] = self.tag_piggyback
        if not isinstance(self.tag_snmp_ds, ApiOmitted):
            attributes["tag_snmp_ds"] = self.tag_snmp_ds
        if not isinstance(self.tag_address_family, ApiOmitted):
            attributes["tag_address_family"] = self.tag_address_family
        if not isinstance(self.locked_attributes, ApiOmitted):
            attributes["locked_attributes"] = self.locked_attributes
        if not isinstance(self.locked_by, ApiOmitted):
            attributes["locked_by"] = self.locked_by.to_internal()

        if not isinstance(self.dynamic_fields, ApiOmitted):
            for k, v in self.dynamic_fields.items():
                attributes[k] = v  # type: ignore[literal-required]

        return attributes
