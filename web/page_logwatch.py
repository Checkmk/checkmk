#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import htmllib, nagios, time, re, check_mk, os, datetime
from lib import *

def show_tabs(html, tabs, active):
    html.write("<table class=tabs cellpadding=0 cellspacing=0><tr>\n")
    for tab, title, uri in tabs:
        if tab == active:
            cssclass = "tabactive"
        else:
            cssclass = "tab"

        html.write("<td>")
        html.write('<a class="%s" href="%s">%s</a>' % \
                   (htmllib.attrencode(cssclass), uri, title))
        html.write("</td>")

    html.write("<td width=\"100%%\" class=pad>"
               "<b class=headtime>%s</b> "
               "<b>Check_mk Logwatch</b> "
               "<a href=\"http://mathias-kettner.de/check_mk\">"
               "<img align=absbottom border=0 src=\"check_mk.trans.60.png\">"
               "</a></td></tr></table>" % time.strftime("%H:%M"))


def page(html):
    global tabs
    tabs = [ ("logwatch", "All Hosts", html.req.uri.split("/")[-1]),
             ("host", "Host", 'logwatch.py?host=' + html.var('host', '')) ]

    html.header("Check_mk Logwatch")

    html.write('<div id="logwatch">')

    if html.has_var('host'):
        host = html.var('host')
        # Check user permissions
        if(not host in all_hosts(html.req.user)):
            html.write("<h1 class=error>Permission denied</h1>\n")
            html.write("<div class=error>You are not allowed to view the logs of the host %s</div>" % htmllib.attrencode(host))
            return

        if html.has_var('file'):
            if html.has_var('ack'):
                do_log_ack(html)
            else:
                show_file(html)
        else:
            show_host_log_list(html)
    else:
        show_host_list(html)

    html.write('</div>')

    html.footer()

def show_host_list(html):
    main_tabs = tabs
    main_tabs.pop(1)

    show_tabs(html, main_tabs, "logwatch")
    html.write("<table class=form id=filter>\n")
    html.write("<tr><td style=\"width:100px\" class=\"legend\">State</td><td class=\"legend\">Hostname</td><td class=\"legend\">Logs</td></tr>\n")

    hosts = all_hosts(html.req.user)
    host_shown = False
    for host in hosts:
        files = host_logs(host)

        if len(files) > 0:
            host_shown = True

            worst_file, worst_log = get_worst_file(host, files)

            html.write("<tr><td class=\"%s\">%s</td><td class=\"content\"><a href=\"logwatch.py?host=%s\">%s</a></td>"
                       "<td class=\"content\">%s</td></tr>\n" % \
                       (form_level(worst_log['level']), form_level(worst_log['level']), host, host, len(host_logs(host)) ))

    if not host_shown:
        html.write('<tr><td class="content" colspan="2">No hosts to list here.</td></tr>')

    html.write('<tr><td colspan="2">This list only shows hosts with non acknowledged logfiles.</td>')
    html.write("</table>")

def show_host_log_list(html):
    show_tabs(html, tabs, "host")

    host = html.var('host')

    if(not host in all_hosts(html.req.user)):
        html.write("<h1 class=error>Permission denied</h1>\n")
        html.write("<div class=error>You are not allowed to view the logs of the host %s</div>" % htmllib.attrencode(host))
        return

    # Show host header
    html.write("<table class=form id=filter>\n")
    html.write('<tr><td class="legend">Hostname:</td><td class="content">%s</td></tr>' % htmllib.attrencode(host))
    html.write('<tr><td class="legend">Host in Nagios:</td>'
               '<td class="content"><a href="%s/status.cgi?host=%s">Link</a></td></tr>' % \
               (htmllib.urlencode(html.req.defaults["nagios_cgi_url"]), htmllib.attrencode(host)))
    html.write('</table>')

    html.write("<table class=form id=filter>\n")
    html.write("<tr><td style=\"width:100px\" class=\"legend\">Level</td><td class=\"legend\">Logfile</td>"
               "<td class=\"legend\">Last Entry</td><td class=\"legend\">Entries</td></tr>\n")

    logs_shown = False
    for file in host_logs(host):
        logs_shown = True
        fileDisplay = file.replace('\\', '/')

        logs = parse_file(check_mk.logwatch_dir + '/' + host + '/' + file)
        worst_log = get_worst_log(logs)
        last_log = get_last_log(logs)

        html.write("<tr><td class=\"%s\">%s</td><td class=\"content\"><a href=\"logwatch.py?host=%s&amp;file=%s\">%s</a></td>"
                   "<td class=\"content\">%s</td>"
                   "<td class=\"content\">%s</td></tr>\n" % \
                   (form_level(worst_log['level']), form_level(worst_log['level']),
                    htmllib.urlencode(host), htmllib.urlencode(file),
                    htmllib.attrencode(fileDisplay), form_datetime(last_log['datetime']), len(logs)))

    if not logs_shown:
        html.write('<tr><td class="content" colspan="2">No logs found for this host.</td></tr>')

    html.write("</table>")


