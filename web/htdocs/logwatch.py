#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import htmllib, livestatus, time, re, os, datetime, config, defaults
from lib import *
import views

stylesheets = [ 'pages', 'status', 'logwatch' ]

def level_name(level):
    if   level == 'W': return 'WARN'
    elif level == 'C': return 'CRIT'
    elif level == 'O': return 'OK'
    else: return 'OK'

def level_state(level):
    if   level == 'W': return 1
    elif level == 'C': return 2
    elif level == 'O': return 0
    else: return 0

#   .----------------------------------------------------------------------.
#   |          ____  _                     _                               |
#   |         / ___|| |__   _____      __ | |    ___   __ _ ___            |
#   |         \___ \| '_ \ / _ \ \ /\ / / | |   / _ \ / _` / __|           |
#   |          ___) | | | | (_) \ V  V /  | |__| (_) | (_| \__ \           |
#   |         |____/|_| |_|\___/ \_/\_/   |_____\___/ \__, |___/           |
#   |                                                 |___/                |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def page_show():
    host = html.var('host')
    filename = html.var('file')

    # Acknowledging logs is supported on
    # a) all logs on all hosts
    # b) all logs on one host
    # c) one log on one host
    if html.has_var('_ack') and not html.var("_do_actions") == _("No"):
        html.live.set_auth_domain('action')
        do_log_ack(host, filename)
        return

    if not host:
        show_log_list()
        return

    # Check user permissions on the host
    if not may_see(host):
        raise MKAuthException(_("You are not allowed to access the logs of the host %s") % htmllib.attrencode(host))

    if filename:
        show_file(host, filename)
    else:
        show_host_log_list(host)

# Shows a list of all problematic logfiles grouped by host
def show_log_list():
    html.header(_("All Problematic Logfiles"), stylesheets = stylesheets)

    html.begin_context_buttons()
    html.context_button(_("Analyze Patterns"), "%swato.py?mode=pattern_editor" % html.var('master_url', ''), 'analyze')
    ack_button()
    html.end_context_buttons()

    html.write("<table class=data>\n")
    for host, logs in all_logs():
        html.write('<tr><td colspan=2><h2><a href="%s">%s</a></h2></td></tr>' % \
                                              (html.makeuri([('host', host)]), host))
        list_logs(host, logs)
    html.write("</table>\n")

    html.footer()

# Shows all problematic logfiles of a host
def show_host_log_list(host):
    master_url = html.var('master_url', '')
    html.header(_("Logfiles of Host %s") % host, stylesheets = stylesheets)
    html.begin_context_buttons()
    html.context_button(_("Services"), "%sview.py?view_name=host&site=&host=%s" %
                                (master_url, htmllib.urlencode(host)), 'services')
    html.context_button(_("All Logfiles"), html.makeuri([('host', ''), ('file', '')]))
    html.context_button(_("Analyze Host Patterns"), "%swato.py?mode=pattern_editor&host=%s" %
                                (master_url, htmllib.urlencode(host)), 'analyze')
    ack_button(host)
    html.end_context_buttons()

    html.write("<table class=data>\n")
    list_logs(host, host_logs(host))
    html.write("</table>\n")

    html.footer()

# Displays a table of logfiles
def list_logs(host, logfiles):
    rowno = 0
    for log_file in logfiles:
        rowno += 1
        if rowno == 1:
            html.write("<tr class=groupheader>\n")
            html.write("<th>"+_('Level')+"</th><th>"+_('Logfile')+"</th>")
            html.write("<th>"+_('Last Entry')+"</th><th>"+_('Entries')+"</th></tr>\n")

        file_display = form_file_to_ext(log_file)

        logs = parse_file(host, log_file)
        if logs == [] or type(logs) != list: # corrupted logfile
            if logs == []: logs = "empty"
            html.write("<tr class=%s0>\n" % (rowno % 2 == 0 and "odd" or "even"))
            html.write("<td>-</td><td>%s</td><td>%s</td><td>0</td></tr>\n" %
                             (htmllib.attrencode(logs), htmllib.attrencode(file_display)))
        else:
            worst_log = get_worst_log(logs)
            last_log = get_last_log(logs)
            state = worst_log['level']
            state_name = form_level(state)
            html.write("<tr class=%s%d>\n" % (rowno % 2 == 0 and "odd" or "even", state))

            html.write("<td class=\"state%d\">%s</td>\n" % (state, state_name))
            html.write("<td><a href=\"%s\">%s</a></td>\n" %
                        (html.makeuri([('host', host), ('file', file_display)]), htmllib.attrencode(file_display)))
            html.write("<td>%s</td><td>%s</td></tr>\n" % \
                        (form_datetime(last_log['datetime']), len(logs)))

    if rowno == 0:
        html.write('<tr><td colspan=4>'+_('No logs found for this host.')+'</td></tr>\n')


def ack_button(host = None, int_filename = None):
    if not config.may("general.act") or (host and not may_see(host)):
        return

    if int_filename:
        label = _("Clear Log")
    else:
        label = _("Clear Logs")

    html.context_button(label, html.makeuri([('_ack', '1')]), 'delete')


