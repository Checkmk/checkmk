#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""This module allows the creation of large numbers of random hosts
for test and development."""

import random

import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
from cmk.gui.i18n import _
from cmk.gui.globals import html

from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
)


@mode_registry.register
class ModeRandomHosts(WatoMode):
    @classmethod
    def name(cls):
        return "random_hosts"

    @classmethod
    def permissions(cls):
        return ["hosts", "random_hosts"]

    def title(self):
        return _("Random Hosts")

    def buttons(self):
        html.context_button(_("Folder"), watolib.Folder.current().url(), "back")

    def action(self):
        if not html.check_transaction():
            return "folder"

        count = int(html.request.var("count"))
        folders = int(html.request.var("folders"))
        levels = int(html.request.var("levels"))
        created = self._create_random_hosts(watolib.Folder.current(), count, folders, levels)
        return "folder", _("Created %d random hosts.") % created

    def page(self):
        html.begin_form("random")
        forms.header(_("Create Random Hosts"))
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
        html.button("start", _("Start!"), "submit")
        html.hidden_fields()
        html.end_form()

    def _create_random_hosts(self, folder, count, folders, levels):
        if levels == 0:
            hosts_to_create = []
            while len(hosts_to_create) < count:
                host_name = "random_%010d" % int(random.random() * 10000000000)
                hosts_to_create.append((host_name, {"ipaddress": "127.0.0.1"}, None))
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
