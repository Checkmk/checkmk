#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

import time
import datetime
import livestatus

import cmk.gui.pages
import cmk.gui.config as config
from cmk.gui.table import table_element
import cmk.gui.sites as sites
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKGeneralException, MKUserError, MKAuthException

#   .--HTML Output---------------------------------------------------------.
#   |     _   _ _____ __  __ _        ___        _               _         |
#   |    | | | |_   _|  \/  | |      / _ \ _   _| |_ _ __  _   _| |_       |
#   |    | |_| | | | | |\/| | |     | | | | | | | __| '_ \| | | | __|      |
#   |    |  _  | | | | |  | | |___  | |_| | |_| | |_| |_) | |_| | |_       |
#   |    |_| |_| |_| |_|  |_|_____|  \___/ \__,_|\__| .__/ \__,_|\__|      |
#   |                                               |_|                    |
#   +----------------------------------------------------------------------+
#   |  Toplevel code for show the actual HTML page                         |
#   '----------------------------------------------------------------------'


@cmk.gui.pages.register("logwatch")
def page_show():
    site = html.request.var("site")  # optional site hint
    host_name = html.request.var("host", "")
    file_name = html.request.var("file", "")

    # Fix problem when URL is missing certain illegal characters
    try:
        file_name = form_file_to_ext(
            find_matching_logfile(site, host_name, form_file_to_int(file_name)))
    except livestatus.MKLivestatusNotFoundError:
        pass  # host_name log dir does not exist

    # Acknowledging logs is supported on
    # a) all logs on all hosts
    # b) all logs on one host_name
    # c) one log on one host_name
    if html.request.has_var('_ack') and not html.request.var("_do_actions") == _("No"):
        sites.live().set_auth_domain('action')
        do_log_ack(site, host_name, file_name)
        return

    if not host_name:
        show_log_list()
        return

    if file_name:
        show_file(site, host_name, file_name)
    else:
        show_host_log_list(site, host_name)


def button_all_logfiles():
    html.context_button(_("All Logfiles"), html.makeuri([('site', ''), ('host', ''), ('file', '')]))


# Shows a list of all problematic logfiles grouped by host
def show_log_list():
    html.header(_("All Problematic Logfiles"))

    html.begin_context_buttons()
    html.context_button(_("Analyze Patterns"),
                        "%swato.py?mode=pattern_editor" % html.request.var('master_url', ''),
                        'analyze')
    ack_button()
    html.end_context_buttons()

    for site, host_name, logs in all_logs():
        if not logs:
            continue

        all_logs_empty = not any([parse_file(site, host_name, file_name) for file_name in logs])

        if all_logs_empty:
            continue  # Logfile vanished

        html.h2(html.render_a(host_name, href=html.makeuri([('site', site), ('host', host_name)])))
        list_logs(site, host_name, logs)
    html.footer()


def services_url(site, host_name):
    return html.makeuri_contextless([("view_name", "host"), ("site", site), ("host", host_name)],
                                    filename="view.py")


def analyse_url(site, host_name, file_name='', match=''):
    return html.makeuri_contextless(
        [
            ("mode", "pattern_editor"),
            ("site", site),
            ("host", host_name),
            ("file", file_name),
            ("match", match),
        ],
        filename="wato.py",
    )


# Shows all problematic logfiles of a host
def show_host_log_list(site, host_name):
    html.header(_("Logfiles of host %s") % host_name)

    html.begin_context_buttons()
    html.context_button(_("Services"), services_url(site, host_name), 'services')
    button_all_logfiles()
    html.context_button(_("Analyze host patterns"), analyse_url(site, host_name), 'analyze')
    ack_button(site, host_name)
    html.end_context_buttons()

    html.open_table(class_=["data"])
    list_logs(site, host_name, logfiles_of_host(site, host_name))
    html.close_table()

    html.footer()


# Displays a table of logfiles
def list_logs(site, host_name, logfile_names):
    with table_element(empty_text=_("No logs found for this host.")) as table:

        for file_name in logfile_names:
            table.row()
            file_display = form_file_to_ext(file_name)
            uri = html.makeuri([('site', site), ('host', host_name), ('file', file_display)])
            logfile_link = html.render_a(file_display, href=uri)

            try:
                log_chunks = parse_file(site, host_name, file_name)
                if not log_chunks:
                    continue  # Logfile vanished

                worst_log = get_worst_chunk(log_chunks)
                last_log = get_last_chunk(log_chunks)
                state = worst_log['level']
                state_name = form_level(state)

                table.cell(_("Level"), state_name, css="state%d" % state)
                table.cell(_("Logfile"), logfile_link)
                table.cell(_("Last Entry"), form_datetime(last_log['datetime']))
                table.cell(_("Entries"), len(log_chunks), css="number")

            except Exception:
                if config.debug:
                    raise
                table.cell(_("Level"), "")
                table.cell(_("Logfile"), logfile_link)
                table.cell(_("Last Entry"), "")
                table.cell(_("Entries"), _("Corrupted"))


