#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from typing import Annotated, get_type_hints, Literal, Self

from pydantic import AfterValidator, model_validator, PlainSerializer

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition
from cmk.gui.openapi.api_endpoints.models.attributes import (
    FolderCustomHostAttributesAndTagGroupsModel,
    HostContactGroupRequestModel,
    HostContactGroupResponseModel,
    HostLabels,
    ipmi_credentials_or_none,
    IPMIParametersModel,
    MetaDataModel,
    metrics_association_from_internal,
    metrics_association_to_internal,
    MetricsAssociationModel,
    NetworkScanModel,
    NetworkScanResultModel,
    render_view_site,
    snmp_community_or_none,
    SNMPCredentialsConverter,
    SNMPCredentialsModel,
    validate_custom_attributes_and_tag_groups,
)
from cmk.gui.openapi.api_endpoints.models.host_attribute_models import BaseHostTagGroupModel
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.converter import (
    HostConverter,
    SiteIdConverter,
    TypedPlainValidator,
)
from cmk.gui.openapi.framework.model.restrict_editions import RestrictEditions
from cmk.gui.openapi.framework.model.restrict_features import RestrictFeatures
from cmk.gui.watolib.builtin_attributes import HostAttributeLabels
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.licensing.basics.options import OptionName
from cmk.utils.agent_registration import HostAgentConnectionMode


@api_model(slots=False)
class BaseFolderAttributeModel:
    """Base class for all folder attribute models."""

    site: str | ApiOmitted = api_field(
        description="The site that should monitor the hosts in this folder.",
        default_factory=ApiOmitted,
    )
    parents: list[Annotated[str, AfterValidator(HostConverter().host_name)]] | ApiOmitted = (
        api_field(
            description="A list of parents for the hosts in this folder.",
            default_factory=ApiOmitted,
        )
    )
    contactgroups: HostContactGroupRequestModel | ApiOmitted = api_field(
        description=(
            "Only members of the contact groups listed here have Setup permission for the "
            "host/folder. Optionally, you can make these contact groups automatically monitor "
            "contacts. The assignment of hosts to contact groups can also be defined by rules."
        ),
        default_factory=ApiOmitted,
    )
    bake_agent_package: Annotated[
        bool | ApiOmitted,
        RestrictFeatures(option_name=OptionName.BAKERY, which_field="bake_agent_package"),
    ] = api_field(
        description="Bake agent packages for this folder even if it is empty. Requires the agent bakery feature to be licensed.",
        default_factory=ApiOmitted,
    )
    cmk_agent_connection: Annotated[
        Literal["push-agent", "pull-agent"] | ApiOmitted,
        RestrictFeatures(
            option_name=OptionName.AGENT_REGISTRATION,
            which_field="cmk_agent_connection",
        ),
    ] = api_field(
        description=(
            "This configures the communication direction of this host.\n"
            f" * `{HostAgentConnectionMode.PULL.value}` (default) - The server will try to contact the monitored host and pull the data by initializing a TCP connection\n"
            f" * `{HostAgentConnectionMode.PUSH.value}` - the host is expected to send the data to the monitoring server without being triggered\n"
            "\n"
            "Requires the agent registration feature to be licensed."
        ),
        default_factory=ApiOmitted,
    )
    snmp_community: SNMPCredentialsModel | ApiOmitted = api_field(
        description=(
            "The SNMP access configuration. A configured SNMP v1/v2 community here "
            "will have precedence over any configured SNMP community rule. For this "
            "attribute to take effect, the attribute `tag_snmp_ds` needs to be set first."
        ),
        default_factory=ApiOmitted,
    )
    metrics_association: Annotated[
        MetricsAssociationModel | ApiOmitted,
        RestrictEditions(supported_editions={Edition.ULTIMATE, Edition.ULTIMATEMT, Edition.CLOUD}),
    ] = api_field(
        description="Configuration for associating OpenTelemetry metrics with the hosts in this folder.",
        default_factory=ApiOmitted,
    )
    labels: HostLabels | ApiOmitted = api_field(
        description=f"{HostAttributeLabels().help()} The key is the host label key.",
        default_factory=ApiOmitted,
    )
    network_scan: NetworkScanModel | ApiOmitted = api_field(
        description=(
            "Configuration for automatic network scan. Pings will be sent to each IP address in "
            "the configured ranges to check if a host is up or down. Each found host will be added "
            "to the folder by its host name (if possible) or IP address."
        ),
        default_factory=ApiOmitted,
    )
    management_protocol: Literal["none", "snmp", "ipmi"] | ApiOmitted = api_field(
        description=(
            "The protocol used to connect to the management board."
            "\n\nValid options are:\n\n * `none` - No management board"
            "\n * `snmp` - Connect using SNMP\n * `ipmi` - Connect using IPMI"
        ),
        default_factory=ApiOmitted,
    )
    management_snmp_community: SNMPCredentialsModel | None | ApiOmitted = api_field(
        description="SNMP credentials",
        default_factory=ApiOmitted,
    )
    management_ipmi_credentials: IPMIParametersModel | None | ApiOmitted = api_field(
        description="IPMI credentials",
        default_factory=ApiOmitted,
    )

    @staticmethod
    def snmp_community_from_internal(value: str | tuple) -> SNMPCredentialsModel:
        return SNMPCredentialsConverter.from_internal(value)

    @staticmethod
    def snmp_community_to_internal(value: SNMPCredentialsModel) -> str | tuple:
        return SNMPCredentialsConverter.to_internal(value)

    @staticmethod
    def management_protocol_to_internal(
        value: Literal["none", "snmp", "ipmi"],
    ) -> Literal["snmp", "ipmi"] | None:
        if value == "none":
            return None
        return value

    @staticmethod
    def management_protocol_from_internal(
        value: Literal["snmp", "ipmi"] | None,
    ) -> Literal["none", "snmp", "ipmi"]:
        if value is None:
            return "none"
        return value


