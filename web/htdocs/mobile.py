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

import re
from lib import *
import views, config, visuals, metrics

# These regexes are taken from the public domain code of Matt Sullivan
# http://sullerton.com/2011/03/django-mobile-browser-detection-middleware/
reg_b = re.compile(r"android.+mobile|avantgo|bada\\/|blackberry|bb10|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|midp|mmp|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\\/|plucker|pocket|psp|symbian|treo|up\\.(browser|link)|vodafone|wap|windows (ce|phone)|xda|xiino", re.I|re.M)
reg_v = re.compile(r"1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\\-(n|u)|c55\\/|capi|ccwa|cdm\\-|cell|chtm|cldc|cmd\\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\\-s|devi|dica|dmob|do(c|p)o|ds(12|\\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\\-|_)|g1 u|g560|gene|gf\\-5|g\\-mo|go(\\.w|od)|gr(ad|un)|haie|hcit|hd\\-(m|p|t)|hei\\-|hi(pt|ta)|hp( i|ip)|hs\\-c|ht(c(\\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\\-(20|go|ma)|i230|iac( |\\-|\\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\\/)|klon|kpt |kwc\\-|kyo(c|k)|le(no|xi)|lg( g|\\/(k|l|u)|50|54|e\\-|e\\/|\\-[a-w])|libw|lynx|m1\\-w|m3ga|m50\\/|ma(te|ui|xo)|mc(01|21|ca)|m\\-cr|me(di|rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\\-2|po(ck|rt|se)|prox|psio|pt\\-g|qa\\-a|qc(07|12|21|32|60|\\-[2-7]|i\\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\\-|oo|p\\-)|sdk\\/|se(c(\\-|0|1)|47|mc|nd|ri)|sgh\\-|shar|sie(\\-|m)|sk\\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\\-|v\\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\\-|tdg\\-|tel(i|m)|tim\\-|t\\-mo|to(pl|sh)|ts(70|m\\-|m3|m5)|tx\\-9|up(\\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|xda(\\-|2|g)|yas\\-|your|zeto|zte\\-", re.I|re.M)

def is_mobile(user_agent):
    return reg_b.search(user_agent) or reg_v.search(user_agent[0:4])

def mobile_html_head(title, ready_code=""):
    html.mobile = True
    html.write("""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">""")
    html.open_html()
    html.open_head()
    html.meta(content="text/html;", charset="utf-8", **{"http-equiv":"Content-Type"})
    html.meta(name="viewport", content="initial-scale=1.0")
    html.meta(name="apple-mobile-web-app-capable", content="yes")
    html.meta(name="apple-mobile-web-app-title", content="Check_MK")
    html.title(title)
    html.stylesheet(href="jquery/jquery.mobile-1.0.css")
    html.stylesheet(href="check_mk.css")
    html.stylesheet(href="status.css")
    html.stylesheet(href="mobile.css")

    if metrics.cmk_graphs_possible():
        html.stylesheet(href="graphs.css")

    html.write(html._render_opening_tag("link", rel="apple-touch-icon", href="images/ios_logo.png", close_tag=True))
    html.javascript_file(src='jquery/jquery-1.6.4.min.js')
    html.javascript_file(src='js/mobile.js')
    html.javascript_file(src='jquery/jquery.mobile-1.0.min.js')
    html.javascript_file(src='js/checkmk.js')

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
    html.store_new_transids()

def jqm_header_button(pos, url, title, icon=""):
    html.a('', href=url, class_="ui-btn-%s" % pos, title=title, **{"data-direction":"reverse", "data-icon":icon, "data-iconpos":"notext"})

def jqm_page_header(title, id=None, left_button=None, right_button=None):
    html.open_div(id_= id if id else None, **{"data-role":"page"})
    html.open_div(**{"data-role":"header", "data-position":"fixed"})
    if left_button:
        jqm_header_button("left", *left_button)
    html.h1(title)
    if right_button:
        jqm_header_button("right",*right_button)
    html.close_div()
    html.open_div(**{"data-role":"content"})

def jqm_page_footer(content=""):
    html.close_div() # close content-div
    html.close_div()
    html.open_div(**{"data-role":"footer"})
    html.open_h4()
    html.write(content)
    html.close_h4()
    html.close_div()
    html.close_div() # close page-div

def jqm_page_navfooter(items, current, page_id):
    html.close_div() # close content
    html.open_div(**{"data-role":"footer", "data-position":"fixed"})
    html.open_div(**{"data-role":"navbar"})
    html.open_ul()

    for href, title, icon, custom_css in items:
        href = html.makeuri([("page", href),("search", "Search")])
        if custom_css == False:
            custom_css = ""
        if current == href:
            custom_css += ' ui-state-persist ui-btn-active'
        else:
            html.open_li()
            html.open_a(href=href, class_=custom_css,
                        **{"data-transition":"slide", "data-icon":icon, "data-iconpos":"bottom"})
            html.write(title)
            html.close_a()
            html.close_li()
    html.close_ul()
    html.close_div()
    html.close_div()
    html.close_div() # close page-div


