#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Set, Tuple, Union, Optional, List

import cmk.gui.views as views
import cmk.gui.config as config
import cmk.gui.visuals as visuals
import cmk.gui.utils
import cmk.gui.view_utils
from cmk.gui.plugins.views.utils import (
    PainterOptions,
    command_registry,
    data_source_registry,
)
import cmk.gui.escaping as escaping
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
from cmk.gui.exceptions import MKUserError
from cmk.gui.log import logger
from cmk.gui.type_defs import (
    Rows,)
from cmk.gui.plugins.views.utils import (
    Cell,
    ABCDataSource,
)
from cmk.gui.plugins.visuals.utils import Filter
from cmk.gui.page_menu import PageMenuEntry, PageMenuLink

HeaderButton = Union[Tuple[str, str, str], Tuple[str, str, str, str]]
Items = List[Tuple[str, str, str]]
NavigationBar = List[Tuple[str, str, str, str]]


def mobile_html_head(title: str) -> None:
    html.mobile = True
    html.write(
        """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">"""
    )
    html.open_html()
    html.open_head()
    html.default_html_headers()
    html.meta(name="viewport", content="initial-scale=1.0")
    html.meta(name="apple-mobile-web-app-capable", content="yes")
    html.meta(name="apple-mobile-web-app-title", content="Check_MK")
    html.title(title)
    html.stylesheet(href="jquery/jquery.mobile-1.2.1.css")
    html.stylesheet(href="themes/classic/theme.css")

    html.write(
        html._render_start_tag("link",
                               rel="apple-touch-icon",
                               href="themes/classic/images/ios_logo.png",
                               close_tag=True))
    html.javascript_file(src='js/mobile_min.js')

    # Never allow the mobile page to be opened in an iframe. Redirect top page to the current content page.
    # This will result in a full screen mobile interface page.
    html.javascript('''if(top != self) { window.top.location.href = location; }''')

    html.javascript("""
      $(document).ready(function() {
          $("a").click(function (event) {
            event.preventDefault();
            window.location = $(this).attr("href");
          });
      });""")

    html.close_head()
    html.open_body(class_="mobile")


def mobile_html_foot() -> None:
    html.close_body()
    html.close_html()


def jqm_header_button(pos: str, url: str, title: str, icon: str = "") -> None:
    html.a('',
           href=url,
           class_="ui-btn-%s" % pos,
           title=title,
           **{
               "data-direction": "reverse",
               "data-icon": icon,
               "data-iconpos": "notext"
           })


def jqm_page_header(title: str,
                    id_: Optional[str] = None,
                    left_button: Optional[HeaderButton] = None,
                    right_button: Optional[HeaderButton] = None) -> None:
    html.open_div(id_=id_ if id_ else None, **{"data-role": "page"})
    html.open_div(
        **{
            "data-role": "header",
            "data-position": "fixed",
            "data-tap-toggle": "false",
            "data-hide-during-focus": "",
        })
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
        })
    html.open_div(**{"data-role": "navbar"})
    html.open_ul()

    for href, title, icon, custom_css in items:
        href = html.makeuri([("page", href), ("search", "Search")])
        if current == href:
            custom_css += ' ui-state-persist ui-btn-active'
        else:
            html.open_li()
            html.open_a(href=href,
                        class_=custom_css,
                        **{
                            "data-transition": "slide",
                            "data-icon": icon,
                            "data-iconpos": "bottom",
                        })
            html.write(title)
            html.close_a()
            html.close_li()
    html.close_ul()
    html.close_div()
    html.close_div()
    html.close_div()  # close page-div


def jqm_page_index(title: str, items: Items) -> None:
    manual_sort = [_("Hosts"), _("Services"), _("Events")]

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

    html.open_p()
    html.write(topic)
    html.close_p()
    html.open_ul(**{"data-role": "listview", "data-inset": "true"})
    for top, href, title in items:
        if top == topic:
            html.open_li()
            html.open_a(href=href, **{"data-ajax": "false", "data-transition": "flip"})
            html.write(title)
            html.close_a()
            html.close_li()
    html.close_ul()


def page_login() -> None:
    title = _("Checkmk Mobile")
    mobile_html_head(title)
    jqm_page_header(title, id_="login")
    html.div(_("Welcome to Checkmk Mobile."), id_="loginhead")

    html.begin_form("login", method='POST', add_transid=False)
    # Keep information about original target URL
    default_origtarget = "index.py" if html.myfile in ["login", "logout"] else html.makeuri([])
    origtarget = html.get_url_input("_origtarget", default_origtarget)
    html.hidden_field('_origtarget', escaping.escape_attribute(origtarget))

    html.text_input("_username", label=_("Username:"), autocomplete="username")
    html.password_input("_password",
                        size=None,
                        label=_("Password:"),
                        autocomplete="current-password")
    html.br()
    html.button("_login", _('Login'))
    html.set_focus("_username")
    html.end_form()
    html.open_div(id_="loginfoot")
    html.img("themes/classic/images/logo_cmk_small.png", class_="logomk")
    html.div(HTML(_("&copy; <a target=\"_blank\" href=\"https://checkmk.com\">tribe29 GmbH</a>")),
             class_="copyright")
    html.close_div()  # close content-div
    html.close_div()
    html.close_div()  # close page-div
    mobile_html_foot()


