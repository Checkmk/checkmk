#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from ._active_checks import ActiveCheckCommand, ActiveCheckConfig
from ._special_agents import SpecialAgentCommand, SpecialAgentConfig
from ._utils import (
    EnvProxy,
    HostConfig,
    IPAddressFamily,
    IPv4Config,
    IPv6Config,
    noop_parser,
    NoProxy,
    replace_macros,
    Secret,
    URLProxy,
)


def entry_point_prefixes() -> Mapping[
    type[ActiveCheckConfig[Any]] | type[SpecialAgentConfig[Any]], str
]:
    """Return the types of plug-ins and their respective prefixes that can be discovered by Checkmk.

    These types can be used to create plug-ins that can be discovered by Checkmk.
    To be discovered, the plug-in must be of one of the types returned by this function and its name
    must start with the corresponding prefix.

    Example:
    ********

    >>> for plugin_type, prefix in entry_point_prefixes().items():
    ...     print(f'{prefix}... = {plugin_type.__name__}(...)')
    active_check_... = ActiveCheckConfig(...)
    special_agent_... = SpecialAgentConfig(...)
    """
    return {  # type: ignore[misc] # expression contains Any
        ActiveCheckConfig: "active_check_",
        SpecialAgentConfig: "special_agent_",
    }


__all__ = [
    "entry_point_prefixes",
    "ActiveCheckConfig",
    "ActiveCheckCommand",
    "EnvProxy",
    "HostConfig",
    "IPAddressFamily",
    "IPv4Config",
    "IPv6Config",
    "noop_parser",
    "NoProxy",
    "replace_macros",
    "Secret",
    "SpecialAgentCommand",
    "SpecialAgentConfig",
    "URLProxy",
]
