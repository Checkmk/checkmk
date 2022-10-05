#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import collections
import json
from typing import Dict, Iterator, List

import cmk.utils.paths
import cmk.utils.version as cmk_version

import cmk.gui.pages
import cmk.gui.sites as sites
import cmk.gui.view_utils
import cmk.gui.visuals as visuals
import cmk.gui.weblib as weblib
from cmk.gui.alarm import play_alarm_sounds
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.command_utils import do_actions, get_command_groups, should_show_command_form
from cmk.gui.config import active_config
from cmk.gui.data_source import row_id
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.htmllib.top_heading import top_heading
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_checkbox_selection_topic,
    make_display_options_dropdown,
    make_external_link,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuPopup,
    PageMenuSidePopup,
    PageMenuTopic,
)
from cmk.gui.page_menu_entry import toggle_page_menu_entries
from cmk.gui.page_menu_utils import (
    collect_context_links,
    get_context_page_menu_dropdowns,
    get_ntop_page_menu_dropdown,
)
from cmk.gui.painter_options import PainterOptions
from cmk.gui.plugins.views.utils import Command, load_used_options
from cmk.gui.plugins.visuals.utils import Filter
from cmk.gui.type_defs import HTTPVariables, InfoName, Rows, ViewSpec
from cmk.gui.utils.html import HTML
from cmk.gui.utils.ntop import get_ntop_connection, is_ntop_configured
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeuri, makeuri_contextless
from cmk.gui.view import View
from cmk.gui.visuals import view_title
from cmk.gui.watolib.activate_changes import get_pending_changes_tooltip, has_pending_changes

if not cmk_version.is_raw_edition():
    from cmk.gui.cee.ntop.connector import get_cache  # pylint: disable=no-name-in-module


def _filter_selected_rows(view_spec: ViewSpec, rows: Rows, selected_ids: List[str]) -> Rows:
    action_rows: Rows = []
    for row in rows:
        if row_id(view_spec["datasource"], row) in selected_ids:
            action_rows.append(row)
    return action_rows


def show_filter_form(view: View, show_filters: List[Filter]) -> None:
    visuals.show_filter_form(
        info_list=view.datasource.infos,
        context={f.ident: view.context.get(f.ident, {}) for f in show_filters if f.available()},
        page_name=view.name,
        reset_ajax_page="ajax_initial_view_filters",
    )


class ABCViewRenderer(abc.ABC):
    def __init__(self, view: View) -> None:
        super().__init__()
        self.view = view
        self._menu_topics: Dict[str, List[PageMenuTopic]] = collections.defaultdict(list)

    def append_menu_topic(self, dropdown: str, topic: PageMenuTopic) -> None:
        self._menu_topics[dropdown].append(topic)

    @abc.abstractmethod
    def render(
        self,
        rows: Rows,
        show_checkboxes: bool,
        num_columns: int,
        show_filters: List[Filter],
        unfiltered_amount_of_rows: int,
    ) -> None:
        raise NotImplementedError()


