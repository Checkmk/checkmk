#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re
from collections.abc import Mapping, Sequence
from typing import Literal

import cmk.utils
import cmk.utils.render
from cmk.utils.tags import TagID

from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.painter.v0.helpers import render_cache_info
from cmk.gui.painter.v1.helpers import is_stale
from cmk.gui.painter_options import paint_age, PainterOptions
from cmk.gui.type_defs import ColumnName, Row, VisualLinkSpec
from cmk.gui.type_defs import Icon as IconSpec
from cmk.gui.utils.html import HTML
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.popups import MethodAjax
from cmk.gui.utils.urls import makeuri, makeuri_contextless
from cmk.gui.visual_link import url_to_visual

from ..graph import cmk_graph_url
from .base import Icon

#   .--Action Menu---------------------------------------------------------.
#   |          _        _   _               __  __                         |
#   |         / \   ___| |_(_) ___  _ __   |  \/  | ___ _ __  _   _        |
#   |        / _ \ / __| __| |/ _ \| '_ \  | |\/| |/ _ \ '_ \| | | |       |
#   |       / ___ \ (__| |_| | (_) | | | | | |  | |  __/ | | | |_| |       |
#   |      /_/   \_\___|\__|_|\___/|_| |_| |_|  |_|\___|_| |_|\__,_|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class ActionMenuIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "action_menu"

    @classmethod
    def title(cls) -> str:
        return _("Action menu")

    def default_toplevel(self) -> bool:
        return True

    def default_sort_index(self) -> int:
        return 10

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
        url_vars = [
            ("host", row["host_name"]),
        ]

        if row.get("site"):
            url_vars.append(("site", row["site"]))

        if what == "service":
            url_vars.append(("service", row["service_description"]))

        if request.has_var("display_options"):
            url_vars.append(("display_options", request.var("display_options")))
        if request.has_var("_display_options"):
            url_vars.append(("_display_options", request.var("_display_options")))
        url_vars.append(("_back_url", makeuri(request, [])))

        return html.render_popup_trigger(
            html.render_icon("menu", _("Open the action menu"), cssclass="iconbutton"),
            "action_menu",
            MethodAjax(endpoint="action_menu", url_vars=url_vars),
        )


# .
#   .--Icon-Image----------------------------------------------------------.
#   |       ___                     ___                                    |
#   |      |_ _|___ ___  _ __      |_ _|_ __ ___   __ _  __ _  ___         |
#   |       | |/ __/ _ \| '_ \ _____| || '_ ` _ \ / _` |/ _` |/ _ \        |
#   |       | | (_| (_) | | | |_____| || | | | | | (_| | (_| |  __/        |
#   |      |___\___\___/|_| |_|    |___|_| |_| |_|\__,_|\__, |\___|        |
#   |                                                   |___/              |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class IconImageIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "icon_image"

    @classmethod
    def title(cls) -> str:
        return _("Icon image")

    def columns(self) -> Sequence[ColumnName]:
        return ["icon_image"]

    def default_toplevel(self) -> bool:
        return True

    def default_sort_index(self) -> int:
        return 25

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> HTML | None:
        img = row[what + "_icon_image"]
        if not img:
            return None

        if img.endswith(".png"):
            img = img[:-4]

        return html.render_icon(img)


