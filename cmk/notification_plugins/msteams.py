#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.ms_teams_constants import (
    ms_teams_tmpl_host_details,
    ms_teams_tmpl_host_summary,
    ms_teams_tmpl_host_title,
    ms_teams_tmpl_svc_details,
    ms_teams_tmpl_svc_summary,
    ms_teams_tmpl_svc_title,
)
from cmk.utils.notify_types import PluginNotificationContext

from cmk.notification_plugins.utils import (
    host_url_from_context,
    post_request,
    process_by_status_code,
    service_url_from_context,
    substitute_context,
)

MAP_STATES: dict[str, str] = {
    "OK": "2eb886",
    "WARNING": "daa038",
    "CRITICAL": "a30200",
    "UNKNOWN": "cccccc",
    "DOWN": "a30200",
    "UP": "2eb886",
}

MAP_TYPES: dict[str, str] = {
    "PROBLEM": "Problem notification",
    "RECOVERY": "Recovery notification",
    "DOWNTIMESTART": "Start of downtime",
    "DOWNTIMEEND": "End of downtime",
    "DOWNTIMECANCELLED": "Downtime cancelled",
    "ACKNOWLEDGEMENT": "Problem acknowledged",
}


def _msteams_msg(
    context: PluginNotificationContext,
) -> dict[str, object]:
    title, summary, details, subtitle = _get_text_fields(context, notify_what := context["WHAT"])
    color = _get_theme_color(context, notify_what)
    section_facts = _get_section_facts(context, details)
    info_url: str = (
        service_url_from_context(context)
        if notify_what == "SERVICE"
        else host_url_from_context(context)
    )

    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "title": substitute_context(title, context),
        "themeColor": color,
        "summary": substitute_context(summary, context),
        "sections": [
            {
                "activitySubtitle": f"**{subtitle}**",  # bold seems to be nicer here
                "facts": section_facts,
                "markdown": "True",
            }
        ],
        "potentialAction": [
            {
                "@type": "OpenUri",
                "name": "View %s details in Checkmk" % notify_what.lower(),
                "targets": [{"os": "default", "uri": info_url}],
            }
        ],
    }


def _get_text_fields(
    context: PluginNotificationContext,
    notify_what: str,
) -> tuple[str, str, str, str]:
    subtitle: str = MAP_TYPES.get(context["NOTIFICATIONTYPE"], "")
    if notify_what == "SERVICE":
        return (
            context.get("PARAMETER_SERVICE_TITLE", ms_teams_tmpl_svc_title()),
            context.get("PARAMETER_SERVICE_SUMMARY", ms_teams_tmpl_svc_summary()),
            context.get("PARAMETER_SERVICE_DETAILS", ms_teams_tmpl_svc_details()),
            subtitle,
        )

    return (
        context.get("PARAMETER_HOST_TITLE", ms_teams_tmpl_host_title()),
        context.get("PARAMETER_HOST_SUMMARY", ms_teams_tmpl_host_summary()),
        context.get("PARAMETER_HOST_DETAILS", ms_teams_tmpl_host_details()),
        subtitle,
    )


def _get_section_facts(context: PluginNotificationContext, details: str) -> list[dict[str, str]]:
    section_facts = [
        {"name": "Detail", "value": substitute_context(details, context)},
    ]

    if "PARAMETER_AFFECTED_HOST_GROUPS" in context:
        section_facts += [{"name": "Affected host groups", "value": context["HOSTGROUPNAMES"]}]

    if context["NOTIFICATIONAUTHOR"] != "":
        section_facts += [
            {"name": "Author", "value": context["NOTIFICATIONAUTHOR"]},
            {"name": "Comment", "value": context["NOTIFICATIONCOMMENT"]},
        ]

    return section_facts


def _get_theme_color(context: PluginNotificationContext, notify_what: str) -> str:
    if context["NOTIFICATIONTYPE"] == "DOWNTIMESTART":
        return "439FE0"
    if context["NOTIFICATIONTYPE"] == "DOWNTIMEEND":
        return "33cccc"
    if context["NOTIFICATIONTYPE"] == "ACKNOWLEDGEMENT":
        return "8f006b"

    return (
        MAP_STATES[context["SERVICESTATE"]]
        if notify_what == "SERVICE"
        else MAP_STATES[context["HOSTSTATE"]]
    )


def main() -> int:
    return process_by_status_code(post_request(_msteams_msg))
