#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Argument 1: Full system path to the pnp4nagios index.php for fetching the graphs. Usually auto configured in OMD.
# Argument 2: HTTP-URL-Prefix to open Multisite. When provided, several links are added to the mail.
#             Example: http://myserv01/prod
#
# This script creates a nifty HTML email in multipart format with
# attached graphs and such neat stuff. Sweet!

import base64
import json
import os
import socket
import sys
from email.message import Message
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Callable, List, Literal, NamedTuple, NoReturn, Optional, Union
from urllib.parse import quote
from urllib.request import urlopen

import cmk.utils.site as site
from cmk.utils.exceptions import MKException

from cmk.notification_plugins import utils


def tmpl_head_html(html_section: str) -> str:
    return (
        """
<html>
<head>
<title>$SUBJECT$</title>
<style>
body {
    background-color: #ffffff;
    padding: 5px;
    font-family: arial,helvetica,sans-serif;
    font-size: 10px;
}
table {
    border-spacing: 0px;
    border-collapse: collapse;
    margin: 5px 0 0 0;
    padding: 0;
    width: 100%;
    color: black;
    empty-cells: show;
}

table th {
    font-weight: normal;
    border-right: 1px solid #cccccc;
    background-color: #999999;
    text-align: center;
    color: #ffffff;
    vertical-align: middle;
    font-size: 9pt;
    height: 14px;
}
table th:last-child {
    border-right-style: none;
}

table tr > td {
    border-right: 1px solid #cccccc;
    padding: 2px 4px;
    height: 22px;
    vertical-align: middle;
}
table tr td:last-child {
    border-right-style: none;
}

table a {
    text-decoration: none;
    color: black;
}
table a:hover {
    text-decoration: underline;
}

table tr td {
    padding-bottom: 4px;
    padding: 4px 5px 2px 5px;
    text-align: left;
    height: 16px;
    line-height: 14px;
    vertical-align: top;
    font-size: 9pt;
}
table tr td.left {
    width: 10%;
    white-space: nowrap;
    vertical-align: top;
    padding-right: 20px;
}
table tr.even0 td.left {
    background-color: #bbbbbb;
}
table tr.odd0 td.left {
    background-color: #cccccc;
}

tr.odd0  { background-color: #eeeeee; }
tr.even0 { background-color: #dddddd; }

td.odd0  { background-color: #eeeeee; }
td.even0 { background-color: #dddddd; }

tr.odd1  { background-color: #ffffcc; }
tr.even1 { background-color: #ffffaa; }

tr.odd2  { background-color: #ffcccc; }
tr.even2 { background-color: #ffaaaa; }

tr.odd3  { background-color: #ffe0a0; }
tr.even3 { background-color: #ffefaf; }

.stateOK, .stateUP {
    padding-left: 3px;
    padding-right: 3px;
    border-radius: 2px;
    font-weight: bold;
    background-color: #0b3; color: #ffffff;
}

.stateWARNING {
    padding-left: 3px;
    padding-right: 3px;
    border-radius: 2px;
    font-weight: bold;
    background-color: #ffff00; color: #000000;
}

.stateCRITICAL, .stateDOWN {
    padding-left: 3px;
    padding-right: 3px;
    border-radius: 2px;
    font-weight: bold;
    background-color: #ff0000; color: #ffffff;
}

.stateUNKNOWN, .stateUNREACHABLE {
    padding-left: 3px;
    padding-right: 3px;
    border-radius: 2px;
    font-weight: bold;
    background-color: #ff8800; color: #ffffff;
}

.statePENDING {
    padding-left: 3px;
    padding-right: 3px;
    border-radius: 2px;
    font-weight: bold;
    background-color: #888888; color: #ffffff;
}

.stateDOWNTIME {
    padding-left: 3px;
    padding-right: 3px;
    border-radius: 2px;
    font-weight: bold;
    background-color: #00aaff; color: #ffffff;
}

b.stmarkOK {
    margin-left: 2px;
    padding: 1px 3px;
    border-radius: 4px;
    font-size: 7pt;
    border: 1px solid #666;
    position: relative;
    top: -1px;

    background-color: #0b3; color: #ffffff;
}

b.stmarkWARNING {
    margin-left: 2px;
    padding: 1px 3px;
    border-radius: 4px;
    font-size: 7pt;
    border: 1px solid #666;
    position: relative;
    top: -1px;

    background-color: #ffff00; color: #000000;
}

b.stmarkCRITICAL {
    margin-left: 2px;
    padding: 1px 3px;
    border-radius: 4px;
    font-size: 7pt;
    border: 1px solid #666;
    position: relative;
    top: -1px;

    background-color: #ff0000; color: #ffffff;
}

b.stmarkUNKNOWN {
    margin-left: 2px;
    padding: 1px 3px;
    border-radius: 4px;
    font-size: 7pt;
    border: 1px solid #666;
    position: relative;
    top: -1px;

    background-color: #ff8800; color: #ffffff;
}

td.graphs {
    width: 617px;
    padding: 10px;
}

img {
    margin-right: 10px;
}

img.nofloat {
    display: block;
    margin-bottom: 10px;
}

table.context {
    border-collapse: collapse;
}

table.context td {
    border: 1px solid #888;
    padding: 3px 8px;
}


</style>
</head>
<body>"""
        + html_section
        + "<table>"
    )


