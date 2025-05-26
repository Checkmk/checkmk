#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Argument 1: Full system path to the pnp4nagios index.php for fetching the graphs. Usually auto configured in OMD.
# Argument 2: HTTP-URL-Prefix to open Multisite. When provided, several links are added to the mail.
#             Example: http://myserv01/prod
#
# This script creates a nifty HTML email in multipart format with
# attached graphs and such neat stuff. Sweet!

import socket
import sys
from collections.abc import Callable, Sequence
from email.message import Message
from typing import NoReturn

from jinja2 import Environment, FileSystemLoader

from cmk.ccc.exceptions import MKException

from cmk.utils.escaping import escape_permissive
from cmk.utils.mail import (
    Attachment,
    default_from_address,
    MailString,
    multipart_mail,
    send_mail_sendmail,
)
from cmk.utils.paths import omd_root, web_dir

from cmk.notification_plugins import utils
from cmk.notification_plugins.utils import get_password_from_env_or_context, render_cmk_graphs

# Elements to be put into the mail body. Columns:
# 1. Name
# 2. "both": always, possible, "host": only for hosts, or "service": only for service notifications
# 3. True -> always enabled, not configurable, False: optional
# 4. "normal"-> for normal notifications, "alerthandler" -> for alert handler notifications, "all" -> for all types
# 5. Title
# 6. Text template

BODY_ELEMENTS = [
    (
        "hostname",
        "both",
        True,
        "all",
        "Host",
        "$HOSTNAME_AND_ALIAS_TXT$",
    ),
    (
        "servicedesc",
        "service",
        True,
        "all",
        "Service",
        "$SERVICEDESC$",
    ),
    (
        "event",
        "both",
        True,
        "all",
        "Event",
        "$EVENT_TXT$",
    ),
    # Elements for both host and service notifications
    (
        "address",
        "both",
        False,
        "all",
        "Address",
        "$HOSTADDRESS$",
    ),
    (
        "abstime",
        "both",
        False,
        "all",
        "Time",
        "$LONGDATETIME$",
    ),
    (
        "omdsite",
        "both",
        False,
        "all",
        "Site",
        "$OMD_SITE$",
    ),
    (
        "hosttags",
        "both",
        False,
        "all",
        "Host tags",
        "$HOST_TAGS$",
    ),
    (
        "notification_author",
        "both",
        False,
        "all",
        "Notification author",
        "$NOTIFICATIONAUTHOR$",
    ),
    (
        "notification_comment",
        "both",
        False,
        "all",
        "Notification comment",
        "$NOTIFICATIONCOMMENT$",
    ),
    (
        "notesurl",
        "both",
        False,
        "all",
        "Custom host notes URL",
        "$HOSTNOTESURL$",
    ),
    # Elements only for host notifications
    (
        "reltime",
        "host",
        False,
        "all",
        "Relative time",
        "$LASTHOSTSTATECHANGE_REL$",
    ),
    (
        "output",
        "host",
        True,
        "normal",
        "Summary",
        "$HOSTOUTPUT$",
    ),
    (
        "ack_author",
        "host",
        False,
        "normal",
        "Acknowledge author",
        "$HOSTACKAUTHOR$",
    ),
    (
        "ack_comment",
        "host",
        False,
        "normal",
        "Acknowledge comment",
        "$HOSTACKCOMMENT$",
    ),
    (
        "perfdata",
        "host",
        False,
        "normal",
        "Metrics",
        "$HOSTPERFDATA$",
    ),
    # Elements only for service notifications
    (
        "reltime",
        "service",
        False,
        "all",
        "Relative time",
        "$LASTSERVICESTATECHANGE_REL$",
    ),
    (
        "output",
        "service",
        True,
        "normal",
        "Summary",
        "$SERVICEOUTPUT$",
    ),
    (
        "longoutput",
        "service",
        False,
        "normal",
        "Details",
        "$LONGSERVICEOUTPUT$",
    ),
    (
        "ack_author",
        "service",
        False,
        "normal",
        "Acknowledge author",
        "$SERVICEACKAUTHOR$",
    ),
    (
        "ack_comment",
        "service",
        False,
        "normal",
        "Acknowledge comment",
        "$SERVICEACKCOMMENT$",
    ),
    (
        "perfdata",
        "service",
        False,
        "normal",
        "Host metrics",
        "$HOSTPERFDATA$",
    ),
    (
        "perfdata",
        "service",
        False,
        "normal",
        "Service metrics",
        "$SERVICEPERFDATA$",
    ),
    (
        "notesurl",
        "service",
        False,
        "all",
        "Custom service notes URL",
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
    ),
    (
        "alerthandler_output",
        "both",
        True,
        "alerthandler",
        "Output of alert handler",
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
    ),
]

