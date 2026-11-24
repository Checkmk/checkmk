#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from dataclasses import asdict

from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.monitor.legacy_context import build_link_url
from cmk.gui.type_defs import FilterName, VisualContext
from cmk.shared_typing.monitoring.page_link_button import MonitoringPageLinkButton

from ._api._filters import ServiceFilterNode
from .context_filters import (
    remove_host_picking_filters,
    translate_filters_for_all_services_link,
    translate_filters_for_host_services_link,
)
from .page_url import all_services_url, host_services_url

_LEGACY_VIEW_NAME = "host"
_LEGACY_ALL_SERVICES_VIEW_NAME = "allservices"
ALL_SERVICES_SURVEY_URL = "https://survey.checkmk.com/index.php/527348?lang=en"


class HostServicesLinkButton:
    def __init__(self, teleport_target: str | None = None) -> None:
        self._teleport_target = teleport_target

    def __call__(self, view_name: str, context: VisualContext) -> None:
        """``context`` is the view's: its filters are taken over where the page can apply and show
        them."""
        if view_name != _LEGACY_VIEW_NAME:
            return
        if not (host_name := request.var("host")) or not (site_id := request.var("site")):
            return
        html.vue_component(
            "cmk-monitoring-page-link-button",
            data=asdict(
                MonitoringPageLinkButton(
                    url=build_link_url(
                        # Also keeps the host filters out of what a failed translation reports.
                        remove_host_picking_filters(context),
                        translate_filters_for_host_services_link,
                        lambda filter_node, unapplied: host_services_url(
                            request,
                            host_name=host_name,
                            site_id=site_id,
                            filter_node=filter_node,
                            unapplied=unapplied,
                        ),
                    ),
                    title=_('Try the new "Services of host" view'),
                    teleport_target=self._teleport_target,
                )
            ),
        )


class AllServicesLinkButton:
    def __init__(self, teleport_target: str | None = None) -> None:
        self._teleport_target = teleport_target

    def __call__(self, view_name: str, context: VisualContext) -> None:
        """``context`` is the view's: its filters are taken over where the page can apply and show
        them."""
        if view_name != _LEGACY_ALL_SERVICES_VIEW_NAME:
            return
        html.vue_component(
            "cmk-monitoring-page-link-button",
            data=asdict(
                MonitoringPageLinkButton(
                    url=build_link_url(
                        context, translate_filters_for_all_services_link, _build_all_services_url
                    ),
                    title=_('Try the new "All services" view'),
                    teleport_target=self._teleport_target,
                    survey_url=ALL_SERVICES_SURVEY_URL,
                )
            ),
        )


def _build_all_services_url(
    filter_node: ServiceFilterNode | None, unapplied: Sequence[FilterName]
) -> str:
    return all_services_url(request, filter_node=filter_node, unapplied=unapplied)