TMPL_FOOT_HTML = """</table>
</body>
</html>"""

# Elements to be put into the mail body. Columns:
# 1. Name
# 2. "both": always, possible, "host": only for hosts, or "service": only for service notifications
# 3. True -> always enabled, not configurable, False: optional
# 4. "normal"-> for normal notifications, "alerthandler" -> for alert handler notifications, "all" -> for all types
# 5. Title
# 6. Text template
# 7. HTML template

BODY_ELEMENTS = [
    (
        "hostname",
        "both",
        True,
        "all",
        "Host",
        "$HOSTNAME$ ($HOSTALIAS$)",
        "$LINKEDHOSTNAME$ ($HOSTALIAS$)",
    ),
    ("servicedesc", "service", True, "all", "Service", "$SERVICEDESC$", "$LINKEDSERVICEDESC$"),
    (
        "event",
        "both",
        True,
        "all",
        "Event",
        "$EVENT_TXT$",
        "$EVENT_HTML$",
    ),
    # Elements for both host and service notifications
    (
        "address",
        "both",
        False,
        "all",
        "Address",
        "$HOSTADDRESS$",
        "$HOSTADDRESS$",
    ),
    (
        "abstime",
        "both",
        False,
        "all",
        "Date / Time",
        "$LONGDATETIME$",
        "$LONGDATETIME$",
    ),
    ("omdsite", "both", False, "all", "OMD Site", "$OMD_SITE$", "$OMD_SITE$"),
    ("hosttags", "both", False, "all", "Host Tags", "$HOST_TAGS$", "$HOST_TAGS$"),
    (
        "notesurl",
        "both",
        False,
        "all",
        "Custom Host Notes URL",
        "$HOSTNOTESURL$",
        "$HOSTNOTESURL$",
    ),
    # Elements only for host notifications
    (
        "reltime",
        "host",
        False,
        "all",
        "Relative Time",
        "$LASTHOSTSTATECHANGE_REL$",
        "$LASTHOSTSTATECHANGE_REL$",
    ),
    (
        "output",
        "host",
        True,
        "normal",
        "Summary",
        "$HOSTOUTPUT$",
        "$HOSTOUTPUT_HTML$",
    ),
    (
        "ack_author",
        "host",
        False,
        "normal",
        "Acknowledge Author",
        "$HOSTACKAUTHOR$",
        "$HOSTACKAUTHOR$",
    ),
    (
        "ack_comment",
        "host",
        False,
        "normal",
        "Acknowledge Comment",
        "$HOSTACKCOMMENT$",
        "$HOSTACKCOMMENT$",
    ),
    (
        "perfdata",
        "host",
        False,
        "normal",
        "Metrics",
        "$HOSTPERFDATA$",
        "$HOSTPERFDATA$",
    ),
    # Elements only for service notifications
    (
        "reltime",
        "service",
        False,
        "all",
        "Relative Time",
        "$LASTSERVICESTATECHANGE_REL$",
        "$LASTSERVICESTATECHANGE_REL$",
    ),
    (
        "output",
        "service",
        True,
        "normal",
        "Summary",
        "$SERVICEOUTPUT$",
        "$SERVICEOUTPUT_HTML$",
    ),
    (
        "longoutput",
        "service",
        False,
        "normal",
        "Details",
        "$LONGSERVICEOUTPUT$",
        "$LONGSERVICEOUTPUT_HTML$",
    ),
    (
        "ack_author",
        "service",
        False,
        "normal",
        "Acknowledge Author",
        "$SERVICEACKAUTHOR$",
        "$SERVICEACKAUTHOR$",
    ),
    (
        "ack_comment",
        "service",
        False,
        "normal",
        "Acknowledge Comment",
        "$SERVICEACKCOMMENT$",
        "$SERVICEACKCOMMENT$",
    ),
    (
        "perfdata",
        "service",
        False,
        "normal",
        "Host Metrics",
        "$HOSTPERFDATA$",
        "$HOSTPERFDATA$",
    ),
    (
        "perfdata",
        "service",
        False,
        "normal",
        "Service Metrics",
        "$SERVICEPERFDATA$",
        "$SERVICEPERFDATA$",
    ),
    (
        "notesurl",
        "service",
        False,
        "all",
        "Custom Service Notes URL",
        "$SERVICENOTESURL$",
        "$SERVICENOTESURL$",
    ),
    # Alert handlers
    (
        "alerthandler_name",
        "both",
        True,
        "alerthandler",
        "Name of alert handler",
        "$ALERTHANDLERNAME$",
        "$ALERTHANDLERNAME$",
    ),
    (
        "alerthandler_output",
        "both",
        True,
        "alerthandler",
        "Output of alert handler",
        "$ALERTHANDLEROUTPUT$",
        "$ALERTHANDLEROUTPUT$",
    ),
    # Debugging
    (
        "context",
        "both",
        False,
        "all",
        "Complete variable list",
        "$CONTEXT_ASCII$",
        "$CONTEXT_HTML$",
    ),
]

