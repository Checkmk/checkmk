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
    if not target.startswith("http:") and target[0] != '/':
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
    html.write("<a href=\"%s\" %s %s><img border=0 onmouseover=\"hilite_icon(this, 1)\" onmouseout=\"hilite_icon(this, 0)\" align=absmiddle src=\"%s/images/icon_%s14lo.png\"></a>\n " % (href, onclick, tg, defaults.checkmk_web_uri, what))

def nagioscgilink(text, target):
    html.write("<li class=sidebar><a target=\"main\" class=link href=\"%s/%s\">%s</a></li>" % \
	    (defaults.nagios_cgi_url, target, htmllib.attrencode(text)))

def heading(text):
    html.write("<h3>%s</h3>\n" % htmllib.attrencode(text))

def load_user_config():
    path = config.user_confdir + "/sidebar.mk"
    try:
	saved_user_config = eval(file(path).read())
    except:
	saved_user_config = config.sidebar

    # Now make sure that all snapins are listed in the config
    # even if turned off.
    user_config = copy.copy(saved_user_config)
    for name in sidebar_snapins.keys():
	found = False
	for n, u in user_config:
	    if n == name: found = True
	if not found:
	    user_config.append((name, "off"))

    # Remove entries the user is not allowed for
    return [ entry for entry in user_config if config.may("sidesnap." + entry[0])]

def save_user_config(user_config):
    path = config.user_confdir + "/sidebar.mk"
    try:
	file(path, "w").write(pprint.pformat(user_config) + "\n")
    except Exception, e:
	raise MKConfigError("Cannot save user configuration to <tt>%s</tt>: %s" % (path, e))
  
# Standalone sidebar
def page_side(h):
    global html
    html = h
    html.write("""<html>
<head>
<title>Check_MK Sidebar</title>
<link href="%s/check_mk.css" type="text/css" rel="stylesheet">
</head>
<body style="background-color: black">
<div id=check_mk_sidebar><script src="%s/sidebar.js"></script></div>
</body>
</html>
""" % ((defaults.checkmk_web_uri, ) * 2))

# Embedded sidebar
def page_sidebar(h):
    global html
    html = h
    if not config.may("see_sidebar"):
	return

    views.html = h
    views.load_views()
    html.write("<div class=header><table><tr>"
		"<td class=title><a target=\"main\" href=\"main.py\">Check_MK</a></td>"
		"<td class=logo><a target=\"_blank\" href=\"http://mathias-kettner.de\"><img border=0 src=\"%s/images/MK-mini-black.gif\"></a></td>"
		"</tr></table></div>\n" % \
	    defaults.checkmk_web_uri)
    user_config = load_user_config()
    refresh_snapins = []
    for name, state in user_config:
	if not name in sidebar_snapins or not config.may("sidesnap." + name):
	   continue
	if state in [ "open", "closed" ]:
	   render_snapin(name, state)
	   refresh_time = sidebar_snapins.get(name).get("refresh", 0)
	   if refresh_time > 0:
	       refresh_snapins.append([name, refresh_time])
    html.write("<div class=footnote><a target=\"main\" href=\"%s/sidebar_config.py\">Configure sidebar</a></div>\n" % \
	    defaults.checkmk_web_uri)
    html.write("<script language=\"javascript\">\n")
    html.write("refresh_snapins = %r;\n" % refresh_snapins)
    html.write("sidebar_scheduler();\n")
    html.write("</script>\n")

def render_snapin(name, state):
    snapin = sidebar_snapins.get(name)
    styles = snapin.get("styles")
    if styles:
	html.write("<style>\n%s\n</style>\n" % styles)

    html.write("<div class=section>\n")
    if state == "closed":
	style = ' style="display:none"'
    else:
	style = ""
    url = defaults.checkmk_web_uri + "/sidebar_openclose.py?name=%s&state=" % name
    iconbutton("close", "sidebar_openclose.py?name=%s&state=off" % name, "side", "removeSnapin", 'snapin_'+name)
    html.write("<b class=heading onclick=\"toggle_sidebar_snapin(this,'%s')\" onmouseover=\"this.style.cursor='pointer'\" "
	       "onmouseout=\"this.style.cursor='auto'\">%s" % (url, snapin["title"]))
    html.write("</b><div id=\"snapin_%s\" class=content%s>\n" % (name, style))
    try:
	snapin["render"]()
    except Exception, e:
	snapin_exception(e)
    html.write("</div></div>\n")

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


def page_configure(h):
    global html
    html = h
    html.header("Configure Sidebar")

    userconf = load_user_config() # contains only allowed snapins
    changed = False

    if html.check_transaction():
	# change states
	if html.var("_saved"):
	    new_config = []
	    n = 0
	    for name, usage in userconf:
		new_usage = html.var("snapin_%d" % n)
		if new_usage in ["off", "open", "closed"]:
		    usage = new_usage
		new_config.append((name, usage))
		n += 1
	    userconf = new_config
	    save_user_config(userconf)
	    changed = True

	# handle up and down
	n = 0
	for name, usage in userconf:
	    if html.var("snapin_up_%d" % n) == "UP": # Cannot be 0
		userconf = userconf[0:n-1] + [(name,usage)] + [userconf[n-1]] + userconf[n+1:]
		save_user_config(userconf)
		changed = True
		break
	    elif html.var("snapin_down_%d" % n) == "DOWN": # Cannot be last one
		userconf = userconf[0:n] + [userconf[n+1]] + [(name,usage)] + userconf[n+2:]
		save_user_config(userconf)
		changed = True
		break
	    n += 1
	
	# reload sidebar, if user changed something
	if changed:
	    html.reload_sidebar()


    html.begin_form("sidebarconfig")
    html.hidden_field("_saved", "yes")
    html.write("<p>Here you can configure, which snapins you want to see in your personal "
	    "sidebar and wether they are closed or opened at startup.</p>")
    html.write("<table class=sidebarconfig>\n"
	    "<tr><th>Snapin</th><th>Usage</th><th colspan=2>Move</th></tr>\n")

    n = 0
    for name, usage in userconf:
	if name not in sidebar_snapins:
	    n += 1
	    continue

	snapin = sidebar_snapins[name]
	html.set_var("snapin_%d" % n, usage)
	html.write("<tr>\n")
	html.write("<td class=title>%s</td>\n" % snapin["title"])
	html.write("<td class=widget>")
	html.select("snapin_%d" % n, [("off", "off"), ("open", "open"), ("closed","closed")], None, "this.form.submit()")
	html.write("</td><td>")
	if n > 0:
	    html.button("snapin_up_%d" % n, "UP")
	html.write("</td><td>")
	if n < len(userconf) - 1:
	    html.button("snapin_down_%d" % n, "DOWN")
	html.write("</td></tr>\n")
	n += 1
    html.write("</table>\n")

    html.write("<p> In order "
	    "to integrate the Check_MK sidebar snapins into your sidebar, please "
	    "add the following to your Nagios' <tt>side.html</tt> or <tt>side.php</tt></p>\n")
    html.write("<pre>\n%s</pre>\n" % htmllib.attrencode('<div id="check_mk_sidebar"><script src="%s/sidebar.js"></script></div>' % defaults.checkmk_web_uri))
    html.end_form()

    html.footer()
