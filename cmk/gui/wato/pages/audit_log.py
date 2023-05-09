#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Handling of the audit logfiles"""

import re
import time
from typing import List, Iterator

import cmk.utils.render as render

import cmk.gui.config as config
from cmk.gui.table import table_element
import cmk.gui.watolib as watolib
from cmk.gui import escaping
from cmk.gui.watolib.changes import AuditLogStore, ObjectRefType
from cmk.gui.userdb import UserSelection
from cmk.gui.valuespec import (
    RegExp,
    CascadingDropdown,
    Integer,
    AbsoluteDate,
    DropdownChoice,
    TextAscii,
)
from cmk.gui.type_defs import Choices, ActionResult
from cmk.gui.utils.urls import makeuri
from cmk.gui.exceptions import FinalizeRequest, MKUserError
from cmk.gui.globals import html, request, display_options
from cmk.gui.i18n import _
from cmk.gui.plugins.wato import (
    WatoMode,
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
    PageMenuSidePopup,
    make_simple_link,
    make_display_options_dropdown,
)
from cmk.gui.wato.pages.activate_changes import render_object_ref


@mode_registry.register
class ModeAuditLog(WatoMode):
    @classmethod
    def name(cls):
        return "auditlog"

    @classmethod
    def permissions(cls):
        return ["auditlog"]

    def __init__(self):
        self._options = {key: vs.default_value() for key, vs in self._audit_log_options()}
        super(ModeAuditLog, self).__init__()
        self._store = AuditLogStore(AuditLogStore.make_path())
        self._show_details = html.request.get_integer_input_mandatory("show_details", 1) == 1

    def title(self):
        return _("Audit log")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="log",
                    title=_("Audit log"),
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
                icon_name="delete",
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
                        icon_name="filters_set" if html.form_submitted("options") else "filter",
                        item=PageMenuSidePopup(self._render_filter_form()),
                        name="filters",
                        is_shortcut=True,
                    ),
                ],
            ))

        display_dropdown.topics.insert(
            0,
            PageMenuTopic(
                title=_("Details"),
                entries=[
                    PageMenuEntry(
                        title=_("Show details"),
                        icon_name="checked_checkbox" if self._show_details else "checkbox",
                        item=make_simple_link(
                            html.makeactionuri([
                                ("show_details", "0" if self._show_details else "1"),
                            ])),
                        name="show_details",
                        css_classes=["toggle"],
                    )
                ],
            ))

    def _render_filter_form(self) -> str:
        with html.plugged():
            self._display_audit_log_options()
            return html.drain()

    def _log_exists(self):
        return self._store.exists()

    def action(self) -> ActionResult:
        if html.request.var("_action") == "clear":
            config.user.need_permission("wato.auditlog")
            config.user.need_permission("wato.clear_auditlog")
            config.user.need_permission("wato.edit")
            return self._clear_audit_log_after_confirm()

        if html.request.var("_action") == "csv":
            config.user.need_permission("wato.auditlog")
            return self._export_audit_log(self._parse_audit_log())

        return None

    def page(self):
        self._options.update(self._get_audit_log_options_from_request())

        audit = self._parse_audit_log()

        if not audit:
            html.show_message(_("Found no matching entry."))

        elif self._options["display"] == "daily":
            self._display_daily_audit_log(audit)

        else:
            self._display_multiple_days_audit_log(audit)

    def _get_audit_log_options_from_request(self):
        options = {}
        for name, vs in self._audit_log_options():
            if not list(html.request.itervars("options_" + name)):
                continue

            try:
                value = vs.from_html_vars("options_" + name)
                vs.validate_value(value, "options_" + name)
                options[name] = value
            except MKUserError as e:
                html.add_user_error(e.varname, e)
        return options

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
            for entry in log:
                table.row()
                table.cell(_("Time"),
                           html.render_nobr(render.date_and_time(float(entry.time))),
                           css="narrow")
                user = ('<i>%s</i>' % _('internal')) if entry.user_id == '-' else entry.user_id
                table.cell(_("User"), html.render_text(user), css="nobreak narrow")

                table.cell(_("Object type"),
                           entry.object_ref.object_type.name if entry.object_ref else "",
                           css="narrow")
                table.cell(_("Object"), render_object_ref(entry.object_ref) or "", css="narrow")

                text = escaping.escape_text(entry.text).replace("\n", "<br>\n")
                table.cell(_("Summary"), text)

                if self._show_details:
                    diff_text = escaping.escape_text(entry.diff_text).replace(
                        "\n", "<br>\n") if entry.diff_text else ""
                    table.cell(_("Details"), diff_text)

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
        end_time = start_time \
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
        for index, entry in enumerate(log):
            if entry.time >= end_time:
                # This log is too new
                continue
            if first_log_index is None and start_time <= entry.time < end_time:
                # This is a log for this day. Save the first index
                if first_log_index is None:
                    first_log_index = index

                    # When possible save the timestamp of the previous log
                    if index > 0:
                        next_log_time = int(log[index - 1][0])

            elif entry.time < start_time and last_log_index is None:
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
                ("options_start_1_day", time.strftime("%d", time.localtime(t))),
                ("options_start_1_month", time.strftime("%m", time.localtime(t))),
                ("options_start_1_year", time.strftime("%Y", time.localtime(t))),
                ("options_start_sel", "1"),
            ]

        if next_log_time is not None:
            html.icon_button(html.makeactionuri([
                ("options_start_sel", "0"),
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

        html.begin_form("options", method="GET")

        self._show_audit_log_options_controls()

        html.open_div(class_="side_popup_content")
        if html.has_user_errors():
            html.show_user_errors()

        for name, vs in self._audit_log_options():
            html.render_floating_option(name, "single", "options_", vs, self._options[name])

        html.close_div()

        html.hidden_fields()
        html.end_form()

    def _show_audit_log_options_controls(self):
        html.open_div(class_="side_popup_controls")

        html.open_div(class_="update_buttons")
        html.button("apply", _("Apply"), "submit")
        html.buttonlink(makeuri(request, [], remove_prefix="options_"), _("Reset"))
        html.close_div()

        html.close_div()

    def _audit_log_options(self):
        object_types: Choices = [
            ("", _("All object types")),
            (None, _("No object type")),
        ] + [(t.name, t.name) for t in ObjectRefType]

        return [
            ("object_type", DropdownChoice(
                title=_("Object type"),
                choices=object_types,
            )),
            ("object_ident", TextAscii(title=_("Object"),)),
            (
                "user_id",
                UserSelection(
                    title=_("User"),
                    only_contacts=False,
                    none=_("All users"),
                ),
            ),
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
        ]

    def _clear_audit_log_after_confirm(self) -> ActionResult:
        self._clear_audit_log()
        flash(_("Cleared audit log."))
        return redirect(self.mode_url())

    def _clear_audit_log(self):
        self._store.clear()

    def _export_audit_log(self, audit: List[AuditLogStore.Entry]) -> ActionResult:
        html.set_output_format("csv")

        if self._options["display"] == "daily":
            filename = "wato-auditlog-%s_%s.csv" % (render.date(
                time.time()), render.time_of_day(time.time()))
        else:
            filename = "wato-auditlog-%s_%s_days.csv" % (render.date(
                time.time()), self._options["display"][1])

        html.response.headers["Content-Disposition"] = "attachment; filename=\"%s\"" % filename

        titles = [
            _('Date'),
            _('Time'),
            _('Object type'),
            _('Object'),
            _('User'),
            _('Action'),
            _('Summary'),
        ]

        if self._show_details:
            titles.append(_('Details'))

        html.write(','.join(titles) + '\n')
        for entry in audit:
            columns = [
                render.date(int(entry.time)),
                render.time_of_day(int(entry.time)),
                entry.object_ref.object_type.name if entry.object_ref else "",
                entry.object_ref.ident if entry.object_ref else "",
                entry.user_id,
                entry.action,
                '"' + escaping.strip_tags(entry.text).replace('"', "'") + '"',
            ]

            if self._show_details:
                columns.append('"' + escaping.strip_tags(entry.diff_text).replace('"', "'") + '"')

            html.write(','.join(columns) + '\n')
        return FinalizeRequest(code=200)

    def _parse_audit_log(self) -> List[AuditLogStore.Entry]:
        return list(reversed([e for e in self._store.read() if self._filter_entry(e)]))

    def _filter_entry(self, entry: AuditLogStore.Entry) -> bool:
        if self._options["object_type"] != "":
            if entry.object_ref is None and self._options["object_type"] is not None:
                return False
            if (entry.object_ref and
                    entry.object_ref.object_type.name != self._options["object_type"]):
                return False

        if self._options["object_ident"] != "":
            if entry.object_ref is None and self._options["object_ident"] is not None:
                return False
            if (entry.object_ref and entry.object_ref.ident != self._options["object_ident"]):
                return False

        if self._options["user_id"] is not None:
            if entry.user_id != self._options["user_id"]:
                return False

        if self._options["filter_regex"]:
            # TODO str(entry.text) is needed, because
            # ABCEditGlobalSettingMode.action() uses HTML() for add
            # change. Remove this and handle compatibility one day...
            return any(
                re.search(self._options["filter_regex"], val)
                for val in [entry.user_id, entry.action,
                            str(entry.text)])

        return True
