#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This script creates an ASCII email. It replaces the builtin ASCII email feature and
# is configurable via WATO with named parameters (only).

import sys
from email.mime.text import MIMEText
from typing import NoReturn

from cmk.notification_plugins import utils

opt_debug = "-d" in sys.argv
bulk_mode = "--bulk" in sys.argv

# Note: When you change something here, please also change this
# in web/plugins/wato/notifications.py in the default values of the configuration
# ValueSpec.
tmpl_host_subject = "Check_MK: $HOSTNAME$ - $EVENT_TXT$"
tmpl_service_subject = "Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$"
tmpl_common_body = """Host:     $HOSTNAME$
Alias:    $HOSTALIAS$
Address:  $HOSTADDRESS$
"""
tmpl_host_body = """Event:    $EVENT_TXT$
Output:   $HOSTOUTPUT$
Perfdata: $HOSTPERFDATA$
$LONGHOSTOUTPUT$
"""
tmpl_service_body = """Service:  $SERVICEDESC$
Event:    $EVENT_TXT$
Output:   $SERVICEOUTPUT$
Perfdata: $SERVICEPERFDATA$
$LONGSERVICEOUTPUT$
"""
tmpl_alerthandler_host_body = """Alert handler: $ALERTHANDLERNAME$
Handler output: $ALERTHANDLEROUTPUT$
"""
tmpl_alerthandler_service_body = "Service:  $SERVICEDESC$\n" + tmpl_alerthandler_host_body


def construct_content(context: dict[str, str]) -> str:  # pylint: disable=too-many-branches

    # Create a notification summary in a new context variable
    # Note: This code could maybe move to cmk --notify in order to
    # make it available every in all notification scripts
    # We have the following types of notifications:

    # - Alerts                OK -> CRIT
    #   NOTIFICATIONTYPE is "PROBLEM" or "RECOVERY"

    # - Flapping              Started, Ended
    #   NOTIFICATIONTYPE is "FLAPPINGSTART" or "FLAPPINGSTOP"

    # - Downtimes             Started, Ended, Cancelled
    #   NOTIFICATIONTYPE is "DOWNTIMESTART", "DOWNTIMECANCELLED", or "DOWNTIMEEND"

    # - Acknowledgements
    #   NOTIFICATIONTYPE is "ACKNOWLEDGEMENT"

    # - Custom notifications
    #   NOTIFICATIONTYPE is "CUSTOM"

    notification_type = context["NOTIFICATIONTYPE"]
    if notification_type in ["PROBLEM", "RECOVERY"]:
        txt_info = "$PREVIOUS@HARDSHORTSTATE$ -> $@SHORTSTATE$"

    elif notification_type.startswith("FLAP"):
        if "START" in notification_type:
            txt_info = "Started Flapping"
        else:
            txt_info = "Stopped Flapping ($@SHORTSTATE$)"

    elif notification_type.startswith("DOWNTIME"):
        what = notification_type[8:].title()
        txt_info = "Downtime " + what + " ($@SHORTSTATE$)"

    elif notification_type == "ACKNOWLEDGEMENT":
        txt_info = "Acknowledged ($@SHORTSTATE$)"

    elif notification_type == "CUSTOM":
        txt_info = "Custom Notification ($@SHORTSTATE$)"

    else:
        txt_info = notification_type  # Should neven happen

    txt_info = utils.substitute_context(txt_info.replace("@", context["WHAT"]), context)

    context["EVENT_TXT"] = txt_info

    # Prepare the mail contents
    if "PARAMETER_COMMON_BODY" in context:
        tmpl_body = context["PARAMETER_COMMON_BODY"]
    else:
        tmpl_body = tmpl_common_body

    if "ALERTHANDLERNAME" in context:
        my_tmpl_host_body = tmpl_alerthandler_host_body
        my_tmpl_service_body = tmpl_alerthandler_service_body
    else:
        my_tmpl_host_body = tmpl_host_body
        my_tmpl_service_body = tmpl_service_body

    # Compute the subject and body of the mail
    if context["WHAT"] == "HOST":
        tmpl = context.get("PARAMETER_HOST_SUBJECT") or tmpl_host_subject
        if "PARAMETER_HOST_BODY" in context:
            tmpl_body += context["PARAMETER_HOST_BODY"]
        else:
            tmpl_body += my_tmpl_host_body
    else:
        tmpl = context.get("PARAMETER_SERVICE_SUBJECT") or tmpl_service_subject
        if "PARAMETER_SERVICE_BODY" in context:
            tmpl_body += context["PARAMETER_SERVICE_BODY"]
        else:
            tmpl_body += my_tmpl_service_body

    context["SUBJECT"] = utils.substitute_context(tmpl, context)
    body = utils.substitute_context(tmpl_body, context)

    return body


def main() -> NoReturn:
    if bulk_mode:
        content_txt = ""
        parameters, contexts = utils.read_bulk_contexts()
        hosts = set()
        for context in contexts:
            context.update(parameters)
            content_txt += construct_content(context)
            mailto = context["CONTACTEMAIL"]  # Assume the same in each context
            subject = context["SUBJECT"]
            hosts.add(context["HOSTNAME"])

        # Use the single context subject in case there is only one context in the bulk
        if len(contexts) > 1:
            subject = utils.get_bulk_notification_subject(contexts, hosts)

    else:
        # gather all options from env
        context = utils.collect_context()
        content_txt = construct_content(context)
        mailto = context["CONTACTEMAIL"]
        subject = context["SUBJECT"]

    if not mailto:  # e.g. empty field in user database
        sys.stdout.write("Cannot send ASCII email: empty destination email address\n")
        sys.exit(2)

    # Create the mail and send it
    from_address = utils.format_address(
        context.get("PARAMETER_FROM_DISPLAY_NAME", ""),
        context.get("PARAMETER_FROM_ADDRESS", utils.default_from_address()),
    )
    reply_to = utils.format_address(
        context.get("PARAMETER_REPLY_TO_DISPLAY_NAME", ""),
        context.get("PARAMETER_REPLY_TO_ADDRESS", ""),
    )
    m = utils.set_mail_headers(
        mailto, subject, from_address, reply_to, MIMEText(content_txt, "plain", _charset="utf-8")
    )
    try:
        sys.exit(utils.send_mail_sendmail(m, mailto, from_address))
    except Exception as e:
        sys.stderr.write("Unhandled exception: %s\n" % e)
        # unhandled exception, don't retry this...
        sys.exit(2)
