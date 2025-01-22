#!/usr/bin/env python3
# SIGNL4 Alerting

# (c) 2023 Derdack GmbH - License: GNU Public License v2
#          SIGNL4 <info@signl4.com>
# SIGNL4: Mobile alerting and incident response.

import base64

from cmk.notification_plugins.utils import get_password_from_env_or_context as passwords
from cmk.notification_plugins.utils import post_request, process_by_matchers, StateInfo

RESULT_MATCHER = [
    ((200, 299), StateInfo(0, "json", "eventId")),
    ((300, 499), StateInfo(2, "str", "Error")),
    ((500, 599), StateInfo(1, "str", "Server-Error")),
]


def _signl4_url() -> str:
    password = passwords(key="NOTIFY_PARAMETER_PASSWORD")
    return f"https://connect.signl4.com/webhook/{password}"


def _signl4_msg(context: dict[str, str]) -> dict[str, object]:
    host_name = context["HOSTNAME"]
    service_desc = context.get("SERVICEDESC", "")
    host_state = ""
    notification_type = context["NOTIFICATIONTYPE"]
    host_problem_id = context.get("HOSTPROBLEMID", "")
    service_problem_id = context.get("SERVICEPROBLEMID", "")
    description = f"{notification_type} on {host_name}"

    # Prepare description information
    if context.get("WHAT", "") == "SERVICE":
        if notification_type in ["PROBLEM", "RECOVERY"]:
            description += " (" + service_desc + ")"
        else:
            description += " (" + service_desc + ")"
    elif notification_type in ["PROBLEM", "RECOVERY"]:
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
    return process_by_matchers(
        response=post_request(
            message_constructor=_signl4_msg,
            url=_signl4_url(),
        ),
        matchers=RESULT_MATCHER,
    )
