#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from cmk.gui.i18n import _
from cmk.gui.valuespec import ValueSpec
from cmk.gui.visuals.info import VisualInfo


class VisualInfoInventoryHistory(VisualInfo):
    @property
    def ident(self) -> str:
        return "invhist"

    @property
    def title(self) -> str:
        return _("Inventory history")

    @property
    def title_plural(self) -> str:
        return _("Inventory histories")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return []