def show_file(site, host_name, file_name):
    int_filename = form_file_to_int(file_name)

    html.header(_("Logfiles of Host %s: %s") % (host_name, file_name))
    html.begin_context_buttons()
    html.context_button(_("Services"), services_url(site, host_name), 'services')
    html.context_button(_("All Logfiles of Host"), html.makeuri([('file', '')]))
    button_all_logfiles()
    html.context_button(_("Analyze patterns"), analyse_url(site, host_name, file_name), 'analyze')

    if html.request.var('_hidecontext', 'no') == 'yes':
        hide_context_label = _('Show Context')
        hide_context_param = 'no'
        hide = True
    else:
        hide_context_label = _('Hide Context')
        hide_context_param = 'yes'
        hide = False

    try:
        log_chunks = parse_file(site, host_name, int_filename, hide)
    except Exception as e:
        if config.debug:
            raise
        html.end_context_buttons()
        html.show_error(_("Unable to show logfile: <b>%s</b>") % e)
        html.footer()
        return

    if log_chunks is None:
        html.end_context_buttons()
        html.show_error(_("The logfile does not exist."))
        html.footer()
        return

    elif log_chunks == []:
        html.end_context_buttons()
        html.message(_("This logfile contains no unacknowledged messages."))
        html.footer()
        return

    ack_button(site, host_name, int_filename)
    html.context_button(hide_context_label, html.makeuri([('_hidecontext', hide_context_param)]))

    html.end_context_buttons()

    html.open_div(id_="logwatch")
    for log in log_chunks:
        html.open_div(class_=["chunk"])
        html.open_table(class_=["section"])
        html.open_tr()
        html.td(form_level(log['level']), class_=form_level(log['level']))
        html.td(form_datetime(log['datetime']), class_="date")
        html.close_tr()
        html.close_table()

        for line in log['lines']:
            html.open_p(class_=line['class'])
            html.icon_button(analyse_url(site, host_name, file_name, line['line']),
                             _("Analyze this line"), "analyze")
            html.write_text(line['line'].replace(" ", "&nbsp;").replace("\1", "<br>"))
            html.close_p()

        html.close_div()

    html.close_div()
    html.footer()


#.
#   .--Acknowledge---------------------------------------------------------.
#   |       _        _                        _          _                 |
#   |      / \   ___| | ___ __   _____      _| | ___  __| | __ _  ___      |
#   |     / _ \ / __| |/ / '_ \ / _ \ \ /\ / / |/ _ \/ _` |/ _` |/ _ \     |
#   |    / ___ \ (__|   <| | | | (_) \ V  V /| |  __/ (_| | (_| |  __/     |
#   |   /_/   \_\___|_|\_\_| |_|\___/ \_/\_/ |_|\___|\__,_|\__, |\___|     |
#   |                                                      |___/           |
#   +----------------------------------------------------------------------+
#   |  Code for acknowleding (i.e. deleting) log files                     |
#   '----------------------------------------------------------------------'


def ack_button(site=None, host_name=None, int_filename=None):
    if not config.user.may("general.act") or (host_name and not may_see(site, host_name)):
        return

    if int_filename:
        label = _("Clear Log")
    else:
        label = _("Clear Logs")

    urivars = [('_ack', '1')]
    if int_filename:
        urivars.append(("file", int_filename))
    html.context_button(label, html.makeactionuri(urivars), 'delete')


