#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from dataclasses import asdict

from cmk.gui.config import active_config
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.monitor.legacy_context import build_link_url, ContextFilterTranslation
from cmk.gui.monitor.shared import FilterNode
from cmk.gui.type_defs import FilterName, VisualContext
from cmk.shared_typing.monitoring.page_link_button import MonitoringPageLinkButton

from .context_filters import translate_filters_for_link
from .page_url import all_hosts_url

_LEGACY_VIEW_NAME = "allhosts"


class AllHostsLinkButton:
    def __init__(self, teleport_target: str | None = None) -> None:
        self._teleport_target = teleport_target

    def __call__(self, view_name: str, context: VisualContext) -> None:
        """``context`` is the view's: its filters are taken over where the page can apply and show
        them."""
        if view_name != _LEGACY_VIEW_NAME:
            return
        html.vue_component(
            "cmk-monitoring-page-link-button",
            data=asdict(
                MonitoringPageLinkButton(
                    url=build_link_url(context, _translate_view_filters, _build_all_hosts_url),
                    title=_('Try the new "All hosts" view'),
                    teleport_target=self._teleport_target,
                )
            ),
        )


def _translate_view_filters(context: VisualContext) -> ContextFilterTranslation[FilterNode]:
    tag_groups = frozenset(group.id for group in active_config.tags.tag_groups)
    return translate_filters_for_link(context, tag_groups=tag_groups)


def _build_all_hosts_url(filter_node: FilterNode | None, unapplied: Sequence[FilterName]) -> str:
    return all_hosts_url(request, filter_node=filter_node, unapplied=unapplied)