# .
#   .--Reschedule----------------------------------------------------------.
#   |          ____                _              _       _                |
#   |         |  _ \ ___  ___  ___| |__   ___  __| |_   _| | ___           |
#   |         | |_) / _ \/ __|/ __| '_ \ / _ \/ _` | | | | |/ _ \          |
#   |         |  _ <  __/\__ \ (__| | | |  __/ (_| | |_| | |  __/          |
#   |         |_| \_\___||___/\___|_| |_|\___|\__,_|\__,_|_|\___|          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class RescheduleIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "reschedule"

    @classmethod
    def title(cls) -> str:
        return _("Reschedule")

    def columns(self) -> Sequence[ColumnName]:
        return ["check_type", "active_checks_enabled", "check_command"]

    def service_columns(self) -> list[str]:
        return ["cached_at", "cache_interval"]

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> tuple[str, str] | tuple[str, str, tuple[str, str]] | None:
        if what == "service" and row["service_cached_at"]:
            output = _("This service is based on cached agent data and cannot be rescheduled.")
            output += " %s" % render_cache_info(what, row)

            return "cannot_reschedule", output

        # Reschedule button
        if row[what + "_check_type"] == 2:
            return None  # shadow hosts/services cannot be rescheduled

        if (
            row[what + "_active_checks_enabled"] == 1
            or row[what + "_check_command"].startswith("check_mk-")
        ) and user.may("action.reschedule"):
            servicedesc = ""
            wait_svc = ""
            icon = "reload"
            txt = _("Reschedule check")

            if what == "service":
                servicedesc = row["service_description"].replace("\\", "\\\\")
                wait_svc = servicedesc

                # Use 'Check_MK' service for cmk based services
                if row[what + "_check_command"].startswith("check_mk-"):
                    servicedesc = "Check_MK"
                    icon = "reload_cmk"
                    txt = _("Reschedule 'Check_MK' service")

            url = "onclick:cmk.views.reschedule_check(this, {}, {}, {}, {});".format(
                json.dumps(row["site"]),
                json.dumps(row["host_name"]),
                json.dumps(servicedesc),
                json.dumps(wait_svc),
            )
            # _self is needed to prevent wrong linking when views are parts of dashlets
            return icon, txt, (url, "_self")
        return None


# .
#   .--Rule-Editor---------------------------------------------------------.
#   |         ____        _            _____    _ _ _                      |
#   |        |  _ \ _   _| | ___      | ____|__| (_) |_ ___  _ __          |
#   |        | |_) | | | | |/ _ \_____|  _| / _` | | __/ _ \| '__|         |
#   |        |  _ <| |_| | |  __/_____| |__| (_| | | || (_) | |            |
#   |        |_| \_\\__,_|_|\___|     |_____\__,_|_|\__\___/|_|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Icon to the parameters of a host or service                         |
#   '----------------------------------------------------------------------'


class RuleEditorIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "rule_editor"

    @classmethod
    def title(cls) -> str:
        return _("Rule editor")

    def columns(self) -> Sequence[ColumnName]:
        return ["check_type"]

    def host_columns(self) -> list[str]:
        return ["name"]

    def service_columns(self) -> list[str]:
        return ["description"]

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
        if row[what + "_check_type"] == 2:
            return None  # shadow services have no parameters

        if (
            active_config.wato_enabled
            and user.may("wato.rulesets")
            and active_config.multisite_draw_ruleicon
        ):
            urlvars = [
                ("mode", "object_parameters"),
                ("host", row["host_name"]),
            ]

            if what == "service":
                urlvars.append(("service", row["service_description"]))
                title = _("Parameters for this service")
            else:
                title = _("Parameters for this host")

            return "rulesets", title, makeuri_contextless(request, urlvars, "wato.py")
        return None


# .
#   .--Manpage-------------------------------------------------------------.
#   |              __  __                                                  |
#   |             |  \/  | __ _ _ __  _ __   __ _  __ _  ___               |
#   |             | |\/| |/ _` | '_ \| '_ \ / _` |/ _` |/ _ \              |
#   |             | |  | | (_| | | | | |_) | (_| | (_| |  __/              |
#   |             |_|  |_|\__,_|_| |_| .__/ \__,_|\__, |\___|              |
#   |                                |_|          |___/                    |
#   +----------------------------------------------------------------------+
#   |  Link to the check manpage                                           |
#   '----------------------------------------------------------------------'


class ManpageIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "check_manpage"

    @classmethod
    def title(cls) -> str:
        return _("Check manual page")

    def service_columns(self) -> list[str]:
        return ["check_command"]

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
        if what == "service" and active_config.wato_enabled and user.may("wato.use"):
            command = row["service_check_command"]
            if command.startswith("check_mk-mgmt_"):
                check_type = command[14:]
            elif command.startswith("check_mk-"):
                check_type = command[9:]
            elif command.startswith("check_mk_active-"):
                check_name = command[16:].split("!")[0]
                check_type = "check_" + check_name
            elif command in ["check-mk", "check-mk-inventory"]:
                if command == "check-mk":
                    check_type = "check-mk"
                elif command == "check-mk-inventory":
                    check_type = "check-mk-inventory"
                else:
                    return None
            else:
                return None
            urlvars = [("mode", "check_manpage"), ("check_type", check_type)]
            return (
                "check_plugins",
                _("Manual page for this check type"),
                makeuri_contextless(request, urlvars, "wato.py"),
            )
        return None


# .
#   .--Acknowledge---------------------------------------------------------.
#   |       _        _                        _          _                 |
#   |      / \   ___| | ___ __   _____      _| | ___  __| | __ _  ___      |
#   |     / _ \ / __| |/ / '_ \ / _ \ \ /\ / / |/ _ \/ _` |/ _` |/ _ \     |
#   |    / ___ \ (__|   <| | | | (_) \ V  V /| |  __/ (_| | (_| |  __/     |
#   |   /_/   \_\___|_|\_\_| |_|\___/ \_/\_/ |_|\___|\__,_|\__, |\___|     |
#   |                                                      |___/           |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class AcknowledgeIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "status_acknowledged"

    @classmethod
    def title(cls) -> str:
        return _("Status acknowledged")

    def columns(self) -> Sequence[ColumnName]:
        return ["acknowledged"]

    def default_toplevel(self) -> bool:
        return True

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
        if row[what + "_acknowledged"]:
            return "ack", _("This problem has been acknowledged")
        return None


# .
#   .--Perfgraph-----------------------------------------------------------.
#   |           ____            __                       _                 |
#   |          |  _ \ ___ _ __ / _| __ _ _ __ __ _ _ __ | |__              |
#   |          | |_) / _ \ '__| |_ / _` | '__/ _` | '_ \| '_ \             |
#   |          |  __/  __/ |  |  _| (_| | | | (_| | |_) | | | |            |
#   |          |_|   \___|_|  |_|  \__, |_|  \__,_| .__/|_| |_|            |
#   |                              |___/          |_|                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class PerfgraphIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "perfgraph"

    @classmethod
    def title(cls) -> str:
        return _("Performance graph")

    def columns(self) -> Sequence[ColumnName]:
        return ["pnpgraph_present"]

    def default_toplevel(self) -> bool:
        return True

    def default_sort_index(self) -> int:
        return 20

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
        if row[what + "_pnpgraph_present"] == 1:
            return self._pnp_icon(row, what)
        return None

    def _pnp_icon(self, row: Row, what: str) -> HTML | None:
        url = self._graph_icon_link(row, what)

        # Don't show the icon with Checkmk graphing. The hover makes no sense and there is no
        # mobile view for graphs, so the graphs on the bottom of the host/service view are enough
        # for the moment.
        if is_mobile(request, response):
            return None

        graph_icon_name = ("%s_graph" % what) if what in ["host", "service"] else "graph"

        return HTMLWriter.render_a(
            content=html.render_icon(graph_icon_name, ""),
            href=url,
            onmouseout="cmk.hover.hide()",
            onmouseover="cmk.graph_integration.show_hover_graphs(event, %s, %s, %s);"
            % (
                json.dumps(row["site"]),
                json.dumps(row["host_name"]),
                json.dumps(row["service_description"] if what == "service" else "_HOST_"),
            ),
        )

    def _graph_icon_link(self, row: Row, what: str) -> str:
        if display_options.disabled(display_options.X):
            return ""
        return cmk_graph_url(row, what, request=request)


