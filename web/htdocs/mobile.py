#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

#!/usr/bin/python
#encoding: utf-8

#import config, defaults, livestatus, htmllib, time, os, re, pprint, time, copy
#import weblib, traceback
import re
from lib import *
import views, config, htmllib
#from pagefunctions import *

# These regexes are taken from the public domain code of Matt Sullivan
# http://sullerton.com/2011/03/django-mobile-browser-detection-middleware/
reg_b = re.compile(r"android.+mobile|avantgo|bada\\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|midp|mmp|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\\/|plucker|pocket|psp|symbian|treo|up\\.(browser|link)|vodafone|wap|windows (ce|phone)|xda|xiino", re.I|re.M)
reg_v = re.compile(r"1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\\-(n|u)|c55\\/|capi|ccwa|cdm\\-|cell|chtm|cldc|cmd\\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\\-s|devi|dica|dmob|do(c|p)o|ds(12|\\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\\-|_)|g1 u|g560|gene|gf\\-5|g\\-mo|go(\\.w|od)|gr(ad|un)|haie|hcit|hd\\-(m|p|t)|hei\\-|hi(pt|ta)|hp( i|ip)|hs\\-c|ht(c(\\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\\-(20|go|ma)|i230|iac( |\\-|\\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\\/)|klon|kpt |kwc\\-|kyo(c|k)|le(no|xi)|lg( g|\\/(k|l|u)|50|54|e\\-|e\\/|\\-[a-w])|libw|lynx|m1\\-w|m3ga|m50\\/|ma(te|ui|xo)|mc(01|21|ca)|m\\-cr|me(di|rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\\-2|po(ck|rt|se)|prox|psio|pt\\-g|qa\\-a|qc(07|12|21|32|60|\\-[2-7]|i\\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\\-|oo|p\\-)|sdk\\/|se(c(\\-|0|1)|47|mc|nd|ri)|sgh\\-|shar|sie(\\-|m)|sk\\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\\-|v\\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\\-|tdg\\-|tel(i|m)|tim\\-|t\\-mo|to(pl|sh)|ts(70|m\\-|m3|m5)|tx\\-9|up(\\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|xda(\\-|2|g)|yas\\-|your|zeto|zte\\-", re.I|re.M)

def is_mobile(user_agent):
    return reg_b.search(user_agent) or reg_v.search(user_agent[0:4])

def mobile_html_head(title, ready_code=""):
    html.mobile = True
    html.write("""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
 <head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
  <meta name="viewport" content="initial-scale=1.0">
  <meta content="yes" name="apple-mobile-web-app-capable" />
  <meta name="apple-mobile-web-app-title" content="Check_MK" />
  <title>%s</title>
  <link rel="stylesheet" type="text/css" href="jquery/jquery.mobile-1.0.css">
  <link rel="stylesheet" type="text/css" href="check_mk.css">
  <link rel="stylesheet" type="text/css" href="status.css">
  <link rel="stylesheet" type="text/css" href="mobile.css">
  <link rel="apple-touch-icon" href="images/ios_logo.png"/>
  <script type='text/javascript' src='jquery/jquery-1.6.4.min.js'></script>
  <script type='text/javascript' src='js/mobile.js'></script>
  <script type='text/javascript' src='jquery/jquery.mobile-1.0.min.js'></script>
  <script type='text/javascript' src='js/checkmk.js'></script>
  <script type='text/javascript'>
      $(document).ready(function() { %s });
      $(document).ready(function() {
        $("a").click(function (event) {
        event.preventDefault();
        window.location = $(this).attr("href");
      });

  </script>

</head>
<body class=mobile>
""" % (title, ready_code))

def mobile_html_foot():
    html.write("</body></html>\n")

def jqm_header_button(pos, url, title, icon=""):
    html.write('<a href="%s" class="ui-btn-%s" data-direction="reverse" data-icon="%s" data-iconpos="notext"  title="%s" ></a>' % (url, pos, icon, title ))

def jqm_page_header(title, id=None, left_button=None, right_button=None):
    idtxt = id and (' id="%s"' % id) or ''
    html.write(
        '<div data-role="page"%s>\n'
        '<div data-role="header" data-position="fixed">\n' % idtxt)
    if left_button:
        jqm_header_button("left", *left_button)
    html.write('<h1>%s</h1>\n' % title)
    if right_button:
        jqm_header_button("right",*right_button)
    html.write('</div>')
    html.write('<div data-role="content">\n')

