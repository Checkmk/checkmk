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

import views, time, defaults

# --------------------------------------------------------------
#       _    _                 _   
#      / \  | |__   ___  _   _| |_ 
#     / _ \ | '_ \ / _ \| | | | __|
#    / ___ \| |_) | (_) | |_| | |_ 
#   /_/   \_\_.__/ \___/ \__,_|\__|
#                                  
# --------------------------------------------------------------
def render_about():
    html.write("Version: " + defaults.check_mk_version)
    bulletlink("Homepage",        "http://mathias-kettner.de/check_mk.html")
    bulletlink("Documentation",   "http://mathias-kettner.de/checkmk.html")
    bulletlink("Download",        "http://mathias-kettner.de/check_mk_download.html")
    bulletlink("Mathias Kettner", "http://mathias-kettner.de")

sidebar_snapins["about"] = {
    "title" : "About Check_MK",
    "render" : render_about,
    "allowed" : [ "admin", "user", "guest" ],
}

# -----------------------------------------------------------------------
#      _       _           _       _     _             _   _             
#     / \   __| |_ __ ___ (_)_ __ (_)___| |_ _ __ __ _| |_(_) ___  _ __  
#    / _ \ / _` | '_ ` _ \| | '_ \| / __| __| '__/ _` | __| |/ _ \| '_ \ 
#   / ___ \ (_| | | | | | | | | | | \__ \ |_| | | (_| | |_| | (_) | | | |
#  /_/   \_\__,_|_| |_| |_|_|_| |_|_|___/\__|_|  \__,_|\__|_|\___/|_| |_|
#
# -----------------------------------------------------------------------
def render_admin():
    bulletlink("View permissions", "view_permissions.py")
    if config.may("edit_permissions"):
	bulletlink("Edit permissions", "edit_permissions.py")

sidebar_snapins["admin"] = {
    "title" : "Administration",
    "render" : render_admin,
    "allowed" : [ "admin" ],
}


# --------------------------------------------------------------
#   __     ___                   
#   \ \   / (_) _____      _____ 
#    \ \ / /| |/ _ \ \ /\ / / __|
#     \ V / | |  __/\ V  V /\__ \
#      \_/  |_|\___| \_/\_/ |___/
#                                
# --------------------------------------------------------------
def render_views():
    authuser = html.req.user
    s = [ (view["title"], name) for name, view in html.available_views.items() if not view["hidden"] ]
    s.sort()
    for title, name in s:
        bulletlink(title, "view.py?view_name=%s" % name)

    links = []
    if config.may("edit_views"):
	if config.debug:
	    links.append(("EXPORT", "export_views.py"))
	links.append(("EDIT", "edit_views.py"))
	footnotelinks(links)

sidebar_snapins["views"] = {
    "title" : "Views",
    "render" : render_views,
    "allowed" : [ "user", "admin", "guest" ],
}

# --------------------------------------------------------------
#    ____                  _                     __
#   / ___|  ___ _ ____   _(_) ___ ___           / /
#   \___ \ / _ \ '__\ \ / / |/ __/ _ \_____    / / 
#    ___) |  __/ |   \ V /| | (_|  __/_____|  / /  
#   |____/ \___|_|    \_/ |_|\___\___|       /_/   
#                                                  
#   _   _           _                                  
#  | | | | ___  ___| |_ __ _ _ __ ___  _   _ _ __  ___ 
#  | |_| |/ _ \/ __| __/ _` | '__/ _ \| | | | '_ \/ __|
#  |  _  | (_) \__ \ || (_| | | | (_) | |_| | |_) \__ \
#  |_| |_|\___/|___/\__\__, |_|  \___/ \__,_| .__/|___/
#                      |___/                |_|        
# --------------------------------------------------------------
def render_groups(what):
    data = html.live.query("GET %sgroups\nColumns: name alias\n" % what)
    name_to_alias = dict(data)
    groups = [(name_to_alias[name], name) for name in name_to_alias.keys()]
    groups.sort() # sort by Alias!
    target = views.get_context_link(html.req.user, "%sgroup" % what)
    if target:
	for alias, name in groups:
	    bulletlink(alias, target + "&%sgroup=%s" % (what, htmllib.urlencode(name)))