TMPL_HOST_SUBJECT = "Check_MK: $HOSTNAME$ - $EVENT_TXT$"
TMPL_SERVICE_SUBJECT = "Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$"

opt_debug = "-d" in sys.argv
bulk_mode = "--bulk" in sys.argv


class GraphException(MKException):
    pass


class AttachmentNamedTuple(NamedTuple):
    what: Literal["img"]
    name: str
    contents: Union[bytes, str]
    how: str


# Keeping this for compatibility reasons
AttachmentUnNamedTuple = tuple[str, str, Union[bytes, str], str]
AttachmentTuple = Union[AttachmentNamedTuple, AttachmentUnNamedTuple]
AttachmentList = list[AttachmentTuple]


# TODO: Just use a single EmailContent parameter.
def multipart_mail(
    target: str,
    subject: str,
    from_address: str,
    reply_to: str,
    content_txt: str,
    content_html: str,
    attach: Optional[AttachmentList] = None,
) -> MIMEMultipart:
    if attach is None:
        attach = []

    m = MIMEMultipart("related", _charset="utf-8")

    alt = MIMEMultipart("alternative")

    # The plain text part
    txt = MIMEText(content_txt, "plain", _charset="utf-8")
    alt.attach(txt)

    # The html text part
    html = MIMEText(content_html, "html", _charset="utf-8")
    alt.attach(html)

    m.attach(alt)

    # Add all attachments
    for what, name, contents, how in attach:
        part = (
            MIMEImage(contents, name=name)
            if what == "img"  #
            else MIMEApplication(contents, name=name)
        )
        part.add_header("Content-ID", "<%s>" % name)
        # how must be inline or attachment
        part.add_header("Content-Disposition", how, filename=name)
        m.attach(part)

    return utils.set_mail_headers(target, subject, from_address, reply_to, m)


