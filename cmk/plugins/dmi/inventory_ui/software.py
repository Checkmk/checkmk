#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from cmk.inventory_ui.v1_unstable import Label, Node, NumberField, TextField, Title


def _render_date(value: int | float) -> Label | str:
    return str(time.strftime("%Y-%m-%d", time.localtime(value)))


node_software_bios = Node(
    name="software_bios",
    path=["software", "bios"],
    title=Title("BIOS"),
    attributes={
        "vendor": TextField(Title("Vendor")),
        "version": TextField(Title("Version")),
        "date": NumberField(Title("Date"), render=_render_date),
    },
)