sidebar_snapins["hostgroups"] = {
    "title" : "Hostgroups",
    "render" : lambda: render_groups("host"),
    "allowed" : [ "user", "admin", "guest" ]
}
sidebar_snapins["servicegroups"] = {
    "title" : "Servicegroups",
    "render" : lambda: render_groups("service"),
    "allowed" : [ "user", "admin", "guest" ]
}

# --------------------------------------------------------------
#    _   _           _       
#   | | | | ___  ___| |_ ___ 
#   | |_| |/ _ \/ __| __/ __|
#   |  _  | (_) \__ \ |_\__ \
#   |_| |_|\___/|___/\__|___/
#                            
# --------------------------------------------------------------
def render_hosts(only_problems = False):
    html.live.set_prepend_site(True)
    query = "GET hosts\nColumns: name state worst_service_state\n"
    if only_problems:
	query += "Filter: state > 0\nFilter: worst_service_state > 0\nOr: 2\n"
        view = "problemsofhost"
    else:
        view = "host"
    hosts = html.live.query(query)
    html.live.set_prepend_site(False)
    hosts.sort()
    views.html = html
    views.load_views()
    target = views.get_context_link(html.req.user, view)
    for site, host, state, worstsvc in hosts:
	if state > 0 or worstsvc == 2:
	   statecolor = 2
	elif worstsvc == 1:
	   statecolor = 1
	elif worstsvc == 3:
	   statecolor = 3
	else:
	   statecolor = 0
	html.write('<div class="statebullet state%d">&nbsp;</div> ' % statecolor)
        html.write(link(host, target + ("&host=%s&site=%s" % (htmllib.urlencode(host), htmllib.urlencode(site)))))
	html.write("<br>\n")

sidebar_all_hosts_styles = """
div.statebullet { margin-left: 2px; margin-right: 4px; width: 10px; height: 10px; border: 1px solid black; float: left; }
div.state0 { background-color: #4c4; border-color: #0f0;  }
div.state1 { background-color: #ff0; }
div.state2 { background-color: #f00; }
div.state3 { background-color: #f80; }
"""

sidebar_snapins["hosts"] = {
    "title" : "All hosts",
    "render" : lambda: render_hosts(False),
    "allowed" : [ "user", "admin", "guest" ],
    "refresh" : 60,
    "styles" : sidebar_all_hosts_styles
}

sidebar_snapins["problem_hosts"] = {
    "title" : "Problem hosts",
    "render" : lambda: render_hosts(True),
    "allowed" : [ "user", "admin", "guest" ],
    "refresh" : 60,
    "styles" : sidebar_all_hosts_styles
}
    

# --------------------------------------------------------------
#    ____  _ _            _        _             
#   / ___|(_) |_ ___  ___| |_ __ _| |_ _   _ ___ 
#   \___ \| | __/ _ \/ __| __/ _` | __| | | / __|
#    ___) | | ||  __/\__ \ || (_| | |_| |_| \__ \
#   |____/|_|\__\___||___/\__\__,_|\__|\__,_|___/
#                                                
# --------------------------------------------------------------
def render_sitestatus():
    if config.is_multisite():
	html.write("<table cellspacing=0 class=sitestate>")
	for sitename in config.allsites():
	    site = config.site(sitename)
	    state = html.site_status[sitename]["state"]
	    if state == "disabled":
		switch = "on"
		text = site["alias"]
	    else:
		switch = "off"
		text = link(site["alias"], "view.py?view_name=sitehosts&site=%s" % sitename)

	    html.write("<tr><td class=left>%s</td>" % text)
	    onclick = "switch_site('%s', '_site_switch=%s:%s')" % (defaults.checkmk_web_uri, sitename, switch)
	    html.write("<td class=\"state %s\">" % state)
	    html.write("<a href=\"\" onclick=\"%s\">%s</a></td>" % (onclick, state[:3]))
	    html.write("</tr>\n")
	html.write("</table>\n")
    

