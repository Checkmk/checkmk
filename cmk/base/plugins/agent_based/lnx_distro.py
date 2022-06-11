#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final, Iterable, Mapping

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

_KVPairs = Iterable[tuple[str, str | None]]
_Line = list[str]

Section = Mapping[str, _Line]


def parse_lnx_distro(string_table: StringTable) -> Section:
    parsed: dict[str, list[str]] = {}
    filename = None
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            filename = line[0][3:-3]
        elif filename is not None:
            parsed.setdefault(filename, line)
        elif filename is None:
            # stay compatible to older versions of output
            parsed.setdefault(line[0], line[1:])
    return parsed


register.agent_section(
    name="lnx_distro",
    parse_function=parse_lnx_distro,
)


def inv_lnx_parse_os(line: _Line) -> _KVPairs:
    for entry in line:
        if entry.count("=") == 0:
            continue
        k, v = [x.replace('"', "") for x in entry.split("=", 1)]
        if k == "VERSION_ID":
            yield "version", v
        elif k == "PRETTY_NAME":
            yield "name", v
        elif k == "VERSION_CODENAME":
            yield "code_name", v.title()
        elif k == "ID":
            yield "vendor", v.title()


_SUSE_CODE_NAMES: Final = {
    "11.2": "Emerald",
    "11.3": "Teal",
    "11.4": "Celadon",
    "12.1": "Asparagus",
    "12.2": "Mantis",
    "12.3": "Darthmouth",
    "13.1": "Bottle",
}


def inv_lnx_parse_suse(line: _Line) -> _KVPairs:
    major = line[1].split()[-1]
    if len(line) >= 3:
        patchlevel = line[2].split()[-1]
    else:
        patchlevel = "0"

    version = "%s.%s" % (major, patchlevel)

    yield "vendor", "SuSE"
    yield "version", version
    yield "name", "%s.%s" % (line[0].split("(")[0].strip(), patchlevel)

    if (code_name := _SUSE_CODE_NAMES.get(version)) is not None:
        yield "code_name", code_name


def inv_lnx_parse_redhat(line: _Line) -> _KVPairs:
    entry = line[0]
    if entry.startswith("Oracle"):
        yield from inv_lnx_parse_oracle_vm_server(line)
    else:
        parts = entry.split("(")
        left = parts[0].strip()
        # if codename "(CODENAME)" is present, list looks like
        # ['Red Hat Enterprise Linux Server release 6.7 ', 'Santiago)']
        if len(parts) == 2:
            yield "code_name", parts[1].rstrip(")")
        name, _release, version = left.rsplit(None, 2)
        if name.startswith("Red Hat"):
            yield "vendor", "Red Hat"
        yield "version", version
        yield "name", left


def inv_lnx_parse_oracle_vm_server(line: _Line) -> _KVPairs:
    parts = line[0].split(" ")
    yield "vendor", parts.pop(0)
    yield "version", parts.pop(-1)
    yield "name", " ".join(parts[:-1])


def inv_lnx_parse_lsb(line: _Line) -> _KVPairs:
    for entry in line:
        varname, value = entry.split("=", 1)
        value = value.strip("'").strip('"')
        if varname == "DISTRIB_ID":
            yield "vendor", value
        elif varname == "DISTRIB_RELEASE":
            yield "version", value
        elif varname == "DISTRIB_CODENAME":
            yield "code_name", value.title()
        elif varname == "DISTRIB_DESCRIPTION":
            yield "name", value


_DEBIAN_CODE_NAMES: Final = (
    ("2.0.", "Hamm"),
    ("2.1.", "Slink"),
    ("2.2.", "Potato"),
    ("3.0.", "Woody"),
    ("3.1.", "Sarge"),
    ("4.", "Etch"),
    ("5.", "Lenny"),
    ("6.", "Squeeze"),
    ("7.", "Wheezy"),
    ("8.", "Jessie"),
    ("9.", "Stretch"),
    ("10.", "Buster"),
    ("11.", "Bullseye"),
)


# Do not overwrite Ubuntu information
def inv_lnx_parse_debian(line: _Line) -> _KVPairs:
    entry = line[0]
    yield "name", "Debian " + entry
    yield "vendor", "Debian"
    yield "version", entry

    for prefix, code_name in _DEBIAN_CODE_NAMES:
        if entry.startswith(prefix):
            yield "code_name", code_name
            return


def inv_lnx_parse_cma(line: _Line) -> _KVPairs:
    yield "name", "Checkmk Appliance " + line[0]
    yield "vendor", "tribe29 GmbH"
    yield "version", line[0]
    yield "code_name", None


def inv_lnx_parse_gentoo(line: _Line) -> _KVPairs:
    entry = line[0]
    yield "name", entry
    yield "vendor", "Gentoo"
    parts = entry.split(" ")
    yield "version", parts.pop(-1)
    yield "code_name", None


_HANDLERS: Final = (
    ("/usr/share/cma/version", inv_lnx_parse_cma),
    ("/etc/os-release", inv_lnx_parse_os),
    ("/etc/gentoo-release", inv_lnx_parse_gentoo),
    ("/etc/SuSE-release", inv_lnx_parse_suse),
    ("/etc/oracle-release", inv_lnx_parse_oracle_vm_server),
    ("/etc/redhat-release", inv_lnx_parse_redhat),
    ("/etc/lsb-release", inv_lnx_parse_lsb),
    ("/etc/debian_version", inv_lnx_parse_debian),
)


def inventory_lnx_distro(section: Section) -> InventoryResult:

    for file_name, handler in _HANDLERS:
        if file_name in section:
            yield Attributes(
                path=["software", "os"],
                inventory_attributes={
                    "type": "Linux",
                    **dict(handler(section[file_name])),
                },
            )
            break


register.inventory_plugin(
    name="lnx_distro",
    inventory_function=inventory_lnx_distro,
)