def do_log_ack(site, host_name, file_name):
    logs_to_ack = []
    if not host_name and not file_name:  # all logs on all hosts
        for this_site, this_host, logs in all_logs():
            for int_filename in logs:
                file_display = form_file_to_ext(int_filename)
                logs_to_ack.append((this_site, this_host, int_filename, file_display))
        ack_msg = _('all logfiles on all hosts')

    elif host_name and not file_name:  # all logs on one host
        for int_filename in logfiles_of_host(site, host_name):
            file_display = form_file_to_ext(int_filename)
            logs_to_ack.append((site, host_name, int_filename, file_display))
        ack_msg = _('all logfiles of host %s') % html.render_text(host_name)

    elif host_name and file_name:  # one log on one host
        int_filename = form_file_to_int(file_name)
        logs_to_ack = [(site, host_name, int_filename, form_file_to_ext(int_filename))]
        ack_msg = html.render_text(_('the log file %s on host %s') % (file_name, host_name))

    else:
        for this_site, this_host, logs in all_logs():
            file_display = form_file_to_ext(file_name)
            if file_name in logs:
                logs_to_ack.append((this_site, this_host, file_name, file_display))
        ack_msg = html.render_text(_('log file %s on all hosts') % file_name)

    html.header(_("Acknowledge %s") % ack_msg)

    html.begin_context_buttons()
    button_all_logfiles()
    if host_name:
        html.context_button(_("All Logfiles of Host"), html.makeuri([('file', '')]))
    if host_name and file_name:
        html.context_button(_("Back to Logfile"), html.makeuri([]))
    html.end_context_buttons()

    ack = html.request.var('_ack')
    if not html.confirm(
            _("Do you really want to acknowledge %s by <b>deleting</b> all stored messages?") %
            ack_msg):
        html.footer()
        return

    if not config.user.may("general.act"):
        html.h1(_('Permission denied'), class_=["error"])
        html.div(_('You are not allowed to acknowledge %s') % ack_msg, class_=["error"])
        html.footer()
        return

    # filter invalid values
    if ack != '1':
        raise MKUserError('_ack', _('Invalid value for ack parameter.'))

    for this_site, this_host, int_filename, display_name in logs_to_ack:
        try:
            acknowledge_logfile(this_site, this_host, int_filename, display_name)
        except Exception as e:
            html.show_error(_('The log file <tt>%s</tt> of host <tt>%s</tt> could not be deleted: %s.') % \
                                      (display_name, this_host, e))
            html.footer()
            return

    html.message('<b>%s</b><p>%s</p>' %
                 (_('Acknowledged %s') % ack_msg, _('Acknowledged all messages in %s.') % ack_msg))
    html.footer()


def acknowledge_logfile(site, host_name, int_filename, display_name):
    if not may_see(site, host_name):
        raise MKAuthException(_('Permission denied.'))

    command = "MK_LOGWATCH_ACKNOWLEDGE;%s;%s" % (host_name, int_filename)
    sites.live().command("[%d] %s" % (int(time.time()), command), site)


#.
#   .--Parsing-------------------------------------------------------------.
#   |                  ____                _                               |
#   |                 |  _ \ __ _ _ __ ___(_)_ __   __ _                   |
#   |                 | |_) / _` | '__/ __| | '_ \ / _` |                  |
#   |                 |  __/ (_| | |  \__ \ | | | | (_| |                  |
#   |                 |_|   \__,_|_|  |___/_|_| |_|\__, |                  |
#   |                                              |___/                   |
#   +----------------------------------------------------------------------+
#   |  Parsing the contents of a logfile                                   |
#   '----------------------------------------------------------------------'


def parse_file(site, host_name, file_name, hidecontext=False):
    log_chunks = []
    try:
        chunk = None
        lines = get_logfile_lines(site, host_name, file_name)
        if lines is None:
            return None
        # skip hash line. this doesn't exist in older files
        while lines and lines[0].startswith('#'):
            lines = lines[1:]

        for line in lines:
            line = line.strip()
            if line == '':
                continue

            if line[:3] == '<<<':  # new chunk begins
                log_lines = []
                chunk = {'lines': log_lines}
                log_chunks.append(chunk)

                # New header line
                date, logtime, level = line[3:-3].split(' ')

                # Save level as integer to make it better comparable
                if level == 'CRIT':
                    chunk['level'] = 2
                elif level == 'WARN':
                    chunk['level'] = 1
                elif level == 'OK':
                    chunk['level'] = 0
                else:
                    chunk['level'] = 0

                # Gather datetime object
                # Python versions below 2.5 don't provide datetime.datetime.strptime.
                # Use the following instead:
                #chunk['datetime'] = datetime.datetime.strptime(date + ' ' + logtime, "%Y-%m-%d %H:%M:%S")
                chunk['datetime'] = datetime.datetime(
                    *time.strptime(date + ' ' + logtime, "%Y-%m-%d %H:%M:%S")[0:5])

            elif chunk:  # else: not in a chunk?!
                # Data line
                line_display = line[2:]

                # Classify the line for styling
                if line[0] == 'W':
                    line_level = 1
                    line_class = 'WARN'

                elif line[0] == 'u':
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
                    continue  # ignore this line

                log_lines.append({'level': line_level, 'class': line_class, 'line': line_display})
    except Exception as e:
        if config.debug:
            raise
        raise MKGeneralException(
            html.render_text(_("Cannot parse log file %s: %s") % (file_name, e)))

    return log_chunks


def get_worst_chunk(log_chunks):
    worst_level = 0
    worst_log = log_chunks[0]

    for chunk in log_chunks:
        for line in chunk['lines']:
            if line['level'] >= worst_level:
                worst_level = line['level']
                worst_log = chunk

    return worst_log