def send_mail_smtp(  # pylint: disable=too-many-branches
    message: Message, target: str, from_address: str, context: dict[str, str]
) -> int:
    import smtplib  # pylint: disable=import-outside-toplevel

    host_index = 1

    retry_possible = False
    success = False

    while not success:
        host_var = "PARAMETER_SMTP_SMARTHOSTS_%d" % host_index
        if host_var not in context:
            break
        host_index += 1

        smarthost = context[host_var]
        try:
            send_mail_smtp_impl(message, target, smarthost, from_address, context)
            success = True
        except socket.timeout as e:
            sys.stderr.write('timeout connecting to "%s": %s\n' % (smarthost, str(e)))
        except socket.gaierror as e:
            sys.stderr.write('socket error connecting to "%s": %s\n' % (smarthost, str(e)))
        except smtplib.SMTPRecipientsRefused as e:
            # the exception contains a dict of failed recipients to the respective error. since we
            # only have one recipient there has to be exactly one element
            errorcode, err_message = list(e.recipients.values())[0]

            # default is to retry, these errorcodes are known to
            if errorcode not in [
                450,  # sender address domain not found
                550,  # sender address unknown
            ]:
                retry_possible = True

            sys.stderr.write('mail to "%s" refused: %d, %r\n' % (target, errorcode, err_message))
        except smtplib.SMTPHeloError as e:
            retry_possible = True  # server is acting up, this may be fixed quickly
            sys.stderr.write('protocol error from "%s": %s\n' % (smarthost, str(e)))
        except smtplib.SMTPSenderRefused as e:
            sys.stderr.write(
                'server didn\'t accept from-address "%s" refused: %s\n' % (from_address, str(e))
            )
        except smtplib.SMTPAuthenticationError as e:
            sys.stderr.write('authentication failed on "%s": %s\n' % (smarthost, str(e)))
        except smtplib.SMTPDataError as e:
            retry_possible = True  # unexpected error - give retry a chance
            sys.stderr.write('unexpected error code from "%s": %s\n' % (smarthost, str(e)))
        except smtplib.SMTPException as e:
            retry_possible = True  # who knows what went wrong, a retry might just work
            sys.stderr.write('undocumented error code from "%s": %s\n' % (smarthost, str(e)))

    if success:
        return 0
    if retry_possible:
        return 1
    return 2


def send_mail_smtp_impl(
    message: Message, target: str, smarthost: str, from_address: str, context: dict[str, str]
) -> None:
    import smtplib  # pylint: disable=import-outside-toplevel
    import types  # pylint: disable=import-outside-toplevel

    def getreply_wrapper(self: smtplib.SMTP) -> tuple[int, bytes]:
        # We introduce those attributes...
        self.last_code, self.last_repl = smtplib.SMTP.getreply(self)  # type: ignore[attr-defined]
        return self.last_code, self.last_repl  # type: ignore[attr-defined]

    port = int(context["PARAMETER_SMTP_PORT"])

    encryption = context.get("PARAMETER_SMTP_ENCRYPTION", "NONE")

    conn = (
        smtplib.SMTP_SSL(smarthost, port)
        if encryption == "ssl_tls"  #
        else smtplib.SMTP(smarthost, port)
    )

    # TODO: Can we make the hack a bit less evil?
    # evil hack: the smtplib doesn't allow access to the reply code/message
    # in case of success. But we want it!
    conn.last_code = 0  # type: ignore[attr-defined]
    conn.last_repl = ""  # type: ignore[attr-defined]
    conn.getreply = types.MethodType(getreply_wrapper, conn)  # type: ignore[assignment]

    if encryption == "starttls":
        conn.starttls()

    if context.get("PARAMETER_SMTP_AUTH_USER") is not None:
        conn.login(context["PARAMETER_SMTP_AUTH_USER"], context["PARAMETER_SMTP_AUTH_PASSWORD"])

    # this call returns a dictionary with the recipients that failed + the reason, but only
    # if at least one succeeded, otherwise it throws an exception.
    # since we send only one mail per call, we either get an exception or an empty dict.

    # the first parameter here is actually used in the return_path header
    try:
        conn.sendmail(from_address, target.split(","), message.as_string())
        sys.stdout.write(
            "success %d - %s\n" % (conn.last_code, conn.last_repl)  # type: ignore[attr-defined]
        )
    finally:
        conn.quit()


# TODO: Use EmailContent parameter.
def send_mail(message: Message, target: str, from_address: str, context: dict[str, str]) -> int:
    if "PARAMETER_SMTP_PORT" in context:
        return send_mail_smtp(message, target, from_address, context)
    return utils.send_mail_sendmail(message, target, from_address)


