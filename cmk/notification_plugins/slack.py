#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
r"""
Send notification messages to Slack
===================================

Use a slack webhook to send notification messages
"""

from collections.abc import Iterable
from dataclasses import dataclass

from urllib3.util import parse_url

from cmk.utils.notify_types import PluginNotificationContext

from cmk.notification_plugins.utils import (
    host_url_from_context,
    post_request,
    pretty_notification_type,
    pretty_state,
    process_by_status_code,
    retrieve_from_passwordstore,
    service_url_from_context,
)

MSG_ADDITIONAL_INFO = "Additional Info"
MSG_TIMESTAMP_PREFIX = "Check_MK notification: "
COLORS = {
    "CRITICAL": "#EE0000",
    "DOWN": "#EE0000",
    "WARNING": "#FFDD00",
    "OK": "#00CC00",
    "UP": "#00CC00",
    "UNKNOWN": "#CCCCCC",
    "UNREACHABLE": "#CCCCCC",
}
EMOJI = {
    "CRITICAL": "rotating_light",
    "DOWN": "rotating_light",
    "WARNING": "warning",
    "OK": "white_check_mark",
    "UP": "white_check_mark",
    "UNKNOWN": "question",
    "UNREACHABLE": "no_entry",
}


def _get_color(notification_type: str, state: str) -> str:
    if notification_type in ("ACKNOWLEDGEMENT", "DOWNTIMESTART"):
        return "#CCCCCC"
    if notification_type == "FLAPPINGSTART":
        return "#FFDD00"
    if notification_type.startswith("ALERTHANDLER"):
        return "#EE0000"

    # PROBLEM, RECOVERY, FLAPPINGSTOP, FLAPPINGDISABLED, DOWNTIMEEND, DOWNTIMECANCELLED, CUSTOM
    return COLORS.get(state, "#CCCCCC")


def _get_emoji(notification_type: str, state: str) -> str | None:
    if notification_type == "ACKNOWLEDGEMENT":
        return "hammer_and_wrench"
    if notification_type == "DOWNTIMESTART":
        return "construction"
    if notification_type == "FLAPPINGSTART":
        return "vertical_traffic_light"
    if notification_type.startswith("ALERTHANDLER"):
        return "bell"

    # PROBLEM, RECOVERY, FLAPPINGSTOP, FLAPPINGDISABLED, DOWNTIMEEND, DOWNTIMECANCELLED, CUSTOM
    return EMOJI.get(state)


@dataclass
class OptionalLink:
    url: str | None
    text: str

    def markdown(self) -> str:
        if self.url:
            return f"[{self.text}]({self.url})"

        return self.text

    def block_kit(self, bold: bool = False) -> dict[str, object]:
        if self.url:
            return {
                "type": "link",
                "url": self.url,
                "text": self.text,
                "style": {"bold": bold},
            }

        return {"type": "text", "text": self.text, "style": {"bold": bold}}


@dataclass
class CommonContent:
    state: str
    output: str
    contacts: list[str]
    host_link: OptionalLink
    service_link: OptionalLink | None
    title_prefix: str

    def contacts_markdown(self) -> str:
        return "Please take a look: " + ", ".join(map("@{}".format, self.contacts))

    def contacts_block_kit(self) -> Iterable[dict[str, object]]:
        if not self.contacts:
            return

        yield {"type": "text", "text": "Please take a look: "}
        add_comma = False
        for contact in self.contacts:
            if add_comma:
                yield {"type": "text", "text": ", "}

            add_comma = True
            if contact in ("here", "channel", "everyone"):
                yield {"type": "broadcast", "range": contact}
            else:
                yield {"type": "user", "user_id": contact}

        yield {"type": "text", "text": "\n"}