_STATIC_ATTRIBUTE_NAMES = set(get_type_hints(HostAttributes))


@api_model
class FolderViewAttributeModel(
    BaseFolderAttributeModel,
    BaseHostTagGroupModel,
    FolderCustomHostAttributesAndTagGroupsModel,
):
    network_scan_result: NetworkScanResultModel | ApiOmitted = api_field(
        description="Read only access to the network scan result",
        default_factory=ApiOmitted,
    )
    meta_data: MetaDataModel | ApiOmitted = api_field(
        description="Read only access to configured metadata.",
        default_factory=ApiOmitted,
    )
    # read-only overrides
    contactgroups: HostContactGroupResponseModel | ApiOmitted = api_field(
        description=(
            "Only members of the contact groups listed here have Setup permission for the "
            "host/folder. Optionally, you can make these contact groups automatically monitor "
            "contacts. The assignment of hosts to contact groups can also be defined by rules."
        ),
        default_factory=ApiOmitted,
    )
    site: Annotated[SiteId, PlainSerializer(render_view_site, return_type=str)] | ApiOmitted = (
        api_field(
            description="The site that should monitor the hosts in this folder.",
            default_factory=ApiOmitted,
        )
    )
    snmp_community: SNMPCredentialsModel | None | ApiOmitted = api_field(  # type: ignore[assignment]
        description=(
            "The SNMP access configuration. A configured SNMP v1/v2 community here will have "
            "precedence over any configured SNMP community rule. For this attribute to take "
            "effect, the attribute `tag_snmp_ds` needs to be set first."
        ),
        default_factory=ApiOmitted,
    )

    @staticmethod
    def from_internal(value: HostAttributes) -> FolderViewAttributeModel:
        return FolderViewAttributeModel(
            site=value.get("site", ApiOmitted()),
            parents=[str(parent) for parent in value["parents"]]
            if "parents" in value
            else ApiOmitted(),
            contactgroups=(
                HostContactGroupResponseModel.from_internal(value["contactgroups"])
                if "contactgroups" in value
                else ApiOmitted()
            ),
            bake_agent_package=value.get("bake_agent_package", ApiOmitted()),
            cmk_agent_connection=value.get("cmk_agent_connection", ApiOmitted()),
            snmp_community=(
                snmp_community_or_none(value["snmp_community"])
                if "snmp_community" in value
                else ApiOmitted()
            ),
            metrics_association=(
                metrics_association_from_internal(value["metrics_association"])
                if "metrics_association" in value
                else ApiOmitted()
            ),
            labels=dict(value["labels"]) if "labels" in value else ApiOmitted(),
            network_scan=(
                NetworkScanModel.from_internal(value["network_scan"])
                if "network_scan" in value
                else ApiOmitted()
            ),
            management_protocol=(
                BaseFolderAttributeModel.management_protocol_from_internal(
                    value["management_protocol"]
                )
                if "management_protocol" in value
                else ApiOmitted()
            ),
            management_snmp_community=(
                snmp_community_or_none(value["management_snmp_community"])
                if "management_snmp_community" in value
                else ApiOmitted()
            ),
            management_ipmi_credentials=(
                ipmi_credentials_or_none(value["management_ipmi_credentials"])
                if "management_ipmi_credentials" in value
                else ApiOmitted()
            ),
            tag_agent=value.get("tag_agent", ApiOmitted()),
            tag_piggyback=value.get("tag_piggyback", ApiOmitted()),
            tag_snmp_ds=value.get("tag_snmp_ds", ApiOmitted()),
            tag_address_family=value.get("tag_address_family", ApiOmitted()),
            network_scan_result=(
                NetworkScanResultModel.from_internal(value["network_scan_result"])
                if "network_scan_result" in value
                else ApiOmitted()
            ),
            meta_data=(
                MetaDataModel.from_internal(value["meta_data"])
                if "meta_data" in value
                else ApiOmitted()
            ),
            dynamic_fields={
                k: v
                for k, v in value.items()
                if (k not in _STATIC_ATTRIBUTE_NAMES or k == "tag_criticality")
                and (isinstance(v, str) or v is None)
            },
        )


