#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.watolib as watolib
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.page_menu import PageMenuEntry, make_simple_link


def global_buttons():
    changelog_button()


def changelog_button():
    pending_info = watolib.get_pending_changes_info()
    if pending_info:
        hot = True
        icon = "wato_changes"
        buttontext = pending_info
    else:
        hot = False
        icon = "wato_nochanges"
        buttontext = _("No changes")
    html.context_button(buttontext, watolib.folder_preserving_link([("mode", "changelog")]), icon,
                        hot)


def host_status_button(hostname, viewname):
    html.context_button(
        _("Status"), "view.py?" + html.urlencode_vars([
            ("view_name", viewname),
            ("filename", watolib.Folder.current().path() + "/hosts.mk"),
            ("host", hostname),
            ("site", ""),
        ]), "status")


def make_host_status_link(host_name: str, view_name: str) -> PageMenuEntry:
    return PageMenuEntry(
        title=_("Monitoring status"),
        icon_name="status",
        item=make_simple_link(
            html.makeuri_contextless([
                ("view_name", view_name),
                ("filename", watolib.Folder.current().path() + "/hosts.mk"),
                ("host", host_name),
                ("site", ""),
            ],
                                     filename="view.py")),
    )


def service_status_button(hostname, servicedesc):
    html.context_button(
        _("Status"), "view.py?" + html.urlencode_vars([
            ("view_name", "service"),
            ("host", hostname),
            ("service", servicedesc),
        ]), "status")


def folder_status_button(viewname="allhosts"):
    html.context_button(
        _("Status"), "view.py?" + html.urlencode_vars([
            ("view_name", viewname),
            ("wato_folder", watolib.Folder.current().path()),
        ]), "status")


def make_folder_status_link(folder: watolib.CREFolder, view_name: str) -> PageMenuEntry:
    return PageMenuEntry(
        title=_("Status"),
        icon_name="status",
        item=make_simple_link(
            html.makeuri_contextless(
                [
                    ("view_name", view_name),
                    ("wato_folder", folder.path()),
                ],
                filename="view.py",
            )),
    )