# .
#   .--Prediction----------------------------------------------------------.
#   |            ____               _ _      _   _                         |
#   |           |  _ \ _ __ ___  __| (_) ___| |_(_) ___  _ __              |
#   |           | |_) | '__/ _ \/ _` | |/ __| __| |/ _ \| '_ \             |
#   |           |  __/| | |  __/ (_| | | (__| |_| | (_) | | | |            |
#   |           |_|   |_|  \___|\__,_|_|\___|\__|_|\___/|_| |_|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class PredictionIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "prediction"

    @classmethod
    def title(cls) -> str:
        return _("Prediction")

    def columns(self) -> Sequence[ColumnName]:
        return ["perf_data"]

    def default_toplevel(self) -> bool:
        return True

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
        # TODO: At least for interfaces we have 2 predictive values. But this icon
        # only creates a link to the first one. Add multiple icons or add a navigation
        # element to the prediction page.
        if what == "service":
            parts = row[what + "_perf_data"].split()
            for p in parts:
                if p.startswith("predict_"):
                    varname, _value = p.split("=")
                    dsname = varname[8:]
                    urlvars = [
                        ("site", row["site"]),
                        ("host", row["host_name"]),
                        ("service", row["service_description"]),
                        ("dsname", dsname),
                    ]
                    return (
                        "prediction",
                        _("Analyse predictive monitoring for this service"),
                        makeuri_contextless(request, urlvars, "prediction_graph.py"),
                    )
        return None


# .
#   .--Action-URL----------------------------------------------------------.
#   |           _        _   _                   _   _ ____  _             |
#   |          / \   ___| |_(_) ___  _ __       | | | |  _ \| |            |
#   |         / _ \ / __| __| |/ _ \| '_ \ _____| | | | |_) | |            |
#   |        / ___ \ (__| |_| | (_) | | | |_____| |_| |  _ <| |___         |
#   |       /_/   \_\___|\__|_|\___/|_| |_|      \___/|_| \_\_____|        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class CustomActionIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "custom_action"

    @classmethod
    def title(cls) -> str:
        return _("Custom action")

    def columns(self) -> Sequence[ColumnName]:
        return ["action_url_expanded", "pnpgraph_present"]

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
        if display_options.enabled(display_options.X):
            # action_url (only, if not a PNP-URL and pnp_graph is working!)
            action_url = row[what + "_action_url_expanded"]
            pnpgraph_present = row[what + "_pnpgraph_present"]
            if action_url and not ("/pnp4nagios/" in action_url and pnpgraph_present >= 0):
                return "action", _("Custom Action"), action_url
        return None


# .
#   .--Logwatch------------------------------------------------------------.
#   |            _                              _       _                  |
#   |           | |    ___   __ ___      ____ _| |_ ___| |__               |
#   |           | |   / _ \ / _` \ \ /\ / / _` | __/ __| '_ \              |
#   |           | |__| (_) | (_| |\ V  V / (_| | || (__| | | |             |
#   |           |_____\___/ \__, | \_/\_/ \__,_|\__\___|_| |_|             |
#   |                       |___/                                          |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class LogwatchIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "logwatch"

    @classmethod
    def title(cls) -> str:
        return _("Logwatch")

    def service_columns(self) -> list[str]:
        return ["host_name", "service_description", "check_command"]

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
        if what != "service" or row[what + "_check_command"] not in [
            "check_mk-logwatch",
            "check_mk-logwatch_groups",
        ]:
            return None

        sitename, hostname, item = row["site"], row["host_name"], row["service_description"][4:]
        url = makeuri_contextless(
            request,
            [("site", sitename), ("host", hostname), ("file", item)],
            filename="logwatch.py",
        )
        return "logwatch", _("Open Log"), url


# .
#   .--Notes-URL-----------------------------------------------------------.
#   |          _   _       _                  _   _ ____  _                |
#   |         | \ | | ___ | |_ ___  ___      | | | |  _ \| |               |
#   |         |  \| |/ _ \| __/ _ \/ __|_____| | | | |_) | |               |
#   |         | |\  | (_) | ||  __/\__ \_____| |_| |  _ <| |___            |
#   |         |_| \_|\___/ \__\___||___/      \___/|_| \_\_____|           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class NotesIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "notes"

    @classmethod
    def title(cls) -> str:
        return _("Notes")

    def columns(self) -> Sequence[ColumnName]:
        return ["notes_url_expanded", "check_command"]

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> tuple[str, str, tuple[str, str]] | None:
        # Adds the url_prefix of the services site to the notes url configured in this site.
        # It also adds the master_url which will be used to link back to the source site
        # in multi site environments.
        if display_options.enabled(display_options.X):
            notes_url = row[what + "_notes_url_expanded"]
            if notes_url:
                return "notes", _("Notes (URL)"), (notes_url, "_blank")
        return None


