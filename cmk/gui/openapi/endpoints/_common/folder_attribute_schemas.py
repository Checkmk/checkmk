#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk import fields
from cmk.gui import fields as gui_fields
from cmk.gui.agent_registration import CONNECTION_MODE_FIELD
from cmk.gui.fields.attributes import HostContactGroup
from cmk.gui.fields.base import BaseSchema
from cmk.gui.fields.definitions import CustomHostAttributesAndTagGroups
from cmk.gui.watolib.builtin_attributes import (
    HostAttributeLabels,
    HostAttributeManagementIPMICredentials,
    HostAttributeManagementProtocol,
    HostAttributeManagementSNMPCommunity,
    HostAttributeMetaData,
    HostAttributeNetworkScan,
    HostAttributeNetworkScanResult,
    HostAttributeParents,
    HostAttributeSite,
    HostAttributeSNMPCommunity,
)
from cmk.gui.watolib.groups import HostAttributeContactGroups
from cmk.gui.watolib.host_attributes import ABCHostAttribute

from .host_attribute_schemas import BaseHostTagGroup


class BaseFolderTagGroup(BaseHostTagGroup):
    pass


class BaseFolderAttribute(BaseSchema):
    """Base class for all folder attribute schemas."""

    site = HostAttributeSite().openapi_field()
    parents = HostAttributeParents().openapi_field()

    contactgroups = fields.Nested(
        HostContactGroup,
        description=HostAttributeContactGroups().help(),
    )

    bake_agent_package = gui_fields.bake_agent_field()
    cmk_agent_connection = CONNECTION_MODE_FIELD
    snmp_community = HostAttributeSNMPCommunity().openapi_field()

    labels = HostAttributeLabels().openapi_field()

    network_scan = HostAttributeNetworkScan().openapi_field()

    management_protocol = HostAttributeManagementProtocol().openapi_field()
    management_snmp_community = HostAttributeManagementSNMPCommunity().openapi_field()
    management_ipmi_credentials = HostAttributeManagementIPMICredentials().openapi_field()


class FolderCustomHostAttributesAndTagGroups(CustomHostAttributesAndTagGroups):
    def _get_custom_host_attribute(
        self, attribute_name: str, attributes: dict[str, ABCHostAttribute]
    ) -> ABCHostAttribute | None:
        attribute = super()._get_custom_host_attribute(attribute_name, attributes)

        if attribute and not attribute.show_in_folder():
            attribute = None

        return attribute


class FolderCreateAttribute(
    BaseFolderAttribute, BaseFolderTagGroup, FolderCustomHostAttributesAndTagGroups
):
    _raise_error_if_attribute_is_readonly = True


class FolderUpdateAttribute(
    BaseFolderAttribute, BaseFolderTagGroup, FolderCustomHostAttributesAndTagGroups
):
    _raise_error_if_attribute_is_readonly = True


class FolderViewAttribute(
    BaseFolderAttribute, BaseFolderTagGroup, FolderCustomHostAttributesAndTagGroups
):
    network_scan_result = HostAttributeNetworkScanResult().openapi_field()
    meta_data = HostAttributeMetaData().openapi_field()