def render_cmk_graphs(context: dict[str, str], is_bulk: bool) -> list[bytes]:
    if context["WHAT"] == "HOST":
        svc_desc = "_HOST_"
    else:
        svc_desc = context["SERVICEDESC"]

    url = (
        "http://localhost:%d/%s/check_mk/ajax_graph_images.py?host=%s&service=%s&num_graphs=%s"
        % (
            site.get_apache_port(),
            os.environ["OMD_SITE"],
            quote(context["HOSTNAME"]),
            quote(svc_desc),
            quote(context["PARAMETER_GRAPHS_PER_NOTIFICATION"]),
        )
    )

    try:
        with urlopen(url) as opened_file:
            json_data = opened_file.read()
    except Exception as e:
        if opt_debug:
            raise
        sys.stderr.write("ERROR: Failed to fetch graphs: %s\nURL: %s\n" % (e, url))
        return []

    try:
        base64_strings = json.loads(json_data)
    except Exception as e:
        if opt_debug:
            raise
        sys.stderr.write(
            "ERROR: Failed to decode graphs: %s\nURL: %s\nData: %r\n" % (e, url, json_data)
        )
        return []

    return [base64.b64decode(s) for s in base64_strings]


def render_performance_graphs(context: dict[str, str], is_bulk: bool) -> tuple[AttachmentList, str]:
    graphs = render_cmk_graphs(context, is_bulk)

    attachments: AttachmentList = []
    graph_code = ""
    for source, graph_png in enumerate(graphs):
        if context["WHAT"] == "HOST":
            svc_desc = "_HOST_"
        else:
            svc_desc = context["SERVICEDESC"].replace(" ", "_")
            # replace forbidden windows characters < > ? " : | \ / *
            for token in ["<", ">", "?", '"', ":", "|", "\\", "/", "*"]:
                svc_desc = svc_desc.replace(token, "x%s" % ord(token))

        filename = "%s-%s-%d.png" % (context["HOSTNAME"], svc_desc, source)

        attachments.append(AttachmentNamedTuple("img", filename, graph_png, "inline"))

        cls = ""
        if context.get("PARAMETER_NO_FLOATING_GRAPHS"):
            cls = ' class="nofloat"'
        graph_code += '<img src="cid:%s"%s />' % (filename, cls)

    if graph_code:
        graph_code = (
            "<tr><th colspan=2>Graphs</th></tr>"
            '<tr class="even0"><td colspan=2 class=graphs>%s</td></tr>' % graph_code
        )

    return attachments, graph_code


def construct_content(
    context: dict[str, str], is_bulk: bool = False, notification_number: int = 1
) -> tuple[str, str, AttachmentList]:
    # A list of optional information is configurable via the parameter "elements"
    # (new configuration style)
    # Note: The value PARAMETER_ELEMENTSS is NO TYPO.
    #       Have a look at the function events.py:add_to_event_context(..)
    if "PARAMETER_ELEMENTSS" in context:
        elements = context["PARAMETER_ELEMENTSS"].split()
    else:
        elements = ["perfdata", "graph", "abstime", "address", "longoutput"]

    if is_bulk and "graph" in elements:
        notifications_with_graphs = context["PARAMETER_NOTIFICATIONS_WITH_GRAPHS"]
        if notification_number > int(notifications_with_graphs):
            elements.remove("graph")

    # Prepare the mail contents
    template_txt, template_html = body_templates(
        context["WHAT"].lower(),
        "ALERTHANDLEROUTPUT" in context,
        elements,
        BODY_ELEMENTS,
    )
    content_txt = utils.substitute_context(template_txt, context)
    content_html = utils.substitute_context(template_html, context)

    attachments: AttachmentList = []
    if "graph" in elements and "ALERTHANDLEROUTPUT" not in context:
        # Add Checkmk graphs
        try:
            attachments, graph_code = render_performance_graphs(context, is_bulk)
            content_html += graph_code
        except Exception as e:
            sys.stderr.write("Failed to add graphs to mail. Continue without them. (%s)\n" % e)

    extra_html_section = ""
    if "PARAMETER_INSERT_HTML_SECTION" in context:
        extra_html_section = context["PARAMETER_INSERT_HTML_SECTION"]

    content_html = (
        utils.substitute_context(tmpl_head_html(extra_html_section), context)
        + content_html
        + utils.substitute_context(TMPL_FOOT_HTML, context)
    )

    return content_txt, content_html, attachments