# .
#   .--Downtimes-----------------------------------------------------------.
#   |         ____                      _   _                              |
#   |        |  _ \  _____      ___ __ | |_(_)_ __ ___   ___  ___          |
#   |        | | | |/ _ \ \ /\ / / '_ \| __| | '_ ` _ \ / _ \/ __|         |
#   |        | |_| | (_) \ V  V /| | | | |_| | | | | | |  __/\__ \         |
#   |        |____/ \___/ \_/\_/ |_| |_|\__|_|_| |_| |_|\___||___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class DowntimesIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "status_downtimes"

    @classmethod
    def title(cls) -> str:
        return _("Status downtimes")

    def default_toplevel(self) -> bool:
        return True

    def columns(self) -> Sequence[ColumnName]:
        return ["scheduled_downtime_depth", "downtimes_with_extra_info"]

    def host_columns(self) -> list[str]:
        return ["scheduled_downtime_depth", "downtimes_with_extra_info"]

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> tuple[IconSpec, str, str | None] | None:
        def detail_txt(
            downtimes_with_extra_info: Sequence[
                tuple[int, str, str, str, int, int, int, bool, int, bool, bool]
            ],
        ) -> str:
            if not downtimes_with_extra_info:
                return ""

            lines = []
            for downtime_entry in downtimes_with_extra_info:
                (
                    _downtime_id,
                    author,
                    comment,
                    _origin,
                    _entry_time,
                    start_time,
                    end_time,
                    fixed,
                    duration,
                    _recurring,
                    _is_pending,
                ) = downtime_entry[:11]

                if fixed:
                    time_info = f"Start: {cmk.utils.render.date_and_time(start_time)}, End: {cmk.utils.render.date_and_time(end_time)}"
                else:
                    time_info = f"May start from {cmk.utils.render.date_and_time(start_time)} till {cmk.utils.render.date_and_time(end_time)} with duration of {cmk.utils.render.Age(duration)}"
                    lines.append(f"{author} ({time_info}) - {comment}")

            return "\n%s" % "\n".join(lines)

        # Currently we are in a downtime + link to list of downtimes
        # for this host / service
        if row[what + "_scheduled_downtime_depth"] > 0:
            if what == "host":
                icon = "downtime"
            else:
                icon = "downtime"

            title = _("Currently in downtime")
            title += detail_txt(row[what + "_downtimes_with_extra_info"])

            return (
                icon,
                title,
                url_to_visual(
                    row, VisualLinkSpec("views", "downtimes_of_" + what), request=request
                ),
            )

        if what == "service" and row["host_scheduled_downtime_depth"] > 0:
            title = _("The host is currently in downtime")
            title += detail_txt(row["host_downtimes_with_extra_info"])

            return (
                {"icon": "folder", "emblem": "downtime"},
                title,
                url_to_visual(row, VisualLinkSpec("views", "downtimes_of_host"), request=request),
            )
        return None


# .
#   .--Comments------------------------------------------------------------.
#   |           ____                                     _                 |
#   |          / ___|___  _ __ ___  _ __ ___   ___ _ __ | |_ ___           |
#   |         | |   / _ \| '_ ` _ \| '_ ` _ \ / _ \ '_ \| __/ __|          |
#   |         | |__| (_) | | | | | | | | | | |  __/ | | | |_\__ \          |
#   |          \____\___/|_| |_| |_|_| |_| |_|\___|_| |_|\__|___/          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class CommentsIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "status_comments"

    @classmethod
    def title(cls) -> str:
        return _("Status comments")

    def columns(self) -> Sequence[ColumnName]:
        return ["comments_with_extra_info"]

    def default_toplevel(self) -> bool:
        return True

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> tuple[str, str, str | None] | None:
        comments = row[what + "_comments_with_extra_info"]
        if len(comments) > 0:
            text = ""
            for c in sorted(comments, key=lambda x: x[4]):
                _id, author, comment, _ty, timestamp = c
                comment = comment.replace("\n", "<br>")
                text += '{} {}: "{}" \n'.format(
                    paint_age(
                        timestamp,
                        True,
                        0,
                        request=request,
                        painter_options=PainterOptions.get_instance(),
                        mode="abs",
                    )[1],
                    author,
                    comment,
                )
            return (
                "comment",
                text,
                url_to_visual(row, VisualLinkSpec("views", "comments_of_" + what), request=request),
            )
        return None


