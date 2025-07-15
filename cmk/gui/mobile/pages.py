#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.ccc.site import omd_site

import cmk.gui.utils
import cmk.gui.view_utils
from cmk.gui import visuals
from cmk.gui.config import Config
from cmk.gui.data_source import ABCDataSource, data_source_registry
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.page_menu import PageMenuEntry, PageMenuLink
from cmk.gui.page_menu_utils import collect_context_links
from cmk.gui.pages import Page, PageResult
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.painter_options import PainterOptions
from cmk.gui.type_defs import Rows, VisualContext
from cmk.gui.userdb import get_active_saml_connections
from cmk.gui.utils import escaping
from cmk.gui.utils.confirm_with_preview import command_confirm_dialog
from cmk.gui.utils.escaping import escape_text
from cmk.gui.utils.html import HTML
from cmk.gui.utils.login import show_saml2_login, show_user_errors
from cmk.gui.utils.urls import makeuri, requested_file_name
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.view import View
from cmk.gui.view_renderer import ABCViewRenderer
from cmk.gui.views.command import command_registry, CommandSpec, core_command
from cmk.gui.views.page_show_view import (
    get_limit,
    get_row_count,
    get_user_sorters,
    get_want_checkboxes,
    process_view,
)
from cmk.gui.views.store import get_permitted_views
from cmk.gui.visuals import get_only_sites_from_context, view_title
from cmk.gui.visuals.filter import Filter

HeaderButton = tuple[str, str, str] | tuple[str, str, str, str]
Items = list[tuple[str, str, str]]
NavigationBar = list[tuple[str, str, str, str]]


def mobile_html_head(title: str) -> None:
    html.write_html(
        HTML.without_escaping(
            """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">"""
        )
    )
    html.open_html()
    html.open_head()
    html.default_html_headers()
    html.meta(name="viewport", content="initial-scale=1.0")
    html.meta(name="apple-mobile-web-app-capable", content="yes")
    html.meta(name="apple-mobile-web-app-title", content="Check_MK")
    html.title(title)
    html.stylesheet(href="jquery/jquery.mobile-1.4.5.min.css")
    html.stylesheet(href="themes/facelift/theme.css")

    html.link(rel="apple-touch-icon", href="themes/facelift/images/favicon.ico")
    html.javascript_file(src="js/mobile_min.js")
    html.set_js_csrf_token()

    html.close_head()
    html.open_body(class_="mobile")


def mobile_html_foot() -> None:
    html.write_final_javascript()
    html.close_body()
    html.close_html()


def jqm_header_button(pos: str, url: str, title: str, icon: str = "") -> None:
    html.a(
        "",
        href=url,
        class_="ui-btn-%s" % pos,
        title=title,
        **{"data-direction": "reverse", "data-icon": icon, "data-iconpos": "notext"},
    )


def jqm_page_header(
    title: str,
    id_: str | None = None,
    left_button: HeaderButton | None = None,
    right_button: HeaderButton | None = None,
) -> None:
    html.open_div(id_=id_ if id_ else None, **{"data-role": "page"})
    html.open_div(
        **{
            "data-role": "header",
            "data-position": "fixed",
            "data-tap-toggle": "false",
            "data-hide-during-focus": "",
        }
    )
    if left_button:
        jqm_header_button("left", *left_button)
    html.h1(title)
    if right_button:
        jqm_header_button("right", *right_button)
    html.close_div()
    html.open_div(**{"data-role": "content"})


def jqm_page_navfooter(items: NavigationBar, current: str, page_id: str) -> None:
    html.close_div()  # close content
    html.open_div(
        **{
            "data-role": "footer",
            "data-position": "fixed",
            "data-tap-toggle": "false",
            "data-hide-during-focus": "",
        }
    )
    html.open_div(**{"data-role": "navbar"})
    html.open_ul()

    for href, title, icon, custom_css in items:
        href = makeuri(request, [("page", href), ("search", "Search")])
        if current == href:
            custom_css += " ui-state-persist ui-btn-active"
        else:
            html.open_li()
            html.a(
                title,
                href=href,
                class_=custom_css,
                **{
                    "data-transition": "slide",
                    "data-icon": icon,
                    "data-iconpos": "bottom",
                },
            )
            html.close_li()
    html.close_ul()
    html.close_div()
    html.close_div()
    html.close_div()  # close page-div


