#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Container
from typing import override

from cmk.discover_plugins import discover_families, PluginGroup
from cmk.utils.man_pages import make_man_page_path_map
from cmk.web.exceptions import MKUserError
from cmk.web.page_container import PageContainer
from cmk.web.pages import Page, PageContext
from cmk.werks.site import find_werk, load_werk_entries
from cmk.werks.site.acknowledgement import is_acknowledged, load_acknowledgements

from .werk_detail import render_werk_detail

_ACKNOWLEDGE_PERMISSION = "general.acknowledge_werks"


def _get_known_checks() -> Container[str]:
    return make_man_page_path_map(discover_families(raise_errors=False), PluginGroup.CHECKMAN.value)


class WerkDetailPage(Page):
    """Renders the detail view of a single werk."""

    @override
    def page(self, ctx: PageContext) -> PageContainer:
        werk = find_werk(load_werk_entries(), ctx.request.get_integer_input_mandatory("werk"))
        if werk is None:
            raise MKUserError("werk", ctx.i18n("This Werk does not exist."))
        return render_werk_detail(
            werk,
            acknowledged=is_acknowledged(werk, load_acknowledgements()),
            acknowledge_url=(
                ctx.make_action_url([("_werk_ack", werk.id)], filename="change_log.py")
                if ctx.user.may(_ACKNOWLEDGE_PERMISSION)
                else None
            ),
            known_checks=_get_known_checks,
            i18n=ctx.i18n,
        )