class GUIViewRenderer(ABCViewRenderer):
    def __init__(self, view: View, show_buttons: bool) -> None:
        super().__init__(view)
        self._show_buttons = show_buttons

    def render(  # type:ignore[no-untyped-def] # pylint: disable=too-many-branches
        self,
        rows: Rows,
        show_checkboxes: bool,
        num_columns: int,
        show_filters: List[Filter],
        unfiltered_amount_of_rows: int,
    ):
        view_spec = self.view.spec

        if transactions.transaction_valid() and html.do_actions():
            html.browser_reload = 0.0

        # Show/Hide the header with page title, MK logo, etc.
        if display_options.enabled(display_options.H):
            html.body_start(view_title(view_spec, self.view.context))

        if display_options.enabled(display_options.T):
            if self.view.checkboxes_displayed:
                weblib.selection_id()
            breadcrumb = self.view.breadcrumb()
            top_heading(
                html,
                request,
                view_title(view_spec, self.view.context),
                breadcrumb,
                page_menu=self._page_menu(rows, show_filters),
                browser_reload=html.browser_reload,
            )
            html.begin_page_content()

        has_done_actions = False
        row_count = len(rows)

        command_form = should_show_command_form(self.view.datasource)
        if command_form:
            weblib.init_selection()

        # Used this before. This does not looked like it's correct, replaced the logic
        # enable_commands = painter_options.painter_option_form_enabled()
        # enable_checkboxes = view.layout.can_display_checkboxes and not checkboxes_enforced
        # selection_enabled = enable_checkboxes if enable_commands else checkboxes_enforced
        html.javascript(
            "cmk.selection.set_selection_enabled(%s);" % json.dumps(self.view.checkboxes_displayed)
        )

        layout = self.view.layout

        # Display the filter form on page rendering in some cases
        if self._should_show_filter_form():
            html.final_javascript("cmk.page_menu.open_popup('popup_filters');")

        # Actions
        if command_form:
            # There are one shot actions which only want to affect one row, filter the rows
            # by this id during actions
            if request.has_var("_row_id") and html.do_actions():
                rows = _filter_selected_rows(
                    view_spec, rows, [request.get_str_input_mandatory("_row_id")]
                )

            # If we are currently within an action (confirming or executing), then
            # we display only the selected rows (if checkbox mode is active)
            elif show_checkboxes and html.do_actions():
                rows = _filter_selected_rows(
                    view_spec,
                    rows,
                    user.get_rowselection(weblib.selection_id(), "view-" + view_spec["name"]),
                )

            if (
                html.do_actions() and transactions.transaction_valid()
            ):  # submit button pressed, no reload
                try:
                    # Create URI with all actions variables removed
                    backurl = makeuri(request, [], delvars=["filled_in", "actions"])
                    has_done_actions = do_actions(
                        view_spec, self.view.datasource.infos[0], rows, backurl
                    )
                except MKUserError as e:
                    html.user_error(e)

        # Also execute commands in cases without command form (needed for Python-
        # web service e.g. for NagStaMon)
        elif (
            row_count > 0
            and user.may("general.act")
            and html.do_actions()
            and transactions.transaction_valid()
        ):

            # There are one shot actions which only want to affect one row, filter the rows
            # by this id during actions
            if request.has_var("_row_id") and html.do_actions():
                rows = _filter_selected_rows(
                    view_spec, rows, [request.get_str_input_mandatory("_row_id")]
                )

            try:
                do_actions(view_spec, self.view.datasource.infos[0], rows, "")
            except Exception:
                pass  # currently no feed back on webservice

        # The refreshing content container
        if display_options.enabled(display_options.R):
            html.open_div(id_="data_container")

        missing_single_infos = self.view.missing_single_infos
        if missing_single_infos:
            html.show_warning(
                _(
                    "Unable to render this view, "
                    "because we miss some required context information (%s). Please update the "
                    "form on the right to make this view render."
                )
                % ", ".join(sorted(missing_single_infos))
            )

        for message in self.view.warning_messages:
            html.show_warning(message)

        if not has_done_actions and not missing_single_infos:
            html.div("", id_="row_info")
            if display_options.enabled(display_options.W):
                row_limit = None if self.view.datasource.ignore_limit else self.view.row_limit
                if cmk.gui.view_utils.row_limit_exceeded(
                    unfiltered_amount_of_rows,
                    row_limit,
                ) or cmk.gui.view_utils.row_limit_exceeded(
                    len(rows),
                    row_limit,
                ):
                    cmk.gui.view_utils.query_limit_exceeded_warn(row_limit, user)
                    del rows[row_limit:]
                    self.view.process_tracking.amount_rows_after_limit = len(rows)

            layout.render(
                rows,
                view_spec,
                self.view.group_cells,
                self.view.row_cells,
                num_columns,
                show_checkboxes and not html.do_actions(),
            )
            row_info = "%d %s" % (row_count, _("row") if row_count == 1 else _("rows"))
            if show_checkboxes:
                selected = _filter_selected_rows(
                    view_spec,
                    rows,
                    user.get_rowselection(weblib.selection_id(), "view-" + view_spec["name"]),
                )
                row_info = "%d/%s" % (len(selected), row_info)
            html.javascript("cmk.utils.update_row_info(%s);" % json.dumps(row_info))

            # The number of rows might have changed to enable/disable actions and checkboxes
            if self._show_buttons:
                # don't take display_options into account here ('c' is set during reload)
                toggle_page_menu_entries(
                    html,
                    css_class="command",
                    state=row_count > 0
                    and should_show_command_form(self.view.datasource, ignore_display_option=True),
                )

            # Play alarm sounds, if critical events have been displayed
            if display_options.enabled(display_options.S) and view_spec.get("play_sounds"):
                play_alarm_sounds()
        else:
            # Always hide action related context links in this situation
            toggle_page_menu_entries(html, css_class="command", state=False)

        # In multi site setups error messages of single sites do not block the
        # output and raise now exception. We simply print error messages here.
        # In case of the web service we show errors only on single site installations.
        if active_config.show_livestatus_errors and display_options.enabled(display_options.W):
            for info in sites.live().dead_sites().values():
                if isinstance(info["site"], dict):
                    html.show_error(
                        "<b>%s - %s</b><br>%s"
                        % (info["site"]["alias"], _("Livestatus error"), info["exception"])
                    )

        if display_options.enabled(display_options.R):
            html.close_div()

        if display_options.enabled(display_options.T):
            html.end_page_content()

        if display_options.enabled(display_options.H):
            html.body_end()

    def _should_show_filter_form(self) -> bool:
        """Whether or not the filter form should be displayed on page load

        a) In case the user toggled the popup in the frontend, always enforce that property

        b) Show in case the view is a "mustsearch" view (User needs to submit the filter form before
        data is shown).

        c) Show after submitting the filter form. The user probably wants to update the filters
        after first filtering.

        d) In case there are single info filters missing
        """

        show_form = request.get_integer_input("_show_filter_form")
        if show_form is not None:
            return show_form == 1

        if self.view.spec.get("mustsearch"):
            return True

        if request.get_ascii_input("filled_in") == "filter":
            return True

        if self.view.missing_single_infos:
            return True

        return False

    def _page_menu(self, rows: Rows, show_filters: List[Filter]) -> PageMenu:
        breadcrumb: Breadcrumb = self.view.breadcrumb()
        if not display_options.enabled(display_options.B):
            return PageMenu()  # No buttons -> no menu

        export_dropdown = [
            PageMenuDropdown(
                name="export",
                title=_("Export"),
                topics=[
                    PageMenuTopic(
                        title=_("Data"),
                        entries=list(self._page_menu_entries_export_data()),
                    ),
                    PageMenuTopic(
                        title=_("Reports"),
                        entries=list(self._page_menu_entries_export_reporting(rows)),
                    ),
                ],
            ),
        ]

        page_menu_dropdowns = (
            self._page_menu_dropdown_commands()
            + self._page_menu_dropdowns_context(rows)
            + self._page_menu_dropdown_add_to()
            + export_dropdown
        )

        if rows:
            host_address = rows[0].get("host_address")
            if is_ntop_configured():
                ntop_connection = get_ntop_connection()
                assert ntop_connection
                ntop_instance = ntop_connection["hostaddress"]
                if (
                    host_address is not None
                    and get_cache().is_instance_up(ntop_instance)
                    and get_cache().is_ntop_host(host_address)
                ):
                    page_menu_dropdowns.insert(3, self._page_menu_dropdowns_ntop(host_address))

        menu = PageMenu(
            dropdowns=page_menu_dropdowns,
            breadcrumb=breadcrumb,
            has_pending_changes=has_pending_changes(),
            pending_changes_tooltip=get_pending_changes_tooltip(),
        )

        self._extend_display_dropdown(menu, show_filters)
        self._extend_help_dropdown(menu)

        for dropdown_name, topics in self._menu_topics.items():
            menu[dropdown_name].topics.extend(topics)

        return menu

    def _page_menu_dropdown_commands(self) -> List[PageMenuDropdown]:
        if not display_options.enabled(display_options.C):
            return []

        return [
            PageMenuDropdown(
                name="commands",
                title=_("Commands"),
                topics=[
                    PageMenuTopic(
                        title=_("On selected objects"),
                        entries=list(self._page_menu_entries_selected_objects()),
                    ),
                    make_checkbox_selection_topic(
                        "view-%s" % self.view.spec["name"],
                        is_enabled=self.view.checkboxes_displayed,
                    ),
                ],
            )
        ]

    def _page_menu_entries_selected_objects(self) -> Iterator[PageMenuEntry]:
        info_name: InfoName = self.view.datasource.infos[0]
        by_group = get_command_groups(info_name)

        for _group_class, commands in sorted(by_group.items(), key=lambda x: x[0]().sort_index):
            for command in commands:
                yield PageMenuEntry(
                    title=command.title,
                    icon_name=command.icon_name,
                    item=PageMenuPopup(self._render_command_form(info_name, command)),
                    name="command_%s" % command.ident,
                    is_enabled=should_show_command_form(self.view.datasource),
                    is_show_more=command.is_show_more,
                    is_shortcut=command.is_shortcut,
                    is_suggested=command.is_suggested,
                    css_classes=["command"],
                )

    def _page_menu_dropdowns_context(self, rows: Rows) -> List[PageMenuDropdown]:
        return get_context_page_menu_dropdowns(self.view, rows, mobile=False)

    def _page_menu_dropdowns_ntop(  # type:ignore[no-untyped-def]
        self, host_address
    ) -> PageMenuDropdown:
        return get_ntop_page_menu_dropdown(self.view, host_address)

    def _page_menu_entries_export_data(self) -> Iterator[PageMenuEntry]:
        if not user.may("general.csv_export"):
            return

        yield PageMenuEntry(
            title=_("Export CSV"),
            icon_name="download_csv",
            item=make_simple_link(
                makeuri(
                    request,
                    [("output_format", "csv_export")],
                    delvars=["show_checkboxes", "selection"],
                )
            ),
        )

        yield PageMenuEntry(
            title=_("Export JSON"),
            icon_name="download_json",
            item=make_simple_link(
                makeuri(
                    request,
                    [("output_format", "json_export")],
                    delvars=["show_checkboxes", "selection"],
                )
            ),
        )

    def _page_menu_entries_export_reporting(self, rows: Rows) -> Iterator[PageMenuEntry]:
        if cmk_version.is_raw_edition():
            return

        if not user.may("general.instant_reports"):
            return

        yield PageMenuEntry(
            title=_("This view as PDF"),
            icon_name="report",
            item=make_external_link(
                makeuri(
                    request,
                    [],
                    filename="report_instant.py",
                    delvars=["show_checkboxes", "selection"],
                )
            ),
            css_classes=["context_pdf_export"],
        )

        # Link related reports
        yield from collect_context_links(self.view, rows, mobile=False, visual_types=["reports"])

    def _extend_display_dropdown(self, menu: PageMenu, show_filters: List[Filter]) -> None:
        display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())

        display_dropdown.topics.insert(
            0,
            PageMenuTopic(
                title=_("View layout"),
                entries=list(self._page_menu_entries_view_layout()),
            ),
        )

        if display_options.enabled(display_options.D):
            display_dropdown.topics.insert(
                0,
                PageMenuTopic(
                    title=_("Format"),
                    entries=list(self._page_menu_entries_view_format()),
                ),
            )

        if display_options.enabled(display_options.F):
            display_dropdown.topics.insert(
                0,
                PageMenuTopic(
                    title=_("Filter"),
                    entries=list(self._page_menu_entries_filter(show_filters)),
                ),
            )

    def _page_menu_entries_filter(self, show_filters: List[Filter]) -> Iterator[PageMenuEntry]:
        is_filter_set = request.var("filled_in") == "filter"

        yield PageMenuEntry(
            title=_("Filter"),
            icon_name="filters_set" if is_filter_set else "filter",
            item=PageMenuSidePopup(self._render_filter_form(show_filters)),
            name="filters",
            is_shortcut=True,
        )

    def _page_menu_entries_view_format(self) -> Iterator[PageMenuEntry]:
        painter_options = PainterOptions.get_instance()
        yield PageMenuEntry(
            title=_("Modify display options"),
            icon_name="painteroptions",
            item=PageMenuPopup(self._render_painter_options_form()),
            name="display_painter_options",
            is_enabled=painter_options.painter_option_form_enabled(),
        )

    def _page_menu_entries_view_layout(self) -> Iterator[PageMenuEntry]:
        checkboxes_toggleable = (
            self.view.layout.can_display_checkboxes and not self.view.checkboxes_enforced
        )
        yield PageMenuEntry(
            title=_("Show checkboxes"),
            icon_name="checked_checkbox" if self.view.checkboxes_displayed else "checkbox",
            item=make_simple_link(
                makeuri(
                    request,
                    [
                        ("show_checkboxes", "0" if self.view.checkboxes_displayed else "1"),
                    ],
                )
            ),
            is_shortcut=True,
            is_suggested=True,
            is_enabled=checkboxes_toggleable,
        )

        if display_options.enabled(display_options.E) and user.may("general.edit_views"):
            url_vars: HTTPVariables = [
                ("back", request.requested_url),
                ("load_name", self.view.name),
            ]

            clone_mode: bool = False
            if self.view.spec["owner"] != user.id:
                url_vars.append(("owner", self.view.spec["owner"]))
                if not user.may("general.edit_foreign_views"):
                    clone_mode = True

            url_vars.append(("mode", "clone" if clone_mode else "edit"))
            url = makeuri_contextless(request, url_vars, filename="edit_view.py")

            yield PageMenuEntry(
                title=_("Clone view") if clone_mode else _("Customize view"),
                icon_name="clone" if clone_mode else "edit",
                item=make_simple_link(url),
            )

    def _page_menu_dropdown_add_to(self) -> List[PageMenuDropdown]:
        return visuals.page_menu_dropdown_add_to_visual(add_type="view", name=self.view.name)

    def _render_filter_form(self, show_filters: List[Filter]) -> HTML:
        if not display_options.enabled(display_options.F) or not show_filters:
            return HTML()

        with output_funnel.plugged():
            show_filter_form(self.view, show_filters)
            return HTML(output_funnel.drain())

    def _render_painter_options_form(self) -> HTML:
        with output_funnel.plugged():
            painter_options = PainterOptions.get_instance()
            painter_options.show_form(
                self.view.spec,
                load_used_options(self.view.spec, self.view.group_cells + self.view.row_cells),
            )
            return HTML(output_funnel.drain())

    def _render_command_form(self, info_name: InfoName, command: Command) -> HTML:
        with output_funnel.plugged():
            if not should_show_command_form(self.view.datasource):
                return HTML()

            # TODO: Make unique form names (object IDs), investigate whether or not something
            # depends on the form name "actions"
            html.begin_form("actions")
            # TODO: Are these variables still needed
            html.hidden_field("_do_actions", "yes")
            html.hidden_field("actions", "yes")

            command.render(info_name)

            html.hidden_fields()
            html.end_form()

            return HTML(output_funnel.drain())

    def _extend_help_dropdown(self, menu: PageMenu) -> None:
        # TODO
        # menu.add_doc_reference(title=_("Host administration"), doc_ref=DocReference.WATO_HOSTS)
        # menu.add_youtube_reference(title=_("Episode 4: Monitoring Windows in Checkmk"),
        #                           youtube_id="Nxiq7Jb9mB4")
        pass
