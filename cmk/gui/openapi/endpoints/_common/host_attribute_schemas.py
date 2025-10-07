#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, override

from cmk import fields
from cmk.ccc import version
from cmk.gui import fields as gui_fields
from cmk.gui.agent_registration import CONNECTION_MODE_FIELD
from cmk.gui.fields.attributes import HostContactGroup
from cmk.gui.fields.base import BaseSchema
from cmk.gui.fields.definitions import CustomHostAttributesAndTagGroups
from cmk.gui.fields.utils import edition_field_description
from cmk.gui.watolib.builtin_attributes import (
    HostAttributeAdditionalIPv4Addresses,
    HostAttributeAdditionalIPv6Addresses,
    HostAttributeAlias,
    HostAttributeDiscoveryFailed,
    HostAttributeIPv4Address,
    HostAttributeIPv6Address,
    HostAttributeLabels,
    HostAttributeLockedAttributes,
    HostAttributeLockedBy,
    HostAttributeManagementAddress,
    HostAttributeManagementIPMICredentials,
    HostAttributeManagementProtocol,
    HostAttributeManagementSNMPCommunity,
    HostAttributeMetaData,
    HostAttributeNetworkScan,
    HostAttributeNetworkScanResult,
    HostAttributeParents,
    HostAttributeSite,
    HostAttributeSNMPCommunity,
    HostAttributeWaitingForDiscovery,
)
from cmk.gui.watolib.groups import HostAttributeContactGroups
from cmk.utils import paths
from cmk.utils.tags import BuiltinTagConfig, TagGroupID

built_in_tag_group_config = BuiltinTagConfig()


def _get_valid_tag_ids(built_in_tag_group_id: TagGroupID) -> list[str | None]:
    tag_group = built_in_tag_group_config.get_tag_group(built_in_tag_group_id)
    assert tag_group is not None

    return [None if tag_id is None else str(tag_id) for tag_id in tag_group.get_tag_ids()]


class RelayField(fields.String):
    """A field representing the relay address."""

    default_error_messages = {
        "edition_not_supported": "Relay field not supported in this edition.",
    }

    def __init__(self, **kwargs: Any):
        self._supported_editions = {version.Edition.CME, version.Edition.CCE, version.Edition.CSE}
        kwargs["description"] = edition_field_description(
            description=kwargs["description"],
            supported_editions=self._supported_editions,
        )
        super().__init__(**kwargs)

    @override
    def _validate(self, value: str) -> None:
        if version.edition(paths.omd_root) not in self._supported_editions:
            raise self.make_error("edition_not_supported")
        super()._validate(value)


class BaseHostTagGroup(BaseSchema):
    tag_address_family = fields.String(
        description="The IP address family of the host.",
        example="ip-v4-only",
        enum=_get_valid_tag_ids(TagGroupID("address_family")),
    )

    tag_agent = fields.String(
        description="Agent and API integrations",
        example="cmk-agent",
        enum=_get_valid_tag_ids(TagGroupID("agent")),
    )

    tag_snmp_ds = fields.String(
        description="The SNMP data source of the host.",
        example="snmp-v2",
        enum=_get_valid_tag_ids(TagGroupID("snmp_ds")),
    )

    tag_piggyback = fields.String(
        description="Use piggyback data for this host.",
        example="piggyback",
        enum=_get_valid_tag_ids(TagGroupID("piggyback")),
    )


class BaseHostAttribute(BaseSchema):
    """Base class for all host attribute schemas."""

    alias = HostAttributeAlias().openapi_field()
    site = HostAttributeSite().openapi_field()
    parents = HostAttributeParents().openapi_field()

    contactgroups = fields.Nested(
        HostContactGroup,
        description=HostAttributeContactGroups().help(),
    )

    ipaddress = HostAttributeIPv4Address().openapi_field()
    ipv6address = HostAttributeIPv6Address().openapi_field()
    additional_ipv4addresses = HostAttributeAdditionalIPv4Addresses().openapi_field()
    additional_ipv6addresses = HostAttributeAdditionalIPv6Addresses().openapi_field()

    bake_agent_package = gui_fields.bake_agent_field()
    cmk_agent_connection = CONNECTION_MODE_FIELD
    snmp_community = HostAttributeSNMPCommunity().openapi_field()
    # This field is only a placeholder to make the CI happy. It is implemented properly in the new
    # Rest API framework.
    # This only covers the case `("disabled", None)` (JSON-serialized as a list).
    metrics_association = fields.List(
        fields.String(allow_none=True),
    )

    labels = HostAttributeLabels().openapi_field()
    waiting_for_discovery = HostAttributeWaitingForDiscovery().openapi_field()

    network_scan = HostAttributeNetworkScan().openapi_field()

    management_protocol = HostAttributeManagementProtocol().openapi_field()
    management_address = HostAttributeManagementAddress().openapi_field()
    management_snmp_community = HostAttributeManagementSNMPCommunity().openapi_field()
    management_ipmi_credentials = HostAttributeManagementIPMICredentials().openapi_field()

    locked_by = HostAttributeLockedBy().openapi_field()
    locked_attributes = HostAttributeLockedAttributes().openapi_field()
    inventory_failed = HostAttributeDiscoveryFailed().openapi_field()
    relay = RelayField(
        description="The name/address of the relay through which this host is monitored, if not empty."
    )


class HostCreateAttribute(BaseHostAttribute, BaseHostTagGroup, CustomHostAttributesAndTagGroups):
    _raise_error_if_attribute_is_readonly = True


class HostViewAttribute(BaseHostAttribute, BaseHostTagGroup, CustomHostAttributesAndTagGroups):
    class Meta:
        dateformat = "iso8601"

    network_scan_result = HostAttributeNetworkScanResult().openapi_field()
    meta_data = HostAttributeMetaData().openapi_field()


class HostUpdateAttribute(BaseHostAttribute, BaseHostTagGroup, CustomHostAttributesAndTagGroups):
    _raise_error_if_attribute_is_readonly = True


class ClusterCreateAttribute(BaseHostAttribute, BaseHostTagGroup, CustomHostAttributesAndTagGroups):
    _raise_error_if_attribute_is_readonly = True
