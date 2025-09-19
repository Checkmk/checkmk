#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

import requests

from cmk.notification_plugins import utils

api_url = "https://api.pushover.net/1/messages.json"

PRIORITY_MAP: dict[str, int] = {
    "emergency": 2,
    "high": 1,
    "normal": 0,
    "low": -1,
    "lowest": -2,
}


def main() -> int:
    context = utils.collect_context()
    subject = get_subject(context)
    text = get_text(context)

    api_key = context["PARAMETER_API_KEY"]
    recipient_key = context["PARAMETER_RECIPIENT_KEY"]

    return send_push_notification(api_key, recipient_key, subject, text, context)


def get_subject(context: dict[str, str]) -> str:
    s = context["HOSTNAME"]

    if context["WHAT"] != "HOST":
        s += "/" + context["SERVICEDESC"]
    s += " "

    notification_type = context["NOTIFICATIONTYPE"]
    if notification_type in ["PROBLEM", "RECOVERY"]:
        s += "$PREVIOUS@HARDSHORTSTATE$ \u2192 $@SHORTSTATE$"

    elif notification_type.startswith("FLAP"):
        if "START" in notification_type:
            s += "Started Flapping"
        else:
            s += "Stopped Flapping ($@SHORTSTATE$)"

    elif notification_type.startswith("DOWNTIME"):
        what = notification_type[8:].title()
        s += "Downtime " + what + " ($@SHORTSTATE$)"

    elif notification_type == "ACKNOWLEDGEMENT":
        s += "Acknowledged ($@SHORTSTATE$)"

    elif notification_type == "CUSTOM":
        s += "Custom Notification ($@SHORTSTATE$)"

    else:
        s += notification_type

    return utils.substitute_context(s.replace("@", context["WHAT"]), context)


def get_text(context: dict[str, str]) -> str:
    s = ""

    s += "$@OUTPUT$"

    if "PARAMETER_URL_PREFIX_1" in context:
        s += " <i>Link: </i>"
        s += utils.format_link(
            '<a href="%s">%s</a>', utils.host_url_from_context(context), context["HOSTNAME"]
        )
        if context["WHAT"] != "HOST":
            s += utils.format_link(
                '<a href="%s">%s</a>',
                utils.service_url_from_context(context),
                context["SERVICEDESC"],
            )

    return utils.substitute_context(s.replace("@", context["WHAT"]), context)


def send_push_notification(
    api_key: str, recipient_key: str, subject: str, text: str, context: dict[str, str]
) -> int:
    params: list[tuple[str, str | int | bytes]] = [
        ("token", api_key),
        ("user", recipient_key),
        ("title", subject.encode("utf-8")),
        ("message", text.encode("utf-8")),
        ("timestamp", int(float(context["MICROTIME"]) / 1000000.0)),
        ("html", 1),
    ]

    if (priority := context.get("PARAMETER_PRIORITY_1")) and priority in PRIORITY_MAP:
        if priority == "emergency":
            retry = context.get("PARAMETER_PRIORITY_2_1", 0)
            expire = context.get("PARAMETER_PRIORITY_2_2", 0)
            params += [
                ("priority", PRIORITY_MAP[priority]),
                ("retry", str(int(float(retry)))),
                ("expire", str(int(float(expire)))),
            ]
            if recipient := context.get("PARAMETER_RECIPIENT_KEY"):
                params.append(("receipts", recipient))
        else:
            params += [("priority", PRIORITY_MAP[priority])]

    if context.get("PARAMETER_SOUND", "none") != "none":
        params.append(("sound", context["PARAMETER_SOUND"]))

    proxy_url = context.get("PARAMETER_PROXY_URL")
    proxies = {"https": proxy_url} if proxy_url else None

    session = requests.Session()
    try:
        response = session.post(
            api_url,
            params=dict(params),
            proxies=proxies,
        )
    except requests.exceptions.ProxyError:
        sys.stdout.write("Cannot connect to proxy: %s\n" % context["PARAMETER_PROXY_URL"])
        return 1
    except requests.exceptions.RequestException:
        sys.stdout.write("POST request to server failed: %s\n" % api_url)
        return 1

    if response.status_code not in [200, 204]:
        sys.stdout.write(
            f"Failed to send notification. Status: {response.status_code}, Response: {response.text}\n"
        )
        return 1

    try:
        data = response.json()
    except ValueError:
        sys.stdout.write("Failed to decode JSON response: %s\n" % response.text)
        return 1

    # According to the Pushover API the status should be 1 if we get a 200,
    # but check it just in case
    if data.get("status") != 1:
        sys.stdout.write("Received an error from the Pushover API: %s" % response.text)
        return 1

    return 0