def extend_context(context: dict[str, str]) -> None:
    if context.get("PARAMETER_2"):
        context["PARAMETER_URL_PREFIX"] = context["PARAMETER_2"]

    context["LINKEDHOSTNAME"] = utils.format_link(
        '<a href="%s">%s</a>', utils.host_url_from_context(context), context["HOSTNAME"]
    )
    context["LINKEDSERVICEDESC"] = utils.format_link(
        '<a href="%s">%s</a>',
        utils.service_url_from_context(context),
        context.get("SERVICEDESC", ""),
    )

    event_template_txt, event_template_html = event_templates(context["NOTIFICATIONTYPE"])

    context["EVENT_TXT"] = utils.substitute_context(
        event_template_txt.replace("@", context["WHAT"]), context
    )
    context["EVENT_HTML"] = utils.substitute_context(
        event_template_html.replace("@", context["WHAT"]), context
    )

    if "HOSTOUTPUT" in context:
        context["HOSTOUTPUT_HTML"] = utils.format_plugin_output(context["HOSTOUTPUT"])
    if context["WHAT"] == "SERVICE":
        context["SERVICEOUTPUT_HTML"] = utils.format_plugin_output(context["SERVICEOUTPUT"])

        long_serviceoutput = (
            context["LONGSERVICEOUTPUT"].replace("\\n", "<br>").replace("\n", "<br>")
        )
        context["LONGSERVICEOUTPUT_HTML"] = utils.format_plugin_output(long_serviceoutput)

    # Compute the subject of the mail
    if context["WHAT"] == "HOST":
        tmpl = context.get("PARAMETER_HOST_SUBJECT") or TMPL_HOST_SUBJECT
        context["SUBJECT"] = utils.substitute_context(tmpl, context)
    else:
        tmpl = context.get("PARAMETER_SERVICE_SUBJECT") or TMPL_SERVICE_SUBJECT
        context["SUBJECT"] = utils.substitute_context(tmpl, context)


def event_templates(notification_type: str) -> tuple[str, str]:
    # Returns an event summary
    if notification_type in ["PROBLEM", "RECOVERY"]:
        return (
            "$PREVIOUS@HARDSHORTSTATE$ -> $@SHORTSTATE$",
            '<span class="state$PREVIOUS@HARDSTATE$">$PREVIOUS@HARDSTATE$</span> &rarr; <span class="state$@STATE$">$@STATE$</span>',
        )
    if notification_type == "FLAPPINGSTART":
        return "Started Flapping", "Started Flapping"
    if notification_type == "FLAPPINGSTOP":
        return (
            "Stopped Flapping ($@SHORTSTATE$)",
            'Stopped Flapping (while <span class="state$@STATE$">$@STATE$</span>)',
        )
    if notification_type == "FLAPPINGDISABLED":
        return (
            "Disabled Flapping ($@SHORTSTATE$)",
            'Disabled Flapping (while <span class="state$@STATE$">$@STATE$</span>)',
        )
    if notification_type == "DOWNTIMESTART":
        return (
            "Downtime Start ($@SHORTSTATE$)",
            'Downtime Start (while <span class="state$@STATE$">$@STATE$</span>)',
        )
    if notification_type == "DOWNTIMEEND":
        return (
            "Downtime End ($@SHORTSTATE$)",
            'Downtime End (while <span class="state$@STATE$">$@STATE$</span>)',
        )
    if notification_type == "DOWNTIMECANCELLED":
        return (
            "Downtime Cancelled ($@SHORTSTATE$)",
            'Downtime Cancelled (while <span class="state$@STATE$">$@STATE$</span>)',
        )
    if notification_type == "ACKNOWLEDGEMENT":
        return (
            "Acknowledged ($@SHORTSTATE$)",
            'Acknowledged (while <span class="state$@STATE$">$@STATE$</span>)',
        )
    if notification_type == "CUSTOM":
        return (
            "Custom Notification ($@SHORTSTATE$)",
            'Custom Notification (while <span class="state$@STATE$">$@STATE$</span>)',
        )
    if notification_type.startswith("ALERTHANDLER"):
        # The notification_type here is "ALERTHANDLER (exit_code)"
        return notification_type, notification_type
    return notification_type, notification_type


def body_templates(
    what: str,
    is_alert_handler: bool,
    elements: list[str],
    body_elements: list[tuple[str, str, bool, str, str, str, str]],
) -> tuple[str, str]:
    even = "even"
    tmpl_txt: List[str] = []
    tmpl_html: List[str] = []
    for name, whence, forced, nottype, title, txt, html in body_elements:
        if nottype == "alerthandler" and not is_alert_handler:
            continue

        if nottype not in ("alerthandler", "all") and is_alert_handler:
            continue

        if (whence in ("both", what)) and (forced or (name in elements)):
            tmpl_txt += "%-20s %s\n" % (title + ":", txt)
            tmpl_html += '<tr class="%s0"><td class=left>%s</td><td>%s</td></tr>' % (
                even,
                title,
                html,
            )
            even = "odd" if even == "even" else "even"

    return "".join(tmpl_txt), "".join(tmpl_html)


