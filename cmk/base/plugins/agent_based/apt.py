#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import ClassVar, NamedTuple, Optional, Pattern, Sequence

from .agent_based_api.v1 import regex, register
from .agent_based_api.v1.type_defs import StringTable
from .utils.apt import ESM_ENABLED, ESM_NOT_ENABLED, NOTHING_PENDING_FOR_INSTALLATION


class Section(NamedTuple):
    updates: Sequence[str]
    removals: Sequence[str]
    sec_updates: Sequence[str]
    no_esm_support: bool = False


@dataclass(frozen=True)
class ParsedLine:
    action_line_regex: ClassVar[Pattern] = regex(
        r"(Inst|Remv)"  # capture action
        r"\s"  # whitespace
        r"(\S+)"  # capture package
        r"(?:\s\[(\S+?)\])?"  # optional old version, capture text inside []
        r"(?:\s\((.*?)\))?"  # optional update/new package metadata, capture text inside ()
        r".*?"  # any other stuff
    )
    sec_regex: ClassVar[Pattern] = regex(r"Debian-Security:|Ubuntu[^/]*/[^/]*-\bsecurity\b")
    action: str
    package: str
    old_version: Optional[str]
    update_metadata: Optional[str]

    @classmethod
    def try_from_str(cls, line: str) -> Optional["ParsedLine"]:
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


def _trim_esm_enabled_warning(string_table: StringTable) -> StringTable:
    """Trims infra warning of the format:
    *The following packages could receive security updates with UA Infra: ESM service enabled:
    libglib2.0-data libglib2.0-0
    Learn more about UA Infra: ESM service for Ubuntu 16.04 at https://ubuntu.com/16-04

    Ubuntu comes with ABSOLUTELY NO WARRANTY, to the extent permitted by
    applicable law.
    """
    if ESM_ENABLED in string_table[0][0]:
        return string_table[5:]
    return string_table


# Check that the apt section is in valid format of mk_apt plugin and not
# from the apt agent plugin which can be found on the Checkmk exchange.
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


def parse_apt(string_table: StringTable) -> Optional[Section]:
    if ESM_NOT_ENABLED in string_table[0][0]:
        return Section(updates=[], removals=[], sec_updates=[], no_esm_support=True)

    trimmed_string_table = _trim_esm_enabled_warning(string_table)

    if not _data_is_valid(trimmed_string_table):
        return None

    updates = []
    removals = []
    sec_updates = []

    for line in (ParsedLine.try_from_str(entry[0]) for entry in trimmed_string_table):
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


register.agent_section(
    name="apt",
    parse_function=parse_apt,
)