def jqm_page_index(title: str, items: Items) -> None:
    manual_sort = [_("Overview"), _("Problems"), _("History"), _("Event Console")]

    items.sort(key=lambda x: (x[0], x[2]))
    for topic in manual_sort:
        jqm_page_index_topic_renderer(topic, items)

    other_topics = list({x[0] for x in items if x[0] not in manual_sort})

    for topic in other_topics:
        jqm_page_index_topic_renderer(topic, items)


def jqm_page_index_topic_renderer(topic: str, items: Items) -> None:
    has_items_for_topic = any(i for i in items if i[0] == topic)
    if not has_items_for_topic:
        return

    html.p(topic)
    html.open_ul(**{"data-role": "listview", "data-inset": "true"})
    for top, href, title in items:
        if top == topic:
            html.open_li()
            html.open_a(href=href, **{"data-ajax": "false", "data-transition": "flip"})
            html.write_html(HTML.without_escaping(title))
            html.close_a()
            html.close_li()
    html.close_ul()


def page_login(config: Config) -> None:
    title = _("Checkmk Mobile")
    mobile_html_head(title)
    jqm_page_header(title, id_="login")
    html.div(_("Welcome to Checkmk Mobile."), id_="loginhead")

    with html.form_context("login", method="POST", add_transid=False):
        # Keep information about original target URL
        default_origtarget = (
            "index.py"
            if requested_file_name(request) in ["login", "logout"]
            else makeuri(request, [])
        )
        origtarget = request.get_url_input("_origtarget", default_origtarget)
        html.hidden_field("_origtarget", escaping.escape_attribute(origtarget))

        saml2_user_error: str | None = None
        if saml_connections := [
            c for c in get_active_saml_connections().values() if c["owned_by_site"] == omd_site()
        ]:
            saml2_user_error = show_saml2_login(saml_connections, saml2_user_error, origtarget)

        html.text_input(
            "_username", label=_("Username:"), autocomplete="username", id_="input_user"
        )
        html.password_input(
            "_password",
            size=None,
            label=_("Password:"),
            autocomplete="current-password",
            id_="input_pass",
        )
        html.br()
        html.button("_login", _("Login"))

        if user_errors and not saml2_user_error:
            show_user_errors("login_error")

        html.set_focus("_username")
    html.open_div(id_="loginfoot")
    html.img("themes/facelift/images/logo_cmk_small.png", class_="logomk")
    html.div(
        HTML.without_escaping("&copy; ")
        + HTMLWriter.render_a("Checkmk GmbH", href="https://checkmk.com", target="_blank"),
        class_="copyright",
    )
    html.close_div()  # close content-div
    html.close_div()
    html.close_div()  # close page-div
    mobile_html_foot()


class PageMobileIndex(Page):
    def page(self, config: Config) -> PageResult:
        _page_index()
        return None


def _page_index() -> None:
    title = _("Checkmk Mobile")
    mobile_html_head(title)
    jqm_page_header(
        title,
        right_button=("javascript:document.location.reload();", _("Reload"), "refresh"),
        id_="data",
    )
    items = []
    for view_name, view_spec in get_permitted_views().items():
        if view_spec.get("mobile") and not view_spec.get("hidden"):
            datasource = data_source_registry[view_spec["datasource"]]()
            context = visuals.active_context_from_request(datasource.infos, view_spec["context"])

            view = View(view_name, view_spec, context)
            view.row_limit = get_limit()
            view.only_sites = get_only_sites_from_context(context)
            view.user_sorters = get_user_sorters(view.spec["sorters"], view.row_cells)
            view.want_checkboxes = get_want_checkboxes()

            url = "mobile_view.py?view_name=%s" % view_name
            count = ""
            if not view_spec.get("mustsearch"):
                painter_options = PainterOptions.get_instance()
                painter_options.load(view_name)
                count = '<span class="ui-li-count">%d</span>' % get_row_count(view)

            topic = PagetypeTopics.get_topic(view_spec.get("topic", ""))
            items.append(
                (topic.title(), url, "{} {}".format(escape_text(view_spec["title"]), count))
            )

    jqm_page_index(_("Checkmk Mobile"), items)
    # Link to non-mobile GUI

    html.hr()
    html.open_ul(**{"data-role": "listview", "data-theme": "b", "data-inset": "true"})
    html.open_li()
    html.a(
        _("Classical web GUI"),
        href="index.py?mobile=",
        **{"data-ajax": "false", "data-transition": "fade"},
    )
    html.close_li()
    html.close_ul()

    html.open_ul(**{"data-role": "listview", "data-theme": "f", "data-inset": "true"})
    html.open_li()
    html.a(_("Logout"), href="logout.py", **{"data-ajax": "false", "data-transition": "fade"})
    html.close_li()
    html.close_ul()
    mobile_html_foot()