def jqm_page_index(title, items):
    manual_sort = [_("Hosts"), _("Services"), _("Events")]

    items.sort(cmp = lambda a,b: cmp((a[0],a[2]),(b[0],b[2])))
    for topic in manual_sort:
        jqm_page_index_topic_renderer(topic, items)

    other_topics = list(set([ x[0] for x in items if x[0] not in manual_sort]))

    for topic in other_topics:
        jqm_page_index_topic_renderer(topic, items)


def jqm_page_index_topic_renderer(topic, items):
    for top, href, title in items:
        if top == topic:
            html.open_p()
            html.write(topic)
            html.close_p()
            html.open_ul(**{"data-role":"listview", "data-inset":"true"})
            for top, href, title in items:
                if top == topic:
                    html.open_li()
                    html.open_a(href=href, **{"data-ajax":"false", "data-transition":"flip"})
                    html.write(title)
                    html.close_a()
                    html.close_li()
            html.close_ul()
            return


def jqm_page(title, content, foot, id=None):
    jqm_page_header(title, id)
    html.write(content)
    jqm_page_footer(foot)

def page_login():
    title = _("Check_MK Mobile")
    mobile_html_head(title)
    jqm_page_header(title, id="login")
    html.div(_("Welcome to Check_MK Mobile."), id_="loginhead")

    html.begin_form("login", method = 'POST', add_transid = False)
    # Keep information about original target URL
    origtarget = html.var('_origtarget', '')
    if not origtarget and not html.myfile == 'login':
        origtarget = html.req.uri
    html.hidden_field('_origtarget', html.attrencode(origtarget))

    html.text_input("_username", label = _("Username:"))
    html.password_input("_password", size=None, label = _("Password:"))
    html.br()
    html.button("_login", _('Login'))
    html.set_focus("_username")
    html.end_form()
    html.open_div(id_="loginfoot")
    html.write('<img class="logomk" src="images/logo_cmk_small.png">')
    html.write('<div class="copyright">%s</div>' %
      _("&copy; <a target=\"_blank\" href=\"https://mathias-kettner.com\">Mathias Kettner</a>"))
    html.write('</div>')
    jqm_page_footer()
    mobile_html_foot()


def page_index():
    title = _("Check_MK Mobile")
    mobile_html_head(title)
    jqm_page_header(title, right_button=("javascript:document.location.reload();", _("Reload"), "refresh"),id="data")
    views.load_views()
    items = []
    for view_name, view in views.permitted_views().items():
        if view.get("mobile") and not view.get("hidden"):
            url = "mobile_view.py?view_name=%s" % view_name
            count = ""
            if not view.get("mustsearch"):
                views.prepare_painter_options(view_name)
                count = views.show_view(view, only_count = True)
                count = '<span class="ui-li-count">%d</span>' % count
            items.append((view.get("topic"), url, '%s %s' % (view.get("linktitle", view["title"]), count)))
    jqm_page_index(_("Check_MK Mobile"), items)
    # Link to non-mobile GUI

    html.hr()
    html.open_ul(**{"data-role":"listview", "data-theme":"b", "data-inset":"true"})
    html.open_li()
    html.a(_("Classical web GUI"), href="index.py?mobile=", **{"data-ajax":"false", "data-transition":"fade"})
    html.close_li()
    html.close_ul()

    html.open_ul(**{"data-role":"listview", "data-theme":"f", "data-inset":"true"})
    html.open_li()
    html.a(_("Logout"), href="logout.py", **{"data-ajax":"false", "data-transition":"fade"})
    html.close_li()
    html.close_ul()
    mobile_html_foot()

def page_view():
    views.load_views()
    view_name = html.var("view_name")
    if not view_name:
        return page_index()

    view = views.permitted_views().get(view_name)
    if not view:
        raise MKGeneralException("No view defined with the name '%s'." % view_name)

    title = views.view_title(view)
    mobile_html_head(title)

    views.prepare_painter_options(view_name)

    try:
        views.show_view(view, show_heading = False, show_buttons = False,
            show_footer = False, render_function = render_view)
    except Exception, e:
        if config.debug:
            raise
        html.write("ERROR showing view: %s" % html.attrencode(e))


    mobile_html_foot()

