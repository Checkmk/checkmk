#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from . import form_specs, rule_specs
from ._localize import Help, Label, Message, Title


def entry_point_prefixes() -> Mapping[
    type[
        rule_specs.ActiveCheck
        | rule_specs.AgentConfig
        | rule_specs.AgentAccess
        | rule_specs.EnforcedService
        | rule_specs.CheckParameters
        | rule_specs.Host
        | rule_specs.InventoryParameters
        | rule_specs.NotificationParameters
        | rule_specs.DiscoveryParameters
        | rule_specs.Service
        | rule_specs.SNMP
        | rule_specs.SpecialAgent
    ],
    str,
]:
    """Return the types of plug-ins and their respective prefixes that can be discovered by Checkmk.

    These types can be used to create plug-ins that can be discovered by Checkmk.
    To be discovered, the plug-in must be of one of the types returned by this function and its name
    must start with the corresponding prefix.

    Example:
    ********

    >>> for plugin_type, prefix in entry_point_prefixes().items():
    ...     print(f'{prefix}... = {plugin_type.__name__}(...)')
    rule_spec_... = ActiveCheck(...)
    rule_spec_... = AgentConfig(...)
    rule_spec_... = AgentAccess(...)
    rule_spec_... = EnforcedService(...)
    rule_spec_... = CheckParameters(...)
    rule_spec_... = Host(...)
    rule_spec_... = InventoryParameters(...)
    rule_spec_... = NotificationParameters(...)
    rule_spec_... = DiscoveryParameters(...)
    rule_spec_... = Service(...)
    rule_spec_... = SNMP(...)
    rule_spec_... = SpecialAgent(...)
    """
    return {
        rule_specs.ActiveCheck: "rule_spec_",
        rule_specs.AgentConfig: "rule_spec_",
        rule_specs.AgentAccess: "rule_spec_",
        rule_specs.EnforcedService: "rule_spec_",
        rule_specs.CheckParameters: "rule_spec_",
        rule_specs.Host: "rule_spec_",
        rule_specs.InventoryParameters: "rule_spec_",
        rule_specs.NotificationParameters: "rule_spec_",
        rule_specs.DiscoveryParameters: "rule_spec_",
        rule_specs.Service: "rule_spec_",
        rule_specs.SNMP: "rule_spec_",
        rule_specs.SpecialAgent: "rule_spec_",
    }


__all__ = [
    "form_specs",
    "Title",
    "Label",
    "Help",
    "Message",
    "entry_point_prefixes",
    "rule_specs",
]
