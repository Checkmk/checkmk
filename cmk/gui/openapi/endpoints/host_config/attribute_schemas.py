# !/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.fields.attributes import HostContactGroup
from cmk.gui.fields.utils import BaseSchema
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

from cmk import fields


class HostCreateAttribute(BaseSchema):
    alias = HostAttributeAlias().openapi_field()
    site = HostAttributeSite().openapi_field()
    parents = HostAttributeParents().openapi_field()

    # Definition should be removed
    contactgroups = fields.Nested(
        HostContactGroup,
        description=HostAttributeContactGroups().help(),
    )

    ipaddress = HostAttributeIPv4Address().openapi_field()
    ipv6address = HostAttributeIPv6Address().openapi_field()
    additional_ipv4addresses = HostAttributeAdditionalIPv4Addresses().openapi_field()
    additional_ipv6addresses = HostAttributeAdditionalIPv6Addresses().openapi_field()

    # TODO: CEE specific host attribute must be added without violating the import structure
    #  the registration should be edition specific instead (temporarily it would also be fine
    #  to do something like the customer attribute to keep simplicity
    # bake_agent_package = HostAttributeBakeAgentPackage().openapi_field()
    snmp_community = HostAttributeSNMPCommunity().openapi_field()

    labels = HostAttributeLabels().openapi_field()

    network_scan = HostAttributeNetworkScan().openapi_field()
    waiting_for_discovery = HostAttributeWaitingForDiscovery().openapi_field()

    management_protocol = HostAttributeManagementProtocol().openapi_field()
    management_address = HostAttributeManagementAddress().openapi_field()
    management_snmp_community = HostAttributeManagementSNMPCommunity().openapi_field()
    management_ipmi_credentials = HostAttributeManagementIPMICredentials().openapi_field()

    locked_by = HostAttributeLockedBy().openapi_field()
    locked_attributes = HostAttributeLockedAttributes().openapi_field()
    inventory_failed = HostAttributeDiscoveryFailed().openapi_field()


class HostViewAttribute(BaseSchema):
    alias = HostAttributeAlias().openapi_field()
    site = HostAttributeSite().openapi_field()

    contactgroups = fields.Nested(
        HostContactGroup,
        description=HostAttributeContactGroups().help(),
    )

    parents = HostAttributeParents().openapi_field()

    ipaddress = HostAttributeIPv4Address().openapi_field()
    ipv6address = HostAttributeIPv6Address().openapi_field()
    additional_ipv4addresses = HostAttributeAdditionalIPv4Addresses().openapi_field()
    additional_ipv6addresses = HostAttributeAdditionalIPv6Addresses().openapi_field()

    # TODO: CEE specific host attribute must be added without violating the import structure
    #  the registration should be edition specific instead (temporarily it would also be fine
    #  to do something like the customer attribute to keep simplicity
    # bake_agent_package = HostAttributeBakeAgentPackage().openapi_field()

    snmp_community = HostAttributeSNMPCommunity().openapi_field()

    labels = HostAttributeLabels().openapi_field()
    waiting_for_discovery = HostAttributeWaitingForDiscovery().openapi_field()

    network_scan = HostAttributeNetworkScan().openapi_field()
    network_scan_result = HostAttributeNetworkScanResult().openapi_field()

    management_protocol = HostAttributeManagementProtocol().openapi_field()
    management_address = HostAttributeManagementAddress().openapi_field()
    management_snmp_community = HostAttributeManagementSNMPCommunity().openapi_field()
    management_ipmi_credentials = HostAttributeManagementIPMICredentials().openapi_field()

    meta_data = HostAttributeMetaData().openapi_field()

    locked_by = HostAttributeLockedBy().openapi_field()
    locked_attributes = HostAttributeLockedAttributes().openapi_field()
    inventory_failed = HostAttributeDiscoveryFailed().openapi_field()
