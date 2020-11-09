#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.config as config
from cmk.gui.globals import html, request
from cmk.gui.i18n import _
from cmk.gui.plugins.views import display_options
from cmk.gui.plugins.views.icons import Icon, icon_and_action_registry
from cmk.gui.utils.urls import makeuri, makeuri_contextless


@icon_and_action_registry.register
class WatoIcon(Icon):
    @classmethod
    def ident(cls):
        return "wato"

    def host_columns(self):
        return ['filename']

    def render(self, what, row, tags, custom_vars):
        def may_see_hosts():
            return config.user.may("wato.use") and \
              (config.user.may("wato.seeall") or config.user.may("wato.hosts"))

        if not may_see_hosts() or html.mobile:
            return None

        wato_folder = _wato_folder_from_filename(row["host_filename"])
        if wato_folder is None:
            return None

        if what == "host":
            return self._wato_link(wato_folder, row["site"], row["host_name"], "edithost")

        if row["service_description"] in ["Check_MK inventory", "Check_MK Discovery"]:
            return self._wato_link(wato_folder, row["site"], row["host_name"], "inventory")

    def _wato_link(self, folder, site, hostname, where):
        if not config.wato_enabled:
            return None

        if display_options.enabled(display_options.X):
            url = "wato.py?folder=%s&host=%s" % \
              (html.urlencode(folder), html.urlencode(hostname))
            if where == "inventory":
                url += "&mode=inventory"
                help_txt = _("Edit services")
                icon = "services"
            else:
                url += "&mode=edit_host"
                help_txt = _("Edit this host")
                icon = "wato"
            return icon, help_txt, url

        return None


@icon_and_action_registry.register
class DownloadAgentOutputIcon(Icon):
    """Action for downloading the current agent output."""
    @classmethod
    def ident(cls):
        return "download_agent_output"

    def default_sort_index(self):
        return 50

    def host_columns(self):
        return ["filename", "check_type"]

    def render(self, what, row, tags, custom_vars):
        return _paint_download_host_info(what, row, tags, custom_vars, ty="agent")  # pylint: disable=no-value-for-parameter


@icon_and_action_registry.register
class DownloadSnmpWalkIcon(Icon):
    """Action for downloading the current snmp output."""
    @classmethod
    def ident(cls):
        return "download_snmp_walk"

    def host_columns(self):
        return ["filename", "check_type"]

    def default_sort_index(self):
        return 50

    def render(self, what, row, tags, custom_vars):
        return _paint_download_host_info(what, row, tags, custom_vars, ty="walk")  # pylint: disable=no-value-for-parameter


def _paint_download_host_info(what, row, tags, host_custom_vars, ty):
    if (what == "host" or (what == "service" and row["service_description"] == "Check_MK")) \
       and config.user.may("wato.download_agent_output") \
       and not row["host_check_type"] == 2:  # Not for shadow hosts

        # Not 100% acurate to use the tags here, but this is the best we can do
        # with the available information.
        # Render "download agent output" for non agent hosts, because there might
        # be piggyback data available which should be downloadable.
        if ty == "walk" and "snmp" not in tags:
            return

        if ty == "agent" and "snmp" in tags and "tcp" not in tags:
            return

        params = [
            ("host", row["host_name"]),
            ("folder", _wato_folder_from_filename(row["host_filename"])),
            ("type", ty),
            ("_start", "1"),
        ]

        # When the download icon is part of the host/service action menu, then
        # the _back_url set in paint_action_menu() needs to be used. Otherwise
        # makeuri(request, []) (not html.requested_uri()) is the right choice.
        back_url = html.get_url_input("_back_url", makeuri(request, []))
        if back_url:
            params.append(("back_url", back_url))

        if ty == "agent":
            title = _("Download agent output")
        else:
            title = _("Download SNMP walk")

        url = makeuri_contextless(request, params, filename="fetch_agent_output.py")
        return "agent_output", title, url


def _wato_folder_from_filename(filename):
    if filename.startswith("/wato/") and filename.endswith("hosts.mk"):
        return filename[6:-8].rstrip("/")
