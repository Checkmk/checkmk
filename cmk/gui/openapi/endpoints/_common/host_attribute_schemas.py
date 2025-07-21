# !/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk import fields
from cmk.gui.fields.base import BaseSchema
from cmk.gui.fields.definitions import CustomHostAttributesAndTagGroups
from cmk.gui.watolib.builtin_attributes import (
    HostAttributeMetaData,
    HostAttributeNetworkScanResult,
)
from cmk.utils.tags import BuiltinTagConfig, TagGroupID

from .base_host_attribute_schema import BaseHostAttribute

built_in_tag_group_config = BuiltinTagConfig()


def _get_valid_tag_ids(built_in_tag_group_id: TagGroupID) -> list[str | None]:
    tag_group = built_in_tag_group_config.get_tag_group(built_in_tag_group_id)
    assert tag_group is not None

    return [None if tag_id is None else str(tag_id) for tag_id in tag_group.get_tag_ids()]


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
