#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

import htmllib, livestatus, time, re, os, datetime, config, defaults
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

    html.write("<td width=\"100%%\" class=pad></td></tr></table>")


def page(h):
    global html
    html = h

    global tabs
    tabs = [ ("logwatch", "All Hosts", html.req.uri.split("/")[-1]),
             ("host", "All Logs of Host", 'logwatch.py?host=' + html.var('host', '')) ]

    html.header("Check_mk Logwatch")

    html.write('<div id="logwatch">')

    if html.has_var('host'):
        host = html.var('host')

        # Check user permissions on the host
        if(not host in all_hosts()):
            html.write("<h1 class=error>Permission denied</h1>\n")
            html.write("<div class=error>You are not allowed to access the logs of the host %s</div>" % htmllib.attrencode(host))
            return

        if html.has_var('file'):
            if html.has_var('ack'):
                html.live.set_auth_domain('action')
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

    hosts = all_hosts()
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

    if(not host in all_hosts()):
        html.write("<h1 class=error>Permission denied</h1>\n")
        html.write("<div class=error>You are not allowed to view the logs of the host %s</div>" % htmllib.attrencode(host))
        return

    show_host_header(html, host)

    html.write("<table class=form id=filter>\n")
    html.write("<tr><td style=\"width:100px\" class=\"legend\">Level</td><td class=\"legend\">Logfile</td>"
               "<td class=\"legend\">Last Entry</td><td class=\"legend\">Entries</td></tr>\n")

    logs_shown = False
    for file in host_logs(host):
        logs_shown = True
        fileDisplay = form_file_to_ext(file)

        logs = parse_file(host, file)
        worst_log = get_worst_log(logs)
        last_log = get_last_log(logs)

        html.write("<tr><td class=\"%s\">%s</td><td class=\"content\"><a href=\"logwatch.py?host=%s&amp;file=%s\">%s</a></td>"
                   "<td class=\"content\">%s</td>"
                   "<td class=\"content\">%s</td></tr>\n" % \
                   (form_level(worst_log['level']), form_level(worst_log['level']),
                    htmllib.urlencode(host), htmllib.urlencode(fileDisplay),
                    htmllib.attrencode(fileDisplay), form_datetime(last_log['datetime']), len(logs)))

    if not logs_shown:
        html.write('<tr><td class="content" colspan="4">No logs found for this host.</td></tr>')

    html.write("</table>")


def show_file(html):
    show_tabs(html, tabs, "file")

    host = html.var('host')
    file = form_file_to_int(html.var('file'))

    if html.var('hidecontext', 'no') == 'yes':
        hide_context_label = 'Show context'
        hide_context_param = 'no'
    else:
        hide_context_label = 'Hide context'
        hide_context_param = 'yes'

    show_host_header(html, host)

    try:
        logs = parse_file(host, file, html.var('hidecontext', 'no'))
    except MKFileNotFoundException, e:
        html.write('<table class="form" id="filter"><tr><td class="content">%s</td></tr></table>' % e)
        return

    for log in logs:
        html.write('<div class="chunk">');
        html.write('<table class="section"><tr>');
        html.write('<td class="%s">%s</td>' % (form_level(log['level']), form_level(log['level'])));
        html.write('<td class="date">%s</td>' % (form_datetime(log['datetime'])));
        html.write('<td class="button"><a href="logwatch.py?host=%s&amp;'
                   'file=%s&amp;hidecontext=%s">%s</td>' % \
                   (htmllib.urlencode(host), \
                    htmllib.urlencode(html.var('file')), \
                    htmllib.urlencode(hide_context_param), \
                    htmllib.attrencode(hide_context_label) ));
        html.write('</tr></table>');

        for line in log['lines']:
            html.write('<pre class="%s">%s</pre>' % (line['class'], htmllib.attrencode(line['line']) ))

        html.write('</div>')

    if config.may("act_all") or host in all_hosts():
        html.write('<p><br /><a class="ack" href="logwatch.py?host=%s&amp;'
                   'file=%s&amp;ack=1">Acknowledge and delete messages</a>' % \
                   (htmllib.urlencode(host), htmllib.urlencode(html.var('file')) ))

def show_host_header(html, host):
    html.write("<table class=form id=filter>\n")
    html.write('<tr><td class="legend">Hostname:</td><td class="content">%s</td></tr>' % htmllib.attrencode(host))
    html.write('<tr><td class="legend">Host in Nagios:</td>'
               '<td class="content"><a href="%s/status.cgi?host=%s">Link</a></td></tr>' % \
               (htmllib.urlencode(defaults.nagios_cgi_url), htmllib.attrencode(host)))
    html.write('</table><br />')

def do_log_ack(html):
    show_tabs(html, tabs, "log")

    host = html.var('host')
    file = form_file_to_int(html.var('file'))
    fileDisplay = form_file_to_ext(file)
    ack  = html.var('ack')

    if not (config.may("act") and (config.may("see_all") or host in all_hosts())):
        html.write("<h1 class=error>Permission denied</h1>\n")
        html.write("<div class=error>You are not allowed to acknowledge the logs of the host %s</div>" % htmllib.attrencode(host))
        return

    # filter invalid values
    if ack != '1':
        raise MKUserError('ack', 'Invalid value for ack parameter.')

    try:
        os.remove(defaults.logwatch_dir + '/' + host + '/' + file)

        html.write('<h1>%s: %s Acknowledged</h1>' % \
          (htmllib.attrencode(host), htmllib.attrencode(fileDisplay)))
        html.write('<p>The log messages from host &quot;%s&quot; in file'
                   '&quot;%s&quot; have been acknowledged.</p>' % \
                     (htmllib.attrencode(host), htmllib.attrencode(fileDisplay)))
    except Exception, e:
        raise MKGeneralException('The log file &quot;%s&quot; from host &quot;%s&quot;'
                                 ' could not be deleted: %s.' % \
                                  (htmllib.attrencode(fileDisplay), htmllib.attrencode(host), e))

def get_worst_file(host, files):
    worst_file = None
    worst_log = None
    worst_level = 0

    for file in files:
        logs = parse_file(host, file)
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


def parse_file(host, file, hidecontext = "no"):
    filePath = defaults.logwatch_dir + '/' + host + '/' + file
    try:
        f = open(filePath, 'r')
    except:
        raise MKFileNotFoundException('The log file &quot;%s&quot; on host &quot;%s&quot; is empty or does not exist.' % \
                                       (htmllib.attrencode(form_file_to_ext(file)), htmllib.attrencode(host)))
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
        return filter(lambda x: x != '..' and x != '.', os.listdir(defaults.logwatch_dir + '/' + host))
    except:
        return []

def all_hosts():
    # FIXME: Or maybe make completely transparent and add pseudo local_connection() to Single livestatus clas?
    if config.is_multisite():
        conn = html.live.local_connection()
    else:
        conn = html.live

    hosts = conn.query_column_unique("GET hosts\nColumns: name\n")

    hosts.sort()
    return hosts

def form_level(level):
    levels = [ 'OK', 'WARN', 'CRIT' ]
    return levels[level]

def form_file_to_int(file):
    return file.replace('/', '\\')

def form_file_to_ext(file):
    return file.replace('\\', '/')

def form_datetime(dt, format = '%Y-%m-%d %H:%M:%S'):
    # FIXME: Dateformat could be configurable
   return dt.strftime(format)