def render_view(view, rows, datasource, group_painters, painters,
                show_heading, show_buttons,
                show_checkboxes, layout, num_columns, show_filters, show_footer,
                browser_reload):

    home=("mobile.py", "Home", "home")

    page = html.var("page")
    if not page:
       if view.get("mustsearch"):
           page = "filter"
       else:
            page = "data"

    title = views.view_title(view)
    navbar = [ ( "data",     _("Results"), "grid", 'results_button'),
               ( "filter",   _("Filter"),   "search", False )]
    if config.user.may("general.act"):
        navbar.append(( "commands", _("Commands"), "gear", False ))

    # Should we show a page with context links?
    context_links = visuals.collect_context_links(view, mobile = True, only_types = ['views'])

    if context_links:
        navbar.append(( "context", _("Context"), "arrow-r", False))
    page_id = "view_" + view["name"]


    if page == "filter":
        jqm_page_header(_("Filter / Search"), left_button=home, id="filter")
        show_filter_form(show_filters)
        jqm_page_navfooter(navbar, 'filter', page_id)

    elif page == "commands":
            # Page: Commands
            if config.user.may("general.act"):
                jqm_page_header(_("Commands"), left_button=home, id="commands")
                show_commands = True
                if html.has_var("_do_actions"):
                    try:
                        show_commands = do_commands(view, datasource["infos"][0], rows)
                    except MKUserError, e:
                        html.show_error(e)
                        html.add_user_error(e.varname, e)
                        show_commands = True
                if show_commands:
                    show_command_form(view, datasource, rows)
                jqm_page_navfooter(navbar, 'commands', page_id)

    elif page == "data":
          # Page: data rows of view
          jqm_page_header(title, left_button=home, right_button=("javascript:document.location.reload();", _("Reload"), "refresh"), id="data")
          html.open_div(id_="view_results")
          if len(rows) == 0:
              html.write(_("No hosts/services found."))
          else:
              try:
                  # TODO: special limit for mobile UI
                  html.check_limit(rows, views.get_limit())
                  layout["render"](rows, view, group_painters, painters, num_columns,
                                  show_checkboxes and not html.do_actions())
              except Exception, e:
                  html.write(_("Error showing view: %s") % e)
          html.close_div()
          jqm_page_navfooter(navbar, 'data', page_id)

    # Page: Context buttons
    #if context_links:
    elif page == "context":
        jqm_page_header(_("Context"), left_button=home, id="context")
        show_context_links(context_links)
        jqm_page_navfooter(navbar, 'context', page_id)


def show_filter_form(show_filters):
    # Sort filters
    s = [(f.sort_index, f.title, f) for f in show_filters if f.available()]
    s.sort()

    html.begin_form("filter")
    html.open_ul(**{"data-role":"listview", "data-inset":"false"})
    for sort_index, title, f in s:
        html.open_li(**{"data-role":"fieldcontain"})
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
    what = datasource["infos"][0]
    html.javascript("""
    $(document).ready(function() {
      $('.command_group').has('x').trigger('expand');
      $('x').children().css('background-color', '#f84');
    });
    """)
    html.begin_form("commands", html.myfile + ".py#commands")
    html.hidden_field("_do_actions", "yes")
    html.hidden_field("actions", "yes")
    html.hidden_fields() # set all current variables, exception action vars

    one_shown = False
    html.open_div(**{"data-role":"collapsible-set"})
    for command in views.multisite_commands:
        if what in command["tables"] and config.user.may(command["permission"]):
            html.open_div(class_=["command_group"], **{"data-role":"collapsible"})
            html.h3(command["title"])
            html.open_p()
            command["render"]()
            html.close_p()
            html.close_div()
            one_shown = True
    html.close_div()
    if not one_shown:
        html.write(_('No commands are possible in this view'))

# FIXME: Reduce ducplicate code with views.py
def do_commands(view, what, rows):
    command = None
    title, executor = views.core_command(what, rows[0], 0, len(rows))[1:3] # just get the title
    title_what = _("hosts") if what == "host" else _("services")
    r = html.confirm(_("Do you really want to %(title)s the %(count)d %(what)s?") %
            { "title" : title, "count" : len(rows), "what" : title_what, })
    if r != True:
        return r == None # Show commands on negative answer

    count = 0
    already_executed = set([])
    for nr, row in enumerate(rows):
        nagios_commands, title, executor = views.core_command(what, row, nr, len(rows))
        for command in nagios_commands:
            if command not in already_executed:
                if type(command) == unicode:
                    command = command.encode("utf-8")
                executor(command, row["site"])
                already_executed.add(command)
                count += 1

    if count > 0:
        html.message(_("Successfully sent %d commands.") % count)
    return True # Show commands again

def show_context_links(context_links):
    items = []
    for title, uri, icon, buttonid in context_links:
        items.append(('Context', uri, title))
    jqm_page_index(_("Related Views"), items)

