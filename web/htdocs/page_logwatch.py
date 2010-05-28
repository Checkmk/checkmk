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
import views


def page(h):
    global html
    html = h

    host = html.var('host')
    filename = html.var('file')
    if not host:
        raise MKGeneralException("You called this page via an invalid URL: missing host")

    # Check user permissions on the host
    if not may_see(host):
        raise MKAuthException("You are not allowed to access the logs of the host %s" % htmllib.attrencode(host))

    if filename:
        if html.has_var('ack') and not html.var("_do_actions") == "No":
            html.live.set_auth_domain('action')
            do_log_ack(host, filename)
        else:
            show_file(host, filename)
    else:
        show_host_log_list(host)

def show_host_log_list(host):
    html.header("Logfiles of host " + host)
    html.begin_context_buttons()
    html.context_button("Services", "view.py?view_name=host&site=&host=%s" % htmllib.urlencode(host))
    html.end_context_buttons()

    logs_shown = False
    rowno = 0
    for file in host_logs(host):
        rowno += 1
        if rowno == 1:
            html.write("<table class=services>\n")
            html.write("<tr class=groupheader>\n")
            html.write("<th>Level</th><th>Logfile</th><th>Last Entry</th><th>Entries</th></tr>\n")

        file_display = form_file_to_ext(file)

        logs = parse_file(host, file)
        if logs == [] or type(logs) != list: # corrupted logfile
            if logs == []: logs = "empty"
            html.write("<tr class=%s0>\n" % (rowno % 2 == 0 and "odd" or "even"))
            html.write("<td>-</td><td>%s</td><td>%s</td><td>0</td></tr>\n" % (htmllib.attrencode(logs), htmllib.attrencode(file_display)))
        else:
            worst_log = get_worst_log(logs)
            last_log = get_last_log(logs)
            state = worst_log['level']
            state_name = form_level(state)
            html.write("<tr class=%s%d>\n" % (rowno % 2 == 0 and "odd" or "even", state))
        
            html.write("<td class=\"state%d\">%s</td>\n" % (state, state_name))
            html.write("<td><a href=\"logwatch.py?host=%s&amp;file=%s\">%s</a></td>\n" % 
                        (htmllib.urlencode(host), htmllib.urlencode(file_display),htmllib.attrencode(file_display)))
            html.write("<td>%s</td><td>%s</td></tr>\n" % \
                        (form_datetime(last_log['datetime']), len(logs)))

    if rowno > 0:
        html.write("</table>")
    else:
        html.write('<p>No logs found for this host.</p>\n')

    html.footer()


def show_file(host, filename):
    file = form_file_to_int(filename)
    html.header("Logfiles of host %s: %s" % (host, filename))
    html.begin_context_buttons()
    html.context_button("Services", "view.py?view_name=host&site=&host=%s" % htmllib.urlencode(host))
    html.context_button("All logfiles", "logwatch.py?host=%s" % htmllib.urlencode(host))

    if html.var('hidecontext', 'no') == 'yes':
        hide_context_label = 'Show context'
        hide_context_param = 'no'
        hide = True
    else:
        hide_context_label = 'Hide context'
        hide_context_param = 'yes'
        hide = False

    logs = parse_file(host, file, hide)
    if type(logs) != list:
        html.end_context_buttons()
        html.show_error("Unable to show logfile: <b>%s</b>" % logs)
        html.footer()
        return
    elif logs == []:
        html.end_context_buttons()
        html.message("This logfile contains no unacknowledged messages.")
        html.footer()
        return

    if config.may("act") and may_see(host):
        html.context_button("Acknowledge", "logwatch.py?host=%s&amp;file=%s&amp;ack=1" % \
                   (htmllib.urlencode(host), htmllib.urlencode(html.var('file')) ))

    html.context_button("Context", 'logwatch.py?host=%s&file=%s&hidecontext=%s">%s</a>' % \
                   (htmllib.urlencode(host), \
                    htmllib.urlencode(html.var('file')), \
                    htmllib.urlencode(hide_context_param), \
                    htmllib.attrencode(hide_context_label) ))

    html.end_context_buttons()

    html.write("<div id=logwatch>\n")
    for log in logs:
        html.write('<div class="chunk">\n');
        html.write('<table class="section">\n<tr>\n');
        html.write('<td class="%s">%s</td>\n' % (form_level(log['level']), form_level(log['level'])));
        html.write('<td class="date">%s</td>\n' % (form_datetime(log['datetime'])));
        html.write('</tr>\n</table>\n');

        for line in log['lines']:
            html.write('<pre class="%s">%s</pre>\n' % (line['class'], htmllib.attrencode(line['line']) ))

        html.write('</div>\n')

    html.write("</div>\n")
    html.footer()


