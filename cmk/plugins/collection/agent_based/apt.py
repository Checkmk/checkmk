#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<apt:sep(0)>>>
# Inst dpkg [1.17.5ubuntu5.3] (1.17.5ubuntu5.4 Ubuntu:14.04/trusty-updates [amd64])
# Inst libtasn1-6-dev [3.4-3ubuntu0.1] (3.4-3ubuntu0.2 Ubuntu:14.04/trusty-updates [amd64]) []
# Inst libtasn1-6 [3.4-3ubuntu0.1] (3.4-3ubuntu0.2 Ubuntu:14.04/trusty-updates [amd64])
# Inst ntpdate [1:4.2.6.p5+dfsg-3ubuntu2.14.04.2] (1:4.2.6.p5+dfsg-3ubuntu2.14.04.3 Ubuntu:14.04/trusty-security [amd64])
# Inst udev [204-5ubuntu20.10] (204-5ubuntu20.11 Ubuntu:14.04/trusty-updates [amd64]) []
# Inst libudev1 [204-5ubuntu20.10] (204-5ubuntu20.11 Ubuntu:14.04/trusty-updates [amd64])
# Inst libpam-systemd [204-5ubuntu20.10] (204-5ubuntu20.11 Ubuntu:14.04/trusty-updates [amd64]) []
# Inst systemd-services [204-5ubuntu20.10] (204-5ubuntu20.11 Ubuntu:14.04/trusty-updates [amd64]) []
# Inst libsystemd-daemon0 [204-5ubuntu20.10] (204-5ubuntu20.11 Ubuntu:14.04/trusty-updates [amd64])
# Inst libsystemd-login0 [204-5ubuntu20.10] (204-5ubuntu20.11 Ubuntu:14.04/trusty-updates [amd64])
# Inst libpolkit-gobject-1-0 [0.105-4ubuntu2] (0.105-4ubuntu2.14.04.1 Ubuntu:14.04/trusty-updates [amd64])
# Inst libxext-dev [2:1.3.2-1] (2:1.3.2-1ubuntu0.0.14.04.1 Ubuntu:14.04/trusty-security [amd64]) []

# or

# <<<apt:sep(0)>>>
# Remv default-java-plugin [2:1.8-58]
# Remv icedtea-8-plugin [1.6.2-3.1]
# Inst default-jre [2:1.8-58] (2:1.8-58+deb9u1 Debian:9.11/oldstable [amd64]) []
# Inst default-jre-headless [2:1.8-58] (2:1.8-58+deb9u1 Debian:9.11/oldstable [amd64])

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import islice
from typing import Any, ClassVar, NamedTuple

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.apt import (
    ESM_ENABLED,
    ESM_NOT_ENABLED,
    NOTHING_PENDING_FOR_INSTALLATION,
    UBUNTU_PRO,
)


class Section(NamedTuple):
    updates: Sequence[str]
    removals: Sequence[str]
    sec_updates: Sequence[str]
    esm_support: bool = True

    @property
    def n_updates(self) -> int:
        return sum(len(l) for l in [self.updates, self.removals, self.sec_updates])


@dataclass(frozen=True)
class ParsedLine:
    action_line_regex: ClassVar[re.Pattern] = re.compile(
        r"(Inst|Remv)"  # capture action
        r"\s"  # whitespace
        r"(\S+)"  # capture package
        r"(?:\s\[(\S+?)\])?"  # optional old version, capture text inside []
        r"(?:\s\((.*?)\))?"  # optional update/new package metadata, capture text inside ()
        r".*?"  # any other stuff
    )
    sec_regex: ClassVar[re.Pattern] = re.compile(r"Debian-Security:|Ubuntu[^/]*/[^/]*-\bsecurity\b")
    action: str
    package: str
    old_version: str | None
    update_metadata: str | None

    @classmethod
    def try_from_str(cls, line: str) -> "ParsedLine | None":
        """Parse a line of the agent output, returning the parts
        >>> assert ParsedLine.try_from_str(
        ...     "Remv default-java-plugin [2:1.8-58]"
        ... ) == ParsedLine("Remv", "default-java-plugin", "2:1.8-58", None)
        >>> assert ParsedLine.try_from_str(
        ...     "Inst default-jre [2:1.8-58] (2:1.8-58+deb9u1 Debian:9.11/oldstable [amd64]) []"
        ... ) == ParsedLine("Inst", "default-jre", "2:1.8-58", "2:1.8-58+deb9u1 Debian:9.11/oldstable [amd64]")
        >>> assert ParsedLine.try_from_str(
        ...     "Inst default-jre-headless [2:1.8-58] (2:1.8-58+deb9u1 Debian:9.11/oldstable [amd64])"
        ... ) == ParsedLine("Inst", "default-jre-headless", "2:1.8-58", "2:1.8-58+deb9u1 Debian:9.11/oldstable [amd64]")
        >>> assert ParsedLine.try_from_str(
        ...     "Inst linux-image-4.19.0-19-amd64 (4.19.232-1 Debian-Security:10/oldstable [amd64])"
        ... ) == ParsedLine("Inst", "linux-image-4.19.0-19-amd64", None, "4.19.232-1 Debian-Security:10/oldstable [amd64]")
        """
        match_result = ParsedLine.action_line_regex.match(line)
        return (
            None
            if match_result is None
            else ParsedLine(
                action=match_result.group(1),
                package=match_result.group(2),
                old_version=match_result.group(3),
                update_metadata=match_result.group(4),
            )
        )

    def is_security_update(self) -> bool:
        """Is the update a security update
        >>> assert ParsedLine.try_from_str(
        ...     "Inst tzdata (2021e-0ubuntu0.16.04+esm1 UbuntuESM:16.04/xenial-infra-security [all])"
        ... ).is_security_update()
        >>> assert ParsedLine.try_from_str(
        ...     "Inst linux-image-4.19.0-19-amd64 (4.19.232-1 Debian-Security:10/oldstable [amd64])"
        ... ).is_security_update()
        >>> assert not ParsedLine.try_from_str(
        ...     "Inst default-jre [2:1.8-58] (2:1.8-58+deb9u1 Debian:9.11/oldstable [amd64]) []"
        ... ).is_security_update()
        """
        return (
            False
            if self.update_metadata is None
            else bool(ParsedLine.sec_regex.search(self.update_metadata))
        )