sidebar_snapins["sitestatus"] = {
  "title" : "Site status",
  "render" : render_sitestatus,
  "allowed" : [ "user", "admin" ],
  "styles" : """
div#check_mk_sidebar table.sitestate {
    width: 100%;
}

div#check_mk_sidebar table.sitestate td {
    padding: 0px 0px;
    text-align: right;
}

div#check_mk_sidebar table.sitestate td a {
    font-weight: bold;
    -moz-border-radius: 4px;
    margin: 0px;
    padding: 0px 0px;
    text-align: center;
    font-size: 7pt;
    display: block;
}
div#check_mk_sidebar table.sitestate td.left a {
    text-align: left;
    font-size: 8pt;
    font-weight: normal;
}

div#check_mk_sidebar table.sitestate td.state {
    width: 30px;
}
div#check_mk_sidebar table.sitestate td.left {
    text-align: left;
}

div#check_mk_sidebar table.sitestate td.offline a {
    background-color: #f00;
    color: #000;
    border-color: #800;
}
div#check_mk_sidebar table.sitestate td.online a {
    background-color: #3f6;
    color: #fff;
    border-color: #0f0;
}
div#check_mk_sidebar table.sitestate td.disabled a {
    background-color: #666;
    border-color: #888;
}
"""
}


# --------------------------------------------------------------
#    _____          _   _           _                             _               
#   |_   _|_ _  ___| |_(_) ___ __ _| |   _____   _____ _ ____   _(_) _____      __
#     | |/ _` |/ __| __| |/ __/ _` | |  / _ \ \ / / _ \ '__\ \ / / |/ _ \ \ /\ / /
#     | | (_| | (__| |_| | (_| (_| | | | (_) \ V /  __/ |   \ V /| |  __/\ V  V / 
#     |_|\__,_|\___|\__|_|\___\__,_|_|  \___/ \_/ \___|_|    \_/ |_|\___| \_/\_/  
#                                                                                 
# --------------------------------------------------------------
# Filter for host problems:
#
tactical_overview_hostfilter = \
"""
"""

tactical_overview_servicefilter = \
"""Filter: service_state = 1
Filter: service_has_been_checked = 1
And: 2
Filter: service_state = 2
Filter: service_has_been_checked = 1
And: 2
Filter: service_state = 3
Filter: service_has_been_checked = 1
And: 2
Or: 3
Filter: service_scheduled_downtime_depth = 0
Filter: host_scheduled_downtime_depth = 0
And: 2
"""