# .
#   .--Notifications-------------------------------------------------------.
#   |       _   _       _   _  __ _           _   _                        |
#   |      | \ | | ___ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __  ___        |
#   |      |  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | \__ \       |
#   |      |_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class NotificationsIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "status_notifications_enabled"

    @classmethod
    def title(cls) -> str:
        return _("Status notifications enabled")

    def columns(self) -> Sequence[ColumnName]:
        return ["modified_attributes_list", "notifications_enabled"]

    def default_toplevel(self) -> bool:
        return True

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
        # Notifications disabled
        enabled = row[what + "_notifications_enabled"]
        modified = "notifications_enabled" in row[what + "_modified_attributes_list"]
        if modified and enabled:
            return "notif_enabled", _("Notifications are manually enabled for this %s") % what
        if modified and not enabled:
            return "notif_man_disabled", _("Notifications are manually disabled for this %s") % what
        if not enabled:
            return "notif_disabled", _("Notifications are disabled for this %s") % what
        return None


# .
#   .--Flapping------------------------------------------------------------.
#   |               _____ _                   _                            |
#   |              |  ___| | __ _ _ __  _ __ (_)_ __   __ _                |
#   |              | |_  | |/ _` | '_ \| '_ \| | '_ \ / _` |               |
#   |              |  _| | | (_| | |_) | |_) | | | | | (_| |               |
#   |              |_|   |_|\__,_| .__/| .__/|_|_| |_|\__, |               |
#   |                            |_|   |_|            |___/                |
#   '----------------------------------------------------------------------'


class FlappingIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "status_flapping"

    @classmethod
    def title(cls) -> str:
        return _("Status flapping")

    def columns(self) -> Sequence[ColumnName]:
        return ["is_flapping"]

    def default_toplevel(self) -> bool:
        return True

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | tuple[str, str]:
        if row[what + "_is_flapping"]:
            if what == "host":
                title = _("This host is flapping")
            else:
                title = _("This service is flapping")
            return "flapping", title
        return None


# .
#   .--Staleness-----------------------------------------------------------.
#   |              ____  _        _                                        |
#   |             / ___|| |_ __ _| | ___ _ __   ___  ___ ___               |
#   |             \___ \| __/ _` | |/ _ \ '_ \ / _ \/ __/ __|              |
#   |              ___) | || (_| | |  __/ | | |  __/\__ \__ \              |
#   |             |____/ \__\__,_|_|\___|_| |_|\___||___/___/              |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class StalenessIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "status_stale"

    @classmethod
    def title(cls) -> str:
        return _("Status stale")

    def columns(self) -> Sequence[ColumnName]:
        return ["staleness"]

    def default_toplevel(self) -> bool:
        return True

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
        if is_stale(row, config=active_config):
            if what == "host":
                title = _("This host is stale")
            else:
                title = _("This service is stale")
                title += (
                    _(", no data has been received within the last %.1f check periods")
                    % active_config.staleness_threshold
                )
            return "stale", title
        return None


