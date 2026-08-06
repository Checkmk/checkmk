#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from __future__ import annotations

from typing import override

from cmk.gui.i18n import _
from cmk.gui.valuespec import ValueSpec
from cmk.gui.visuals.filter.components import FilterComponent
from cmk.gui.visuals.info import VisualInfo


class VisualInfoInventoryHistory(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "invhist"

    @property
    @override
    def title(self) -> str:
        return _("Inventory history")

    @property
    @override
    def title_plural(self) -> str:
        return _("Inventory histories")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return []

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return []
