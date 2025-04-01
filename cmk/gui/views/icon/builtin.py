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
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.painter.v0.helpers import render_cache_info
from cmk.gui.painter.v1.helpers import is_stale
from cmk.gui.painter_options import paint_age, PainterOptions
from cmk.gui.type_defs import Icon as IconSpec
from cmk.gui.type_defs import Row, VisualLinkSpec
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


def _render_action_menu_icon(
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


ActionMenuIcon = Icon(
    ident="action_menu",
    title=_l("Action menu"),
    toplevel=True,
    sort_index=10,
    render=_render_action_menu_icon,
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


def _render_icon_image_icon(
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


IconImageIcon = Icon(
    ident="icon_image",
    title=_l("Icon image"),
    columns=["icon_image"],
    toplevel=True,
    sort_index=25,
    render=_render_icon_image_icon,
)


# .
#   .--Reschedule----------------------------------------------------------.
#   |          ____                _              _       _                |
#   |         |  _ \ ___  ___  ___| |__   ___  __| |_   _| | ___           |
#   |         | |_) / _ \/ __|/ __| '_ \ / _ \/ _` | | | | |/ _ \          |
#   |         |  _ <  __/\__ \ (__| | | |  __/ (_| | |_| | |  __/          |
#   |         |_| \_\___||___/\___|_| |_|\___|\__,_|\__,_|_|\___|          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _render_reschedule_icon(
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


RescheduleIcon = Icon(
    ident="reschedule",
    title=_l("Reschedule"),
    columns=["check_type", "active_checks_enabled", "check_command"],
    service_columns=["cached_at", "cache_interval"],
    render=_render_reschedule_icon,
)


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


def _render_rule_editor_icon(
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


RuleEditorIcon = Icon(
    ident="rule_editor",
    title=_l("Rule editor"),
    columns=["check_type"],
    host_columns=["name"],
    service_columns=["description"],
    render=_render_rule_editor_icon,
)


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


def _render_manpage_icon(
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


ManpageIcon = Icon(
    ident="check_manpage",
    title=_l("Check manual page"),
    service_columns=["check_command"],
    render=_render_manpage_icon,
)


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


def _render_acknowledge_icon(
    what: Literal["host", "service"],
    row: Row,
    tags: Sequence[TagID],
    custom_vars: Mapping[str, str],
) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
    if row[what + "_acknowledged"]:
        return "ack", _("This problem has been acknowledged")
    return None


AcknowledgeIcon = Icon(
    ident="status_acknowledged",
    title=_l("Status acknowledged"),
    columns=["acknowledged"],
    toplevel=True,
    render=_render_acknowledge_icon,
)


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


def _render_perfgraph_icon(
    what: Literal["host", "service"],
    row: Row,
    tags: Sequence[TagID],
    custom_vars: Mapping[str, str],
) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
    if row[what + "_pnpgraph_present"] == 1:
        return _pnp_icon(row, what)
    return None


PerfgraphIcon = Icon(
    ident="perfgraph",
    title=_l("Performance graph"),
    columns=["pnpgraph_present"],
    toplevel=True,
    sort_index=20,
    render=_render_perfgraph_icon,
)


def _pnp_icon(row: Row, what: str) -> HTML | None:
    url = _graph_icon_link(row, what)

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


def _graph_icon_link(row: Row, what: str) -> str:
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


def _render_prediction_icon(
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


PredictionIcon = Icon(
    ident="prediction",
    title=_l("Prediction"),
    columns=["perf_data"],
    toplevel=True,
    render=_render_prediction_icon,
)


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


def _render_custom_action_icon(
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


CustomActionIcon = Icon(
    ident="custom_action",
    title=_l("Custom action"),
    columns=["action_url_expanded", "pnpgraph_present"],
    render=_render_custom_action_icon,
)


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


def _render_logwatch_icon(
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


LogwatchIcon = Icon(
    ident="logwatch",
    title=_l("Logwatch"),
    service_columns=["host_name", "service_description", "check_command"],
    render=_render_logwatch_icon,
)


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


def _render_notes_url_icon(
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


NotesIcon = Icon(
    ident="notes",
    title=_l("Notes"),
    columns=["notes_url_expanded", "check_command"],
    render=_render_notes_url_icon,
)


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


def _render_downtimes_icon(
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
            url_to_visual(row, VisualLinkSpec("views", "downtimes_of_" + what), request=request),
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


DowntimesIcon = Icon(
    ident="status_downtimes",
    title=_l("Status downtimes"),
    toplevel=True,
    columns=["scheduled_downtime_depth", "downtimes_with_extra_info"],
    host_columns=["scheduled_downtime_depth", "downtimes_with_extra_info"],
    render=_render_downtimes_icon,
)


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


def _render_comments_icon(
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


CommentsIcon = Icon(
    ident="status_comments",
    title=_l("Status comments"),
    columns=["comments_with_extra_info"],
    toplevel=True,
    render=_render_comments_icon,
)


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


def _render_notifications_icon(
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


NotificationsIcon = Icon(
    ident="status_notifications_enabled",
    title=_l("Status notifications enabled"),
    columns=["modified_attributes_list", "notifications_enabled"],
    toplevel=True,
    render=_render_notifications_icon,
)


# .
#   .--Flapping------------------------------------------------------------.
#   |               _____ _                   _                            |
#   |              |  ___| | __ _ _ __  _ __ (_)_ __   __ _                |
#   |              | |_  | |/ _` | '_ \| '_ \| | '_ \ / _` |               |
#   |              |  _| | | (_| | |_) | |_) | | | | | (_| |               |
#   |              |_|   |_|\__,_| .__/| .__/|_|_| |_|\__, |               |
#   |                            |_|   |_|            |___/                |
#   '----------------------------------------------------------------------'


def _render_flapping_icon(
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


FlappingIcon = Icon(
    ident="status_flapping",
    title=_l("Status flapping"),
    columns=["is_flapping"],
    toplevel=True,
    render=_render_flapping_icon,
)


# .
#   .--Staleness-----------------------------------------------------------.
#   |              ____  _        _                                        |
#   |             / ___|| |_ __ _| | ___ _ __   ___  ___ ___               |
#   |             \___ \| __/ _` | |/ _ \ '_ \ / _ \/ __/ __|              |
#   |              ___) | || (_| | |  __/ | | |  __/\__ \__ \              |
#   |             |____/ \__\__,_|_|\___|_| |_|\___||___/___/              |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def _render_staleness_icon(
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


StalenessIcon = Icon(
    ident="status_stale",
    title=_l("Status stale"),
    columns=["staleness"],
    toplevel=True,
    render=_render_staleness_icon,
)


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


def _render_active_checks_icon(
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


ActiveChecksIcon = Icon(
    ident="status_active_checks",
    title=_l("Status active checks"),
    columns=["modified_attributes_list", "active_checks_enabled"],
    toplevel=True,
    render=_render_active_checks_icon,
)

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


def _render_passive_checks_icon(
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


PassiveChecksIcon = Icon(
    ident="status_passive_checks",
    title=_l("Status passive checks"),
    columns=["modified_attributes_list", "accept_passive_checks"],
    toplevel=True,
    render=_render_passive_checks_icon,
)


# .
#   .--Notif.-Periods------------------------------------------------------.
#   |    _   _       _   _  __       ____           _           _          |
#   |   | \ | | ___ | |_(_)/ _|     |  _ \ ___ _ __(_) ___   __| |___      |
#   |   |  \| |/ _ \| __| | |_ _____| |_) / _ \ '__| |/ _ \ / _` / __|     |
#   |   | |\  | (_) | |_| |  _|_____|  __/  __/ |  | | (_) | (_| \__ \     |
#   |   |_| \_|\___/ \__|_|_|(_)    |_|   \___|_|  |_|\___/ \__,_|___/     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _render_notification_period_icon(
    what: Literal["host", "service"],
    row: Row,
    tags: Sequence[TagID],
    custom_vars: Mapping[str, str],
) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
    if not row[what + "_in_notification_period"]:
        return "outofnot", _("Out of notification period")
    return None


NotificationPeriodIcon = Icon(
    ident="status_notification_period",
    title=_l("Status notification period"),
    columns=["in_notification_period"],
    toplevel=True,
    render=_render_notification_period_icon,
)

# .
#   .--Service Period------------------------------------------------------.
#   |          ____                  _            ____                     |
#   |         / ___|  ___ _ ____   _(_) ___ ___  |  _ \ ___ _ __           |
#   |         \___ \ / _ \ '__\ \ / / |/ __/ _ \ | |_) / _ \ '__|          |
#   |          ___) |  __/ |   \ V /| | (_|  __/ |  __/  __/ | _           |
#   |         |____/ \___|_|    \_/ |_|\___\___| |_|   \___|_|(_)          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _render_service_period_icon(
    what: Literal["host", "service"],
    row: Row,
    tags: Sequence[TagID],
    custom_vars: Mapping[str, str],
) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
    if not row[what + "_in_service_period"]:
        return "outof_serviceperiod", _("Out of service period")
    return None


ServicePeriodIcon = Icon(
    ident="status_service_period",
    title=_l("Status service period"),
    columns=["in_service_period"],
    toplevel=True,
    render=_render_service_period_icon,
)


# .
#   .--Stars *-------------------------------------------------------------.
#   |                   ____  _                                            |
#   |                  / ___|| |_ __ _ _ __ ___  __/\__                    |
#   |                  \___ \| __/ _` | '__/ __| \    /                    |
#   |                   ___) | || (_| | |  \__ \ /_  _\                    |
#   |                  |____/ \__\__,_|_|  |___/   \/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _render_stars(
    what: Literal["host", "service"],
    row: Row,
    tags: Sequence[TagID],
    custom_vars: Mapping[str, str],
) -> None | str | HTML | tuple[str, str] | tuple[str, str, str]:
    stars = _get_stars()

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
def _get_stars() -> set[str]:
    return user.stars.copy()


StarsIcon = Icon(ident="stars", title=_l("Stars"), render=_render_stars)


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


def _render_crashed_check_icon(
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


CrashdumpsIcon = Icon(
    ident="crashed_check",
    title=_l("Crashed check"),
    toplevel=True,
    service_columns=["plugin_output", "state", "host_name"],
    render=_render_crashed_check_icon,
)


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


def _render_check_period_icon(
    what: Literal["host", "service"],
    row: Row,
    tags: Sequence[TagID],
    custom_vars: Mapping[str, str],
) -> None | tuple[str, str]:
    if what == "service":
        if row["%s_in_passive_check_period" % what] == 0 or row["%s_in_check_period" % what] == 0:
            return "pause", _("This service is currently not being checked")
    elif what == "host":
        if row["%s_in_check_period" % what] == 0:
            return "pause", _("This host is currently not being checked")
    return None


CheckPeriodIcon = Icon(
    ident="check_period",
    title=_l("Check period"),
    columns=["in_check_period"],
    toplevel=True,
    service_columns=["in_passive_check_period"],
    render=_render_check_period_icon,
)
