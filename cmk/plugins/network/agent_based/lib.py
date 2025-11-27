#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import startswith

DETECT_CISCO = startswith(".1.3.6.1.2.1.1.2.0", "1.3.6.1.4.1.9")
DETECT_FORTINET = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12356")
DETECT_MERAKI = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.29671")


_INTERFACE_DISPLAY_HINTS = {
    "ethernet": "eth",
    "fastethernet": "Fa",
    "gigabitethernet": "Gi",
    "tengigabitethernet": "Te",
    "fortygigabitethernet": "Fo",
    "hundredgigabitethernet": "Hu",
    "port-channel": "Po",
    "tunnel": "Tu",
    "loopback": "Lo",
    "cellular": "Cel",
    "vlan": "Vlan",
    "management": "Ma",
}


def get_short_if_name(if_name: str) -> str:
    """Return a shortened, display-friendly interface name derived from a long interface name.

    This function searches the module-level mapping `_INTERFACE_DISPLAY_HINTS`
    (which maps long interface-name prefixes to short display prefixes, e.g.
    {"GigabitEthernet": "Gi", "FastEthernet": "Fa"}) for a prefix that matches the
    start of `if_name`. Matching is performed case-insensitively. On a match the
    function returns a new string where the matched long prefix (in the lowered
    input) is replaced by the corresponding short prefix from the mapping; only
    the first matching prefix is replaced. If no prefix matches, the original
    `if_name` is returned unchanged.

    Parameters
    ----------
    if_name : str
        The long/interface name to shorten (e.g. "GigabitEthernet0/1", "Loopback0").

    Returns
    -------
    str
        The shortened interface name when a known prefix is found, otherwise the
        original `if_name`.

    Notes
    -----
    - Matching is case-insensitive.
    - The input is lowercased before performing the prefix replacement, and the
      short prefix from `_INTERFACE_DISPLAY_HINTS` is inserted as provided.
    - Only the first matching prefix from `_INTERFACE_DISPLAY_HINTS` is used.

    Examples
    --------
    >>> # Ensure the mapping contains a known prefix for the examples
    >>> _INTERFACE_DISPLAY_HINTS['GigabitEthernet'] = 'Gi'
    >>> get_short_if_name('GigabitEthernet0/1')
    'Gi0/1'
    >>> # Matching is case-insensitive
    >>> get_short_if_name('gigabitethernet0/2')
    'Gi0/2'
    >>> # If no known prefix matches, the original name is returned unchanged
    >>> get_short_if_name('UnknownPrefix0')
    'UnknownPrefix0'
    """

    for if_name_prefix, if_name_short in _INTERFACE_DISPLAY_HINTS.items():
        if if_name.lower().startswith(if_name_prefix.lower()):
            return if_name.lower().replace(if_name_prefix.lower(), if_name_short, 1)
    return if_name