def get_last_chunk(log_chunks):
    last_log = None
    last_datetime = None

    for chunk in log_chunks:
        if not last_datetime or chunk['datetime'] > last_datetime:
            last_datetime = chunk['datetime']
            last_log = chunk

    return last_log


#.
#   .--Constants-----------------------------------------------------------.
#   |              ____                _              _                    |
#   |             / ___|___  _ __  ___| |_ __ _ _ __ | |_ ___              |
#   |            | |   / _ \| '_ \/ __| __/ _` | '_ \| __/ __|             |
#   |            | |__| (_) | | | \__ \ || (_| | | | | |_\__ \             |
#   |             \____\___/|_| |_|___/\__\__,_|_| |_|\__|___/             |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Definition of various constants - also used by WATO                  |
#   '----------------------------------------------------------------------'

nagios_illegal_chars = '`;~!$%^&*|\'"<>?,()='


def level_name(level):
    if level == 'W':
        return 'WARN'
    elif level == 'C':
        return 'CRIT'
    elif level == 'O':
        return 'OK'
    return 'OK'


def level_state(level):
    if level == 'W':
        return 1
    elif level == 'C':
        return 2
    elif level == 'O':
        return 0
    return 0


#.
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   |  Various helper functions                                            |
#   '----------------------------------------------------------------------'


def form_level(level):
    levels = ['OK', 'WARN', 'CRIT', 'UNKNOWN']
    return levels[level]


def form_file_to_int(f):
    return f.replace('/', '\\')


def form_file_to_ext(f):
    return f.replace('\\', '/')


def form_datetime(dt, fmt='%Y-%m-%d %H:%M:%S'):
    return dt.strftime(fmt)


#.
#   .--Access--------------------------------------------------------------.
#   |                       _                                              |
#   |                      / \   ___ ___ ___  ___ ___                      |
#   |                     / _ \ / __/ __/ _ \/ __/ __|                     |
#   |                    / ___ \ (_| (_|  __/\__ \__ \                     |
#   |                   /_/   \_\___\___\___||___/___/                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Code for fetching data and for acknowledging. Now all via Live-     |
#   |  status.                                                             |
#   '----------------------------------------------------------------------'


def logfiles_of_host(site, host_name):
    if site:  # Honor site hint if available
        sites.live().set_only_sites([site])
    file_names = sites.live().query_value("GET hosts\n"
                                          "Columns: mk_logwatch_files\n"
                                          "Filter: name = %s\n" % livestatus.lqencode(host_name))
    if site:  # Honor site hint if available
        sites.live().set_only_sites(None)
    if file_names is None:  # Not supported by that Livestatus version
        raise MKGeneralException(
            _("The monitoring core of the target site '%s' has the version '%s'. That "
              "does not support fetching logfile information. Please upgrade "
              "to a newer version.") % (site, sites.state(site)["program_version"]))
    return file_names


def get_logfile_lines(site, host_name, file_name):
    if site:  # Honor site hint if available
        sites.live().set_only_sites([site])
    query = \
        "GET hosts\n" \
        "Columns: mk_logwatch_file:file:%s\n" \
        "Filter: name = %s\n" % (livestatus.lqencode(file_name.replace('\\', '\\\\').replace(' ', '\\s')), livestatus.lqencode(host_name))
    file_content = sites.live().query_value(query)
    if site:  # Honor site hint if available
        sites.live().set_only_sites(None)
    if file_content is None:
        return None
    return file_content.splitlines()


def all_logs():
    sites.live().set_prepend_site(True)
    rows = sites.live().query("GET hosts\n" "Columns: name mk_logwatch_files\n")
    sites.live().set_prepend_site(False)
    return rows


def may_see(site, host_name):
    if config.user.may("general.see_all"):
        return True

    host_found = False
    try:
        if site:
            sites.live().set_only_sites([site])
        # Note: This query won't work in a distributed setup and no site given as argument
        # livestatus connection is setup with AuthUser
        host_found = sites.live().query_value("GET hosts\nStats: state >= 0\nFilter: name = %s\n" %
                                              livestatus.lqencode(host_name)) > 0
    finally:
        sites.live().set_only_sites(None)

    return host_found


# Tackle problem, where some characters are missing in the service
# description
def find_matching_logfile(site, host_name, file_name):
    existing_files = logfiles_of_host(site, host_name)
    if file_name in existing_files:
        return file_name  # Most common case

    for logfile_name in existing_files:
        if remove_illegal_service_characters(logfile_name) == file_name:
            return logfile_name

    # Not found? Fall back to original name. Logfile might be cleared.
    return file_name


def remove_illegal_service_characters(file_name):
    return "".join([c for c in file_name if c not in nagios_illegal_chars])