def render_tactical_overview():
    host_query = \
        "GET hosts\n" \
        "Stats: state >= 0\n" \
	"Stats: state > 0\n" \
        "Stats: scheduled_downtime_depth = 0\n" \
        "StatsAnd: 2\n" \
	"Stats: state > 0\n" \
        "Stats: scheduled_downtime_depth = 0\n" \
	"Stats: acknowledged = 0\n" \
	"StatsAnd: 3\n"

    service_query = \
        "GET services\n" \
        "Stats: state >= 0\n" \
	"Stats: state > 0\n" \
        "Stats: scheduled_downtime_depth = 0\n" \
        "Stats: host_scheduled_downtime_depth = 0\n" \
        "StatsAnd: 3\n" \
	"Stats: state > 0\n" \
        "Stats: scheduled_downtime_depth = 0\n" \
        "Stats: host_scheduled_downtime_depth = 0\n" \
	"Stats: acknowledged = 0\n" \
	"StatsAnd: 4\n"

    # ACHTUNG: Stats-Filter so anpassen, dass jeder Host gezaehlt wird.

    try:
        hstdata = html.live.query_summed_stats(host_query)
        svcdata = html.live.query_summed_stats(service_query)
    except livestatus.MKLivestatusNotFoundError:
	html.write("<center>No data from any site</center>")
	return
    html.write("<table class=tacticaloverview cellspacing=0 cellpadding=0 border=0>\n")
    for title, data, view, what in [
	    ("Hosts",    hstdata, 'hostproblems', 'host'),
	    ("Services", svcdata, 'svcproblems',  'service'), 
	    ]:
	html.write("<tr><th>%s</th><th>Problems</th><th>Unhandled</th></tr>\n" % title)
	html.write("<tr>")

	html.write("<td class=total>%d</td>" % data[0])
	unhandled = False
	for value in data[1:]:
	    if value > 0:
		href = "view.py?view_name=" + view
		if unhandled:
		             
		    href += "&is_%s_acknowledged=0" % what
		text = link(str(value), href)
	    else:
		text = str(value)
            html.write("<td class=%sprob>%s</td>" % (value == 0 and "no" or "", text))
	    unhandled = True
	html.write("</tr>\n")
    html.write("</table>\n")
		    
sidebar_snapins["tactical_overview"] = {
    "title" : "Tactical Overview",
    "refresh" : 10,
    "render" : render_tactical_overview,
    "allowed" : [ "user", "admin", "guest" ],
    "styles" : """
table.tacticaloverview { border-collapse: separate; border-spacing: 5px 0px; width: 100%;}
table.tacticaloverview th { font-size: 7pt; text-align: left; font-weight: normal; padding: 0px; padding-top: 2px; }
table.tacticaloverview td { text-align: right; border: 1px solid #444; padding: 0px; padding-right: 2px; }
table.tacticaloverview td.prob { background-color: #f08; color: #f00; font-weight: bold; }
"""
}

# --------------------------------------------------------------
#    ____            __                                           
#   |  _ \ ___ _ __ / _| ___  _ __ _ __ ___   __ _ _ __   ___ ___ 
#   | |_) / _ \ '__| |_ / _ \| '__| '_ ` _ \ / _` | '_ \ / __/ _ \
#   |  __/  __/ |  |  _| (_) | |  | | | | | | (_| | | | | (_|  __/
#   |_|   \___|_|  |_|  \___/|_|  |_| |_| |_|\__,_|_| |_|\___\___|
#                                                                 
# --------------------------------------------------------------
def render_performance():
    data = html.live.query("GET status\nColumns: service_checks_rate host_checks_rate connections_rate forks_rate\n")
    html.write("<table class=performance>\n")
    for what, col in \
	[("Serv. checks", 0), 
	("Host checks", 1),
	("Livestatus-conn.", 2),
	("Process creations", 3)]:
	html.write("<tr><td class=left>%s:</td><td class=right>%.2f/s</td></tr>\n" % (what, sum([row[col] for row in data])))
    html.write("</table>\n")
		    
sidebar_snapins["performance"] = {
    "title" : "Server performance",
    "refresh" : 5,
    "render" : render_performance,
    "allowed" : [ "admin", ],
    "styles" : """
table.performance { font-size: 8pt; width: 100%; background-color: #888; border-style: solid; border-color: #444 #bbb #eee #666; border-width: 1px; }
table.Performance td.right { text-align: right; font-weight: bold; padding: 0px; }

"""
}

# --------------------------------------------------------------
#    ____                           _   _                
#   / ___|  ___ _ ____   _____ _ __| |_(_)_ __ ___   ___ 
#   \___ \ / _ \ '__\ \ / / _ \ '__| __| | '_ ` _ \ / _ \
#    ___) |  __/ |   \ V /  __/ |  | |_| | | | | | |  __/
#   |____/ \___|_|    \_/ \___|_|   \__|_|_| |_| |_|\___|
#                                                        
# --------------------------------------------------------------
def render_current_time():
    import time
    html.write("<div class=time>%s</div>" % time.strftime("%H:%M"))