# .
#   .--Active-Checks-------------------------------------------------------.
#   |     _        _   _                  ____ _               _           |
#   |    / \   ___| |_(_)_   _____       / ___| |__   ___  ___| | _____    |
#   |   / _ \ / __| __| \ \ / / _ \_____| |   | '_ \ / _ \/ __| |/ / __|   |
#   |  / ___ \ (__| |_| |\ V /  __/_____| |___| | | |  __/ (__|   <\__ \   |
#   | /_/   \_\___|\__|_| \_/ \___|      \____|_| |_|\___|\___|_|\_\___/   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class ActiveChecksIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "status_active_checks"

    @classmethod
    def title(cls) -> str:
        return _("Status active checks")

    def columns(self) -> Sequence[ColumnName]:
        return ["modified_attributes_list", "active_checks_enabled"]

    def default_toplevel(self) -> bool:
        return True

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
        # Setting of active checks modified by user
        if "active_checks_enabled" in row[what + "_modified_attributes_list"]:
            if row[what + "_active_checks_enabled"] == 0:
                return (
                    "disabled",
                    _("Active checks have been manually disabled for this %s!") % what,
                )
            return "checkmark", _("Active checks have been manually enabled for this %s!") % what
        return None


# .
#   .--Passiv-Checks-------------------------------------------------------.
#   |   ____               _             ____ _               _            |
#   |  |  _ \ __ _ ___ ___(_)_   __     / ___| |__   ___  ___| | _____     |
#   |  | |_) / _` / __/ __| \ \ / /____| |   | '_ \ / _ \/ __| |/ / __|    |
#   |  |  __/ (_| \__ \__ \ |\ V /_____| |___| | | |  __/ (__|   <\__ \    |
#   |  |_|   \__,_|___/___/_| \_/       \____|_| |_|\___|\___|_|\_\___/    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class PassiveChecksIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "status_passive_checks"

    @classmethod
    def title(cls) -> str:
        return _("Status passive checks")

    def columns(self) -> Sequence[ColumnName]:
        return ["modified_attributes_list", "accept_passive_checks"]

    def default_toplevel(self) -> bool:
        return True

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
        # Passive checks disabled manually?
        if "passive_checks_enabled" in row[what + "_modified_attributes_list"]:
            if row[what + "_accept_passive_checks"] == 0:
                return (
                    "npassive",
                    _("Passive checks have been manually disabled for this %s!") % what,
                )
        return None


# .
#   .--Notif.-Periods------------------------------------------------------.
#   |    _   _       _   _  __       ____           _           _          |
#   |   | \ | | ___ | |_(_)/ _|     |  _ \ ___ _ __(_) ___   __| |___      |
#   |   |  \| |/ _ \| __| | |_ _____| |_) / _ \ '__| |/ _ \ / _` / __|     |
#   |   | |\  | (_) | |_| |  _|_____|  __/  __/ |  | | (_) | (_| \__ \     |
#   |   |_| \_|\___/ \__|_|_|(_)    |_|   \___|_|  |_|\___/ \__,_|___/     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class NotificationPeriodIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "status_notification_period"

    @classmethod
    def title(cls) -> str:
        return _("Status notification period")

    def columns(self) -> Sequence[ColumnName]:
        return ["in_notification_period"]

    def default_toplevel(self) -> bool:
        return True

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
        if not row[what + "_in_notification_period"]:
            return "outofnot", _("Out of notification period")
        return None


# .
#   .--Service Period------------------------------------------------------.
#   |          ____                  _            ____                     |
#   |         / ___|  ___ _ ____   _(_) ___ ___  |  _ \ ___ _ __           |
#   |         \___ \ / _ \ '__\ \ / / |/ __/ _ \ | |_) / _ \ '__|          |
#   |          ___) |  __/ |   \ V /| | (_|  __/ |  __/  __/ | _           |
#   |         |____/ \___|_|    \_/ |_|\___\___| |_|   \___|_|(_)          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class ServicePeriodIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "status_service_period"

    @classmethod
    def title(cls) -> str:
        return _("Status service period")

    def columns(self) -> Sequence[ColumnName]:
        return ["in_service_period"]

    def default_toplevel(self) -> bool:
        return True

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
        if not row[what + "_in_service_period"]:
            return "outof_serviceperiod", _("Out of service period")
        return None


