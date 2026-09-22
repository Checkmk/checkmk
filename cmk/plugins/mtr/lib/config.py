#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Section names for the mtr agent plug-in configuration.

A section name doubles as the Checkmk service item, so two entries tracing the same
destination need something to tell them apart. Instead of making the user invent a
suffix, derive one from the settings that change what mtr actually does.

The agent plug-in hands mtr everything up to the first space, so the address has to
come first and must not contain one.
"""

# mypy: disable-error-code="explicit-any"

from collections.abc import Callable, Mapping, Sequence
from typing import Any

__all__ = ["section_names"]


def _ip_version(value: Any) -> str:
    return {"ipv4": "IPv4", "ipv6": "IPv6"}.get(str(value), str(value))


# Settings that change what gets traced, in the order their tokens appear. Everything
# else (count, time, interval, timeout, dns) only changes how often or how patiently
# the trace runs and therefore does not earn a service of its own.
_DISCRIMINATORS: Sequence[tuple[str, Callable[[Any], str]]] = (
    ("type", lambda value: str(value).upper()),
    ("enforce_what", _ip_version),
    ("port", lambda value: "port %s" % value),
    ("size", lambda value: "size %s" % value),
    ("address", lambda value: "from %s" % value),
    ("max_hops", lambda value: "max hops %s" % value),
)


def section_names(mtr_config: Sequence[Mapping[str, Any]]) -> Sequence[str]:
    """One section name per entry, in input order.

    A destination configured once keeps its bare address. Entries sharing an address
    get a suffix built from the settings that differ within that group, so two names
    are equal only if the two configurations are indistinguishable.
    """
    groups: dict[str, list[int]] = {}
    for nr, address_conf in enumerate(mtr_config):
        groups.setdefault(address_conf["hostname"], []).append(nr)

    names = [""] * len(mtr_config)
    for hostname, members in groups.items():
        distinguishing = [
            (key, render)
            for key, render in _DISCRIMINATORS
            if len({mtr_config[nr].get(key) for nr in members}) > 1
        ]
        for nr in members:
            tokens = [
                render(value)
                for key, render in distinguishing
                if (value := mtr_config[nr].get(key))
            ]
            names[nr] = "%s (%s)" % (hostname, " ".join(tokens)) if tokens else hostname

    return names
