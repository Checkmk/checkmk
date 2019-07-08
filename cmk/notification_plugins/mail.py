# -*- coding: utf-8 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

# Argument 1: Full system path to the pnp4nagios index.php for fetching the graphs. Usually auto configured in OMD.
# Argument 2: HTTP-URL-Prefix to open Multisite. When provided, several links are added to the mail.
#             Example: http://myserv01/prod
#
# This script creates a nifty HTML email in multipart format with
# attached graphs and such neat stuff. Sweet!

import base64
import os
import socket
import sys
import subprocess
import urllib
import urllib2
import json
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from cmk.notification_plugins import utils
import cmk.utils.site as site


def tmpl_head_html(html_section):
    return '''
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
<body>''' + html_section + '<table>'


tmpl_foot_html = '''</table>
</body>
</html>'''

# Elements to be put into the mail body. Columns:
# 1. Name
# 2. "both": always, possible, "host": only for hosts, or "service": only for service notifications
# 3. True -> always enabled, not configurable, False: optional
# 4. "normal"-> for normal notifications, "alerthandler" -> for alert handler notifications, "all" -> for all types
# 5. Title
# 6. Text template
# 7. HTML template

body_elements = [
    ("hostname", "both", True, "all", "Host", "$HOSTNAME$ ($HOSTALIAS$)",
     "$LINKEDHOSTNAME$ ($HOSTALIAS$)"),
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
        "Plugin Output",
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
        "Plugin Output",
        "$SERVICEOUTPUT$",
        "$SERVICEOUTPUT_HTML$",
    ),
    (
        "longoutput",
        "service",
        False,
        "normal",
        "Additional Output",
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

tmpl_host_subject = 'Check_MK: $HOSTNAME$ - $EVENT_TXT$'
tmpl_service_subject = 'Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$'

opt_debug = '-d' in sys.argv
bulk_mode = '--bulk' in sys.argv


class GraphException(Exception):
    pass


def multipart_mail(target, subject, from_address, reply_to, content_txt, content_html, attach=None):
    if attach is None:
        attach = []

    m = MIMEMultipart('related', _charset='utf-8')

    alt = MIMEMultipart('alternative')

    # The plain text part
    txt = MIMEText(content_txt, 'plain', _charset='utf-8')
    alt.attach(txt)

    # The html text part
    html = MIMEText(content_html, 'html', _charset='utf-8')
    alt.attach(html)

    m.attach(alt)

    # Add all attachments
    for what, name, contents, how in attach:
        if what == 'img':
            part = MIMEImage(contents, name=name)
        else:
            part = MIMEApplication(contents, name=name)

        part.add_header('Content-ID', '<%s>' % name)
        # how must be inline or attachment
        part.add_header('Content-Disposition', how, filename=name)
        m.attach(part)

    return utils.set_mail_headers(target, subject, from_address, reply_to, m)


def send_mail_smtp(message, target, from_address, context):
    import smtplib  # for the error messages
    host_index = 1

    retry_possible = False
    success = False

    while not success:
        host_var = 'PARAMETER_SMTP_SMARTHOSTS_%d' % host_index
        if host_var not in context:
            break
        else:
            host_index += 1

        smarthost = context[host_var]
        try:
            send_mail_smtp_impl(message, target, smarthost, from_address, context)
            success = True
        except socket.timeout as e:
            sys.stderr.write("timeout connecting to \"%s\": %s\n" % (smarthost, str(e)))
        except socket.gaierror as e:
            sys.stderr.write("socket error connecting to \"%s\": %s\n" % (smarthost, str(e)))
        except smtplib.SMTPRecipientsRefused as e:
            # the exception contains a dict of failed recipients to the respective error. since we
            # only have one recipient there has to be exactly one element
            errorcode, message = e.recipients.values()[0]

            # default is to retry, these errorcodes are known to
            if errorcode not in [
                    450,  # sender address domain not found
                    550,  # sender address unknown
            ]:
                retry_possible = True

            sys.stderr.write("mail to \"%s\" refused: %d, %s\n" % (target, errorcode, message))
        except smtplib.SMTPHeloError as e:
            retry_possible = True  # server is acting up, this may be fixed quickly
            sys.stderr.write("protocol error from \"%s\": %s\n" % (smarthost, str(e)))
        except smtplib.SMTPSenderRefused as e:
            sys.stderr.write("server didn't accept from-address \"%s\" refused: %s\n" %\
                             (from_address, str(e)))
        except smtplib.SMTPAuthenticationError as e:
            sys.stderr.write("authentication failed on \"%s\": %s\n" % (smarthost, str(e)))
        except smtplib.SMTPDataError as e:
            retry_possible = True  # unexpected error - give retry a chance
            sys.stderr.write("unexpected error code from \"%s\": %s\n" % (smarthost, str(e)))
        except smtplib.SMTPException as e:
            retry_possible = True  # who knows what went wrong, a retry might just work
            sys.stderr.write("undocumented error code from \"%s\": %s\n" % (smarthost, str(e)))

    if success:
        return 0
    elif retry_possible:
        return 1
    return 2


def default_from_address():
    return os.environ.get("OMD_SITE", "checkmk") + "@" + socket.getfqdn()


def send_mail_smtp_impl(message, target, smarthost, from_address, context):
    import smtplib
    import types

    def getreply_wrapper(self):
        self.last_code, self.last_repl = smtplib.SMTP.getreply(self)
        return self.last_code, self.last_repl

    port = int(context['PARAMETER_SMTP_PORT'])

    encryption = context.get('PARAMETER_SMTP_ENCRYPTION', "NONE")

    if encryption == "SSL_TLS":
        conn = smtplib.SMTP_SSL(smarthost, port)  # , from_address)
    else:
        conn = smtplib.SMTP(smarthost, port)  # , from_address)

    # evil hack: the smtplib doesn't allow access to the reply code/message
    #  in case of success. But we want it!
    conn.last_code = 0
    conn.last_repl = ""
    conn.getreply = types.MethodType(getreply_wrapper, conn)

    if encryption == "STARTTLS":
        conn.starttls()

    if context.get('PARAMETER_SMTP_AUTH_USER') is not None:
        conn.login(context['PARAMETER_SMTP_AUTH_USER'], context['PARAMETER_SMTP_AUTH_PASSWORD'])

    # this call returns a dictionary with the recipients that failed + the reason, but only
    # if at least one succeeded, otherwise it throws an exception.
    # since we send only one mail per call, we either get an exception or an empty dict.

    # the first parameter here is actually used in the return_path header
    try:
        conn.sendmail(from_address, target.split(','), message.as_string())
        sys.stdout.write("success %d - %s\n" % (conn.last_code, conn.last_repl))
    finally:
        conn.quit()


def send_mail(message, target, from_address, context):
    if "PARAMETER_SMTP_PORT" in context:
        return send_mail_smtp(message, target, from_address, context)
    return utils.send_mail_sendmail(message, target, from_address)


def fetch_pnp_data(context, params):
    path = "%s/share/pnp4nagios/htdocs/index.php" % context['OMD_ROOT'].encode('utf-8')
    php_save_path = "-d session.save_path=%s/tmp/php/session" % context['OMD_ROOT'].encode('utf-8')
    env = {
        'REMOTE_USER': "check-mk",
        "SKIP_AUTHORIZATION": "1",
    }

    if not os.path.exists(path):
        raise GraphException('Unable to locate pnp4nagios index.php (%s)' % path)

    return subprocess.check_output(["php", php_save_path, path, params], env=env)


def fetch_num_sources(context):
    svc_desc = '_HOST_' if context['WHAT'] == 'HOST' else context['SERVICEDESC']
    infos = fetch_pnp_data(
        context, '/json?host=%s&srv=%s&view=0' %
        (context['HOSTNAME'].encode('utf-8'), svc_desc.encode('utf-8')))
    if not infos.startswith('[{'):
        raise GraphException('Unable to fetch graph infos: %s' % extract_graph_error(infos))

    return infos.count('source=')


def fetch_graph(context, source, view=1):
    svc_desc = '_HOST_' if context['WHAT'] == 'HOST' else context['SERVICEDESC']
    graph = fetch_pnp_data(
        context, '/image?host=%s&srv=%s&view=%d&source=%d' %
        (context['HOSTNAME'], svc_desc.encode('utf-8'), view, source))

    if graph[:8] != '\x89PNG\r\n\x1a\n':
        raise GraphException('Unable to fetch the graph: %s' % extract_graph_error(graph))

    return graph


def extract_graph_error(output):
    lines = output.splitlines()
    for nr, line in enumerate(lines):
        if "Please check the documentation for information about the following error" in line:
            return lines[nr + 1]
    return output


# Fetch graphs for this object. It first tries to detect how many sources
# are available for this object. Then it loops through all sources and
# fetches retrieves the images. If a problem occurs, it is printed to
# stderr (-> notify.log) and the graph is not added to the mail.
def render_pnp_graphs(context):
    try:
        num_sources = fetch_num_sources(context)
    except GraphException as e:
        graph_error = extract_graph_error(str(e))
        if '.xml" not found.' not in graph_error:
            sys.stderr.write('Unable to fetch number of graphs: %s\n' % graph_error)
        num_sources = 0

    graph_list = []
    for source in range(0, num_sources):
        try:
            content = fetch_graph(context, source)
        except GraphException as e:
            sys.stderr.write('Unable to fetch graph: %s\n' % e)
            continue

        graph_list.append(content)

    return graph_list


def render_cmk_graphs(context):
    if context["WHAT"] == "HOST":
        svc_desc = "_HOST_"
    else:
        svc_desc = context["SERVICEDESC"]

    url = "http://localhost:%d/%s/check_mk/ajax_graph_images.py?host=%s&service=%s" % \
                    (site.get_apache_port(), os.environ["OMD_SITE"],
                     urllib.quote(context["HOSTNAME"]), urllib.quote(svc_desc))

    try:
        json_data = urllib2.urlopen(url).read()
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
        sys.stderr.write("ERROR: Failed to decode graphs: %s\nURL: %s\nData: %r\n" %
                         (e, url, json_data))
        return []

    return map(base64.b64decode, base64_strings)


def use_cmk_graphs():
    return site.get_omd_config("CONFIG_CORE") == "cmc"


def render_performance_graphs(context):
    if use_cmk_graphs():
        graphs = render_cmk_graphs(context)
    else:
        graphs = render_pnp_graphs(context)

    attachments, graph_code = [], ''
    for source, graph_png in enumerate(graphs):
        if context['WHAT'] == 'HOST':
            svc_desc = '_HOST_'
        else:
            svc_desc = context['SERVICEDESC'].replace(' ', '_')
            # replace forbidden windows characters < > ? " : | \ / *
            for token in ["<", ">", "?", "\"", ":", "|", "\\", "/", "*"]:
                svc_desc = svc_desc.replace(token, "x%s" % ord(token))

        filename = '%s-%s-%d.png' % (context['HOSTNAME'], svc_desc, source)

        attachments.append(('img', filename, graph_png, 'inline'))

        cls = ''
        if context.get('PARAMETER_NO_FLOATING_GRAPHS'):
            cls = ' class="nofloat"'
        graph_code += '<img src="cid:%s"%s />' % (filename, cls)

    if graph_code:
        graph_code = '<tr><th colspan=2>Graphs</th></tr>' \
                     '<tr class="even0"><td colspan=2 class=graphs>%s</td></tr>' % graph_code

    return attachments, graph_code


def construct_content(context):
    # A list of optional information is configurable via the parameter "elements"
    # (new configuration style)
    # Note: The value PARAMETER_ELEMENTSS is NO TYPO.
    #       Have a look at the function events.py:add_to_event_context(..)
    if "PARAMETER_ELEMENTSS" in context:
        elements = context["PARAMETER_ELEMENTSS"].split()
    else:
        elements = ["perfdata", "graph", "abstime", "address", "longoutput"]

    # If argument 2 is given (old style) or the parameter url_prefix is set (new style),
    # we know the base url to the installation and can add
    # links to hosts and services. ubercomfortable!
    if context.get('PARAMETER_2'):
        context["PARAMETER_URL_PREFIX"] = context["PARAMETER_2"]

    utils.extend_context_with_link_urls(context, '<a href="%s">%s</a>')

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

    html_info = ""
    html_state = '<span class="state$@STATE$">$@STATE$</span>'
    notification_type = context["NOTIFICATIONTYPE"]
    if notification_type in ["PROBLEM", "RECOVERY"]:
        txt_info = "$PREVIOUS@HARDSHORTSTATE$ -> $@SHORTSTATE$"
        html_info = '<span class="state$PREVIOUS@HARDSTATE$">$PREVIOUS@HARDSTATE$</span> &rarr; ' + \
                    html_state

    elif notification_type.startswith("FLAP"):
        if "START" in notification_type:
            txt_info = "Started Flapping"
        else:
            txt_info = "Stopped Flapping ($@SHORTSTATE$)"
            html_info = "Stopped Flapping (while " + html_state + ")"

    elif notification_type.startswith("DOWNTIME"):
        what = notification_type[8:].title()
        txt_info = "Downtime " + what + " ($@SHORTSTATE$)"
        html_info = "Downtime " + what + " (while " + html_state + ")"

    elif notification_type == "ACKNOWLEDGEMENT":

        txt_info = "Acknowledged ($@SHORTSTATE$)"
        html_info = "Acknowledged (while " + html_state + ")"

    elif notification_type == "CUSTOM":
        txt_info = "Custom Notification ($@SHORTSTATE$)"
        html_info = "Custom Notification (while " + html_state + ")"

    else:
        txt_info = notification_type  # Should never happen

    if not html_info:
        html_info = txt_info

    txt_info = utils.substitute_context(txt_info.replace("@", context["WHAT"]), context)
    context["EVENT_TXT"] = txt_info

    # Add HTML formated plugin output
    html_info = utils.substitute_context(html_info.replace("@", context["WHAT"]), context)
    context["EVENT_HTML"] = html_info
    if "HOSTOUTPUT" in context:
        context["HOSTOUTPUT_HTML"] = utils.format_plugin_output(context["HOSTOUTPUT"])
    if context["WHAT"] == "SERVICE":
        context["SERVICEOUTPUT_HTML"] = utils.format_plugin_output(context["SERVICEOUTPUT"])

        long_serviceoutput = context["LONGSERVICEOUTPUT"]\
            .replace('\\n', '<br>')\
            .replace('\n', '<br>')
        context["LONGSERVICEOUTPUT_HTML"] = utils.format_plugin_output(long_serviceoutput)

    attachments = []

    # Compute the subject of the mail
    if context['WHAT'] == 'HOST':
        tmpl = context.get('PARAMETER_HOST_SUBJECT') or tmpl_host_subject
        context['SUBJECT'] = utils.substitute_context(tmpl, context)
    else:
        tmpl = context.get('PARAMETER_SERVICE_SUBJECT') or tmpl_service_subject
        context['SUBJECT'] = utils.substitute_context(tmpl, context)

    # Prepare the mail contents
    content_txt, content_html = render_elements(context, elements)

    if "graph" in elements and not "ALERTHANDLEROUTPUT" in context:
        # Add PNP or Check_MK graph
        try:
            attachments, graph_code = render_performance_graphs(context)
            content_html += graph_code
        except Exception as e:
            sys.stderr.write("Failed to add graphs to mail. Continue without them. (%s)\n" % e)

    extra_html_section = ""
    if "PARAMETER_INSERT_HTML_SECTION" in context:
        extra_html_section = context['PARAMETER_INSERT_HTML_SECTION']

    content_html = utils.substitute_context(tmpl_head_html(extra_html_section), context) + \
                   content_html + \
                   utils.substitute_context(tmpl_foot_html, context)

    return content_txt, content_html, attachments


def render_elements(context, elements):
    what = context['WHAT'].lower()
    is_alert_handler = "ALERTHANDLEROUTPUT" in context
    even = "even"
    tmpl_txt = ""
    tmpl_html = ""
    for name, whence, forced, nottype, title, txt, html in body_elements:
        if nottype == "alerthandler" and not is_alert_handler:
            continue

        if nottype not in ("alerthandler", "all") and is_alert_handler:
            continue

        if (whence == "both" or whence == what) and \
            (forced or (name in elements)):
            tmpl_txt += "%-20s %s\n" % (title + ":", txt)
            tmpl_html += '<tr class="%s0"><td class=left>%s</td><td>%s</td></tr>' % (even, title,
                                                                                     html)
            even = 'odd' if even == 'even' else 'even'

    return utils.substitute_context(tmpl_txt, context), \
           utils.substitute_context(tmpl_html, context)


class BulkEmailContent(object):
    def __init__(self, context_function):
        self.attachments = []
        self.content_txt = ""
        self.content_html = ""
        parameters, contexts = context_function()
        hosts = set([])
        for context in contexts:
            context.update(parameters)
            utils.html_escape_context(context)
            txt, html, att = construct_content(context)
            self.content_txt += txt
            self.content_html += html
            self.attachments += att
            hosts.add(context["HOSTNAME"])

        last_context = contexts[-1]
        self.mailto = last_context['CONTACTEMAIL']  # Assume the same in each context

        # Use the single context subject in case there is only one context in the bulk
        self.subject = (utils.get_bulk_notification_subject(contexts, hosts)
                        if len(contexts) > 1 else last_context['SUBJECT'])

        # TODO: cleanup duplicate code with SingleEmailContent
        # TODO: the context is only needed because of SMPT settings used in send_mail
        self.from_address = last_context.get("PARAMETER_FROM") or default_from_address()
        self.reply_to = last_context.get("PARAMETER_REPLY_TO")
        self.context = last_context


class SingleEmailContent(object):
    def __init__(self, context_function):
        # gather all options from env
        context = context_function()
        utils.html_escape_context(context)
        content_txt, content_html, attachments = construct_content(context)

        self.content_txt = content_txt
        self.content_html = content_html
        self.attachments = attachments
        self.mailto = context['CONTACTEMAIL']
        self.subject = context['SUBJECT']

        # TODO: cleanup duplicate code with BulkEmailContent
        # TODO: the context is only needed because of SMPT settings used in send_mail
        self.from_address = context.get("PARAMETER_FROM") or default_from_address()
        self.reply_to = context.get("PARAMETER_REPLY_TO")
        self.context = context


def main():
    if bulk_mode:
        content = BulkEmailContent(utils.read_bulk_contexts)
    else:
        content = SingleEmailContent(utils.collect_context)

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
        sys.exit(send_mail(
            m,
            content.mailto,
            content.from_address,
            content.context,
        ))
    except Exception as e:
        sys.stderr.write("Unhandled exception: %s\n" % e)
        # unhandled exception, don't retry this...
        sys.exit(2)
