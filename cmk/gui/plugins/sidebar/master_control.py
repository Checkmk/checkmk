#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from contextlib import nullcontext
from typing import ContextManager, Dict, List, Tuple

from livestatus import SiteId

import cmk.gui.site_config as site_config
import cmk.gui.sites as sites
import cmk.gui.user_sites as user_sites
from cmk.gui.globals import html, request, response
from cmk.gui.htmllib import foldable_container
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.plugins.sidebar.utils import (
    PageHandlers,
    SidebarSnapin,
    snapin_registry,
    write_snapin_exception,
)
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeactionuri_contextless


@snapin_registry.register
class MasterControlSnapin(SidebarSnapin):
    @staticmethod
    def type_name() -> str:
        return "master_control"

    @classmethod
    def title(cls) -> str:
        return _("Master control")

    @classmethod
    def description(cls) -> str:
        return _(
            "Buttons for switching globally states such as enabling " "checks and notifications"
        )

    def show(self) -> None:
        items = self._core_toggles()
        sites.update_site_states_from_dead_sites()

        site_status_info: Dict[sites.SiteId, List] = {}
        try:
            sites.live().set_prepend_site(True)
            for row in sites.live().query(
                "GET status\nColumns: %s" % " ".join([i[0] for i in items])
            ):
                site_id, values = row[0], row[1:]
                site_status_info[site_id] = values
        finally:
            sites.live().set_prepend_site(False)

        for site_id, site_alias in user_sites.sorted_sites():
            container: ContextManager[bool] = (
                foldable_container(
                    treename="master_control",
                    id_=site_id,
                    isopen=True,
                    title=site_alias,
                    icon="foldable_sidebar",
                )
                if not site_config.is_single_local_site()
                else nullcontext(False)
            )
            with container:
                try:
                    self._show_master_control_site(site_id, site_status_info, items)
                except Exception as e:
                    logger.exception("error rendering master control for site %s", site_id)
                    write_snapin_exception(e)

    def _core_toggles(self) -> List[Tuple[str, str]]:
        return [
            ("enable_notifications", _("Notifications")),
            ("execute_service_checks", _("Service checks")),
            ("execute_host_checks", _("Host checks")),
            ("enable_flap_detection", _("Flap Detection")),
            ("enable_event_handlers", _("Event handlers")),
            ("process_performance_data", _("Performance data")),
            ("enable_event_handlers", _("Alert handlers")),
        ]

    def _show_master_control_site(
        self,
        site_id: sites.SiteId,
        site_status_info: Dict[sites.SiteId, List],
        items: List[Tuple[str, str]],
    ) -> None:
        site_state = sites.states().get(site_id)

        if not site_state:
            html.show_error(_("Site state is unknown"))
            return

        if site_state["state"] == "dead":
            html.show_error(site_state["exception"])
            return

        if site_state["state"] == "disabled":
            html.show_message(_("Site is disabled"))
            return

        if site_state["state"] == "unknown":
            if site_state.get("exception"):
                html.show_error(site_state["exception"])
            else:
                html.show_error(_("Site state is unknown"))
            return

        is_cmc = site_state["program_version"].startswith("Check_MK ")

        try:
            site_info = site_status_info[site_id]
        except KeyError:
            html.show_error(_("Site state is unknown"))
            return

        html.open_table(class_="master_control")
        for i, (colname, title) in enumerate(items):
            # Do not show event handlers on Checkmk Micro Core
            if is_cmc and title == _("Event handlers"):
                continue

            if not is_cmc and title == _("Alert handlers"):
                continue

            colvalue = site_info[i]
            url = makeactionuri_contextless(
                request,
                transactions,
                [
                    ("site", site_id),
                    ("switch", colname),
                    ("state", "%d" % (1 - colvalue)),
                ],
                filename="switch_master_state.py",
            )
            onclick = (
                "cmk.ajax.get_url('%s', cmk.utils.update_contents, 'snapin_master_control')" % url
            )

            html.open_tr()
            html.td(title, class_="left")
            html.open_td()
            html.toggle_switch(
                enabled=colvalue,
                help_txt=_("Switch '%s' to '%s'") % (title, _("off") if colvalue else _("on")),
                onclick=onclick,
            )
            html.close_td()
            html.close_tr()

        html.close_table()

    @classmethod
    def allowed_roles(cls) -> List[str]:
        return ["admin"]

    def page_handlers(self) -> PageHandlers:
        return {
            "switch_master_state": self._ajax_switch_masterstate,
        }

    def _ajax_switch_masterstate(self) -> None:
        response.set_content_type("text/plain")

        if not user.may("sidesnap.master_control"):
            return

        if not transactions.check_transaction():
            return

        site = SiteId(request.get_ascii_input_mandatory("site"))
        column = request.get_ascii_input_mandatory("switch")
        state = request.get_integer_input_mandatory("state")
        commands = {
            ("enable_notifications", 1): "ENABLE_NOTIFICATIONS",
            ("enable_notifications", 0): "DISABLE_NOTIFICATIONS",
            ("execute_service_checks", 1): "START_EXECUTING_SVC_CHECKS",
            ("execute_service_checks", 0): "STOP_EXECUTING_SVC_CHECKS",
            ("execute_host_checks", 1): "START_EXECUTING_HOST_CHECKS",
            ("execute_host_checks", 0): "STOP_EXECUTING_HOST_CHECKS",
            ("enable_flap_detection", 1): "ENABLE_FLAP_DETECTION",
            ("enable_flap_detection", 0): "DISABLE_FLAP_DETECTION",
            ("process_performance_data", 1): "ENABLE_PERFORMANCE_DATA",
            ("process_performance_data", 0): "DISABLE_PERFORMANCE_DATA",
            ("enable_event_handlers", 1): "ENABLE_EVENT_HANDLERS",
            ("enable_event_handlers", 0): "DISABLE_EVENT_HANDLERS",
        }

        command = commands.get((column, state))
        if not command:
            html.write_text(_("Command %s/%d not found") % (column, state))
            return

        sites.live().command("[%d] %s" % (int(time.time()), command), site)
        sites.live().set_only_sites([site])
        sites.live().query(
            "GET status\nWaitTrigger: program\nWaitTimeout: 10000\nWaitCondition: %s = %d\nColumns: %s\n"
            % (column, state, column)
        )
        sites.live().set_only_sites()

        self.show()
