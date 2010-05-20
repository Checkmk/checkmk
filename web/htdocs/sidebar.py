#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

import config, defaults, livestatus, htmllib, views, pprint, os, copy
from lib import *

sidebar_snapins = {}

# Load all snapins
snapins_dir = defaults.web_dir + "/plugins/sidebar"
for fn in os.listdir(snapins_dir):
    if fn.endswith(".py"):
	execfile(snapins_dir + "/" + fn)

# Declare permissions: each snapin creates one permission
config.declare_permission_section("sidesnap", "Sidebar snapins")
for name, snapin in sidebar_snapins.items():
    config.declare_permission("sidesnap.%s" % name,
	snapin["title"],
	"",
	snapin["allowed"])

# Helper functions to be used by snapins
def link(text, target):
    # Convert relative links into absolute links. We have three kinds
    # of possible links and we change only [3]
    # [1] protocol://hostname/url/link.py
    # [2] /absolute/link.py
    # [3] relative.py
    if not (":" in target[:10]) and target[0] != '/':
	target = defaults.checkmk_web_uri + "/" + target
    return "<a target=\"main\" class=link href=\"%s\">%s</a>" % (target, htmllib.attrencode(text))

def bulletlink(text, target):
    html.write("<li class=sidebar>" + link(text, target) + "</li>\n")

def footnotelinks(links):
    html.write("<div class=footnotelink>")
    for text, target in links:
	html.write(link(text, target))
    html.write("</div>\n")

def iconbutton(what, url, target="side", handler="", name=""):
    if target == "side":
	onclick = "onclick=\"get_url('%s', %s, '%s')\"" % \
                   (defaults.checkmk_web_uri + "/" + url, handler, name)
	href = "#"
	tg = ""
    else:
	onclick = ""
	href = "%s/%s" % (defaults.checkmk_web_uri, url)
	tg = "target=%s" % target
    html.write("<a href=\"%s\" %s %s><img border=0 onmouseover=\"hilite_icon(this, 1)\" onmouseout=\"hilite_icon(this, 0)\" align=absmiddle src=\"%s/images/button_%s_lo.png\"></a>\n " % (href, onclick, tg, defaults.checkmk_web_uri, what))

def nagioscgilink(text, target):
    html.write("<li class=sidebar><a target=\"main\" class=link href=\"%s/%s\">%s</a></li>" % \
	    (defaults.nagios_cgi_url, target, htmllib.attrencode(text)))

def heading(text):
    html.write("<h3>%s</h3>\n" % htmllib.attrencode(text))

def load_user_config():
    path = config.user_confdir + "/sidebar.mk"
    try:
	user_config = eval(file(path).read())
    except:
	user_config = config.sidebar

    # Remove entries the user is not allowed for or which have state "off" (from legacy version)
    return [ entry for entry in user_config if entry[1] != "off" and config.may("sidesnap." + entry[0])]

def save_user_config(user_config):
    if config.may("configure_sidebar"):
        path = config.user_confdir + "/sidebar.mk"
        try:
            file(path, "w").write(pprint.pformat(user_config) + "\n")
        except Exception, e:
            raise MKConfigError("Cannot save user configuration to <tt>%s</tt>: %s" % (path, e))

def sidebar_head():
    html.write('<div id="side_header" style="margin-top: 0px;">'
	       '<div class="logo"><a target="_blank" href="http://mathias-kettner.de">'
               '<img border=0 src="images/sidebar_oben.png"></a></div>'
#               '<div id="slit_top"></div>'
               '</div>\n')
# "<img src=\"images/side_up.png\" onmouseover=\"scrolling=true;scrollwindow(-2)\" onmouseout=\"scrolling=false\">"

def sidebar_foot():
    html.write('<div id="side_footer">'
               '<div id="slit_bottom"><img src=\"images/sidebar_unten.png\"></div>')
#           '<div class="nav"><img src="images/side_down.png" onmouseover="scrolling=true;scrollwindow(2)" onmouseout="scrolling=false"></div>')
    # if config.may("configure_sidebar"):
    #     html.write('<div class="footnote"><a target="main" href="sidebar_add_snapin.py">Add snapin</a></div>')
    html.write('</div>')

# Standalone sidebar
def page_side(h):
    if not config.may("see_sidebar"):
	return

    global html
    html = h
    html.write("""<html>
<head>
<title>Check_MK Sidebar</title>
<link href="check_mk.css" type="text/css" rel="stylesheet">
<script type="text/javascript" src="check_mk.js"></script>
<script type="text/javascript" src="sidebar.js"></script>
</head>
<body class="side">
<div id="check_mk_sidebar">""")

    views.html = h
    views.load_views()
    sidebar_head()
    user_config = load_user_config()
    refresh_snapins = []

    html.write('<div id="side_content">')
    for name, state in user_config:
	if not name in sidebar_snapins or not config.may("sidesnap." + name):
	   continue
	if state in [ "open", "closed" ]:
	   render_snapin(name, state)
	   refresh_time = sidebar_snapins.get(name).get("refresh", 0)
	   if refresh_time > 0:
	       refresh_snapins.append([name, refresh_time])
    html.write('</div>')
    sidebar_foot()
    html.write('</div>')

    html.write("<script language=\"javascript\">\n")
    html.write("setSidebarHeight();\n")
    html.write("refresh_snapins = %r;\n" % refresh_snapins)
    html.write("sidebar_scheduler();\n")
    html.write("window.onresize = function() { setSidebarHeight(); }\n")
    html.write("</script>\n")

    # html.write("</div>\n")
    html.write("</body>\n</html>")