def show_file(html):
    show_tabs(html, tabs, "file")

    host = html.var('host')
    file = html.var('file')

    if html.var('hidecontext', 'no') == 'yes':
        hide_context_label = 'Show context'
        hide_context_param = 'no'
    else:
        hide_context_label = 'Hide context'
        hide_context_param = 'yes'

    logs = parse_file(check_mk.logwatch_dir + '/' + host + '/' + file, html.var('hidecontext', 'no'))

    for log in logs:
        html.write('<div class="chunk">');
        html.write('<table class="section"><tr>');
        html.write('<td class="%s">%s</td>' % (form_level(log['level']), form_level(log['level'])));
        html.write('<td class="date">%s</td>' % (form_datetime(log['datetime'])));
        html.write('<td class="button"><a href="logwatch.py?host=%s&amp;'
                   'file=%s&amp;hidecontext=%s">%s</td>' % \
                   (htmllib.urlencode(host), \
                    htmllib.urlencode(file), \
                    htmllib.urlencode(hide_context_param), \
                    htmllib.attrencode(hide_context_label) ));
        html.write('</tr></table>');

        for line in log['lines']:
            html.write('<pre class="%s">%s</pre>' % (line['class'], htmllib.attrencode(line['line']) ))

        html.write('</div>')

    if check_mk.is_allowed_to_act(html.req.user):
        html.write('<p><br /><a class="ack" href="logwatch.py?host=%s&amp;'
                   'file=%s&amp;ack=1">Acknowledge and delete mesages</a>' % \
                   (htmllib.urlencode(host), htmllib.urlencode(file) ))

def do_log_ack(html):
    show_tabs(html, tabs, "log")

    host = html.var('host')
    file = html.var('file')
    fileDisplay = file.replace('\\', '/')
    ack  = html.var('ack')

    # filter invalid values
    if ack != '1':
        raise MKUserError('ack', 'Invalid value for ack parameter.')

    if not check_mk.is_allowed_to_act(html.req.user):
        raise nagios.MKAuthException('Not authorized to perform actions.')

    try:
        os.remove(check_mk.logwatch_dir + '/' + host + '/' + file)

        html.write('<h1>%s: %s Acknowledged</h1>' % \
          (htmllib.attrencode(host), htmllib.attrencode(fileDisplay)))
        html.write('<p>The log messages from host &quot;%s&quot; in file'
                   '&quot;%s&quot; have been acknowledged.</p>' % \
                     (htmllib.attrencode(host), htmllib.attrencode(fileDisplay)))
    except:
        raise nagios.MKGeneralException('The log file &quot;%s&quot; from host &quot;%s&quot;'
                                        ' could not be deleted.' % \
                                        (htmllib.attrencode(fileDisplay), htmllib.attrencode(host)))

def get_worst_file(host, files):
    worst_file = None
    worst_log = None
    worst_level = 0

    for file in files:
        logs = parse_file(check_mk.logwatch_dir + '/' + host + '/' + file)
        worst_file_log = get_worst_log(logs)

        if worst_file_log['level'] > worst_level:
            worst_level = worst_file_log['level']
            worst_file = logs
            worst_log = worst_file_log

    return worst_file, worst_log

def get_worst_log(logs):
    worst_level = 0
    worst_log = None

    for log in logs:
        for line in log['lines']:
            if line['level'] > worst_level:
                worst_level = line['level']
                worst_log = log

    return worst_log

def get_last_log(logs):
    last_log = None
    last_datetime = None

    for log in logs:
        if not last_datetime or log['datetime'] > last_datetime:
            last_datetime = log['datetime']
            last_log = log

    return last_log


def parse_file(file, hidecontext = "no"):
    try:
        f = open(file, 'r')
    except:
        raise nagios.MKGeneralException('The log file &quot;%s&quot; from host &quot;%s&quot;'
                                        ' could not be opened.' % \
                                        (htmllib.attrencode(file.replace('\\', '/')), htmllib.attrencode(host)))
    chunk_open = False
    logs = []
    log = None
    for line in f.readlines():
        line = line.strip()
        if line == '':
            continue

        if line[:3] == '<<<':
            # Add maybe old log to lisst
            if log:
                logs.append(log)

            log = {'lines': []}

            # New header line
            date, time, level = line[3:-3].split(' ')

            # Save level as integer to make it better comparable
            if level == 'CRIT':
                log['level'] = 2
            elif level == 'WARN':
                log['level'] = 1
            else:
                log['level'] = 0

            # Gather datetime object
            log['datetime'] = datetime.datetime.strptime(date + ' ' + time, "%Y-%m-%d %H:%M:%S") 
        else:
            # Data line
            lineDisplay = line[2:]

            # Classify the line for styling
            if line[0] == 'W':
                line_level = 1
                line_class = 'WARN'
            elif line[0] == 'C':
                line_level = 2
                line_class = 'CRIT'
            elif hidecontext == 'yes':
                line_level = 0
                line_class = 'context'
            else:
                line_level = 0
                line_class = ''

            log['lines'].append({ 'level': line_level, 'class': line_class, 'line': lineDisplay })

    # Append last log
    if log:
        logs.append(log)

    return logs

def host_logs(host):
    try:
        return filter(lambda x: x != '..' and x != '.', os.listdir(check_mk.logwatch_dir + '/' + host))
    except:
        return []

def all_hosts(user = None):
    if user:
        auth = "AuthUser: %s\n" % user
    else:
        auth = ''

    hosts = nagios.query_livestatus_column_unique("GET hosts\n" + auth + "Columns: name\n")
    hosts.sort()
    return hosts

def form_level(level):
    levels = [ 'OK', 'WARN', 'CRIT' ]
    return levels[level]

def form_datetime(dt, format = '%Y-%m-%d %H:%M:%S'):
    # FIXME: Dateformat could be configurable
   return dt.strftime(format)
