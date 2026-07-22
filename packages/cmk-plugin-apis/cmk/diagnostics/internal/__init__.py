#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

r"""
Scope
-----

This API provides functionality to create support diagnostics plug-ins that
can be discovered by Checkmk. Such plug-ins contribute files to the support
diagnostics dump created via the GUI (Setup > Maintenance > Support
diagnostics) or ``cmk --create-diagnostics-dump``.

To be discovered, a plug-in module must be placed in the
``diagnostics`` subdirectory of a plug-in family (e.g.
``cmk/plugins/<family>/diagnostics/<module>.py``) and the plug-in
instance name must start with the corresponding prefix.
"""

from collections.abc import Mapping

from ._context import CollectContext, CollectLogger
from ._exceptions import CollectError, CollectInfo, CollectWarning
from ._localize import Help, Title, Topic
from ._plugins import (
    DiagnosticsPlugin,
    DumpItem,
    GeneratedContent,
    Sensitivity,
    VerbatimCopy,
)
from ._redaction import (
    redact_passwords_in_content,
    redact_passwords_in_file,
    REDACT_STRING,
)


def entry_point_prefixes() -> Mapping[type[DiagnosticsPlugin], str]:
    """Return the types of plug-ins and their respective prefixes that can be discovered by Checkmk.

    These types can be used to create plug-ins that can be discovered by Checkmk.
    To be discovered, the plug-in must be of one of the types returned by this function and its name
    must start with the corresponding prefix.

    Example:
    ********

    >>> for plugin_type, prefix in entry_point_prefixes().items():
    ...     print(f'{prefix}... = {plugin_type.__name__}(...)')
    diagnostics_plugin_... = DiagnosticsPlugin(...)
    """
    return {
        DiagnosticsPlugin: "diagnostics_plugin_",
    }


__all__ = [
    "CollectContext",
    "CollectError",
    "CollectInfo",
    "CollectLogger",
    "CollectWarning",
    "DiagnosticsPlugin",
    "DumpItem",
    "entry_point_prefixes",
    "GeneratedContent",
    "Help",
    "redact_passwords_in_content",
    "redact_passwords_in_file",
    "REDACT_STRING",
    "Sensitivity",
    "Title",
    "Topic",
    "VerbatimCopy",
]
