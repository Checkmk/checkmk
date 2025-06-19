#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module allows the creation of large numbers of random hosts
for test and development."""

import random
from collections.abc import Collection

from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import make_simple_form_page_menu, PageMenu
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.wato.pages.folders import ModeFolder
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import Folder, folder_from_request
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeRandomHosts)


class ModeRandomHosts(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "random_hosts"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts", "random_hosts"]

    def title(self) -> str:
        return _("Add random hosts")

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeFolder

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Hosts"), breadcrumb, form_name="random", button_name="_save", save_title=_("Start!")
        )

    def action(self) -> ActionResult:
        folder = folder_from_request(request.var("folder"), request.get_ascii_input("host"))
        if not transactions.check_transaction():
            return redirect(mode_url("folder", folder=folder.path()))

        count = request.get_integer_input_mandatory("count")
        folders = request.get_integer_input_mandatory("folders")
        levels = request.get_integer_input_mandatory("levels")
        created = self._create_random_hosts(
            folder, count, folders, levels, pprint_value=active_config.wato_pprint_config
        )
        flash(_("Added %d random hosts.") % created)
        return redirect(mode_url("folder", folder=folder.path()))

    def page(self) -> None:
        with html.form_context("random"):
            forms.header(_("Add random hosts"))
            forms.section(_("Number to create"))
            html.write_text_permissive("%s: " % _("Hosts to create in each folder"))
            html.text_input("count", default_value="10", cssclass="number")
            html.set_focus("count")
            html.br()
            html.write_text_permissive("%s: " % _("Number of folders to create in each level"))
            html.text_input("folders", default_value="10", cssclass="number")
            html.br()
            html.write_text_permissive("%s: " % _("Levels of folders to create"))
            html.text_input("levels", default_value="1", cssclass="number")

            forms.end()
            html.hidden_fields()

    def _create_random_hosts(
        self, folder: Folder, count: int, folders: int, levels: int, *, pprint_value: bool
    ) -> int:
        if levels == 0:
            hosts_to_create: list[tuple[HostName, HostAttributes, None]] = []
            while len(hosts_to_create) < count:
                host_name = "random_%010d" % int(random.random() * 10000000000)
                hosts_to_create.append(
                    (HostName(host_name), {"ipaddress": HostAddress("127.0.0.1")}, None)
                )
            folder.create_hosts(hosts_to_create, pprint_value=pprint_value)
            return count

        total_created = 0
        created = 0
        while created < folders:
            created += 1
            i = 1
            while True:
                folder_name = "folder_%02d" % i
                if not folder.has_subfolder(folder_name):
                    break
                i += 1

            subfolder = folder.create_subfolder(
                folder_name, "Subfolder %02d" % i, {}, pprint_value=pprint_value
            )
            total_created += self._create_random_hosts(
                subfolder, count, folders, levels - 1, pprint_value=pprint_value
            )
        return total_created