# .
#   .--Stars *-------------------------------------------------------------.
#   |                   ____  _                                            |
#   |                  / ___|| |_ __ _ _ __ ___  __/\__                    |
#   |                  \___ \| __/ _` | '__/ __| \    /                    |
#   |                   ___) | || (_| | |  \__ \ /_  _\                    |
#   |                  |____/ \__\__,_|_|  |___/   \/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class StarsIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "stars"

    @classmethod
    def title(cls) -> str:
        return _("Stars")

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
        stars = self._get_stars()

        if what == "host":
            starred = row["host_name"] in stars
            title = _("host")
        else:
            svc = row["host_name"] + ";" + row["service_description"]
            starred = svc in stars
            title = _("service")

        if starred:
            return "starred", _("This %s is one of your favorites") % title
        return None

    @request_memoize()
    def _get_stars(self) -> set[str]:
        return user.stars.copy()


# .
#   .--Crashdump-----------------------------------------------------------.
#   |         ____               _         _                               |
#   |        / ___|_ __ __ _ ___| |__   __| |_   _ _ __ ___  _ __          |
#   |       | |   | '__/ _` / __| '_ \ / _` | | | | '_ ` _ \| '_ \         |
#   |       | |___| | | (_| \__ \ | | | (_| | |_| | | | | | | |_) |        |
#   |        \____|_|  \__,_|___/_| |_|\__,_|\__,_|_| |_| |_| .__/         |
#   |                                                       |_|            |
#   +----------------------------------------------------------------------+
#   |  Icon for a crashed check with a link to the crash dump page.        |
#   '----------------------------------------------------------------------'


class CrashdumpsIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "crashed_check"

    @classmethod
    def title(cls) -> str:
        return _("Crashed check")

    def default_toplevel(self) -> bool:
        return True

    def service_columns(self) -> list[str]:
        return ["plugin_output", "state", "host_name"]

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | tuple[str, str] | tuple[str, str, str]:
        if (
            what == "service"
            and row["service_state"] == 3
            and "check failed - please submit a crash report!" in row["service_plugin_output"]
        ):
            if not user.may("general.see_crash_reports"):
                return "crash", _(
                    "This check crashed. Please inform a Checkmk user that is allowed "
                    "to view and submit crash reports to the development team."
                )

            # Extract the crash ID produced by cmk/base/crash_reporting.py from output
            match = re.search(r"\(Crash-ID: ([^\)]+)\)", row["service_plugin_output"])
            if not match:
                return "crash", _(
                    "This check crashed, but no crash dump is available, please report this "
                    "to the development team."
                )

            crash_id = match.group(1)
            crashurl = makeuri_contextless(
                request,
                [
                    ("site", row["site"]),
                    ("crash_id", crash_id),
                ],
                filename="crash.py",
            )
            return (
                "crash",
                _(
                    "This check crashed. Please click here for more information. You also can submit "
                    "a crash report to the development team if you like."
                ),
                crashurl,
            )
        return None


# .
#   .--Check Period--------------------------------------------------------.
#   |       ____ _               _      ____           _           _       |
#   |      / ___| |__   ___  ___| | __ |  _ \ ___ _ __(_) ___   __| |      |
#   |     | |   | '_ \ / _ \/ __| |/ / | |_) / _ \ '__| |/ _ \ / _` |      |
#   |     | |___| | | |  __/ (__|   <  |  __/  __/ |  | | (_) | (_| |      |
#   |      \____|_| |_|\___|\___|_|\_\ |_|   \___|_|  |_|\___/ \__,_|      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Icon shown if the check is outside its check period                  |
#   '----------------------------------------------------------------------'


class CheckPeriodIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "check_period"

    @classmethod
    def title(cls) -> str:
        return _("Check period")

    def columns(self) -> Sequence[ColumnName]:
        return ["in_check_period"]

    def default_toplevel(self) -> bool:
        return True

    def service_columns(self) -> list[str]:
        return ["in_passive_check_period"]

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | tuple[str, str]:
        if what == "service":
            if (
                row["%s_in_passive_check_period" % what] == 0
                or row["%s_in_check_period" % what] == 0
            ):
                return "pause", _("This service is currently not being checked")
        elif what == "host":
            if row["%s_in_check_period" % what] == 0:
                return "pause", _("This host is currently not being checked")
        return None