def _sanitize_string_table(string_table: StringTable) -> StringTable:
    """Trims infra warning of the format:
    *The following packages could receive security updates with UA Infra: ESM service enabled:
    libglib2.0-data libglib2.0-0
    Learn more about UA Infra: ESM service for Ubuntu 16.04 at https://ubuntu.com/16-04

    Ubuntu comes with ABSOLUTELY NO WARRANTY, to the extent permitted by
    applicable law.

    Also trims the Ubuntu Pro advertisement:
    Receive additional future security updates with Ubuntu Pro.
    Learn more about Ubuntu Pro at https://ubuntu.com/pro
    """

    sanitized_string_table = []
    iter_table = iter(string_table)

    for line in iter_table:
        if UBUNTU_PRO in line[0]:
            next(iter_table)
        elif ESM_ENABLED in line[0]:
            next(islice(iter_table, 3, 4))
        else:
            sanitized_string_table.append(line)

    return sanitized_string_table


# Check that the apt section is in valid format of mk_apt plug-in and not
# from the apt agent plug-in which can be found on the Checkmk exchange.
def _data_is_valid(string_table: StringTable) -> bool:
    if not string_table:
        return False

    first_line = string_table[0]
    if len(first_line) != 1:
        return False

    if first_line[0] == NOTHING_PENDING_FOR_INSTALLATION:
        return True

    # Newer versions of apt display something like
    # 3 esm-infra security updates
    # 10 standard security updates
    # 1 standard security update
    if "security update" in first_line[0]:
        first_line = string_table[1]

    parts = ParsedLine.try_from_str(first_line[0])
    return parts is not None and (
        parts.old_version is not None or parts.update_metadata is not None
    )


def parse_apt(string_table: StringTable) -> Section | None:
    sanitized_string_table = _sanitize_string_table(string_table)
    if len(sanitized_string_table) == 0:
        return Section(updates=[], removals=[], sec_updates=[])

    if ESM_NOT_ENABLED in sanitized_string_table[0][0]:
        return Section(updates=[], removals=[], sec_updates=[], esm_support=False)

    if not _data_is_valid(sanitized_string_table):
        return None

    updates = []
    removals = []
    sec_updates = []

    for line in (ParsedLine.try_from_str(entry[0]) for entry in sanitized_string_table):
        if line is None:
            continue
        if line.action == "Remv":
            removals.append(line.package)
            continue
        if line.is_security_update():
            sec_updates.append(line.package)
            continue
        updates.append(line.package)

    return Section(
        updates,
        removals,
        sec_updates,
    )


agent_section_apt = AgentSection(
    name="apt",
    parse_function=parse_apt,
)


def discover_apt(section: Section) -> DiscoveryResult:
    yield Service()


def _format_summary(action: str, packages: Sequence[str], verbose: bool = False) -> str:
    summary = f"{len(packages)} {action}"
    if verbose and packages:
        summary += " (%s)" % (
            ", ".join(
                packages,
            )
        )

    return summary


def check_apt(params: Mapping[str, Any], section: Section) -> CheckResult:
    if not section.esm_support:
        yield Result(
            state=State.CRIT,
            summary="System could receive security updates, but needs extended support license",
        )
        return

    if section.n_updates == 0:
        yield Result(state=State.OK, summary=NOTHING_PENDING_FOR_INSTALLATION)
        yield Metric(name="normal_updates", value=0)
        yield Metric(name="security_updates", value=0)
        return

    yield Result(
        state=State(params["normal"]) if section.updates else State.OK,
        summary=_format_summary("normal updates", section.updates),
    )
    yield Metric(name="normal_updates", value=len(section.updates))

    # Only show removals when necessary as they are very rare.
    if section.removals:
        yield Result(
            state=State(params["removals"]) if section.removals else State.OK,
            summary=_format_summary("auto removals", section.removals, verbose=True),
        )
        yield Metric(name="removals", value=len(section.removals))

    yield Result(
        state=State(params["security"]) if section.sec_updates else State.OK,
        summary=_format_summary("security updates", section.sec_updates, verbose=True),
    )
    yield Metric(name="security_updates", value=len(section.sec_updates))


check_plugin_apt = CheckPlugin(
    name="apt",
    service_name="APT Updates",
    check_function=check_apt,
    discovery_function=discover_apt,
    check_default_parameters={
        "normal": 1,
        "removals": 1,
        "security": 2,
    },
    check_ruleset_name="apt",
)