def jqm_page_footer(content=""):
    html.write('</div>') # close content-div
    html.write(
        '</div>\n'
        '<div data-role="footer"><h4>%s</h4></div>\n' % content)
    html.write('</div>') # close page-div

def jqm_page_navfooter(items, current, page_id):
    html.write("</div>\n") # close content
    html.write(
        '<div data-role="footer" data-position="fixed">\n'
        '<div data-role="navbar">\n'
        '<ul>\n')

    for href, title, icon, custom_css in items:
        href = html.makeuri([("page", href),("search", "Search")])
        if custom_css == False:
	    custom_css = ""
        if current == href:
            custom_css += ' ui-state-persist ui-btn-active'
        else:
            html.write('<li><a class="%s" data-transition="slide"'
                   'data-icon="%s" data-iconpos="bottom" '
                   'href="%s">%s</a></li>\n' %
                   (custom_css, icon, href, title))
    html.write(
        '</ul>\n'
        '</div>\n'
        '</div>\n')
    html.write('</div>') # close page-div


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
            html.write('<p>%s</p><ul data-role="listview" data-inset="true">\n' % topic)
            for top, href, title in items:
                if top == topic:
                    html.write('<li><a data-ajax="false" data-transition="flip" href="%s">%s</a></li>\n' % (href, title))
            html.write('</ul>')
            return


def jqm_page(title, content, foot, id=None):
    jqm_page_header(title, id)
    html.write(content)
    jqm_page_footer(foot)

def page_login():
    title = _("Check_MK Mobile")
    mobile_html_head(title)
    jqm_page_header(title, id="login")
    html.write('<div id="loginhead">%s</div>' %
      _("Welcome to Check_MK Multisite Mobile. Please Login."))

    html.begin_form("login", method = 'POST', add_transid = False)
    # Keep information about original target URL
    origtarget = html.var('_origtarget', '')
    if not origtarget and not html.req.myfile == 'login':
        origtarget = html.req.uri
    html.hidden_field('_origtarget', htmllib.attrencode(origtarget))

    html.text_input("_username", label = _("Username:"))
    html.password_input("_password", size=None, label = _("Password:"))
    html.write("<br>")
    html.button("_login", _('Login'))
    html.set_focus("_username")
    html.end_form()
    html.write('<div id="loginfoot">')
    html.write('<img class="logomk" src="images/logo_mk.png">')
    html.write('<div class="copyright">%s</div>' % _("Copyright Mathias Kettner 2012"))
    html.write('</div>')
    jqm_page_footer()
    mobile_html_foot()
    return 0 # apache.OK


def page_index():
    title = _("Check_MK Mobile")
    mobile_html_head(title)
    jqm_page_header(title, right_button=("javascript:document.location.reload();", _("Reload"), "refresh"),id="data")
    views.load_views()
    items = []
    for view_name, view in html.available_views.items():
        if view.get("mobile") and not view.get("hidden"):
            url = "mobile_view.py?view_name=%s" % view_name
            count = ""
            if not view.get("mustsearch"):
	        count = views.show_view(view, only_count = True)
                count = '<span class="ui-li-count">%d</span>' % count
            items.append((view.get("topic"), url, '%s %s' % (view.get("linktitle", view["title"]), count)))
    jqm_page_index(_("Check_MK Mobile"), items)
    # Link to non-mobile GUI

    html.write('<hr>')
    html.write('<ul data-role="listview" data-theme="b" data-inset="true">\n')
    html.write('<li><a data-ajax="false" data-transition="fade" href="%s">%s</a></li>\n' %                 ("index.py?mobile=", _("Classical web GUI")))
    html.write('</ul>\n')

    html.write('<ul data-role="listview" data-theme="f" data-inset="true">\n')
    html.write('<li><a data-ajax="false" data-transition="fade" href="%s">%s</a></li>\n' %                 ("logout.py", _("Logout")))
    html.write('</ul>\n')
    mobile_html_foot()