@cmk.gui.pages.register("mobile")
def page_index() -> None:
    title = _("Checkmk Mobile")
    mobile_html_head(title)
    jqm_page_header(title,
                    right_button=("javascript:document.location.reload();", _("Reload"), "refresh"),
                    id_="data")
    items = []
    for view_name, view_spec in views.get_permitted_views().items():
        if view_spec.get("mobile") and not view_spec.get("hidden"):

            datasource = data_source_registry[view_spec["datasource"]]()
            context = visuals.get_merged_context(
                visuals.get_context_from_uri_vars(datasource.infos,
                                                  single_infos=view_spec["single_infos"]),
                view_spec["context"],
            )

            view = views.View(view_name, view_spec, context)
            view.row_limit = views.get_limit()
            view.only_sites = visuals.get_only_sites_from_context(context)
            view.user_sorters = views.get_user_sorters()
            view.want_checkboxes = views.get_want_checkboxes()

            url = "mobile_view.py?view_name=%s" % view_name
            count = ""
            if not view_spec.get("mustsearch"):
                painter_options = PainterOptions.get_instance()
                painter_options.load(view_name)
                count = '<span class="ui-li-count">%d</span>' % views.get_row_count(view)

            topic = view_spec.get("topic")
            if topic is None:
                topic = ""
            this_title = '%s %s' % (view_spec.get("linktitle", view_spec["title"]), count)
            items.append((topic, url, this_title))

    jqm_page_index(_("Checkmk Mobile"), items)
    # Link to non-mobile GUI

    html.hr()
    html.open_ul(**{"data-role": "listview", "data-theme": "b", "data-inset": "true"})
    html.open_li()
    html.a(_("Classical web GUI"),
           href="index.py?mobile=",
           **{
               "data-ajax": "false",
               "data-transition": "fade"
           })
    html.close_li()
    html.close_ul()

    html.open_ul(**{"data-role": "listview", "data-theme": "f", "data-inset": "true"})
    html.open_li()
    html.a(_("Logout"), href="logout.py", **{"data-ajax": "false", "data-transition": "fade"})
    html.close_li()
    html.close_ul()
    mobile_html_foot()


@cmk.gui.pages.register("mobile_view")
def page_view() -> None:
    view_name = html.request.var("view_name")
    if not view_name:
        return page_index()

    view_spec = views.get_permitted_views().get(view_name)
    if not view_spec:
        raise MKUserError("view_name", "No view defined with the name '%s'." % view_name)

    datasource = data_source_registry[view_spec["datasource"]]()
    context = visuals.get_merged_context(
        visuals.get_context_from_uri_vars(datasource.infos, single_infos=view_spec["single_infos"]),
        view_spec["context"],
    )

    view = views.View(view_name, view_spec, context)
    view.row_limit = views.get_limit()
    view.only_sites = visuals.get_only_sites_from_context(context)
    view.user_sorters = views.get_user_sorters()
    view.want_checkboxes = views.get_want_checkboxes()

    title = views.view_title(view_spec)
    mobile_html_head(title)

    painter_options = PainterOptions.get_instance()
    painter_options.load(view_name)

    try:
        view_renderer = MobileViewRenderer(view)
        views.process_view(view, view_renderer)
    except Exception as e:
        logger.exception("error showing mobile view")
        if config.debug:
            raise
        html.write("ERROR showing view: %s" % escaping.escape_attribute(str(e)))

    mobile_html_foot()