sidebar_snapins["time"] = {
    "title" : "Server time",
    "refresh" : 30,
    "render" : render_current_time,
    "allowed" : [ "user", "admin", "guest", ],
    "styles" : """
div.time {
   text-align: center;
   font-size: 18pt;
   font-weight: bold;
   border: 2px dotted #8cc;
   -moz-border-radius: 10px;
   background-color: #588;
   color: #aff;
}
"""
}


# --------------------------------------------------------------
#    _   _             _           
#   | \ | | __ _  __ _(_) ___  ___ 
#   |  \| |/ _` |/ _` | |/ _ \/ __|
#   | |\  | (_| | (_| | | (_) \__ \
#   |_| \_|\__,_|\__, |_|\___/|___/
#                |___/             
# --------------------------------------------------------------
def render_nagios():
    bulletlink("Home", "http://www.nagios.org")
    bulletlink("Documentation", "%s/docs/toc.html" % defaults.nagios_url)
    for entry in [
	"General",
        ("tac.cgi", "Tactical Overview"),
        ("statusmap.cgi?host=all", "Map"),
	"Current Status",
        ("status.cgi?hostgroup=all&amp;style=hostdetail", "Hosts"),
        ("status.cgi?host=all", "Services"),
        ("status.cgi?hostgroup=all&amp;style=overview", "Host Groups"),
        ("status.cgi?hostgroup=all&amp;style=summary", "*Summary"),
        ("status.cgi?hostgroup=all&amp;style=grid", "*Grid"),
        ("status.cgi?servicegroup=all&amp;style=overview", "Service Groups"),
        ("status.cgi?servicegroup=all&amp;style=summary", "*Summary"),
        ("status.cgi?servicegroup=all&amp;style=grid", "*Grid"),
        ("status.cgi?host=all&amp;servicestatustypes=28", "Problems"),
        ("status.cgi?host=all&amp;type=detail&amp;hoststatustypes=3&amp;serviceprops=42&amp;servicestatustypes=28", "*Service (Unhandled)"),
        ("status.cgi?hostgroup=all&amp;style=hostdetail&amp;hoststatustypes=12&amp;hostprops=42", "*Hosts (Unhandled)"),
        ("outages.cgi", "Network Outages"),
	"Reports",
        ("avail.cgi", "Availability"),
        ("trends.cgi", "Trends"),
        ("history.cgi?host=all", "Alerts"),
        ("history.cgi?host=all", "*History"),
        ("summary.cgi", "*Summary"),
        ("histogram.cgi", "*Histogram"),
        ("notifications.cgi?contact=all", "Notifications"),
        ("showlog.cgi", "Event Log"),
	"System",
        ("extinfo.cgi?type=3", "Comments"),
        ("extinfo.cgi?type=6", "Downtime"),
        ("extinfo.cgi?type=0", "Process Info"),
        ("extinfo.cgi?type=4", "Performance Info"),
        ("extinfo.cgi?type=7", "Scheduling Queue"),
        ("config.cgi", "Configuration"),
	]:
	if type(entry) == str:
	    heading(entry)
	else:
	    ref, text = entry
	    if text[0] == "*":
		html.write("<ul class=link>")
		nagioscgilink(text[1:], ref)
		html.write("</ul>")
	    else:
		nagioscgilink(text, ref)

sidebar_snapins["nagios_legacy"] = {
    "title" : "Nagios",
    "render" : render_nagios,
    "allowed" : [ "user", "admin", "guest", ],
}

