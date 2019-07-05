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

import cmk.gui.views as views
import cmk.gui.config as config
import cmk.gui.visuals as visuals
import cmk.gui.metrics as metrics
import cmk.gui.utils
import cmk.gui.view_utils
from cmk.gui.plugins.views.utils import (
    PainterOptions,
    command_registry,
)

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
from cmk.gui.exceptions import MKUserError


def mobile_html_head(title, ready_code=""):
    html.mobile = True
    html.write(
        """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">"""
    )
    html.open_html()
    html.open_head()
    html.meta(content="text/html;", charset="utf-8", **{"http-equiv": "Content-Type"})
    html.meta(name="viewport", content="initial-scale=1.0")
    html.meta(name="apple-mobile-web-app-capable", content="yes")
    html.meta(name="apple-mobile-web-app-title", content="Check_MK")
    html.title(title)
    html.stylesheet(href="jquery/jquery.mobile-1.0.css")
    html.stylesheet(href="themes/classic/theme.css")

    html.write(
        html._render_opening_tag(
            "link",
            rel="apple-touch-icon",
            href="themes/classic/images/ios_logo.png",
            close_tag=True))
    html.javascript_file(src='js/mobile_min.js')

    if metrics.cmk_graphs_possible():
        html.javascript_file(src='js/graphs.js')

    # Never allow the mobile page to be opened in a frameset. Redirect top page to the current content page.
    # This will result in a full screen mobile interface page.
    html.javascript('''if(top != self) { window.top.location.href = location; }''')

    html.javascript("""
      $(document).ready(function() { %s });
      $(document).ready(function() {
          $("a").click(function (event) {
            event.preventDefault();
            window.location = $(this).attr("href");
          });
      });""" % ready_code)

    html.close_head()
    html.open_body(class_="mobile")


def mobile_html_foot():
    html.close_body()
    html.close_html()


def jqm_header_button(pos, url, title, icon=""):
    html.a(
        '',
        href=url,
        class_="ui-btn-%s" % pos,
        title=title,
        **{
            "data-direction": "reverse",
            "data-icon": icon,
            "data-iconpos": "notext"
        })


def jqm_page_header(title, id_=None, left_button=None, right_button=None):
    html.open_div(id_=id_ if id_ else None, **{"data-role": "page"})
    html.open_div(**{"data-role": "header", "data-position": "fixed"})
    if left_button:
        jqm_header_button("left", *left_button)
    html.h1(title)
    if right_button:
        jqm_header_button("right", *right_button)
    html.close_div()
    html.open_div(**{"data-role": "content"})


def jqm_page_footer(content=""):
    html.close_div()  # close content-div
    html.close_div()
    html.open_div(**{"data-role": "footer"})
    html.open_h4()
    html.write(content)
    html.close_h4()
    html.close_div()
    html.close_div()  # close page-div


def jqm_page_navfooter(items, current, page_id):
    html.close_div()  # close content
    html.open_div(**{"data-role": "footer", "data-position": "fixed"})
    html.open_div(**{"data-role": "navbar"})
    html.open_ul()

    for href, title, icon, custom_css in items:
        href = html.makeuri([("page", href), ("search", "Search")])
        if custom_css is False:
            custom_css = ""
        if current == href:
            custom_css += ' ui-state-persist ui-btn-active'
        else:
            html.open_li()
            html.open_a(
                href=href,
                class_=custom_css,
                **{
                    "data-transition": "slide",
                    "data-icon": icon,
                    "data-iconpos": "bottom"
                })
            html.write(title)
            html.close_a()
            html.close_li()
    html.close_ul()
    html.close_div()
    html.close_div()
    html.close_div()  # close page-div


def jqm_page_index(title, items):
    manual_sort = [_("Hosts"), _("Services"), _("Events")]

    items.sort(cmp=lambda a, b: cmp((a[0], a[2]), (b[0], b[2])))
    for topic in manual_sort:
        jqm_page_index_topic_renderer(topic, items)

    other_topics = list({x[0] for x in items if x[0] not in manual_sort})

    for topic in other_topics:
        jqm_page_index_topic_renderer(topic, items)


def jqm_page_index_topic_renderer(topic, items):
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


def jqm_page(title, content, foot, id_=None):
    jqm_page_header(title, id_)
    html.write(content)
    jqm_page_footer(foot)


def page_login():
    title = _("Check_MK Mobile")
    mobile_html_head(title)
    jqm_page_header(title, id_="login")
    html.div(_("Welcome to Check_MK Mobile."), id_="loginhead")

    html.begin_form("login", method='POST', add_transid=False)
    # Keep information about original target URL
    origtarget = html.request.var('_origtarget', '')
    if not origtarget and not html.myfile == 'login':
        origtarget = html.request.requested_url
    html.hidden_field('_origtarget', html.attrencode(origtarget))

    html.text_input("_username", label=_("Username:"))
    html.password_input("_password", size=None, label=_("Password:"))
    html.br()
    html.button("_login", _('Login'))
    html.set_focus("_username")
    html.end_form()
    html.open_div(id_="loginfoot")
    html.img("themes/classic/images/logo_cmk_small.png", class_="logomk")
    html.div(
        HTML(_("&copy; <a target=\"_blank\" href=\"https://checkmk.com\">tribe29 GmbH</a>")),
        class_="copyright")
    jqm_page_footer()
    mobile_html_foot()