class PageMobileView(Page):
    def page(self, config: Config) -> PageResult:
        _page_view(debug=config.debug)
        return None


def _page_view(*, debug: bool) -> None:
    view_name = request.var("view_name")
    if not view_name:
        return _page_index()

    view_spec = get_permitted_views().get(view_name)
    if not view_spec:
        raise MKUserError("view_name", "No view defined with the name '%s'." % view_name)

    datasource = data_source_registry[view_spec["datasource"]]()
    context = visuals.active_context_from_request(datasource.infos, view_spec["context"])

    view = View(view_name, view_spec, context)
    view.row_limit = get_limit()
    view.only_sites = get_only_sites_from_context(context)
    view.user_sorters = get_user_sorters(view.spec["sorters"], view.row_cells)
    view.want_checkboxes = get_want_checkboxes()

    title = view_title(view.spec, view.context)
    mobile_html_head(title)

    # Need to be loaded before processing the painter_options below.
    # TODO: Make this dependency explicit
    display_options.load_from_html(request, html)

    painter_options = PainterOptions.get_instance()
    painter_options.load(view_name)

    try:
        process_view(MobileViewRenderer(view), debug=debug)
    except Exception as e:
        logger.exception("error showing mobile view")
        if debug:
            raise
        html.write_text_permissive("ERROR showing view: %s" % e)

    mobile_html_foot()
    return None


class MobileViewRenderer(ABCViewRenderer):
    def render(
        self,
        rows: Rows,
        show_checkboxes: bool,
        num_columns: int,
        show_filters: list[Filter],
        unfiltered_amount_of_rows: int,
        *,
        debug: bool,
    ) -> None:
        view_spec = self.view.spec
        home = ("mobile.py", "Home", "home")

        page = request.var("page")
        if not page:
            if view_spec.get("mustsearch"):
                page = "filter"
            else:
                page = "data"

        title = view_title(self.view.spec, self.view.context)
        navbar = [
            ("data", _("Results"), "grid", "results_button"),
            ("filter", _("Filter"), "search", ""),
        ]
        if user.may("general.act"):
            navbar.append(("commands", _("Commands"), "gear", ""))

        # Should we show a page with context links?
        context_links = list(
            collect_context_links(self.view, rows, mobile=True, visual_types=["views"])
        )

        if context_links:
            navbar.append(("context", _("Context"), "arrow-r", ""))
        page_id = "view_" + view_spec["name"]

        if page == "filter":
            jqm_page_header(_("Filter / Search"), left_button=home, id_="filter")
            _show_filter_form(show_filters, self.view.context)
            jqm_page_navfooter(navbar, "filter", page_id)

        elif page == "commands":
            # Page: Commands
            if user.may("general.act"):
                jqm_page_header(_("Commands"), left_button=home, id_="commands")
                show_commands = True
                if request.has_var("_do_actions"):
                    try:
                        show_commands = do_commands(self.view.datasource.infos[0], rows)
                    except MKUserError as e:
                        html.user_error(e)
                        show_commands = True
                if show_commands:
                    _show_command_form(self.view.datasource, rows)
                jqm_page_navfooter(navbar, "commands", page_id)

        elif page == "data":
            # Page: data rows of view
            jqm_page_header(
                title,
                left_button=home,
                right_button=("javascript:document.location.reload();", _("Reload"), "refresh"),
                id_="data",
            )
            html.open_div(id_="view_results")
            if len(rows) == 0:
                html.write_text_permissive(_("No hosts/services found."))
            else:
                try:
                    if cmk.gui.view_utils.row_limit_exceeded(
                        unfiltered_amount_of_rows, self.view.row_limit
                    ):
                        cmk.gui.view_utils.query_limit_exceeded_warn(self.view.row_limit, user)
                        del rows[self.view.row_limit :]
                    self.view.layout.render(
                        rows,
                        view_spec,
                        self.view.group_cells,
                        self.view.row_cells,
                        num_columns,
                        show_checkboxes and not html.do_actions(),
                    )
                except Exception as e:
                    logger.exception("error rendering mobile view")
                    html.write_text_permissive(_("Error showing view: %s") % e)
            html.close_div()
            jqm_page_navfooter(navbar, "data", page_id)

        # Page: Context buttons
        elif page == "context":
            jqm_page_header(_("Context"), left_button=home, id_="context")
            _show_context_links(context_links)
            jqm_page_navfooter(navbar, "context", page_id)


