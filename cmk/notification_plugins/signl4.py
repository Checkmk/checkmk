#!/usr/bin/env python3
# SIGNL4 Alerting

# (c) 2020 Derdack GmbH - License: GNU Public License v2
#          SIGNL4 <info@signl4.com>
# Reliable team alerting using SIGNL4.

from os import environ

from cmk.notification_plugins.utils import post_request, process_by_result_map
from cmk.notification_plugins.utils import retrieve_from_passwordstore as passwords
from cmk.notification_plugins.utils import StateInfo

RESULT_MAP = {
    (200, 299): StateInfo(0, "json", "eventId"),
    (300, 499): StateInfo(2, "str", "Error"),
    (500, 599): StateInfo(1, "str", "Server-Error"),
}


def _signl4_url() -> str:
    password = passwords(environ["NOTIFY_PARAMETER_PASSWORD"])
    return f"https://connect.signl4.com/webhook/{password}"

def _signl4_msg(context: dict[str, str]) -> dict[str, object]:
    host_name = context.get("HOSTNAME", "")
    service_desc = context.get("SERVICEDESC", "")
    host_state = ""
    notification_type = context.get("NOTIFICATIONTYPE", "")
    host_problem_id = context.get("HOSTPROBLEMID", "")
    service_problem_id = context.get("SERVICEPROBLEMID", "")
    description = f"{notification_type} on {host_name}"

    # Prepare description information
    if context.get("WHAT", "") == "SERVICE":
        if notification_type in [ "PROBLEM", "RECOVERY" ]:
            description += " (" + service_desc + ")"
        else:
            description += " (" + service_desc + ")"
    else:
        if notification_type in [ "PROBLEM", "RECOVERY" ]:
            host_state = context.get("HOSTSTATE", "") or ""
            description += " (" + host_state + ")"
        else:
            description += " (" + host_state + ")"

    # Remove placeholder "$SERVICEPROBLEMID$" if exists
    if service_problem_id.find("$") != -1:
        service_problem_id = ""

    # Check if this is a new problem or a recovery
    s4_status = "new" if notification_type != "RECOVERY" else "resolved"

    # Base64 encode the SERVICEDESC for matching updates for service alerts
    service_desc = context.get("SERVICEDESC", "")
    service_desc_base64 = ""
    service_desc_id_part = ""
    if len(service_desc) > 0:
        service_desc_bytes = service_desc.encode("ascii")
        service_desc_base64 = base64.b64encode(service_desc_bytes).decode()
        service_desc_id_part = ":ServiceDesc:" + service_desc_base64

    return {
        "Title": description,
        "HostName": host_name,
        "NotificationType": notification_type,
        "ServiceState": context.get("SERVICESTATE", ""),
        "ServiceDescription": service_desc,
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
        + service_problem_id
        + service_desc_id_part,
        "X-S4-Status": s4_status,
    }

def main() -> int:
    return process_by_result_map(
        response=post_request(
            message_constructor=_signl4_msg,
            url=_signl4_url(),
        ),
        result_map=RESULT_MAP,
    )