@api_model
class FolderAttributeRequestModel(
    BaseFolderAttributeModel,
    BaseHostTagGroupModel,
    FolderCustomHostAttributesAndTagGroupsModel,
):
    """Writable folder attributes (create/update).

    Read-only attributes (``network_scan_result``, ``meta_data``) are intentionally absent, so they
    cannot be set via the API.
    """

    # Override the read base's non-validating ``site`` with an existence-checking variant.
    site: Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_exist)] | ApiOmitted = (
        api_field(
            description="The site that should monitor the hosts in this folder.",
            default_factory=ApiOmitted,
        )
    )

    @model_validator(mode="after")
    def _validate_dynamic_fields(self) -> Self:
        validate_custom_attributes_and_tag_groups(self.dynamic_fields)
        return self

    def to_internal(self) -> HostAttributes:
        attributes = HostAttributes()
        if not isinstance(self.site, ApiOmitted):
            attributes["site"] = self.site
        if not isinstance(self.parents, ApiOmitted):
            attributes["parents"] = [HostName(parent) for parent in self.parents]
        if not isinstance(self.contactgroups, ApiOmitted):
            attributes["contactgroups"] = self.contactgroups.to_internal()
        if not isinstance(self.bake_agent_package, ApiOmitted):
            attributes["bake_agent_package"] = self.bake_agent_package
        if not isinstance(self.cmk_agent_connection, ApiOmitted):
            attributes["cmk_agent_connection"] = self.cmk_agent_connection
        if not isinstance(self.snmp_community, ApiOmitted):
            attributes["snmp_community"] = self.snmp_community_to_internal(self.snmp_community)
        if not isinstance(self.metrics_association, ApiOmitted):
            attributes["metrics_association"] = metrics_association_to_internal(
                self.metrics_association
            )
        if not isinstance(self.labels, ApiOmitted):
            attributes["labels"] = self.labels
        if not isinstance(self.network_scan, ApiOmitted):
            attributes["network_scan"] = self.network_scan.to_internal()
        if not isinstance(self.management_protocol, ApiOmitted):
            attributes["management_protocol"] = self.management_protocol_to_internal(
                self.management_protocol
            )
        if not isinstance(self.management_snmp_community, ApiOmitted):
            # ``None`` clears the credential; the HostAttributes TypedDict types the value as
            # non-optional, but storing ``None`` is valid at runtime.
            management_snmp = (
                None
                if self.management_snmp_community is None
                else self.snmp_community_to_internal(self.management_snmp_community)
            )
            attributes["management_snmp_community"] = management_snmp  # type: ignore[typeddict-item]
        if not isinstance(self.management_ipmi_credentials, ApiOmitted):
            management_ipmi = (
                None
                if self.management_ipmi_credentials is None
                else self.management_ipmi_credentials.to_internal()
            )
            attributes["management_ipmi_credentials"] = management_ipmi  # type: ignore[typeddict-item]
        if not isinstance(self.tag_address_family, ApiOmitted):
            attributes["tag_address_family"] = self.tag_address_family
        if not isinstance(self.tag_agent, ApiOmitted):
            attributes["tag_agent"] = self.tag_agent
        if not isinstance(self.tag_snmp_ds, ApiOmitted):
            attributes["tag_snmp_ds"] = self.tag_snmp_ds
        if not isinstance(self.tag_piggyback, ApiOmitted):
            attributes["tag_piggyback"] = self.tag_piggyback

        for key, value in self.dynamic_fields.items():
            attributes[key] = value  # type: ignore[literal-required]

        return attributes