def do_log_ack(host, filename):
    file = form_file_to_int(filename)
    file_display = form_file_to_ext(file)
    html.header("Acknowledge logfile %s" % file_display)
    html.write("<a class=navi href=\"logwatch.py?host=%s\">All logfiles of %s</a>\n" % tuple([htmllib.urlencode(host)] * 2))
    ack  = html.var('ack')
    if not html.confirm("Please confirm the deletion of the message from <tt>%s</tt>" % filename):
        html.footer()
        return

    if not (config.may("act") and may_see(host)):
        html.write("<h1 class=error>Permission denied</h1>\n")
        html.write("<div class=error>You are not allowed to acknowledge the logs of the host %s</div>" % htmllib.attrencode(host))
        html.footer()
        return

    # filter invalid values
    if ack != '1':
        raise MKUserError('ack', 'Invalid value for ack parameter.')

    try:
        os.remove(defaults.logwatch_dir + '/' + host + '/' + file)

        message = '<b>%s: %s Acknowledged</b><br>' % \
          (htmllib.attrencode(host), htmllib.attrencode(file_display))
        message += '<p>The log messages from host &quot;%s&quot; in file' \
                   '&quot;%s&quot; have been acknowledged.</p>' % \
                     (htmllib.attrencode(host), htmllib.attrencode(file_display))
        html.message(message)
    except Exception, e:
        html.show_error('The log file &quot;%s&quot; from host &quot;%s&quot;'
                                 ' could not be deleted: %s.' % \
                                  (htmllib.attrencode(file_display), htmllib.attrencode(host), e))
    html.footer()


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


def parse_file(host, file, hidecontext = False):
    logs = [] 
    try:
        file_path = defaults.logwatch_dir + '/' + host + '/' + file 
        if not os.path.exists(file_path):
            return []
        f = open(file_path, 'r') 
        chunk_open = False 
        log = None 
        for line in f.readlines():
            line = line.strip() 
            if line == '':
                continue

            if line[:3] == '<<<': # new chunk begins
                log_lines = []
                log = {'lines': log_lines}
                logs.append(log)

                # New header line
                date, logtime, level = line[3:-3].split(' ')

                # Save level as integer to make it better comparable
                if level == 'CRIT':
                    log['level'] = 2
                elif level == 'WARN':
                    log['level'] = 1
                else:
                    log['level'] = 0

                # Gather datetime object
                # Python versions below 2.5 don't provide datetime.datetime.strptime.
                # Use the following instead:
                #log['datetime'] = datetime.datetime.strptime(date + ' ' + logtime, "%Y-%m-%d %H:%M:%S") 
                log['datetime'] = datetime.datetime(*time.strptime(date + ' ' + logtime, "%Y-%m-%d %H:%M:%S")[0:5])
            elif log: # else: not in a chunk?!
                # Data line
                line_display = line[2:]

                # Classify the line for styling
                if line[0] == 'W':
                    line_level = 1
                    line_class = 'WARN'

                elif line[0] == 'C':
                    line_level = 2
                    line_class = 'CRIT'

                elif not hidecontext:
                    line_level = 0
                    line_class = 'context'

                else:
                    continue # ignore this line

                log_lines.append({ 'level': line_level, 'class': line_class, 'line': line_display })
    except Exception, e:
        # cannot parse logfile: corrupted
        return str(e)

    return logs

def host_logs(host):
    try:
        return filter(lambda x: x != '..' and x != '.', os.listdir(defaults.logwatch_dir + '/' + host))
    except:
        return []

def may_see(host):
    if config.may("see_all"):
        return True

    # FIXME: Or maybe make completely transparent and add pseudo local_connection() to Single livestatus clas?
    if config.is_multisite():
        conn = html.live.local_connection()
    else:
        conn = html.live

    # livestatus connection is setup with AuthUser
    return conn.query_value("GET hosts\nStats: state >= 0\nFilter: name = %s\n" % host) > 0

def form_level(level):
    levels = [ 'OK', 'WARN', 'CRIT', 'UNKNOWN' ]
    return levels[level]

def form_file_to_int(file):
    return file.replace('/', '\\')

def form_file_to_ext(file):
    return file.replace('\\', '/')

def form_datetime(dt, format = '%Y-%m-%d %H:%M:%S'):
    # FIXME: Dateformat could be configurable
    return dt.strftime(format)
