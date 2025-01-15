#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable

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
    actions = []
    if info_url := (
        service_url_from_context(context)
        if notify_what == "SERVICE"
        else host_url_from_context(context)
    ):
        actions.append(
            {
                "type": "Action.OpenUrl",
                "title": f"View {notify_what.lower()} details in Checkmk",
                "url": info_url,
                "role": "Button",
            }
        )

    return {
        "type": "message",
        "summary": substitute_context(title, context),
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": "null",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.3",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": substitute_context(title, context),
                            "weight": "bolder",
                            "size": "large",
                            "style": "heading",
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": substitute_context(subtitle, context),
                            "weight": "bolder",
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": substitute_context(summary, context),
                            "wrap": True,
                        },
                        {
                            "type": "ColumnSet",
                            "separator": True,
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": "auto",
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "text": "Details",
                                            "wrap": True,
                                            "weight": "bolder",
                                        }
                                    ],
                                },
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "items": list(_get_details(context, details)),
                                },
                            ],
                        },
                        *_get_section_facts(context),
                    ],
                    "actions": actions,
                    "msteams": {
                        "width": "Full",
                    },
                },
            },
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


def _get_details(context: PluginNotificationContext, details: str) -> Iterable[dict[str, object]]:
    full_details = substitute_context(details, context).replace("\\n", "\n\n")
    add_separator = False
    for segment in full_details.split("\n\n"):
        if not segment.strip():
            add_separator = True
            continue

        if add_separator:
            yield {"type": "TextBlock", "text": segment, "wrap": True, "separator": True}
            add_separator = False
        else:
            yield {"type": "TextBlock", "text": segment, "wrap": True, "spacing": "none"}


def _get_section_facts(context: PluginNotificationContext) -> Iterable[dict[str, object]]:
    section_facts = []
    if "PARAMETER_AFFECTED_HOST_GROUPS" in context:
        section_facts += [{"title": "Affected host groups", "value": context["HOSTGROUPNAMES"]}]

    if author := context.get("NOTIFICATIONAUTHOR"):
        section_facts += [
            {"title": "Author", "value": author},
            {"title": "Comment", "value": context.get("NOTIFICATIONCOMMENT", "")},
        ]

    if section_facts:
        yield {
            "type": "FactSet",
            "facts": section_facts,
            "separator": True,
        }


def main() -> int:
    # 200: old webhooks (deprecated)
    # 202: workflows
    return process_by_status_code(post_request(_msteams_msg), (200, 202))