TMPL_HOST_SUBJECT = "Checkmk: $HOSTNAME$ - $EVENT_TXT$"
TMPL_SERVICE_SUBJECT = "Checkmk: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$"

opt_debug = "-d" in sys.argv
bulk_mode = "--bulk" in sys.argv


class GraphException(MKException):
    pass


class TemplateRenderer:
    def __init__(self) -> None:
        self.env = Environment(
            loader=FileSystemLoader(omd_root / "share/check_mk/notifications/templates/mail"),
            autoescape=True,
        )

    def render_template(self, template_file: str, data: dict[str, object]) -> str:
        template = self.env.get_template(template_file)
        return template.render(data)


def send_mail_smtp(
    message: Message, target: MailString, from_address: MailString, context: dict[str, str]
) -> int:
    import smtplib

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
            send_mail_smtp_impl(message, target, MailString(smarthost), from_address, context)
            success = True
        except TimeoutError as e:
            sys.stderr.write(f'timeout connecting to "{smarthost}": {str(e)}\n')
        except socket.gaierror as e:
            sys.stderr.write(f'socket error connecting to "{smarthost}": {str(e)}\n')
        except smtplib.SMTPRecipientsRefused as e:
            # the exception contains a dict of failed recipients to the respective error. since we
            # only have one recipient there has to be exactly one element
            errorcode, err_message = list(e.recipients.values())[0]

            # default is to retry, these errorcodes are known to
            if errorcode not in [
                450,  # sender address domain not found
                550,  # sender address unknown
                554,  # "Transaction failed" / "Message rejected"
            ]:
                retry_possible = True

            sys.stderr.write(
                'mail from %s" to "%s" refused: %d, %r\n'
                % (
                    from_address,
                    target,
                    errorcode,
                    err_message,
                )
            )
        except smtplib.SMTPHeloError as e:
            retry_possible = True  # server is acting up, this may be fixed quickly
            sys.stderr.write(
                f'protocol error from "{smarthost}": {_ensure_str_error_message(e.smtp_error)}\n'
            )
        except smtplib.SMTPSenderRefused as e:
            sys.stderr.write(
                f'server didn\'t accept from-address "{from_address}" refused: {_ensure_str_error_message(e.smtp_error)}\n'
            )
        except smtplib.SMTPAuthenticationError as e:
            sys.stderr.write(
                f'authentication failed on "{smarthost}": {_ensure_str_error_message(e.smtp_error)}\n'
            )
        except smtplib.SMTPDataError as e:
            retry_possible = True  # unexpected error - give retry a chance
            sys.stderr.write(
                f'unexpected error code from "{smarthost}": {_ensure_str_error_message(e.smtp_error)}\n'
            )
        except smtplib.SMTPException as e:
            retry_possible = True  # who knows what went wrong, a retry might just work
            sys.stderr.write(f'undocumented error code from "{smarthost}": {str(e)}\n')

    if success:
        return 0
    if retry_possible:
        return 1
    return 2


def _ensure_str_error_message(message: bytes | str) -> str:
    return message.decode("utf-8") if isinstance(message, bytes) else message