class MobileViewRenderer(views.ABCViewRenderer):
    def render(self, rows: Rows, group_cells: List[Cell], cells: List[Cell], show_checkboxes: bool,
               num_columns: int, show_filters: List[Filter],
               unfiltered_amount_of_rows: int) -> None:
        view_spec = self.view.spec
        home = ("mobile.py", "Home", "home")

        page = html.request.var("page")
        if not page:
            if view_spec.get("mustsearch"):
                page = "filter"
            else:
                page = "data"

        title = views.view_title(view_spec)
        navbar = [("data", _("Results"), "grid", 'results_button'),
                  ("filter", _("Filter"), "search", '')]
        if config.user.may("general.act"):
            navbar.append(("commands", _("Commands"), "gear", ''))

        # Should we show a page with context links?
        context_links = list(
            views.collect_context_links(self.view, rows, mobile=True, only_types=['views']))

        if context_links:
            navbar.append(("context", _("Context"), "arrow-r", ''))
        page_id = "view_" + view_spec["name"]

        if page == "filter":
            jqm_page_header(_("Filter / Search"), left_button=home, id_="filter")
            _show_filter_form(show_filters)
            jqm_page_navfooter(navbar, 'filter', page_id)

        elif page == "commands":
            # Page: Commands
            if config.user.may("general.act"):
                jqm_page_header(_("Commands"), left_button=home, id_="commands")
                show_commands = True
                if html.request.has_var("_do_actions"):
                    try:
                        show_commands = do_commands(self.view.datasource.infos[0], rows)
                    except MKUserError as e:
                        html.show_error("%s" % e)
                        html.add_user_error(e.varname, e)
                        show_commands = True
                if show_commands:
                    _show_command_form(self.view.datasource, rows)
                jqm_page_navfooter(navbar, 'commands', page_id)

        elif page == "data":
            # Page: data rows of view
            jqm_page_header(title,
                            left_button=home,
                            right_button=("javascript:document.location.reload();", _("Reload"),
                                          "refresh"),
                            id_="data")
            html.open_div(id_="view_results")
            if len(rows) == 0:
                html.write(_("No hosts/services found."))
            else:
                try:
                    if cmk.gui.view_utils.row_limit_exceeded(unfiltered_amount_of_rows,
                                                             self.view.row_limit):
                        cmk.gui.view_utils.query_limit_exceeded_warn(self.view.row_limit,
                                                                     config.user)
                        del rows[self.view.row_limit:]
                    self.view.layout.render(rows, view_spec, group_cells, cells, num_columns,
                                            show_checkboxes and not html.do_actions())
                except Exception as e:
                    logger.exception("error rendering mobile view")
                    html.write(_("Error showing view: %s") % e)
            html.close_div()
            jqm_page_navfooter(navbar, 'data', page_id)

        # Page: Context buttons
        elif page == "context":
            jqm_page_header(_("Context"), left_button=home, id_="context")
            _show_context_links(context_links)
            jqm_page_navfooter(navbar, 'context', page_id)


def _show_filter_form(show_filters: List[Filter]) -> None:
    # Sort filters
    s = sorted([(f.sort_index, f.title, f) for f in show_filters if f.available()])

    html.begin_form("filter")
    html.open_ul(**{"data-role": "listview", "data-inset": "false"})
    for _sort_index, title, f in s:
        html.open_li(**{"data-role": "fieldcontain"})
        html.write("<legend>%s</legend>" % title)
        f.display()
        html.close_li()
    html.close_ul()
    html.hidden_fields()
    html.hidden_field("search", "Search")
    html.hidden_field("page", "data")
    html.end_form()
    html.javascript("""
      $('.results_button').live('click',function(e) {
        e.preventDefault();
        $('#form_filter').submit();
      });
    """)


def _show_command_form(datasource: ABCDataSource, rows: Rows) -> None:
    what = datasource.infos[0]
    html.javascript("""
    $(document).ready(function() {
      $('.command_group').has('x').trigger('expand');
      $('x').children().css('background-color', '#f84');
    });
    """)
    html.begin_form("commands", html.myfile + ".py#commands")
    html.hidden_field("_do_actions", "yes")
    html.hidden_field("actions", "yes")
    html.hidden_fields()  # set all current variables, exception action vars

    one_shown = False
    html.open_div(**{"data-role": "collapsible-set"})
    for command_class in command_registry.values():
        command = command_class()
        if what in command.tables and config.user.may(command.permission.name):
            html.open_div(class_=["command_group"], **{"data-role": "collapsible"})
            html.h3(command.title)
            html.open_p()
            command.render(what)
            html.close_p()
            html.close_div()
            one_shown = True
    html.close_div()
    if not one_shown:
        html.write(_('No commands are possible in this view'))


# FIXME: Reduce ducplicate code with views.py
def do_commands(what: str, rows: Rows) -> bool:
    command = None
    title, executor = views.core_command(what, rows[0], 0, len(rows))[1:3]  # just get the title
    title_what = _("hosts") if what == "host" else _("services")
    r = html.confirm(
        _("Do you really want to %(title)s the %(count)d %(what)s?") % {
            "title": title,
            "count": len(rows),
            "what": title_what,
        })
    if r is not True:
        return r is None  # Show commands on negative answer

    count = 0
    already_executed: Set[str] = set()
    for nr, row in enumerate(rows):
        nagios_commands, title, executor = views.core_command(what, row, nr, len(rows))
        for command in nagios_commands:
            if command not in already_executed:
                executor(command, row["site"])
                already_executed.add(command)
                count += 1

    if count > 0:
        html.show_message(_("Successfully sent %d commands.") % count)
    return True  # Show commands again


def _show_context_links(context_links: List[PageMenuEntry]) -> None:
    items = []
    for entry in context_links:
        if not isinstance(entry.item, PageMenuLink):
            continue
        items.append(('Context', entry.item.link.url or "", entry.title))
    jqm_page_index(_("Related Views"), items)
