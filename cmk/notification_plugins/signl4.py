#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# SIGNL4 Alerting

# (c) 2020 Derdack GmbH - License: GNU Public License v2
#          SIGNL4 <info@signl4.com>
# Reliable team alerting using SIGNL4.

from os import environ

from cmk.notification_plugins.utils import retrieve_from_passwordstore as passwords
from cmk.notification_plugins.utils import StateInfo

RESULT_MAP = {
    (200, 299): StateInfo(0, "json", "eventId"),
    (300, 499): StateInfo(2, "str", "Error"),
    (500, 599): StateInfo(1, "str", "Server-Error"),
}


def signl4_url():
    password = passwords(environ.get("NOTIFY_PARAMETER_PASSWORD"))
    return f"https://connect.signl4.com/webhook/{password}"


def signl4_msg(context):
    host_name = context.get("HOSTNAME")
    notification_type = context.get("NOTIFICATIONTYPE")
    host_problem_id = context.get("HOSTPROBLEMID", "")
    service_problem_id = context.get("SERVICEPROBLEMID", "")

    # Remove placeholder "$SERVICEPROBLEMID$" if exists
    if service_problem_id.find("$") != -1:
        service_problem_id = ""

    # Check if this is a new problem or a recovery
    s4_status = "new" if notification_type != "RECOVERY" else "resolved"

    message = {
        "Title": f"{notification_type} on {host_name}",
        "HostName": host_name,
        "NotificationType": notification_type,
        "ServiceState": context.get("SERVICESTATE", ""),
        "ServiceDescription": context.get("SERVICEDESC", ""),
        "ServiceOutput": context.get("SERVICEOUTPUT", ""),
        "HostState": context.get("HOSTSTATE", ""),
        "NotificationComment": "",
        "ContactName": context.get("CONTACTNAME", ""),
        "ContactAlias": context.get("CONTACTALIAS", ""),
        "ContactEmail": context.get("CONTACTEMAIL", ""),
        "ContactPager": context.get("CONTACTPAGER", "").replace(" ", ""),
        "HostProblemId": host_problem_id,
        "ServiceProblemId": service_problem_id,
        "DateTime": context.get("SHORTDATETIME", ""),
        "X-S4-SourceSystem": "Checkmk",
        "X-S4-ExternalID": "Checkmk: "
        + host_name
        + "-"
        + host_problem_id
        + "-"
        + service_problem_id,
        "X-S4-Status": s4_status,
    }

    return message