def send_mail_smtp_impl(
    message: Message,
    target: MailString,
    smarthost: MailString,
    from_address: MailString,
    context: dict[str, str],
) -> None:
    import smtplib
    import types

    def getreply_wrapper(self: smtplib.SMTP) -> tuple[int, bytes]:
        # We introduce those attributes...
        self.last_code, self.last_repl = smtplib.SMTP.getreply(self)  # type: ignore[attr-defined]
        return self.last_code, self.last_repl  # type: ignore[attr-defined]

    port = int(context["PARAMETER_SMTP_PORT"])

    encryption = context.get("PARAMETER_SMTP_ENCRYPTION", "NONE")

    conn = (
        smtplib.SMTP_SSL(smarthost, port)
        if encryption == "ssl_tls"
        else smtplib.SMTP(smarthost, port)
    )

    # TODO: Can we make the hack a bit less evil?
    # evil hack: the smtplib doesn't allow access to the reply code/message
    # in case of success. But we want it!
    conn.last_code = 0  # type: ignore[attr-defined]
    conn.last_repl = ""  # type: ignore[attr-defined]
    conn.getreply = types.MethodType(getreply_wrapper, conn)  # type: ignore[method-assign]

    if encryption == "starttls":
        conn.starttls()

    if context.get("PARAMETER_SMTP_AUTH_USER") is not None:
        conn.login(
            context["PARAMETER_SMTP_AUTH_USER"],
            get_password_from_env_or_context(
                key="PARAMETER_SMTP_AUTH_PASSWORD",
                context=context,
            ),
        )

    # this call returns a dictionary with the recipients that failed + the reason, but only
    # if at least one succeeded, otherwise it throws an exception.
    # since we send only one mail per call, we either get an exception or an empty dict.

    # the first parameter here is actually used in the return_path header
    try:
        conn.sendmail(from_address, target.split(","), message.as_string())
        sys.stdout.write(
            "success %d - %s\n" % (conn.last_code, _ensure_str_error_message(conn.last_repl))  # type: ignore[attr-defined]
        )
    finally:
        conn.quit()


# TODO: Use EmailContent parameter.
def send_mail(message: Message, target: str, from_address: str, context: dict[str, str]) -> int:
    if "PARAMETER_SMTP_PORT" in context:
        return send_mail_smtp(message, MailString(target), MailString(from_address), context)
    send_mail_sendmail(message, MailString(target), MailString(from_address))
    sys.stdout.write("Spooled mail to local mail transmission agent\n")
    return 0


def render_performance_graphs(
    context: dict[str, str],
) -> tuple[list[Attachment], list[str]]:
    attachments: list[Attachment] = []
    file_names = []
    for graph in render_cmk_graphs(context):
        attachments.append(Attachment("img", graph.filename, graph.data, "inline"))

        file_names.append(graph.filename)

    return attachments, file_names


def construct_content(
    context: dict[str, str],
    is_bulk: bool = False,
    bulk_summary: list[dict[str, str]] | None = None,
    last_bulk_entry: bool = False,
    notification_number: int = 1,
) -> tuple[str, str, list[Attachment]]:
    # A list of optional information is configurable via the parameter "elements"
    # (new configuration style)
    # Note: The value PARAMETER_ELEMENTSS is NO TYPO.
    #       Have a look at the function events.py:add_to_event_context(..)
    if "PARAMETER_ELEMENTSS" in context:
        elements = context["PARAMETER_ELEMENTSS"].split()
    else:
        elements = ["graph", "abstime", "address", "longoutput"]

    if is_bulk and "graph" in elements:
        notifications_with_graphs = context["PARAMETER_NOTIFICATIONS_WITH_GRAPHS"]
        if notification_number > int(notifications_with_graphs):
            elements.remove("graph")

    # Prepare the text mail content
    template_txt = body_templates(
        context["WHAT"].lower(),
        "ALERTHANDLEROUTPUT" in context,
        elements,
        BODY_ELEMENTS,
    )
    content_txt = utils.substitute_context(template_txt, context)

    attachments: list[Attachment] = []
    file_names: list[str] = []
    if "graph" in elements and "ALERTHANDLEROUTPUT" not in context:
        # Add Checkmk graphs
        try:
            attachments, file_names = render_performance_graphs(context)
        except Exception as e:
            sys.stderr.write("Failed to add graphs to mail. Continue without them. (%s)\n" % e)

    content_html = utils.substitute_context(
        TemplateRenderer().render_template(
            "base.html",
            {
                "data": context,
                "graphs": file_names,
                "insert": escape_permissive(context.get("PARAMETER_INSERT_HTML_SECTION", "")),
                "is_bulk": is_bulk,
                "bulk_summary": bulk_summary,
                "last_bulk_entry": last_bulk_entry,
            },
        ),
        context,
    )

    return (
        content_txt,
        content_html,
        attachments,
    )


