#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module allows the creation of large numbers of random hosts
for test and development."""

import random
from typing import Dict, List, Optional, Tuple, Type

from cmk.utils.type_defs import HostName

import cmk.gui.forms as forms
import cmk.gui.watolib as watolib
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.htmllib.context import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import make_simple_form_page_menu, PageMenu
from cmk.gui.plugins.wato.utils import flash, mode_registry, mode_url, redirect, WatoMode
from cmk.gui.type_defs import ActionResult
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.wato.pages.folders import ModeFolder


@mode_registry.register
class ModeRandomHosts(WatoMode):
    @classmethod
    def name(cls):
        return "random_hosts"

    @classmethod
    def permissions(cls):
        return ["hosts", "random_hosts"]

    def title(self):
        return _("Add random hosts")

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeFolder

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Hosts"), breadcrumb, form_name="random", button_name="_save", save_title=_("Start!")
        )

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(mode_url("folder", folder=watolib.Folder.current().path()))

        count = request.get_integer_input_mandatory("count")
        folders = request.get_integer_input_mandatory("folders")
        levels = request.get_integer_input_mandatory("levels")
        created = self._create_random_hosts(watolib.Folder.current(), count, folders, levels)
        flash(_("Added %d random hosts.") % created)
        return redirect(mode_url("folder", folder=watolib.Folder.current().path()))

    def page(self):
        html.begin_form("random")
        forms.header(_("Add random hosts"))
        forms.section(_("Number to create"))
        html.write_text("%s: " % _("Hosts to create in each folder"))
        html.text_input("count", default_value="10", cssclass="number")
        html.set_focus("count")
        html.br()
        html.write_text("%s: " % _("Number of folders to create in each level"))
        html.text_input("folders", default_value="10", cssclass="number")
        html.br()
        html.write_text("%s: " % _("Levels of folders to create"))
        html.text_input("levels", default_value="1", cssclass="number")

        forms.end()
        html.hidden_fields()
        html.end_form()

    def _create_random_hosts(self, folder, count, folders, levels):
        if levels == 0:
            hosts_to_create: List[Tuple[HostName, Dict, None]] = []
            while len(hosts_to_create) < count:
                host_name = "random_%010d" % int(random.random() * 10000000000)
                hosts_to_create.append((HostName(host_name), {"ipaddress": "127.0.0.1"}, None))
            folder.create_hosts(hosts_to_create)
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

            subfolder = folder.create_subfolder(folder_name, "Subfolder %02d" % i, {})
            total_created += self._create_random_hosts(subfolder, count, folders, levels - 1)
        return total_created
