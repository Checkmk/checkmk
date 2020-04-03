#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (  # pylint: disable=unused-import
    Text,)

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (  # pylint: disable=unused-import
    ValueSpec, Dictionary,
)

from cmk.gui.plugins.wato.utils.context_buttons import home_button

from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
)


@mode_registry.register
class ModeDiagnostics(WatoMode):
    @classmethod
    def name(cls):
        # type: () -> str
        return "diagnostics"

    @classmethod
    def permissions(cls):
        # type : () -> List[str]
        return ["diagnostics"]

    def _from_vars(self):
        # type: () -> None
        self._start = bool(html.request.get_ascii_input("_start"))

    def title(self):
        # type: () -> Text
        return _("Diagnostics")

    def buttons(self):
        # type: () -> None
        home_button()

    def action(self):
        # type: () -> None
        pass

    def page(self):
        # type: () -> None
        html.begin_form("diagnostics", method="POST")

        vs_diagnostics = self._vs_diagnostics()
        vs_diagnostics.render_input("vs_diagnostics", {})

        html.button("_start", _("Start"))
        html.hidden_fields()
        html.end_form()

    def _vs_diagnostics(self):
        # type: () -> ValueSpec
        return Dictionary(
            title=_("Diagnostic analysis settings"),
            render="form",
            elements=[],
        )
