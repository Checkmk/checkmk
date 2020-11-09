#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Handling of the audit logfiles"""

import re
import time
from typing import List, Tuple, Iterator

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
from cmk.gui.exceptions import FinalizeRequest
from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.plugins.wato import (
    WatoMode,
    ActionResult,
    mode_registry,
    flash,
    redirect,
    make_confirm_link,
)
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    PageMenuPopup,
    make_simple_link,
    make_display_options_dropdown,
)


@mode_registry.register
class ModeAuditLog(WatoMode):
    log_path = watolib.changes.audit_log_path

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

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="log",
                    title=_("Actions"),
                    topics=[
                        PageMenuTopic(
                            title=_("Actions"),
                            entries=list(self._page_menu_entries_actions()),
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="export",
                    title=_("Export"),
                    topics=[
                        PageMenuTopic(
                            title=_("Export"),
                            entries=list(self._page_menu_entries_export()),
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=list(self._page_menu_entries_setup()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

        self._extend_display_dropdown(menu)
        return menu

    def _page_menu_entries_setup(self) -> Iterator[PageMenuEntry]:
        if config.user.may("wato.sites"):
            yield PageMenuEntry(
                title=_("View changes"),
                icon_name="activate",
                item=make_simple_link(watolib.folder_preserving_link([("mode", "changelog")])),
            )

    def _page_menu_entries_actions(self) -> Iterator[PageMenuEntry]:
        if not self._log_exists():
            return

        if not config.user.may("wato.auditlog"):
            return

        if not config.user.may("wato.edit"):
            return

        if config.user.may("wato.clear_auditlog"):
            yield PageMenuEntry(
                title=_("Clear log"),
                icon_name="trash",
                item=make_simple_link(
                    make_confirm_link(
                        url=html.makeactionuri([("_action", "clear")]),
                        message=_("Do you really want to clear the audit log?"),
                    )),
            )

    def _page_menu_entries_export(self) -> Iterator[PageMenuEntry]:
        if not self._log_exists():
            return

        if not config.user.may("wato.auditlog"):
            return

        if not config.user.may("wato.edit"):
            return

        if not config.user.may("general.csv_export"):
            return

        yield PageMenuEntry(
            title=_("Export CSV"),
            icon_name="download_csv",
            item=make_simple_link(html.makeactionuri([("_action", "csv")])),
        )

    def _extend_display_dropdown(self, menu: PageMenu) -> None:
        display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())

        display_dropdown.topics.insert(
            0,
            PageMenuTopic(
                title=_("Filter"),
                entries=[
                    PageMenuEntry(
                        title=_("Filter view"),
                        icon_name="filters_set" if html.form_submitted("options") else "filters",
                        item=PageMenuPopup(self._render_filter_form()),
                        name="filters",
                        is_shortcut=True,
                    ),
                ],
            ))

    def _render_filter_form(self) -> str:
        with html.plugged():
            self._display_audit_log_options()
            return html.drain()

    def _log_exists(self):
        return self.log_path.exists()

    def action(self) -> ActionResult:
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

        return None

    def page(self):
        audit = self._parse_audit_log()

        if not audit:
            html.show_message(_("The audit log is empty."))

        elif self._options["display"] == "daily":
            self._display_daily_audit_log(audit)

        else:
            self._display_multiple_days_audit_log(audit)

    def _display_daily_audit_log(self, log):
        log, times = self._get_next_daily_paged_log(log)

        self._display_page_controls(*times)

        if display_options.enabled(display_options.T):
            html.h3(_("Audit log for %s") % render.date(times[0]))

        self._display_log(log)

        self._display_page_controls(*times)

    def _display_multiple_days_audit_log(self, log):
        log = self._get_multiple_days_log_entries(log)

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
            # No entries today, but log not empty -> go back in time
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
            if first_log_index is None and start_time <= t < end_time:
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
                              minvalue=1,
                              unit=_("days"),
                              default_value=1,
                          )),
                     ],
                 )),
            ],
            optional_keys=[],
        )

    def _clear_audit_log_after_confirm(self) -> ActionResult:
        self._clear_audit_log()
        flash(_("Cleared audit log."))
        return redirect(self.mode_url())

    def _clear_audit_log(self):
        if not self.log_path.exists():
            return

        newpath = self.log_path.with_name(self.log_path.name + time.strftime(".%Y-%m-%d"))
        # The suppressions are needed because of https://github.com/PyCQA/pylint/issues/1660
        if newpath.exists():
            n = 1
            while True:
                n += 1
                with_num = newpath.with_name(newpath.name + "-%d" % n)
                if not with_num.exists():
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

    def _export_audit_log(self) -> ActionResult:
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

            if self._filter_entry(user, action, text):  # TODO: Already filtered?!
                continue

            html.write_text(','.join((render.date(int(t)), render.time_of_day(int(t)), linkinfo,
                                      user, action, '"' + text + '"')) + '\n')
        return FinalizeRequest(code=200)

    def _parse_audit_log(self) -> List[Tuple[int, str, str, str, str]]:
        if not self.log_path.exists():
            return []

        entries = []
        with self.log_path.open(encoding="utf-8") as fp:
            for line in fp:
                splitted = line.rstrip().split(None, 4)
                if len(splitted) == 5 and splitted[0].isdigit():
                    t, linkinfo, user, action, text = splitted
                    if not self._filter_entry(user, action, text):
                        entries.append((int(t), linkinfo, user, action, text))
        entries.reverse()
        return entries

    def _filter_entry(self, user, action, text):
        if not self._options["filter_regex"]:
            return False

        for val in [user, action, text]:
            if re.search(self._options["filter_regex"], val):
                return False

        return True