def _show_filter_form(show_filters: list[Filter], context: VisualContext) -> None:
    # Sort filters
    s = sorted([(f.sort_index, f.title, f) for f in show_filters if f.available()])

    with html.form_context("filter"):
        html.open_ul(**{"data-role": "listview", "data-inset": "false"})
        for _sort_index, title, f in s:
            html.open_li(**{"data-role": "fieldcontain"})
            html.legend(title)
            f.display(context.get(f.ident, {}))
            html.close_li()
        html.close_ul()
        html.hidden_fields()
        html.hidden_field("search", "Search")
        html.hidden_field("page", "data")
        html.form_has_submit_button = True  # a.results_button functions as a submit button
    html.final_javascript(
        """
        const filter_form = document.getElementById("form_filter");
        const results_button = document.getElementsByClassName("results_button")[0];

        cmk.forms.enable_select2_dropdowns(filter_form);
        results_button.onclick = function(event) {
            event.preventDefault();
            filter_form.submit();
        };
        """
    )


def _show_command_form(datasource: ABCDataSource, rows: Rows) -> None:
    what = datasource.infos[0]
    html.javascript(
        """
    $(document).ready(function() {
      $('.command_group').has('x').trigger('expand');
      $('x').children().css('background-color', '#f84');
    });
    """
    )

    one_shown = False
    html.open_div(**{"data-role": "collapsible-set"})
    for command in command_registry.values():
        if what in command.tables and user.may(command.permission.name):
            html.open_div(class_=["command_group"], **{"data-role": "collapsible"})
            html.h3(str(command.title))
            html.open_p()

            with html.form_context("actions"):
                html.hidden_field("_do_actions", "yes")
                html.hidden_field("actions", "yes")
                command.render(what)
                html.hidden_fields()

            html.close_p()
            html.close_div()
            one_shown = True
    html.close_div()
    if not one_shown:
        html.write_text_permissive(_("No commands are possible in this view"))


# FIXME: Reduce duplicate code with views.py
def do_commands(what: str, rows: Rows) -> bool:
    confirm_options, confirm_dialog_options, executor = core_command(what, rows[0], 0, rows)[
        1:4
    ]  # just get confirm_options, confirm_dialog_options and executor

    if not command_confirm_dialog(
        confirm_options,
        confirm_dialog_options.confirm_title,
        (
            confirm_dialog_options.affected + confirm_dialog_options.additions
            if confirm_dialog_options.additions
            else confirm_dialog_options.affected
        ),
        confirm_dialog_options.icon_class,
        confirm_dialog_options.confirm_button,
    ):
        return False

    count = 0
    already_executed: set[CommandSpec] = set()
    for nr, row in enumerate(rows):
        nagios_commands, _confirm_options, _confirm_dialog_options, executor = core_command(
            what,
            row,
            nr,
            rows,
        )
        for command in nagios_commands:
            if command not in already_executed:
                executor(command, row["site"])
                already_executed.add(command)
                count += 1

    if count > 0:
        html.show_message(_("Successfully sent %d commands.") % count)
    return True  # Show commands again


def _show_context_links(context_links: list[PageMenuEntry]) -> None:
    items = []
    for entry in context_links:
        if not isinstance(entry.item, PageMenuLink):
            continue
        items.append(("Context", entry.item.link.url or "", entry.title))
    jqm_page_index(_("Related Views"), items)