def extend_context(context: dict[str, str], is_bulk: bool = False) -> None:
    context["LINKEDHOSTNAME"] = utils.format_link(
        '<a href="%s" style="color:#000000">%s</a>',
        utils.host_url_from_context(context),
        context["HOSTNAME"],
    )
    context["LINKEDSERVICEDESC"] = utils.format_link(
        '<a href="%s" style="color:#000000">%s</a>',
        utils.service_url_from_context(context),
        context.get("SERVICEDESC", ""),
    )

    # For "Additional details", graph is a default
    if "graph" in context.get("PARAMETER_ELEMENTSS", "graph").split():
        context["GRAPH_URL"] = utils.graph_url_from_context(context)

    if is_bulk:
        context["EVENTHISTORYURL"] = utils.eventhistory_url_from_context(context)

    if context["HOSTALIAS"] and context["HOSTNAME"] != context["HOSTALIAS"]:
        context["HOSTNAME_AND_ALIAS_TXT"] = "$HOSTNAME$ ($HOSTALIAS$)"
        context["HOSTNAME_AND_ALIAS_HTML"] = "$LINKEDHOSTNAME$ ($HOSTALIAS$)"
    else:
        context["HOSTNAME_AND_ALIAS_TXT"] = "$HOSTNAME$"
        context["HOSTNAME_AND_ALIAS_HTML"] = "$LINKEDHOSTNAME$"

    event_template_txt = txt_event_template(context["NOTIFICATIONTYPE"])

    context["EVENT_TXT"] = utils.substitute_context(
        event_template_txt.replace("@", context["WHAT"]), context
    )

    if "HOSTOUTPUT" in context:
        context["HOSTOUTPUT_HTML"] = context["HOSTOUTPUT"]

    if context["WHAT"] == "SERVICE":
        context["SERVICEOUTPUT_HTML"] = context["SERVICEOUTPUT"]

        long_serviceoutput = (
            context["LONGSERVICEOUTPUT"].replace("\\n", "<br>").replace("\n", "<br>")
        )
        context["LONGSERVICEOUTPUT_HTML"] = long_serviceoutput

    # Compute the subject of the mail
    if context["WHAT"] == "HOST":
        tmpl = context.get("PARAMETER_HOST_SUBJECT") or TMPL_HOST_SUBJECT
        context["SUBJECT"] = utils.substitute_context(tmpl, context)
    else:
        tmpl = context.get("PARAMETER_SERVICE_SUBJECT") or TMPL_SERVICE_SUBJECT
        context["SUBJECT"] = utils.substitute_context(tmpl, context)


def txt_event_template(notification_type: str) -> str:
    # Returns an event summary
    if notification_type in ["PROBLEM", "RECOVERY"]:
        return "$PREVIOUS@HARDSHORTSTATE$ -> $@SHORTSTATE$"
    if notification_type == "FLAPPINGSTART":
        return "Started Flapping"
    if notification_type == "FLAPPINGSTOP":
        return "Stopped Flapping ($@SHORTSTATE$)"
    if notification_type == "FLAPPINGDISABLED":
        return "Disabled Flapping ($@SHORTSTATE$)"
    if notification_type == "DOWNTIMESTART":
        return "Downtime Start ($@SHORTSTATE$)"
    if notification_type == "DOWNTIMEEND":
        return "Downtime End ($@SHORTSTATE$)"
    if notification_type == "DOWNTIMECANCELLED":
        return "Downtime Cancelled ($@SHORTSTATE$)"
    if notification_type == "ACKNOWLEDGEMENT":
        return "Acknowledged ($@SHORTSTATE$)"
    if notification_type == "CUSTOM":
        return "Custom Notification ($@SHORTSTATE$)"
    if notification_type.startswith("ALERTHANDLER"):
        # The notification_type here is "ALERTHANDLER (exit_code)"
        return notification_type
    return notification_type


