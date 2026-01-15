#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from typing import Annotated, Literal

from pydantic import AfterValidator

from cmk.ccc.version import Edition
from cmk.gui.fields.utils import edition_field_description
from cmk.gui.openapi.api_endpoints.models.attributes import (
    FolderCustomHostAttributesAndTagGroupsModel,
    HostContactGroupModel,
    HostLabels,
    IPMIParametersModel,
    MetaDataModel,
    NetworkScanModel,
    NetworkScanResultModel,
    SNMPCredentialsConverter,
    SNMPCredentialsModel,
)
from cmk.gui.openapi.api_endpoints.models.host_attribute_models import BaseHostTagGroupModel
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.converter import HostConverter
from cmk.gui.openapi.framework.model.restrict_editions import RestrictEditions
from cmk.gui.watolib.builtin_attributes import HostAttributeLabels
from cmk.utils.agent_registration import HostAgentConnectionMode


@api_model(slots=False)
class BaseFolderAttributeModel:
    """Base class for all folder attribute models."""

    site: str | ApiOmitted = api_field(
        description="The site that should monitor this host.", default_factory=ApiOmitted
    )
    parents: list[Annotated[str, AfterValidator(HostConverter.host_name)]] | ApiOmitted = api_field(
        description="A list of parents of this host.",
        default_factory=ApiOmitted,
    )
    contactgroups: HostContactGroupModel | ApiOmitted = api_field(
        description=(
            "Only members of the contact groups listed here have Setup permission for the "
            "host/folder. Optionally, you can make these contact groups automatically monitor "
            "contacts. The assignment of hosts to contact groups can also be defined by rules."
        ),
        default_factory=ApiOmitted,
    )
    # TODO: evaluate if edition handling should be included
    bake_agent_package: bool | ApiOmitted = api_field(
        description="Bake agent packages for this folder even if it is empty.",
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
        description=(
            "The SNMP access configuration. A configured SNMP v1/v2 community here "
            "will have precedence over any configured SNMP community rule. For this "
            "attribute to take effect, the attribute `tag_snmp_ds` needs to be set first."
        ),
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
    def management_protocol_to_internal(value: str) -> str | None:
        if value == "none":
            return None
        return value

    @staticmethod
    def management_protocol_from_internal(value: str | None) -> str:
        if value is None:
            return "none"
        return value


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