# ----------------------------------------------------------------
#   __  __           _                           _             _ 
#  |  \/  | __ _ ___| |_ ___ _ __ ___ ___  _ __ | |_ _ __ ___ | |
#  | |\/| |/ _` / __| __/ _ \ '__/ __/ _ \| '_ \| __| '__/ _ \| |
#  | |  | | (_| \__ \ ||  __/ | | (_| (_) | | | | |_| | | (_) | |
#  |_|  |_|\__,_|___/\__\___|_|  \___\___/|_| |_|\__|_|  \___/|_|
#                                                                
# ----------------------------------------------------------------
def render_master_control():
    items = [
	( "enable_notifications",     "Notifications", ),
	( "execute_service_checks",   "Service checks" ),
	( "execute_host_checks",      "Host checks" ),
	( "enable_event_handlers",    "Event handlers" ),
	( "process_performance_data", "Perf. data"),
	]

    html.live.set_prepend_site(True)
    data = html.live.query("GET status\nColumns: %s" % " ".join([ i[0] for i in items ]))
    html.live.set_prepend_site(False)
    html.write("<table class=master_control>\n")
    for siteline in data:
	siteid = siteline[0]
	if siteid:
	    sitealias = html.site_status[siteid]["site"]["alias"]
	    html.write("<tr><td class=left colspan=2>")
	    heading(sitealias)
	    html.write("</tr>\n")
	for i, (colname, title) in enumerate(items):
	    colvalue = siteline[i + 1]
	    url = defaults.checkmk_web_uri + ("/switch_master_state.py?site=%s&switch=%s&state=%d" % (siteid, colname, 1 - colvalue))
	    onclick = "get_url('%s', updateContents, 'snapin_master_control')" % url
	    enabled = colvalue and "enabled" or "disabled"
	    html.write("<tr><td class=left>%s</td><td class=%s><a onclick=\"%s\" href=\"#\">%s</a></td></tr>\n" % (title, enabled, onclick, enabled))
    html.write("</table>")
	    
sidebar_snapins["master_control"] = {
    "title" : "Master control",
    "render" : render_master_control,
    "allowed" : [ "admin", ],
    "styles" : """
div#check_mk_sidebar table.master_control {
    width: 100%;
}

div#check_mk_sidebar table.master_control td {
    padding: 0px 0px;
    text-align: right;
}

div#check_mk_sidebar table.master_control td a {
    font-weight: bold;
    -moz-border-radius: 4px;
    margin: 0px;
    padding: 0px 3px;
    text-align: center;
    font-size: 7pt;
    margin-right: 3px;
    display: block;
    border: 1px solid black;
}
div#check_mk_sidebar table.master_control td.left a {
    text-align: left;
    font-size: 8pt;
    font-weight: normal;
}

div#check_mk_sidebar table.master_control td.left {
    text-align: left;
}

div#check_mk_sidebar table.master_control td.enabled a {
    background-color: #4f6;
    color: #000;
    border-color: #080;
}
div#check_mk_sidebar table.master_control td.disabled a {
    background-color: #f33;
    border-color: #c00;
    color: #fff;
}
"""
}

def ajax_switch_masterstate(h):
    global html
    html = h
    site = html.var("site")
    column = html.var("switch")
    state = int(html.var("state"))
    commands = {
	( "enable_notifications",     1) : "ENABLE_NOTIFICATIONS",
	( "enable_notifications",     0) : "DISABLE_NOTIFICATIONS",
	( "execute_service_checks",   1) : "START_EXECUTING_SVC_CHECKS",
	( "execute_service_checks",   0) : "STOP_EXECUTING_SVC_CHECKS",
	( "execute_host_checks",      1) : "START_EXECUTING_HOST_CHECKS",
	( "execute_host_checks",      0) : "STOP_EXECUTING_HOST_CHECKS",
	( "process_performance_data", 1) : "ENABLE_PERFORMANCE_DATA",
	( "process_performance_data", 0) : "DISABLE_PERFORMANCE_DATA",
	( "enable_event_handlers",    1) : "ENABLE_EVENT_HANDLERS",
	( "enable_event_handlers",    0) : "DISABLE_EVENT_HANDLERS",
    }

    command = commands.get((column, state))
    if command:
	html.live.command("[%d] %s" % (int(time.time()), command), site)
	html.live.set_only_sites([site])
        html.live.query("GET status\nWaitTrigger: program\nWaitTimeout: 10000\nWaitCondition: %s = %d\nColumns: %s\n" % \
               (column, state, column))
	html.live.set_only_sites(None)
        render_master_control()
    else:
	html.write("Command %s/%d not found" % (column, state))