# TODO: NamedTuple?
class EmailContent:
    def __init__(
        self,
        context: dict[str, str],
        mailto: str,
        subject: str,
        from_address: str,
        reply_to: str,
        content_txt: str,
        content_html: str,
        attachments: AttachmentList,
    ) -> None:
        self.context = context
        self.mailto = mailto
        self.subject = subject
        self.from_address = from_address
        self.reply_to = reply_to
        self.content_txt = content_txt
        self.content_html = content_html
        self.attachments = attachments


class BulkEmailContent(EmailContent):
    def __init__(
        self, context_function: Callable[[], tuple[dict[str, str], list[dict[str, str]]]]
    ) -> None:
        attachments = []
        content_txt = ""
        content_html = ""
        parameters, contexts = context_function()
        hosts = set([])

        for i, c in enumerate(contexts, 1):
            c.update(parameters)
            escaped_context = utils.html_escape_context(c)
            extend_context(escaped_context)

            txt, html, att = construct_content(escaped_context, is_bulk=True, notification_number=i)
            content_txt += txt
            content_html += html
            attachments += att
            hosts.add(c["HOSTNAME"])

        # TODO: cleanup duplicate code with SingleEmailContent
        # TODO: the context is only needed because of SMPT settings used in send_mail
        super().__init__(
            context=escaped_context,
            # Assume the same in each context
            mailto=escaped_context["CONTACTEMAIL"],
            # Use the single context subject in case there is only one context in the bulk
            subject=(
                utils.get_bulk_notification_subject(contexts, hosts)
                if len(contexts) > 1
                else escaped_context["SUBJECT"]
            ),
            from_address=utils.format_address(
                escaped_context.get("PARAMETER_FROM_DISPLAY_NAME", ""),
                # TODO: Correct context parameter???
                escaped_context.get("PARAMETER_FROM_ADDRESS", utils.default_from_address()),
            ),
            reply_to=utils.format_address(
                escaped_context.get("PARAMETER_REPLY_TO_DISPLAY_NAME", ""),
                escaped_context.get("PARAMETER_REPLY_TO", ""),
            ),
            content_txt=content_txt,
            content_html=content_html,
            attachments=attachments,
        )


class SingleEmailContent(EmailContent):
    def __init__(self, context_function: Callable[[], dict[str, str]]) -> None:
        # gather all options from env
        context = context_function()
        escaped_context = utils.html_escape_context(context)
        extend_context(escaped_context)
        content_txt, content_html, attachments = construct_content(escaped_context)

        # TODO: cleanup duplicate code with BulkEmailContent
        # TODO: the context is only needed because of SMPT settings used in send_mail
        super().__init__(
            context=escaped_context,
            mailto=escaped_context["CONTACTEMAIL"],
            subject=escaped_context["SUBJECT"],
            from_address=utils.format_address(
                escaped_context.get("PARAMETER_FROM_DISPLAY_NAME", ""),
                escaped_context.get("PARAMETER_FROM_ADDRESS", utils.default_from_address()),
            ),
            reply_to=utils.format_address(
                escaped_context.get("PARAMETER_REPLY_TO_DISPLAY_NAME", ""),
                escaped_context.get("PARAMETER_REPLY_TO_ADDRESS", ""),
            ),
            content_txt=content_txt,
            content_html=content_html,
            attachments=attachments,
        )


def main() -> NoReturn:
    content = (
        BulkEmailContent(utils.read_bulk_contexts)
        if bulk_mode
        else SingleEmailContent(utils.collect_context)
    )

    if not content.mailto:  # e.g. empty field in user database
        sys.stderr.write("Cannot send HTML email: empty destination email address\n")
        sys.exit(2)

    m = multipart_mail(
        content.mailto,
        content.subject,
        content.from_address,
        content.reply_to,
        content.content_txt,
        content.content_html,
        content.attachments,
    )

    try:
        sys.exit(
            send_mail(
                m,
                content.mailto,
                content.from_address,
                content.context,
            )
        )
    except Exception as e:
        sys.stderr.write("Unhandled exception: %s\n" % e)
        # unhandled exception, don't retry this...
        sys.exit(2)
