#!/usr/bin/env python
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
"""Handling of the audit logfiles"""

import re
import time

from pathlib2 import Path

import cmk.utils.render as render

import cmk.gui.config as config
from cmk.gui.table import table_element
import cmk.gui.watolib as watolib
from cmk.gui.display_options import display_options
from cmk.gui.valuespec import (
    Dictionary,
    RegExp,
    CascadingDropdown,
    Integer,
    AbsoluteDate,
)
from cmk.gui.plugins.wato.utils.context_buttons import (
    changelog_button,
    home_button,
)
from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.plugins.wato import WatoMode, mode_registry, wato_confirm


@mode_registry.register
class ModeAuditLog(WatoMode):
    log_path = Path(watolib.changes.audit_log_path)

    @classmethod
    def name(cls):
        return "auditlog"

    @classmethod
    def permissions(cls):
        return ["auditlog"]

    def __init__(self):
        self._options = self._vs_audit_log_options().default_value()
        super(ModeAuditLog, self).__init__()

    def title(self):
        return _("Audit log")

    def buttons(self):
        changelog_button()
        home_button()
        if self._log_exists() and config.user.may("wato.clear_auditlog") \
           and config.user.may("wato.auditlog") and config.user.may("wato.edit"):
            html.context_button(_("Download"), html.makeactionuri([("_action", "csv")]), "download")
            if config.user.may("wato.edit"):
                html.context_button(_("Clear Log"), html.makeactionuri([("_action", "clear")]),
                                    "trash")

    def _log_exists(self):
        return self.log_path.exists()

    def action(self):
        if html.request.var("_action") == "clear":
            config.user.need_permission("wato.auditlog")
            config.user.need_permission("wato.clear_auditlog")
            config.user.need_permission("wato.edit")
            return self._clear_audit_log_after_confirm()

        vs_options = self._vs_audit_log_options()
        value = vs_options.from_html_vars("options")
        vs_options.validate_value(value, "options")
        self._options = value

        if html.request.var("_action") == "csv":
            config.user.need_permission("wato.auditlog")
            return self._export_audit_log()

    def page(self):
        audit = self._parse_audit_log()

        if not audit:
            html.show_info(_("The audit log is empty."))

        elif self._options["display"] == "daily":
            self._display_daily_audit_log(audit)

        else:
            self._display_multiple_days_audit_log(audit)

    def _display_daily_audit_log(self, log):
        log, times = self._get_next_daily_paged_log(log)

        self._display_audit_log_options()

        self._display_page_controls(*times)

        if display_options.enabled(display_options.T):
            html.h3(_("Audit log for %s") % render.date(times[0]))

        self._display_log(log)

        self._display_page_controls(*times)

    def _display_multiple_days_audit_log(self, log):
        log = self._get_multiple_days_log_entries(log)

        self._display_audit_log_options()

        if display_options.enabled(display_options.T):
            html.h3(
                _("Audit log for %s and %d days ago") %
                (render.date(self._get_start_date()), self._options["display"][1]))

        self._display_log(log)

    def _display_log(self, log):
        with table_element(css="data wato auditlog audit",
                           limit=None,
                           sortable=False,
                           searchable=False) as table:
            for t, linkinfo, user, _action, text in log:
                table.row()
                table.cell(_("Object"), self._render_logfile_linkinfo(linkinfo))
                table.cell(_("Time"), html.render_nobr(render.date_and_time(float(t))))
                user = ('<i>%s</i>' % _('internal')) if user == '-' else user
                table.cell(_("User"), html.render_text(user), css="nobreak")

                # This must not be attrencoded: The entries are encoded when writing to the log.
                table.cell(_("Change"), text.replace("\\n", "<br>\n"), css="fill")

    def _get_next_daily_paged_log(self, log):
        start = self._get_start_date()

        while True:
            log_today, times = self._paged_log_from(log, start)
            if len(log) == 0 or len(log_today) > 0:
                return log_today, times
            else:  # No entries today, but log not empty -> go back in time
                start -= 24 * 3600

    def _get_start_date(self):
        if self._options["start"] == "now":
            st = time.localtime()
            return int(
                time.mktime(time.struct_time(
                    (st.tm_year, st.tm_mon, st.tm_mday, 0, 0, 0, 0, 0, 0))))
        return int(self._options["start"][1])

    def _get_multiple_days_log_entries(self, log):
        start_time = self._get_start_date() + 86399
        end_time   = start_time \
                     - ((self._options["display"][1] * 86400) + 86399)

        logs = []

        for entry in log:
            if entry[0] <= start_time and entry[0] >= end_time:
                logs.append(entry)

        return logs

    def _paged_log_from(self, log, start):
        start_time, end_time = self._get_timerange(start)
        previous_log_time = None
        next_log_time = None
        first_log_index = None
        last_log_index = None
        for index, (t, _linkinfo, _user, _action, _text) in enumerate(log):
            if t >= end_time:
                # This log is too new
                continue
            elif first_log_index is None \
                  and t < end_time \
                  and t >= start_time:
                # This is a log for this day. Save the first index
                if first_log_index is None:
                    first_log_index = index

                    # When possible save the timestamp of the previous log
                    if index > 0:
                        next_log_time = int(log[index - 1][0])

            elif t < start_time and last_log_index is None:
                last_log_index = index
                # This is the next log after this day
                previous_log_time = int(log[index][0])
                # Finished!
                break

        if last_log_index is None:
            last_log_index = len(log)

        return log[first_log_index:last_log_index], (start_time, end_time, previous_log_time,
                                                     next_log_time)

    def _display_page_controls(self, start_time, end_time, previous_log_time, next_log_time):
        html.open_div(class_="paged_controls")

        def time_url_args(t):
            return [
                ("options_p_start_1_day", time.strftime("%d", time.localtime(t))),
                ("options_p_start_1_month", time.strftime("%m", time.localtime(t))),
                ("options_p_start_1_year", time.strftime("%Y", time.localtime(t))),
                ("options_p_start_sel", "1"),
            ]

        if next_log_time is not None:
            html.icon_button(html.makeactionuri([
                ("options_p_start_sel", "0"),
            ]), _("Most recent events"), "start")

            html.icon_button(html.makeactionuri(time_url_args(next_log_time)),
                             "%s: %s" % (_("Newer events"), render.date(next_log_time)), "back")
        else:
            html.empty_icon_button()
            html.empty_icon_button()

        if previous_log_time is not None:
            html.icon_button(html.makeactionuri(time_url_args(previous_log_time)),
                             "%s: %s" % (_("Older events"), render.date(previous_log_time)),
                             "forth")
        else:
            html.empty_icon_button()

        html.close_div()

    def _get_timerange(self, t):
        st = time.localtime(int(t))
        start = int(
            time.mktime(time.struct_time((st[0], st[1], st[2], 0, 0, 0, st[6], st[7], st[8]))))
        end = start + 86399
        return start, end

    def _display_audit_log_options(self):
        if display_options.disabled(display_options.C):
            return

        valuespec = self._vs_audit_log_options()

        html.begin_form("options", method="GET")
        valuespec.render_input_as_form("options", {})

        html.button("options", _("Apply"))
        html.hidden_fields()
        html.end_form()

    def _vs_audit_log_options(self):
        return Dictionary(
            title=_("Options"),
            elements=[
                ("filter_regex", RegExp(
                    title=_("Filter pattern (RegExp)"),
                    mode="infix",
                )),
                ("start",
                 CascadingDropdown(
                     title=_("Start log from"),
                     default_value="now",
                     orientation="horizontal",
                     choices=[
                         ("now", _("Current date")),
                         ("time", _("Specific date"), AbsoluteDate()),
                     ],
                 )),
                ("display",
                 CascadingDropdown(
                     title=_("Display mode of entries"),
                     default_value="daily",
                     orientation="horizontal",
                     choices=[
                         ("daily", _("Daily paged display")),
                         ("number_of_days", _("Number of days from now (single page)"),
                          Integer(
                              minval=1,
                              unit=_("days"),
                              default_value=1,
                              allow_empty=False,
                          )),
                     ],
                 )),
            ],
            optional_keys=[],
        )

    def _clear_audit_log_after_confirm(self):
        c = wato_confirm(_("Confirm deletion of audit log"),
                         _("Do you really want to clear the audit log?"))
        if c:
            self._clear_audit_log()
            return None, _("Cleared audit log.")
        elif c is False:  # not yet confirmed
            return ""
        return None  # browser reload

    def _clear_audit_log(self):
        if not self.log_path.exists():
            return

        newpath = self.log_path.with_name(self.log_path.name + time.strftime(".%Y-%m-%d"))
        # The suppressions are needed because of https://github.com/PyCQA/pylint/issues/1660
        if newpath.exists():  # pylint: disable=no-member
            n = 1
            while True:
                n += 1
                with_num = newpath.with_name(newpath.name + "-%d" % n)
                if not with_num.exists():  # pylint: disable=no-member
                    newpath = with_num
                    break

        self.log_path.rename(newpath)

    def _render_logfile_linkinfo(self, linkinfo):
        if ':' in linkinfo:  # folder:host
            path, host_name = linkinfo.split(':', 1)
            if watolib.Folder.folder_exists(path):
                folder = watolib.Folder.folder(path)
                if host_name:
                    if folder.has_host(host_name):
                        host = folder.host(host_name)
                        url = host.edit_url()
                        title = host_name
                    else:
                        return host_name
                else:  # only folder
                    url = folder.url()
                    title = folder.title()
            else:
                return linkinfo
        else:
            return ""

        return html.render_a(title, href=url)

    def _export_audit_log(self):
        html.set_output_format("csv")

        if self._options["display"] == "daily":
            filename = "wato-auditlog-%s_%s.csv" % (render.date(
                time.time()), render.time_of_day(time.time()))
        else:
            filename = "wato-auditlog-%s_%s_days.csv" % (render.date(
                time.time()), self._options["display"][1])
        html.write(filename)

        html.response.headers["Content-Disposition"] = "attachment; filename=\"%s\"" % filename

        titles = (
            _('Date'),
            _('Time'),
            _('Linkinfo'),
            _('User'),
            _('Action'),
            _('Text'),
        )
        html.write(','.join(titles) + '\n')
        for t, linkinfo, user, action, text in self._parse_audit_log():
            if linkinfo == '-':
                linkinfo = ''

            if self._filter_entry(user, action, text):
                continue

            html.write_text(','.join((render.date(int(t)), render.time_of_day(int(t)), linkinfo,
                                      user, action, '"' + text + '"')) + '\n')
        return False

    def _parse_audit_log(self):
        if not self.log_path.exists():
            return []

        entries = []
        with self.log_path.open(encoding="utf-8") as fp:
            for line in fp:
                splitted = line.rstrip().split(None, 4)

                if len(splitted) == 5 and splitted[0].isdigit():
                    splitted[0] = int(splitted[0])

                    user, action, text = splitted[2:]
                    if self._filter_entry(user, action, text):
                        continue

                    entries.append(splitted)

        entries.reverse()

        return entries

    def _filter_entry(self, user, action, text):
        if not self._options["filter_regex"]:
            return False

        for val in [user, action, text]:
            if re.search(self._options["filter_regex"], val):
                return False

        return True
