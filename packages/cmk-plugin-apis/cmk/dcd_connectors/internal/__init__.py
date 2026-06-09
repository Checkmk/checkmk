#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

r"""
WARNING
-------

**This version of the API is work in progress and not yet stable.
It is not recommended to use this version in production systems.**


Scope
-----

This API provides functionality to create DCD (Dynamic Configuration Daemon) connectors
that can be discovered by Checkmk.

To be discovered, a plug-in module must be placed in the ``dcd_connectors`` subdirectory
of a plug-in family (e.g. ``cmk/plugins/<family>/dcd_connectors/<module>.py``) and the
plug-in instance name must start with the corresponding prefix.
"""

from collections.abc import Mapping

from ._connector_object import ConnectorObject, FailedToContactRemoteSite, NullObject
from ._connector_specs import ConnectorSpec as ConnectorSpec
from ._plugin import Connector, ConnectorContext, PhaseStep, SiteChanges
from ._types import ChangeDirective, find_order, GlobalIdent, HostOrder


def entry_point_prefixes() -> Mapping[type[ConnectorSpec[str]], str]:
    """Return the types of plug-ins and their respective prefixes that can be discovered by Checkmk.

    These types can be used to create plug-ins that can be discovered by Checkmk.
    To be discovered, the plug-in must be of one of the types returned by this function and its name
    must start with the corresponding prefix.

    Example:
    ********

    >>> for plugin_type, prefix in entry_point_prefixes().items():
    ...     print(f'{prefix}... = {plugin_type.__name__}(...)')
    connector_... = ConnectorSpec(...)
    """
    return {
        ConnectorSpec: "connector_",
    }


__all__ = [
    "ConnectorSpec",
    "ChangeDirective",
    "ConnectorContext",
    "ConnectorObject",
    "Connector",
    "entry_point_prefixes",
    "FailedToContactRemoteSite",
    "find_order",
    "GlobalIdent",
    "HostOrder",
    "NullObject",
    "PhaseStep",
    "SiteChanges",
]