def body_templates(
    what: str,
    is_alert_handler: bool,
    elements: list[str],
    body_elements: list[tuple[str, str, bool, str, str, str]],
) -> str:
    tmpl_txt: list[str] = []
    for name, whence, forced, nottype, title, txt in body_elements:
        if nottype == "alerthandler" and not is_alert_handler:
            continue

        if nottype not in ("alerthandler", "all") and is_alert_handler:
            continue

        if (whence in ("both", what)) and (forced or (name in elements)):
            tmpl_txt += "%-20s %s\n" % (title + ":", txt)

    return "".join(tmpl_txt)


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
        attachments: Sequence[Attachment],
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
        hosts = set()

        all_contexts_updated: list[dict[str, str]] = []
        for single_context in contexts:
            single_context.update(parameters)
            escaped_context = utils.html_escape_context(single_context)
            extend_context(escaped_context, is_bulk=True)
            all_contexts_updated.append(escaped_context)

        for i, c in enumerate(all_contexts_updated, 1):
            txt, html, att = construct_content(
                c,
                is_bulk=True,
                bulk_summary=all_contexts_updated if i == 1 else None,
                last_bulk_entry=i == len(all_contexts_updated),
                notification_number=i,
            )
            content_txt += txt
            content_html += html
            attachments += att
            hosts.add(c["HOSTNAME"])

        attachments = _add_template_attachments(escaped_context, attachments)

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
                escaped_context.get("PARAMETER_FROM_ADDRESS", default_from_address()),
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

        attachments = _add_template_attachments(context, attachments)

        # TODO: cleanup duplicate code with BulkEmailContent
        # TODO: the context is only needed because of SMPT settings used in send_mail
        super().__init__(
            context=escaped_context,
            mailto=escaped_context["CONTACTEMAIL"],
            subject=escaped_context["SUBJECT"],
            from_address=utils.format_address(
                escaped_context.get("PARAMETER_FROM_DISPLAY_NAME", ""),
                escaped_context.get("PARAMETER_FROM_ADDRESS", default_from_address()),
            ),
            reply_to=utils.format_address(
                escaped_context.get("PARAMETER_REPLY_TO_DISPLAY_NAME", ""),
                escaped_context.get("PARAMETER_REPLY_TO_ADDRESS", ""),
            ),
            content_txt=content_txt,
            content_html=content_html,
            attachments=attachments,
        )


def _add_template_attachments(
    context: dict[str, str],
    attachments: list[Attachment],
) -> list[Attachment]:
    # always needed
    for icon in [
        "checkmk_logo.png",
        "overview.png",
    ]:
        attachments.append(attach_file(icon=icon))

    if context.get("PARAMETER_CONTACT_GROUPS"):
        attachments.append(attach_file(icon="contact_groups.png"))
    if elements := context.get("PARAMETER_ELEMENTSS", "graph abstime longoutput").split():
        if "graph" in elements:
            attachments.append(attach_file(icon="graph.png"))
            elements.remove("graph")
        if elements:
            attachments.append(attach_file(icon="additional.png"))
    if context.get("PARAMETER_SVC_LABELS") or context.get("PARAMETER_HOST_LABELS"):
        attachments.append(attach_file(icon="label.png"))
    if context.get("PARAMETER_HOST_TAGS"):
        attachments.append(attach_file(icon="vector.png"))

    return attachments


def attach_file(icon: str) -> Attachment:
    with open(web_dir / f"htdocs/images/icons/{icon}", "rb") as file:
        return Attachment(what="img", name=icon, contents=file.read(), how="inline")


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
