#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.dashboard.dashlet.base import IFrameDashlet
from cmk.gui.dashboard.type_defs import DashletConfig, DashletSize
from cmk.gui.i18n import _
from cmk.gui.valuespec import DictionaryEntry, TextInput


class URLDashletConfig(DashletConfig):
    url: str
    show_in_iframe: bool


class URLDashlet(IFrameDashlet[URLDashletConfig]):
    """Dashlet that displays a custom webpage"""

    @classmethod
    def type_name(cls) -> str:
        return "url"

    @classmethod
    def title(cls) -> str:
        return _("Custom URL")

    @classmethod
    def description(cls) -> str:
        return _("Displays the content of a custom website.")

    @classmethod
    def sort_index(cls) -> int:
        return 80

    @classmethod
    def initial_size(cls) -> DashletSize:
        return (30, 10)

    @classmethod
    def vs_parameters(cls) -> list[DictionaryEntry]:
        return [("url", TextInput(title=_("URL"), size=50, allow_empty=False))]

    def update(self) -> None:
        pass  # Not called at all. This dashlet always opens configured pages (see below)

    def _get_iframe_url(self) -> str:
        # override so we don't add context vars
        return self._dashlet_spec["url"]
