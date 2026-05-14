#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import time

from cmk.inventory_ui.v1_unstable import (
    Label,
    Node,
    NumberField,
    SINotation,
    Table,
    TextField,
    Title,
    Unit,
    View,
)

UNIT_BYTES = Unit(SINotation("B"))


def _render_date(value: int | float) -> Label | str:
    return str(time.strftime("%Y-%m-%d", time.localtime(value)))


def _sort_key_version(value: str) -> tuple[int | str, ...]:
    parts: list[int | str] = []
    for value_part in value.split("."):
        for part in re.split(r"(\d+)", value_part):
            try:
                parts.append(int(part))
            except ValueError:
                parts.append(part)
    return tuple(parts)


node_software = Node(
    name="software",
    path=["software"],
    title=Title("Software"),
)

node_software_applications = Node(
    name="software_applications",
    path=["software", "applications"],
    title=Title("Applications"),
)

node_software_kernel_config = Node(
    name="software_kernel_config",
    path=["software", "kernel_config"],
    title=Title("Kernel configuration (sysctl)"),
    table=Table(
        view=View(name="invkernelconfig", title=Title("Kernel configuration (sysctl)")),
        columns={
            "name": TextField(Title("Parameter name")),
            "value": TextField(Title("Value")),
        },
    ),
)

node_software_os = Node(
    name="software_os",
    path=["software", "os"],
    title=Title("Operating system"),
    attributes={
        "name": TextField(Title("Operating system")),
        "version": TextField(Title("Version")),
        "vendor": TextField(Title("Vendor")),
        "type": TextField(Title("Type")),
        "install_date": NumberField(Title("Install date"), render=_render_date),
        "kernel_version": TextField(Title("Kernel version")),
        "arch": TextField(Title("Kernel Architecture")),
        "service_pack": TextField(Title("Latest service pack")),
        "build": TextField(Title("Build")),
    },
)

node_software_packages = Node(
    name="software_packages",
    path=["software", "packages"],
    title=Title("Software packages"),
    table=Table(
        view=View(name="invswpac", title=Title("Software packages")),
        columns={
            "name": TextField(Title("Name")),
            "arch": TextField(Title("Architecture")),
            "package_type": TextField(Title("Type")),
            "summary": TextField(Title("Description")),
            # sort_key enables from-to filtering
            "version": TextField(Title("Version"), sort_key=_sort_key_version),
            "vendor": TextField(Title("Publisher")),
            # sort_key enables from-to filtering
            "package_version": TextField(Title("Package version"), sort_key=_sort_key_version),
            "install_date": NumberField(Title("Install date"), render=_render_date),
            "size": NumberField(Title("Size"), render=UNIT_BYTES),
            "path": TextField(Title("Path")),
        },
    ),
)