def _get_common_content(context: PluginNotificationContext) -> CommonContent:
    contacts = context["CONTACTNAME"].split(",")

    title_prefix = pretty_notification_type(context["NOTIFICATIONTYPE"])
    if context.get("WHAT", None) == "SERVICE":
        if context["NOTIFICATIONTYPE"] == "PROBLEM":
            title_prefix += f" ({pretty_state(context['SERVICESTATE'])})"
        return CommonContent(
            state=context["SERVICESTATE"],
            host_link=OptionalLink(url=host_url_from_context(context), text=context["HOSTNAME"]),
            service_link=OptionalLink(
                url=service_url_from_context(context), text=context["SERVICEDESC"]
            ),
            output=context["SERVICEOUTPUT"],
            contacts=contacts,
            title_prefix=f"{title_prefix}: Service ",
        )

    if context["NOTIFICATIONTYPE"] == "PROBLEM":
        title_prefix += f" ({pretty_state(context['HOSTSTATE'])})"
    return CommonContent(
        state=context["HOSTSTATE"],
        host_link=OptionalLink(url=host_url_from_context(context), text=context["HOSTNAME"]),
        service_link=None,
        output=context["HOSTOUTPUT"],
        contacts=contacts,
        title_prefix=f"{title_prefix}: Host ",
    )


def _is_slack(url: str) -> bool:
    parsed = parse_url(url)
    return isinstance(parsed.host, str) and parsed.host.endswith("slack.com")


def _message(context: PluginNotificationContext) -> dict[str, object]:
    common = _get_common_content(context)
    url = retrieve_from_passwordstore(context["PARAMETER_WEBHOOK_URL"])
    if _is_slack(url):
        return _slack_msg(context, common)

    return _mattermost_msg(context, common)


def _slack_msg(context: PluginNotificationContext, common: CommonContent) -> dict[str, object]:
    """Build the message for slack"""
    elements: list[dict[str, object]] = []
    if emoji := _get_emoji(context["NOTIFICATIONTYPE"], common.state):
        elements.append({"type": "emoji", "name": emoji})
        extra_space = " "
    else:
        extra_space = ""

    elements.append(
        {
            "type": "text",
            "text": f"{extra_space}{common.title_prefix}",
            "style": {"bold": True},
        }
    )
    if common.service_link:  # only set if it is a service notification
        elements.extend(
            (
                common.service_link.block_kit(bold=True),
                {"type": "text", "text": " on ", "style": {"bold": True}},
            )
        )

    elements.extend(
        (
            common.host_link.block_kit(bold=True),
            {"type": "text", "text": f"\n{MSG_ADDITIONAL_INFO}\n", "style": {"bold": True}},
            {
                "type": "text",
                "text": f"{common.output}\n",
            },
            *common.contacts_block_kit(),
            {"type": "text", "text": MSG_TIMESTAMP_PREFIX},
            {
                "type": "date",
                "timestamp": int(context["MICROTIME"]) // 1000000,
                "format": "{date_short_pretty} {time_secs}, {ago}",
                "fallback": context["LONGDATETIME"],
            },
        )
    )
    return {
        "blocks": [
            {
                "type": "rich_text",
                "elements": [
                    {
                        "type": "rich_text_section",
                        "elements": elements,
                    }
                ],
            },
        ]
    }


def _mattermost_msg(context: PluginNotificationContext, common: CommonContent) -> dict[str, object]:
    """Build the message for mattermost"""
    attachment = {
        "color": _get_color(context["NOTIFICATIONTYPE"], common.state),
        "footer": MSG_TIMESTAMP_PREFIX + context["LONGDATETIME"],
        "text": f"**{MSG_ADDITIONAL_INFO}**\n{common.output}\n{common.contacts_markdown()}",
    }
    if common.service_link:  # only set if it is a service notification
        attachment["title"] = f"{common.title_prefix}{common.service_link.text}"
        attachment["text"] = f"Host: {common.host_link.markdown()}\n{attachment['text']}"
        if common.service_link.url:
            attachment["title_link"] = common.service_link.url

    else:
        attachment["title"] = f"{common.title_prefix}{common.host_link.text}"
        if common.host_link.url:
            attachment["title_link"] = common.host_link.url

    return {
        "attachments": [attachment],
    }


def main() -> int:
    return process_by_status_code(post_request(_message))