def page_view():
    views.load_views()
    view_name = html.var("view_name")
    if not view_name:
        return page_index()

    view = html.available_views.get(view_name)
    if not view:
        raise MKGeneralException("No view defined with the name '%s'." % view_name)

    title = views.view_title(view)
    mobile_html_head(title)

    try:
	views.show_view(view, show_heading = False, show_buttons = False,
			show_footer = False, render_function = render_view)
	pass
    except Exception, e:
	if config.debug:
	    raise
	html.write("ERROR showing view: %s" % e)


    mobile_html_foot()

def render_view(view, rows, datasource, group_painters, painters,
                display_options, painter_options, show_heading, show_buttons,
                show_checkboxes, layout, num_columns, show_filters, show_footer, hide_filters,
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
    if config.may("general.act"):
        navbar.append(( "commands", _("Commands"), "gear", False ))

    # Should we show a page with context links?
    context_links = [
        e for e in views.collect_context_links(view, hide_filters)
        if e[0].get("mobile") ]

    if context_links:
        navbar.append(( "context", _("Context"), "arrow-r", False))
    page_id = "view_" + view["name"]


    if page == "filter":
        jqm_page_header(_("Filter / Search"), left_button=home, id="filter")
        show_filter_form(show_filters)
        jqm_page_navfooter(navbar, 'filter', page_id)

    elif page == "commands":
            # Page: Commands
	    if config.may("general.act"):
		jqm_page_header(_("Commands"), left_button=home, id="commands")
		show_commands = True
		if html.has_var("_do_actions"):
		    try:
			show_commands = do_commands(view, datasource["infos"][0], rows)
		    except MKUserError, e:
			html.show_error(e.message)
			html.add_user_error(e.varname, e.message)
			show_commands = True
		if show_commands:
		    show_command_form(view, datasource, rows)
		jqm_page_navfooter(navbar, 'commands', page_id)

    elif page == "data":
          # Page: data rows of view
	  jqm_page_header(title, left_button=home, right_button=("javascript:document.location.reload();", _("Reload"), "refresh"), id="data")
	  html.write('<div id="view_results">')
	  if len(rows) == 0:
	      html.write(_("No hosts/services found."))
	  else:
	      try:
		  # TODO: special limit for mobile UI
		  html.check_limit(rows, views.get_limit())
		  layout["render"](rows, view, group_painters, painters, num_columns,
				  show_checkboxes and not html.do_actions())
	      except Exception, e:
		  html.write(_("Error showing view: %s" % e))
	  html.write("</div>")
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
    html.write('<ul data-inset="false" data-role="listview">\n')
    for sort_index, title, f in s:
        html.write('<li data-role="fieldcontain">\n')
        html.write('<legend>%s</legend>' % title)
        f.display()
        html.write('</li>')
    html.write("</ul>\n")
    html.hidden_fields()
    html.write('<input type="hidden" name="search" value="Search">')
    html.write('<input type="hidden" name="page" value="data">')
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
    html.begin_form("commands", html.req.myfile + ".py#commands")
    html.hidden_field("_do_actions", "yes")
    html.hidden_field("actions", "yes")
    html.hidden_fields() # set all current variables, exception action vars

    one_shown = False
    html.write('<div data-role="collapsible-set">\n')
    for command in views.multisite_commands:
       if what in command["tables"] and config.may(command["permission"]):
            html.write('<div class="command_group" data-role="collapsible">\n')
            html.write("<h3>%s</h3>" % command["title"])
            html.write('<p>\n')
            command["render"]()
            html.write('</p></div>\n')
            one_shown = True
    html.write("</div>")
    if not one_shown:
        html.write(_('No commands are possible in this view'))

def do_commands(view, what, rows):
    command = None
    title, executor = views.core_command(what, rows[0])[1:3] # just get the title
    r = html.confirm(_("Do you really want to %(title)s the %(count)d %(what)ss?") %
            { "title" : title, "count" : len(rows), "what" : _(what + "s"), })
    if r != True:
        return r == None # Show commands on negative answer

    count = 0
    for row in rows:
        nagios_commands, title, executor = views.core_command(what, row)
        for command in nagios_commands:
            if type(command) == unicode:
                command = command.encode("utf-8")
            executor(command, row["site"])
            count += 1

    if command:
        html.message(_("Successfully sent %d commands.") % count)
    return True # Show commands again

def show_context_links(context_links):
    items = []
    for view, title, uri, icon, buttonid in context_links:
        items.append(('Context', uri, title))
    jqm_page_index(_("Related Views"), items)