def show_file(host, filename):
    master_url = html.var('master_url', '')

    int_filename = form_file_to_int(filename)
    html.header(_("Logfiles of Host %s: %s") % (host, filename), stylesheets = stylesheets)
    html.begin_context_buttons()
    html.context_button(_("Services"), "%sview.py?view_name=host&site=&host=%s" % (master_url, htmllib.urlencode(host)), 'services')
    html.context_button(_("All Logfiles of Host"), html.makeuri([('file', '')]))
    html.context_button(_("All Logfiles"), html.makeuri([('host', ''), ('file', '')]))

    html.context_button(_("Analyze Patterns"), "%swato.py?mode=pattern_editor&host=%s&file=%s" %
                                (master_url, htmllib.urlencode(host), htmllib.urlencode(filename)), 'analyze')

    if html.var('_hidecontext', 'no') == 'yes':
        hide_context_label = _('Show Context')
        hide_context_param = 'no'
        hide = True
    else:
        hide_context_label = _('Hide Context')
        hide_context_param = 'yes'
        hide = False

    logs = parse_file(host, int_filename, hide)
    if type(logs) != list:
        html.end_context_buttons()
        html.show_error(_("Unable to show logfile: <b>%s</b>") % logs)
        html.footer()
        return
    elif logs == []:
        html.end_context_buttons()
        html.message(_("This logfile contains no unacknowledged messages."))
        html.footer()
        return

    ack_button(host, int_filename)
    html.context_button(hide_context_label, html.makeuri([('_hidecontext', hide_context_param)]))

    html.end_context_buttons()

    html.write("<div id=logwatch>\n")
    for log in logs:
        html.write('<div class="chunk">\n');
        html.write('<table class="section">\n<tr>\n');
        html.write('<td class="%s">%s</td>\n' % (form_level(log['level']), form_level(log['level'])));
        html.write('<td class="date">%s</td>\n' % (form_datetime(log['datetime'])));
        html.write('</tr>\n</table>\n');

        for line in log['lines']:
            html.write('<p class="%s">' % line['class'])

            edit_url = master_url + "wato.py?" + htmllib.urlencode_vars([
                ('mode',  'pattern_editor'),
                ('host',  host),
                ('file',  filename),
                ('match', line['line']),
            ])
            html.icon_button(edit_url, _("Analyze this line"), "analyze")
            html.write('%s</p>\n' % (htmllib.attrencode(line['line']) ))

        html.write('</div>\n')

    html.write("</div>\n")
    html.footer()


def do_log_ack(host, filename):
    todo = []
    if not host and not filename: # all logs on all hosts
        for this_host, logs in all_logs():
            for int_filename in logs:
                file_display = form_file_to_ext(int_filename)
                todo.append((this_host, int_filename, file_display))
        ack_msg = _('all logfiles on all hosts')

    elif host and not filename: # all logs on one host
        for int_filename in host_logs(host):
            file_display = form_file_to_ext(int_filename)
            todo.append((host, int_filename, file_display))
        ack_msg = _('all logfiles of host <tt>%s</tt>') % htmllib.attrencode(host)

    elif host and filename: # one log on one host
        int_filename = form_file_to_int(filename)
        todo = [ (host, int_filename, form_file_to_ext(int_filename)) ]
        ack_msg = _('the log file <tt>%s</tt> on host <tt>%s</tt>') % \
                       (htmllib.attrencode(filename), htmllib.attrencode(host))

    html.header(_("Acknowledge %s") % ack_msg, stylesheets = stylesheets)

    html.begin_context_buttons()
    html.context_button(_("All Logfiles"), html.makeuri([('host', ''), ('file', '')]))
    if host:
        html.context_button(_("All Logfiles of Host"), html.makeuri([('file', '')]))
    if host and filename:
        html.context_button(_("Back to Logfile"), html.makeuri([]))
    html.end_context_buttons()

    ack = html.var('_ack')
    if not html.confirm(_("Do you really want to acknowledge %s by <b>deleting</b> all stored messages?") % ack_msg):
        html.footer()
        return

    if not config.may("general.act"):
        html.write("<h1 class=error>"+_('Permission denied')+"</h1>\n")
        html.write("<div class=error>" + _('You are not allowed to acknowledge %s</div>') % ack_msg)
        html.footer()
        return

    # filter invalid values
    if ack != '1':
        raise MKUserError('_ack', _('Invalid value for ack parameter.'))

    for this_host, int_filename, display_name in todo:
        try:
            if not may_see(this_host):
                raise MKAuthException(_('Permission denied.'))
            os.remove(defaults.logwatch_dir + '/' + this_host + '/' + int_filename)
        except Exception, e:
            html.show_error(_('The log file <tt>%s</tt> of host <tt>%s</tt> could not be deleted: %s.') % \
                                      (htmllib.attrencode(file_display), htmllib.attrencode(this_host), e))

    html.message('<b>%s</b><p>%s</p>' % (
        _('Acknowledged %s') % ack_msg,
        _('Acknowledged all messages in %s.') % ack_msg
    ))
    html.footer()


def get_worst_log(logs):
    worst_level = 0
    worst_log = None

    for log in logs:
        for line in log['lines']:
            if line['level'] >= worst_level:
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
                elif level == 'OK':
                    log['level'] = 0
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

                elif line[0] == 'O':
                    line_level = 0
                    line_class = 'OK'

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

# Returns a list of tuples where the first element is the hostname
# and the second element is a list of logs of this host
def all_logs():
    logs = []
    try:
        for host in filter(lambda x: x != '..' and x != '.', os.listdir(defaults.logwatch_dir)):
            logs_of_host = host_logs(host)
            if may_see(host) and logs_of_host:
                logs.append((host, logs_of_host))
    except:
        pass
    return logs

def may_see(host):
    if config.may("general.see_all"):
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

def form_file_to_int(f):
    return f.replace('/', '\\')

def form_file_to_ext(f):
    return f.replace('\\', '/')

def form_datetime(dt, fmt = '%Y-%m-%d %H:%M:%S'):
    # FIXME: Dateformat could be configurable
    return dt.strftime(fmt)
