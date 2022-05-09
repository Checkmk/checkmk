#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example for Debian/Ubuntu
# <<<lnx_packages:sep(124)>>>
# zlib1g:amd64|1:1.2.7.dfsg-13|amd64|deb|compression library - runtime|install ok installed
# zlib1g:i386|1:1.2.7.dfsg-13|i386|deb|compression library - runtime|install ok installed
# zlib1g-dev:amd64|1:1.2.7.dfsg-13|amd64|deb|compression library - development|install ok installed

# Example for Gentoo
# sys-libs/ncurses|6.0-r1|amd64|ebuild|Repository gentoo|installed
# sys-libs/pam|1.2.1|amd64|ebuild|Repository gentoo|installed
# sys-libs/readline|6.3_p8-r3|amd64|ebuild|Repository gentoo|installed
# sys-libs/slang|2.3.0|amd64|ebuild|Repository gentoo|installed
# sys-libs/timezone-data|2016h|amd64|ebuild|Repository gentoo|installed
# sys-libs/zlib|1.2.11|amd64|ebuild|Repository gentoo|installed

# Example for RPM
# gpg-pubkey|307e3d54|(none)|rpm|gpg(SuSE Package Signing Key <build@suse.de>)|
# gpg-pubkey|1d061a62|(none)|rpm|gpg(build@novell.com (Novell Linux Products) <support@novell.com>)|
# licenses|20070810|noarch|rpm|License collection as found in the packages of SuSE Linux|
# branding-SLES|11|noarch|rpm|SUSE Linux Enterprise Server Brand File|
# terminfo|5.6|i586|rpm|A terminal descriptions database|
# yast2-schema|2.17.4|noarch|rpm|YaST2 - AutoYaST Schema|
# glibc-i18ndata|2.11.1|i586|rpm|Database Sources for 'locale'|
# cpio-lang|2.9|i586|rpm|Languages for package cpio|
# zlib|1.2.3|i586|rpm|Data Compression Library|

from typing import Iterable, NamedTuple, Optional

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable


class Package(NamedTuple):
    name: str
    version: str
    arch: str
    package_type: str
    summary: str
    package_version: Optional[str]


Section = Iterable[Package]


def parse_lnx_packages(string_table: StringTable) -> Section:
    parsed_packages = []
    for line in string_table:
        if len(line) == 6:
            pacname, version, arch, pactype, summary, inststate = line
            release = None
        elif len(line) == 7:
            pacname, version, arch, pactype, release, summary, inststate = line
        else:
            continue

        if pactype == "deb":
            if "installed" not in inststate:
                continue

        if arch == "amd64":
            arch = "x86_64"

        package_version = None

        # Split version into version of contained software and version of the
        # packages (RPM calls the later "release")
        parts = version.rsplit("-", 1)
        if len(parts) == 2:
            version, package_version = parts

        if release is not None:
            package_version = release

        parsed_packages.append(
            Package(
                name=pacname,
                version=version,
                arch=arch,
                package_type=pactype,
                summary=summary,
                package_version=package_version,
            )
        )
    return parsed_packages


register.agent_section(
    name="lnx_packages",
    parse_function=parse_lnx_packages,
)


def inventory_lnx_packages(section: Section) -> InventoryResult:
    path = ["software", "packages"]
    for package in section:
        inventory_columns = {
            "version": package.version,
            "arch": package.arch,
            "package_type": package.package_type,
            "summary": package.summary,
        }
        if package.package_version:
            inventory_columns["package_version"] = package.package_version
        yield TableRow(
            path=path,
            key_columns={
                "name": package.name,
            },
            inventory_columns=inventory_columns,
            status_columns={},
        )


register.inventory_plugin(
    name="lnx_packages",
    inventory_function=inventory_lnx_packages,
)
