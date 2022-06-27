#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import make_simple_link, PageMenuEntry
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.watolib.hosts_and_folders import CREFolder, Folder


def make_host_status_link(host_name: str, view_name: str) -> PageMenuEntry:
    return PageMenuEntry(
        title=_("Monitoring status"),
        icon_name="status",
        item=make_simple_link(
            makeuri_contextless(
                request,
                [
                    ("view_name", view_name),
                    ("filename", Folder.current().path() + "/hosts.mk"),
                    ("host", host_name),
                    ("site", ""),
                ],
                filename="view.py",
            )
        ),
    )


def make_service_status_link(host_name: str, service_name: str) -> PageMenuEntry:
    return PageMenuEntry(
        title=_("Monitoring status"),
        icon_name="status",
        item=make_simple_link(
            makeuri_contextless(
                request,
                [
                    ("view_name", "service"),
                    ("host", host_name),
                    ("service", service_name),
                ],
                filename="view.py",
            )
        ),
    )


def make_folder_status_link(folder: CREFolder, view_name: str) -> PageMenuEntry:
    return PageMenuEntry(
        title=_("Status"),
        icon_name="status",
        item=make_simple_link(
            makeuri_contextless(
                request,
                [
                    ("view_name", view_name),
                    ("wato_folder", folder.path()),
                ],
                filename="view.py",
            )
        ),
    )
