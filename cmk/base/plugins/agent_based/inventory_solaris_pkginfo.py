#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output
#   PKGINST:  SUNWxvnc
#      NAME:  X11/VNC server
#  CATEGORY:  system
#      ARCH:  sparc
#   VERSION:  6.6.2.0500,REV=0.2008.02.15
#   BASEDIR:  /usr
#    VENDOR:  Sun Microsystems, Inc.
#      DESC:  X Window System server based on X.Org Foundation open source release and RealVNC open source release that displays over RFB protocol to a VNC client
#    PSTAMP:  x10s20100523131751
#  INSTDATE:  Jun 29 2011 12:59
#   HOTLINE:  Please contact your local service provider
#    STATUS:  completely installed
#     FILES:       22 installed pathnames
#                  10 shared pathnames
#                  11 directories
#                   4 executables
#                   1 setuid/setgid executables
#                8862 blocks used (approx)

import time
from typing import Dict, Mapping, Sequence

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Sequence[Mapping]


def parse_solaris_pkginfo(string_table: StringTable) -> Section:
    # TODO Clean up this awful parser:
    # - make package fields explicit - similar to lnx_packages.
    # - type hints will also be better

    entry: Dict = {}
    translation_dict = {
        "ARCH": "arch",
        "CATEGORY": "package_type",
        "DESC": "summary",
        "VERSION": "version",
        "VENDOR": "vendor",
    }

    parsed_packages = []
    for line in string_table:
        stripped_line = [w.strip() for w in line]
        key = stripped_line[0]
        value = " ".join(stripped_line[1:])

        if key == "PKGINST":
            # append the dict wich was build before to paclist
            if entry:  # when the loop is executed for the first time, entry is empty
                parsed_packages.append(entry)
            pkginst = value
        elif key == "NAME":
            # build a dict for each package initiator = PKGINST
            # concat solaris pkginst and name to mk inventory name and write to dict
            entry = {"name": "%s - %s" % (pkginst, value)}
        elif key == "INSTDATE":
            # 'try, except' blog is necessary because date conversion may fail because of non en_US
            # locale settings on the remote solaris server
            try:
                install_date_epoch = int(time.mktime(time.strptime(value, "%b %d %Y %H %M")))
                entry.update({"install_date": install_date_epoch})
            except Exception:
                pass
        else:
            # iterate over translation dict and update entries
            for tkey in translation_dict:
                if key == tkey:
                    entry.update({translation_dict[tkey]: value})
    if entry:
        parsed_packages.append(entry)
    return parsed_packages


register.agent_section(
    name="solaris_pkginfo",
    parse_function=parse_solaris_pkginfo,
)


def inventory_solaris_pkginfo(section: Section) -> InventoryResult:
    path = ["software", "packages"]
    for package in section:
        yield TableRow(
            path=path,
            key_columns={
                "name": package.get("name"),
            },
            inventory_columns={
                "install_date": package.get("install_date"),
                "arch": package.get("arch"),
                "package_type": package.get("package_type"),
                "summary": package.get("summary"),
                "version": package.get("version"),
                "vendor": package.get("vendor"),
            },
            status_columns={},
        )


register.inventory_plugin(
    name="solaris_pkginfo",
    inventory_function=inventory_solaris_pkginfo,
)
