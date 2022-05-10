#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import Dict, Optional

from cmk.gui.http import Request
from cmk.gui.i18n import _

from .generator import HTMLWriter


def debug_vars(
    writer: HTMLWriter,
    request: Request,
    prefix: Optional[str] = None,
    hide_with_mouse: bool = True,
    vars_: Optional[Dict[str, str]] = None,
) -> None:
    it = request.itervars() if vars_ is None else vars_.items()
    hover = "this.style.display='none';"
    writer.open_table(class_=["debug_vars"], onmouseover=hover if hide_with_mouse else None)
    oddeven = "even"
    writer.tr(writer.render_th(_("POST / GET Variables"), colspan="2"), class_=oddeven)
    for name, value in sorted(it):
        oddeven = "even" if oddeven == "odd" else "odd"
        if name in ["_password", "password"]:
            value = "***"
        if not prefix or name.startswith(prefix):
            writer.tr(
                writer.render_td(name, class_="left") + writer.render_td(value, class_="right"),
                class_=oddeven,
            )
    writer.close_table()