@cmk.gui.pages.register("mobile")
def page_index():
    title = _("Check_MK Mobile")
    mobile_html_head(title)
    jqm_page_header(
        title,
        right_button=("javascript:document.location.reload();", _("Reload"), "refresh"),
        id_="data")
    items = []
    for view_name, view_spec in views.get_permitted_views().items():
        if view_spec.get("mobile") and not view_spec.get("hidden"):
            view = views.View(view_name, view_spec)
            view.row_limit = views.get_limit()
            view.only_sites = views.get_only_sites()
            view.user_sorters = views.get_user_sorters()

            url = "mobile_view.py?view_name=%s" % view_name
            count = ""
            if not view_spec.get("mustsearch"):
                painter_options = PainterOptions.get_instance()
                painter_options.load(view_name)
                view_renderer = MobileViewRenderer(view)
                count = views.show_view(view, view_renderer, only_count=True)
                count = '<span class="ui-li-count">%d</span>' % count
            items.append((view_spec.get("topic"), url,
                          '%s %s' % (view_spec.get("linktitle", view_spec["title"]), count)))
    jqm_page_index(_("Check_MK Mobile"), items)
    # Link to non-mobile GUI

    html.hr()
    html.open_ul(**{"data-role": "listview", "data-theme": "b", "data-inset": "true"})
    html.open_li()
    html.a(
        _("Classical web GUI"),
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
def page_view():
    view_name = html.request.var("view_name")
    if not view_name:
        return page_index()

    view_spec = views.get_permitted_views().get(view_name)
    if not view_spec:
        raise MKUserError("view_name", "No view defined with the name '%s'." % view_name)

    view = views.View(view_name, view_spec)
    view.row_limit = views.get_limit()
    view.only_sites = views.get_only_sites()
    view.user_sorters = views.get_user_sorters()

    title = views.view_title(view_spec)
    mobile_html_head(title)

    painter_options = PainterOptions.get_instance()
    painter_options.load(view_name)

    try:
        view_renderer = MobileViewRenderer(view)
        views.show_view(view, view_renderer)
    except Exception as e:
        if config.debug:
            raise
        html.write("ERROR showing view: %s" % html.attrencode(e))

    mobile_html_foot()


class MobileViewRenderer(views.ViewRenderer):
    def render(self, rows, group_cells, cells, show_checkboxes, layout, num_columns, show_filters):
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
                  ("filter", _("Filter"), "search", False)]
        if config.user.may("general.act"):
            navbar.append(("commands", _("Commands"), "gear", False))

        # Should we show a page with context links?
        context_links = visuals.collect_context_links(view_spec, mobile=True, only_types=['views'])

        if context_links:
            navbar.append(("context", _("Context"), "arrow-r", False))
        page_id = "view_" + view_spec["name"]

        if page == "filter":
            jqm_page_header(_("Filter / Search"), left_button=home, id_="filter")
            show_filter_form(show_filters)
            jqm_page_navfooter(navbar, 'filter', page_id)

        elif page == "commands":
            # Page: Commands
            if config.user.may("general.act"):
                jqm_page_header(_("Commands"), left_button=home, id_="commands")
                show_commands = True
                if html.request.has_var("_do_actions"):
                    try:
                        show_commands = do_commands(view_spec, self.view.datasource.infos[0], rows)
                    except MKUserError as e:
                        html.show_error(e)
                        html.add_user_error(e.varname, e)
                        show_commands = True
                if show_commands:
                    show_command_form(view_spec, self.view.datasource, rows)
                jqm_page_navfooter(navbar, 'commands', page_id)

        elif page == "data":
            # Page: data rows of view
            jqm_page_header(
                title,
                left_button=home,
                right_button=("javascript:document.location.reload();", _("Reload"), "refresh"),
                id_="data")
            html.open_div(id_="view_results")
            if len(rows) == 0:
                html.write(_("No hosts/services found."))
            else:
                try:
                    if cmk.gui.view_utils.query_limit_exceeded_with_warn(
                            rows, self.view.row_limit, config.user):
                        del rows[self.view.row_limit:]
                    layout.render(rows, view_spec, group_cells, cells, num_columns,
                                  show_checkboxes and not html.do_actions())
                except Exception as e:
                    html.write(_("Error showing view: %s") % e)
            html.close_div()
            jqm_page_navfooter(navbar, 'data', page_id)

        # Page: Context buttons
        #if context_links:
        elif page == "context":
            jqm_page_header(_("Context"), left_button=home, id_="context")
            show_context_links(context_links)
            jqm_page_navfooter(navbar, 'context', page_id)


def show_filter_form(show_filters):
    # Sort filters
    s = [(f.sort_index, f.title, f) for f in show_filters if f.available()]
    s.sort()

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


def show_command_form(view, datasource, rows):
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
            command.render()
            html.close_p()
            html.close_div()
            one_shown = True
    html.close_div()
    if not one_shown:
        html.write(_('No commands are possible in this view'))


# FIXME: Reduce ducplicate code with views.py
def do_commands(view, what, rows):
    command = None
    title, executor = views.core_command(what, rows[0], 0, len(rows))[1:3]  # just get the title
    title_what = _("hosts") if what == "host" else _("services")
    r = html.confirm(
        _("Do you really want to %(title)s the %(count)d %(what)s?") % {
            "title": title,
            "count": len(rows),
            "what": title_what,
        })
    if r != True:
        return r is None  # Show commands on negative answer

    count = 0
    already_executed = set([])
    for nr, row in enumerate(rows):
        nagios_commands, title, executor = views.core_command(what, row, nr, len(rows))
        for command in nagios_commands:
            if command not in already_executed:
                if isinstance(command, unicode):
                    command = command.encode("utf-8")
                executor(command, row["site"])
                already_executed.add(command)
                count += 1

    if count > 0:
        html.message(_("Successfully sent %d commands.") % count)
    return True  # Show commands again


def show_context_links(context_links):
    items = []
    for title, uri, _icon, _buttonid in context_links:
        items.append(('Context', uri, title))
    jqm_page_index(_("Related Views"), items)