def render_snapin(name, state):
    snapin = sidebar_snapins.get(name)
    styles = snapin.get("styles")
    if styles:
	html.write("<style>\n%s\n</style>\n" % styles)

    html.write("<div id=\"snapin_container_%s\" class=snapin>\n" % name)
    if state == "closed":
	style = ' style="display:none"'
        headclass = "closed"
    else:
	style = ""
        headclass = "open"
    url = "sidebar_openclose.py?name=%s&state=" % name

    html.write('<div class="head %s" ' % headclass)
    if config.may("configure_sidebar"):
        html.write("onmouseover=\"document.body.style.cursor='move';\" onmouseout=\"document.body.style.cursor='';\""
               " onmousedown=\"snapinStartDrag(event)\" onmouseup=\"snapinStopDrag(event)\">")
    else:
        html.write(">")
    if config.may("configure_sidebar"):
        html.write('<div class="closesnapin">')
        iconbutton("closesnapin", "sidebar_close.py?name=%s&state=off" % name, "side", "removeSnapin", 'snapin_'+name)
        html.write('</div>')
        pass
    html.write("<b class=heading onclick=\"toggle_sidebar_snapin(this,'%s')\" onmouseover=\"this.style.cursor='pointer'\" "
	       "onmouseout=\"this.style.cursor='auto'\">%s</b>" % (url, snapin["title"]))
    html.write("</div>")

    html.write("<div id=\"snapin_%s\" class=content%s>\n" % (name, style))
    try:
	snapin["render"]()
    except Exception, e:
	snapin_exception(e)
    html.write('</div><div class="foot"%s></div>\n' % style)
    html.write('</div>')

def snapin_exception(e):
    if config.debug:
        raise
    else:
        html.write("<div class=snapinexception>\n"
                "<h2>Error</h2>\n"
                "<p>%s</p></div>" % e)

def ajax_openclose(h):
    global html
    html = h

    config = load_user_config()
    new_config = []
    for name, usage in config:
	if html.var("name") == name:
	    usage = html.var("state")
        if usage != "off":
            new_config.append((name, usage))
    save_user_config(new_config)

def ajax_snapin(h):
    global html
    html = h
    snapname = html.var("name")
    if not config.may("sidesnap." + snapname):
	return
    snapin = sidebar_snapins.get(snapname)
    try:
	snapin["render"]()
    except Exception, e:
	snapin_exception(e)

def reposition_snapin(h):
    if not config.may("configure_sidebar"):
        return

    global html
    html      = h
    snapname  = html.var("name")
    aftername = html.var("after")

    new_config = []
    after_pos  = -1
    cur_snapin = None
    for id, snapin in enumerate(load_user_config()):
        if aftername == snapin[0]:
            after_pos = id

        if snapname == snapin[0]:
            cur_snapin = snapin
        else:
            new_config.append(snapin)

    if after_pos == -1:
        new_config.append(cur_snapin)
    else:
        new_config.insert(after_pos-1, cur_snapin)
    save_user_config(new_config)

def page_add_snapin(h):
    if not config.may("configure_sidebar"):
        raise MKGeneralException("You are not allowed to change the sidebar.")

    global html
    html = h
    html.header("Add Snapin")
    used_snapins = [name for (name, state) in load_user_config()]

    addname = html.var("name")
    if addname in sidebar_snapins and addname not in used_snapins and html.transaction_valid():
        user_config = load_user_config() + [(addname, "open")]
        save_user_config(user_config)
        used_snapins = [name for (name, state) in load_user_config()]
	html.reload_sidebar()

    names = sidebar_snapins.keys()
    names.sort()
    html.write('<table class="add_snapin">\n<tr>\n')
    n = 0
    for name in names:
        if name in used_snapins:
            continue
        if n == 3:
            html.write("</tr><tr>\n")
            n = 0
        n += 1
        snapin = sidebar_snapins[name]
        title = snapin["title"]
        description = snapin.get("description", "")
        author = snapin.get("author")
	transid = html.current_transid(html.req.user)
        url = 'sidebar_add_snapin.py?name=%s&_transid=%d&pos=top' % (name, transid)
        html.write('<td onmouseover="this.style.background=\'#cde\'; this.style.cursor=\'pointer\';" '
                'onmouseout="this.style.background=\'#abc\' "'
                'onclick="window.location.href=\'%s\';">' % url)
        
        html.write("<b>%s</b><br>\n"
                "%s" % (title, description))
        if author:
            html.write("<br><i>Author: %s</i>" % author)
      
    html.write("<td></td>" * (3-n))

    html.write("</tr></table>\n")
    html.footer()


