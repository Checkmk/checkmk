#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Handling of the audit logfiles"""

import time
from collections.abc import Collection, Iterator

from cmk.utils import render

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import FinalizeRequest, MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import ContentDispositionType, request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_display_options_dropdown,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSidePopup,
    PageMenuTopic,
)
from cmk.gui.table import table_element
from cmk.gui.type_defs import ActionResult, Choices, PermissionName
from cmk.gui.userdb.store import load_users
from cmk.gui.utils import escaping
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link, makeactionuri, makeuri
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec import (
    AbsoluteDate,
    CascadingDropdown,
    DropdownChoice,
    Integer,
    RegExp,
    TextInput,
    ValueSpec,
)
from cmk.gui.wato.pages.activate_changes import render_object_ref
from cmk.gui.watolib.audit_log import AuditLogFilterRaw, AuditLogStore, build_audit_log_filter
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link
from cmk.gui.watolib.mode import ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.objref import ObjectRefType
from cmk.gui.watolib.paths import wato_var_dir


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeAuditLog)


class ModeAuditLog(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "auditlog"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["auditlog"]

    def __init__(self) -> None:
        self._options = {key: vs.default_value() for key, vs in self._audit_log_options()}
        super().__init__()
        self._current_audit_log = wato_var_dir() / "log" / "wato_audit.log"
        self._show_details = request.get_integer_input_mandatory("show_details", 1) == 1
        self._show_object_type = request.get_integer_input_mandatory("show_object_type", 1) == 1
        self._show_object = request.get_integer_input_mandatory("show_object", 1) == 1

    def title(self) -> str:
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
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=list(self._page_menu_entries_setup()),
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
            ],
            breadcrumb=breadcrumb,
        )

        if request.var("file_selection"):
            self._extend_display_dropdown(menu)
        return menu

    def _page_menu_entries_setup(self) -> Iterator[PageMenuEntry]:
        if user.may("wato.sites"):
            yield PageMenuEntry(
                title=_("Activate pending changes"),
                icon_name="activate",
                item=make_simple_link(folder_preserving_link([("mode", "changelog")])),
            )

    def _page_menu_entries_actions(self) -> Iterator[PageMenuEntry]:
        if not user.may("wato.auditlog"):
            return

        if not user.may("wato.edit"):
            return

        if user.may("wato.clear_auditlog") and request.var("file_selection"):
            vs_file_selection = self._vs_file_selection()
            file_selection = vs_file_selection.from_html_vars("file_selection")
            vs_file_selection.validate_value(file_selection, "file_selection")
            yield PageMenuEntry(
                title=_("Archive log"),
                icon_name="delete",
                item=make_simple_link(
                    make_confirm_delete_link(
                        url=makeactionuri(
                            request,
                            transactions,
                            [
                                ("_action", "clear"),
                            ],
                        ),
                        title=_("Archive current audit log"),
                        confirm_button=_("Archive"),
                    )
                ),
                is_enabled=wato_var_dir() / "log" / file_selection == self._current_audit_log,
                disabled_tooltip=_("You can only archive the current audit log"),
            )

    def _page_menu_entries_export(self) -> Iterator[PageMenuEntry]:
        if not user.may("wato.auditlog"):
            return

        if not user.may("wato.edit"):
            return

        if not user.may("general.csv_export"):
            return

        if request.var("file_selection"):
            yield PageMenuEntry(
                title=_("Export CSV"),
                icon_name="download_csv",
                item=make_simple_link(
                    makeactionuri(
                        request,
                        transactions,
                        [
                            ("_action", "csv"),
                            ("file_selection", request.var("file_selection")),
                        ],
                    )
                ),
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
            ),
        )

        display_dropdown.topics.insert(
            0,
            PageMenuTopic(
                title=_("Details"),
                entries=[
                    PageMenuEntry(
                        title=_("Show details"),
                        icon_name="toggle_on" if self._show_details else "toggle_off",
                        item=make_simple_link(
                            makeactionuri(
                                request,
                                transactions,
                                [
                                    ("show_details", "0" if self._show_details else "1"),
                                ],
                            )
                        ),
                        name="show_details",
                        css_classes=["toggle"],
                    ),
                    PageMenuEntry(
                        title=_("Show object type"),
                        icon_name="toggle_on" if self._show_object_type else "toggle_off",
                        item=make_simple_link(
                            makeactionuri(
                                request,
                                transactions,
                                [
                                    ("show_object_type", "0" if self._show_object_type else "1"),
                                ],
                            )
                        ),
                        name="show_object_type",
                        css_classes=["toggle"],
                    ),
                    PageMenuEntry(
                        title=_("Show object"),
                        icon_name="toggle_on" if self._show_object else "toggle_off",
                        item=make_simple_link(
                            makeactionuri(
                                request,
                                transactions,
                                [
                                    ("show_object", "0" if self._show_object else "1"),
                                ],
                            )
                        ),
                        name="show_object",
                        css_classes=["toggle"],
                    ),
                ],
            ),
        )

    def _render_filter_form(self) -> HTML:
        with output_funnel.plugged():
            self._display_audit_log_options()
            return HTML.without_escaping(output_funnel.drain())

    def action(self) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return None

        if request.var("_action") == "clear":
            user.need_permission("wato.auditlog")
            user.need_permission("wato.clear_auditlog")
            user.need_permission("wato.edit")
            return self._clear_audit_log_after_confirm()

        if request.var("_action") == "csv":
            user.need_permission("wato.auditlog")
            return self._export_audit_log(self._parse_audit_log())

        return redirect(makeuri(request, []))

    def page(self) -> None:
        with html.form_context("fileselection_form", method="POST"):
            if not request.has_var("file_selection"):
                html.write_text_permissive(_("Please choose an audit log to view:"))
                html.br()
                html.br()
            self._vs_file_selection().render_input("file_selection", None)
            html.button(varname="_view_log", title=_("View"), cssclass="hot")
            html.hidden_fields()

        if request.var("file_selection"):
            self._options.update(self._get_audit_log_options_from_request())
            self._show_audit_log()

    def _vs_file_selection(self):
        return DropdownChoice(
            title=_("File selection"),
            choices=self._get_audit_log_files(),
            no_preselect_title="",
        )

    def _get_audit_log_files(self) -> list[tuple[str, str]]:
        """
        Collect all audit log files in ~/var/checkmk/wato/log and sort like:

        wato_audit.log (current)
        wato_audit.log.2023-10-24-2
        wato_audit.log.2023-10-24
        wato_audit.log.2023-10-23-2
        wato_audit.log.2023-10-23
        wato_audit.log.2023-09-23
        """
        return sorted(
            [
                (
                    f.name,
                    f.name if f.name != "wato_audit.log" else "wato_audit.log (%s)" % _("current"),
                )
                for f in (wato_var_dir() / "log").glob("wato_audit.*")
            ],
            key=lambda x: x[1].split(".")[-1],
            reverse=True,
        )

    def _show_audit_log(self) -> None:
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
            if not list(request.itervars("options_" + name)):
                continue

            try:
                value = vs.from_html_vars("options_" + name)
                vs.validate_value(value, "options_" + name)
                options[name] = value
            except MKUserError as e:
                user_errors.add(e)
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
                _("Audit log for %s and %d days ago")
                % (render.date(self._get_start_date()), self._options["display"][1])
            )

        self._display_log(log)

    def _display_log(self, log):
        with table_element(
            css="data wato auditlog audit", limit=None, sortable=False, searchable=False
        ) as table:
            for entry in log:
                table.row()
                table.cell(
                    _("Time"),
                    HTMLWriter.render_nobr(render.date_and_time(float(entry.time))),
                    css=["narrow"],
                )
                user_txt = ("<i>%s</i>" % _("internal")) if entry.user_id == "-" else entry.user_id
                table.cell(_("User"), user_txt, css=["nobreak narrow"])

                if self._show_object_type:
                    table.cell(
                        _("Object type"),
                        entry.object_ref.object_type.name if entry.object_ref else "",
                        css=["narrow"],
                    )
                if self._show_object:
                    table.cell(
                        _("Object"), render_object_ref(entry.object_ref) or "", css=["narrow"]
                    )

                text = HTML.without_escaping(
                    escaping.escape_text(entry.text).replace("\n", "<br>\n")
                )
                table.cell(_("Summary"), text)

                if self._show_details:
                    diff_text = HTML.without_escaping(
                        escaping.escape_text(entry.diff_text).replace("\n", "<br>\n")
                        if entry.diff_text
                        else ""
                    )
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
                time.mktime(time.struct_time((st.tm_year, st.tm_mon, st.tm_mday, 0, 0, 0, 0, 0, 0)))
            )
        return int(self._options["start"][1])

    def _get_multiple_days_log_entries(self, log):
        start_time = self._get_start_date() + 86399
        end_time = start_time - ((self._options["display"][1] * 86400) + 86399)

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
                previous_log_time = int(entry[0])
                # Finished!
                break

        if last_log_index is None:
            last_log_index = len(log)

        return log[first_log_index:last_log_index], (
            start_time,
            end_time,
            previous_log_time,
            next_log_time,
        )

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
            html.icon_button(
                makeactionuri(
                    request,
                    transactions,
                    [
                        ("options_start_sel", "0"),
                    ],
                ),
                _("Most recent events"),
                "start",
            )

            html.icon_button(
                makeactionuri(
                    request,
                    transactions,
                    time_url_args(next_log_time),
                ),
                "{}: {}".format(_("Newer events"), render.date(next_log_time)),
                "back",
            )
        else:
            html.empty_icon_button()
            html.empty_icon_button()

        if previous_log_time is not None:
            html.icon_button(
                makeactionuri(
                    request,
                    transactions,
                    time_url_args(previous_log_time),
                ),
                "{}: {}".format(_("Older events"), render.date(previous_log_time)),
                "forth",
            )
        else:
            html.empty_icon_button()

        html.close_div()

    def _get_timerange(self, t):
        st = time.localtime(int(t))
        start = int(
            time.mktime(time.struct_time((st[0], st[1], st[2], 0, 0, 0, st[6], st[7], st[8])))
        )
        end = start + 86399
        return start, end

    def _display_audit_log_options(self):
        if display_options.disabled(display_options.C):
            return

        with html.form_context("options", method="GET"):
            self._show_audit_log_options_controls()

            html.open_div(class_="side_popup_content")
            html.show_user_errors()

            for name, vs in self._audit_log_options():

                def renderer(name: str = name, vs: ValueSpec = vs) -> None:
                    vs.render_input("options_" + name, self._options[name])

                html.render_floating_option(name, "single", vs.title(), renderer)

            html.close_div()

            html.hidden_fields()

    def _show_audit_log_options_controls(self):
        html.open_div(class_="side_popup_controls")

        html.open_div(class_="update_buttons")
        html.button("apply", _("Apply"), "submit")
        html.buttonlink(
            makeuri(
                request,
                [],
                remove_prefix="options_",
            ),
            _("Reset"),
        )
        html.close_div()

        html.close_div()

    def _audit_log_options(self):
        object_types: Choices = [
            ("", _("All object types")),
            (None, _("No object type")),
        ] + [(t.name, t.name) for t in ObjectRefType]

        users = load_users()
        user_choices: Choices = [(None, "All users")] + sorted(
            [("-", "internal")] + [(name, name) for (name, us) in users.items()],
            key=lambda x: x[1],
        )

        return [
            (
                "object_type",
                DropdownChoice(
                    title=_("Object type"),
                    choices=object_types,
                ),
            ),
            (
                "object_ident",
                TextInput(
                    title=_("Object"),
                ),
            ),
            (
                "user_id",
                DropdownChoice(
                    title=_("User"),
                    choices=user_choices,
                ),
            ),
            (
                "filter_regex",
                RegExp(
                    title=_("Filter pattern (RegExp)"),
                    mode="infix",
                ),
            ),
            (
                "start",
                CascadingDropdown(
                    title=_("Start log from"),
                    default_value="now",
                    orientation="horizontal",
                    choices=[
                        ("now", _("Current date")),
                        ("time", _("Specific date"), AbsoluteDate()),
                    ],
                ),
            ),
            (
                "display",
                CascadingDropdown(
                    title=_("Display mode of entries"),
                    default_value="daily",
                    orientation="horizontal",
                    choices=[
                        ("daily", _("Daily paged display")),
                        (
                            "number_of_days",
                            _("Number of days from now (single page)"),
                            Integer(
                                minvalue=1,
                                unit=_("days"),
                                default_value=1,
                            ),
                        ),
                    ],
                ),
            ),
        ]

    def _clear_audit_log_after_confirm(self) -> ActionResult:
        AuditLogStore().clear()
        flash(_("Archived audit log"))
        return redirect(self.mode_url())

    def _export_audit_log(self, audit: list[AuditLogStore.Entry]) -> ActionResult:
        response.set_content_type("text/csv")

        if self._options["display"] == "daily":
            filename = (
                f"wato-auditlog-{render.date(time.time())}_{render.time_of_day(time.time())}.csv"
            )
        else:
            filename = "wato-auditlog-{}_{}_days.csv".format(
                render.date(time.time()),
                self._options["display"][1],
            )

        response.set_content_disposition(ContentDispositionType.ATTACHMENT, filename)

        titles = [
            _("Date"),
            _("Time"),
            _("Object type"),
            _("Object"),
            _("User"),
            _("Action"),
            _("Summary"),
        ]

        if self._show_details:
            titles.append(_("Details"))

        resp = []

        resp.append(",".join(titles) + "\n")
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

            resp.append(",".join(columns) + "\n")

        response.set_data("".join(resp))

        return FinalizeRequest(code=200)

    def _parse_audit_log(self) -> list[AuditLogStore.Entry]:
        vs_file_selection = self._vs_file_selection()
        file_selection = vs_file_selection.from_html_vars("file_selection")
        vs_file_selection.validate_value(file_selection, "file_selection")
        self._options.update(self._get_audit_log_options_from_request())
        options: AuditLogFilterRaw = {
            "object_type": self._options.get("object_type"),
            "object_ident": self._options.get("object_ident"),
            "user_id": self._options.get("user_id"),
            "filter_regex": self._options.get("filter_regex"),
        }

        entries_filter = build_audit_log_filter(options)
        return list(
            reversed(AuditLogStore(wato_var_dir() / "log" / file_selection).read(entries_filter))
        )
