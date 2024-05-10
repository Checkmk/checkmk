#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal

from cmk.utils.tags import TagID

from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import Row
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.urls import makeuri, makeuri_contextless, urlencode
from cmk.gui.views.icon import Icon


class WatoIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "wato"

    @classmethod
    def title(cls) -> str:
        return _("Setup (formerly Wato)")

    def host_columns(self) -> list[str]:
        return ["filename"]

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> tuple[str, str, str] | None:
        def may_see_hosts() -> bool:
            return user.may("wato.use") and (user.may("wato.seeall") or user.may("wato.hosts"))

        if not may_see_hosts() or is_mobile(request, response):
            return None

        wato_folder = _wato_folder_from_filename(row["host_filename"])
        if wato_folder is None:
            return None

        if what == "host":
            return self._wato_link(wato_folder, row["host_name"], "edithost")

        if row["service_description"] in ["Check_MK inventory", "Check_MK Discovery"]:
            return self._wato_link(wato_folder, row["host_name"], "inventory")

        return None

    def _wato_link(
        self, folder: str, hostname: str, where: Literal["edithost", "inventory"]
    ) -> tuple[str, str, str] | None:
        if not active_config.wato_enabled:
            return None

        if display_options.enabled(display_options.X):
            url = f"wato.py?folder={urlencode(folder)}&host={urlencode(hostname)}"
            if where == "inventory":
                url += "&mode=inventory"
                help_txt = _("Run service discovery")
                icon = "services"
            else:
                url += "&mode=edit_host"
                help_txt = _("Edit this host")
                icon = "wato"
            return icon, help_txt, url

        return None


class DownloadAgentOutputIcon(Icon):
    """Action for downloading the current agent output."""

    @classmethod
    def ident(cls) -> str:
        return "download_agent_output"

    @classmethod
    def title(cls) -> str:
        return _("Download agent output")

    def default_sort_index(self) -> int:
        return 50

    def host_columns(self) -> list[str]:
        return ["filename", "check_type"]

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> tuple[str, str, str] | None:
        return _paint_download_host_info(what, row, tags, custom_vars, ty="agent")


class DownloadSnmpWalkIcon(Icon):
    """Action for downloading the current snmp output."""

    @classmethod
    def ident(cls) -> str:
        return "download_snmp_walk"

    @classmethod
    def title(cls) -> str:
        return _("Download snmp walk")

    def host_columns(self):
        return ["filename", "check_type"]

    def default_sort_index(self):
        return 50

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> tuple[str, str, str] | None:
        return _paint_download_host_info(what, row, tags, custom_vars, ty="walk")


def _paint_download_host_info(
    what: Literal["host", "service"],
    row: Row,
    tags: Sequence[TagID],
    custom_vars: Mapping[str, str],
    ty: Literal["agent", "walk"],
) -> tuple[str, str, str] | None:
    if (
        (what == "host" or (what == "service" and row["service_description"] == "Check_MK"))
        and user.may("wato.download_agent_output")
        and not row["host_check_type"] == 2
    ):  # Not for shadow hosts
        # Not 100% acurate to use the tags here, but this is the best we can do
        # with the available information.
        # Render "download agent output" for non agent hosts, because there might
        # be piggyback data available which should be downloadable.
        if ty == "walk" and "snmp" not in tags:
            return None

        if ty == "agent" and "snmp" in tags and "tcp" not in tags:
            return None

        params = [
            ("host", row["host_name"]),
            ("folder", _wato_folder_from_filename(row["host_filename"])),
            ("type", ty),
            ("_start", "1"),
        ]

        # When the download icon is part of the host/service action menu, then
        # the _back_url set in paint_action_menu() needs to be used. Otherwise
        # makeuri(request, []) (not request.requested_uri()) is the right choice.
        back_url = request.get_url_input("_back_url", makeuri(request, []))
        if back_url:
            params.append(("back_url", back_url))

        if ty == "agent":
            title = _("Download agent output")
        else:
            title = _("Download SNMP walk")

        url = makeuri_contextless(request, params, filename="fetch_agent_output.py")
        return "agents", title, url
    return None


def _wato_folder_from_filename(filename: str) -> str | None:
    if filename.startswith("/wato/") and filename.endswith("hosts.mk"):
        return filename[6:-8].rstrip("/")
    return None