# ---------------------------------------------------------
#   ____              _                         _        
#  | __ )  ___   ___ | | ___ __ ___   __ _ _ __| | _____ 
#  |  _ \ / _ \ / _ \| |/ / '_ ` _ \ / _` | '__| |/ / __|
#  | |_) | (_) | (_) |   <| | | | | | (_| | |  |   <\__ \
#  |____/ \___/ \___/|_|\_\_| |_| |_|\__,_|_|  |_|\_\___/
#                                                        
# ---------------------------------------------------------
def load_bookmarks():
    path = config.user_confdir + "/bookmarks.mk"
    try:
	return eval(file(path).read())
    except:
	return []


def save_bookmarks(bookmarks):
    path = config.user_confdir + "/bookmarks.mk"
    file(path, "w").write(repr(bookmarks) + "\n")

def render_bookmarks():
    bookmarks = load_bookmarks()
    n = 0
    for title, href in bookmarks:
        html.write("<div id=\"bookmark_%d\">" % n)
	iconbutton("del", "del_bookmark.py?num=%d" % n, "side", "updateContents", 'snapin_bookmarks')
	iconbutton("edit", "edit_bookmark.py?num=%d" % n, "main")
	html.write(link(title, href))
        html.write("</div>")
	n += 1

    html.write("<div class=footnotelink><a href=\"#\" onclick=\"addBookmark()\">Add Bookmark</a></div>\n")

def page_edit_bookmark(h):
    global html
    html = h
    html.header("Edit Bookmark")
    n = int(html.var("num"))
    bookmarks = load_bookmarks()
    if n >= len(bookmarks):
        raise MKGeneralException("Unknown bookmark id: %d. This is probably a problem with reload or browser history. Please try again." % n)

    if html.var("save") and html.check_transaction():
	title = html.var("title")
	url = html.var("url")
	bookmarks[n] = (title, url)
	save_bookmarks(bookmarks)
	html.reload_sidebar()

    html.begin_form("edit_bookmark")
    if html.var("save"):
        title = html.var("title")
        url = html.var("url")
        bookmarks[n] = (title, url)
        save_bookmarks(bookmarks)
        html.reload_sidebar()
    else:
        title, url = bookmarks[n]
        html.set_var("title", title)
        html.set_var("url", url)
    
    html.write("<table class=edit_bookmarks>")
    html.write("<tr><td>Title:</td><td>")
    html.text_input("title", size = 50)
    html.write("</td></tr><tr><td>URL:</td><td>")
    html.text_input("url", size = 50)
    html.write("</td></tr><tr><td></td><td>")
    html.button("save", "Save")
    html.write("</td></tr></table>\n")
    html.hidden_field("num", str(n))
    html.end_form()
    
    html.footer()

def ajax_del_bookmark(h):
    global html
    html = h
    num = int(html.var("num"))
    bookmarks = load_bookmarks()
    del bookmarks[num]
    save_bookmarks(bookmarks)
    render_bookmarks()

def ajax_add_bookmark(h):
    global html
    html = h
    title = html.var("title")
    href = html.var("href")
    if title and href:
	bookmarks = load_bookmarks()
	bookmarks.append((title, href))
	save_bookmarks(bookmarks)
    render_bookmarks()

sidebar_snapins["bookmarks"] = {
    "title" : "Bookmarks",
    "render" : render_bookmarks,
    "allowed": [ "user", "admin", "guest" ],
}
