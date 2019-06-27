# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import sys
import requests
from cmk.notification_plugins import utils
api_url = "https://api.pushover.net/1/messages.json"


def main():
    context = utils.collect_context()
    subject = get_subject(context)
    text = get_text(context)

    api_key = context["PARAMETER_API_KEY"]
    recipient_key = context["PARAMETER_RECIPIENT_KEY"]

    send_push_notification(api_key, recipient_key, subject, text, context)


def get_subject(context):
    s = context["HOSTNAME"]

    if context["WHAT"] != "HOST":
        s += "/" + context["SERVICEDESC"]
    s += " "

    notification_type = context["NOTIFICATIONTYPE"]
    if notification_type in ["PROBLEM", "RECOVERY"]:
        s += "$PREVIOUS@HARDSHORTSTATE$ %s $@SHORTSTATE$" % unichr(8594)

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


def get_text(context):
    s = ""

    s += "$@OUTPUT$"

    if "PARAMETER_URL_PREFIX" in context:
        utils.extend_context_with_link_urls(context, '<a href="%s">%s</a>')
        s += " <i>Link: </i>"
        s += context["LINKEDHOSTNAME"]
        if context["WHAT"] != "HOST":
            s += context["LINKEDSERVICEDESC"]

    return utils.substitute_context(s.replace("@", context["WHAT"]), context)


def send_push_notification(api_key, recipient_key, subject, text, context):
    params = [
        ("token", api_key),
        ("user", recipient_key),
        ("title", subject.encode("utf-8")),
        ("message", text.encode("utf-8")),
        ("timestamp", int(context["MICROTIME"]) / 1000000),
        ("html", 1),
    ]

    if context.get("PARAMETER_PRIORITY") in ["-2", "-1", "0", "1"]:
        params += [("priority", context["PARAMETER_PRIORITY"])]

    elif context.get("PARAMETER_PRIORITY_PRIORITY") == "2":
        params += [
            ("priority", context["PARAMETER_PRIORITY_PRIORITY"]),
            ("expire", context.get("PARAMETER_PRIORITY_EXPIRE", 0)),
            ("retry", context.get("PARAMETER_PRIORITY_RETRY", 0)),
        ]
        if context.get("PARAMETER_PRIORITY_RECEIPTS"):
            params.append(("receipts", context["PARAMETER_PRIORITY_RECEIPTS"]))

    if context.get("PARAMETER_SOUND", "none") != "none":
        params.append(("sound", context["PARAMETER_SOUND"]))

    session = requests.Session()
    if context.get("PARAMETER_PROXY_URL"):
        response = session.post(
            api_url, params=dict(params), proxies={"https": context["PARAMETER_PROXY_URL"]})
    else:
        response = session.post(api_url, params=dict(params))

    if response.status_code == '200':
        return True

    sys.stdout.write("Failed to send notification. Status: %s, Response: %s\n" %
                     (response.status_code, response.text))
    return False
