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
from lib import *

# Python 2.3 does not have 'set' in normal namespace.
# But it can be imported from 'sets'
try:
    set()
except NameError:
    from sets import Set as set

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
    "description" : "Version information and Links to Documentation, Homepage and Download of Check_MK",
    "author" : "Mathias Kettner",
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
    "description" : "Links to administrations functions, e.g. configuration of permissions",
    "author" : "Mathias Kettner",
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
visible_views = [ "allhosts", "searchsvc" ]

def render_views():
    def render_topic(topic, s):
        first = True
        for t, title, name in s:
            if config.visible_views and name not in config.visible_views:
                continue
            if config.hidden_views and name in config.hidden_views:
                continue
            if t == topic:
                if first:
                    html.write("<h3>%s</h3>\n" % topic)
                    first = False
                bulletlink(title, "view.py?view_name=%s" % name)

    s = [ (view.get("topic", "Other"), view["title"], name) for name, view in html.available_views.items() if not view["hidden"] ]
    s.sort()

    # Enforce a certain order on the topics
    known_topics = [ "Hosts", "Hostgroups", "Services", "Servicegroups", "Problems", "Addons" ]
    for topic in known_topics:
        render_topic(topic, s)

    rest = list(set([ t for (t, _t, _v) in s if t not in known_topics ]))
    rest.sort()
    for topic in rest:
        render_topic(topic, s)


    links = []
    if config.may("edit_views"):
        if config.debug:
            links.append(("EXPORT", "export_views.py"))
        links.append(("EDIT", "edit_views.py"))
        footnotelinks(links)

sidebar_snapins["views"] = {
    "title" : "Views",
    "description" : "Links to all views",
    "author" : "Mathias Kettner",
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
    "description" : "Directs links to all host groups",
    "author" : "Mathias Kettner",
    "render" : lambda: render_groups("host"),
    "allowed" : [ "user", "admin", "guest" ]
}
sidebar_snapins["servicegroups"] = {
    "title" : "Servicegroups",
    "description" : "Direct links to all service groups",
    "author" : "Mathias Kettner",
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
def render_hosts(mode):
    html.live.set_prepend_site(True)
    query = "GET hosts\nColumns: name state worst_service_state\n"
    view = "host"

    if mode == "summary":
        query += "Filter: custom_variable_names >= _REALNAME\n"
    else:
        query += "Filter: custom_variable_names < _REALNAME\n"

    if mode == "problems":
        query += "Filter: state > 0\nFilter: worst_service_state > 0\nOr: 2\n"
        view = "problemsofhost"

    hosts = html.live.query(query)
    html.live.set_prepend_site(False)
    hosts.sort()

    longestname = 0
    for site, host, state, worstsvc in hosts:
        longestname = max(longestname, len(host))
    if longestname > 15:
        num_columns = 1
    else:
        num_columns = 2

    views.html = html
    views.load_views()
    target = views.get_context_link(html.req.user, view)
    html.write("<table class=allhosts>\n")
    col = 1
    for site, host, state, worstsvc in hosts:
        if col == 1:
            html.write("<tr>")
        html.write("<td>")

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
        html.write("</td>")
        if col == num_columns:
            html.write("</tr>\n")
            col = 1
        else:
            col += 1

    if col < num_columns:
        html.write("</tr>\n")
    html.write("</table>\n")

snapin_allhosts_styles = """
  .snapin table.allhosts { width: 100%; }
  .snapin table.allhosts td { width: 50%; padding: 0px 0px; }
"""

sidebar_snapins["hosts"] = {
    "title" : "All hosts",
    "description" : "A summary state of each host with a link to the view showing its services",
    "author" : "Mathias Kettner",
    "render" : lambda: render_hosts("hosts"),
    "allowed" : [ "user", "admin", "guest" ],
    "refresh" : 60,
    "styles" : snapin_allhosts_styles,
}

sidebar_snapins["summary_hosts"] = {
    "title" : "Summary hosts",
    "description" : "A summary state of all summary hosts (summary hosts hold aggregated service states and are a feature of Check_MK)",
    "author" : "Mathias Kettner",
    "render" : lambda: render_hosts("summary"),
    "allowed" : [ "user", "admin", "guest" ],
    "refresh" : 60,
    "styles" : snapin_allhosts_styles,
}

sidebar_snapins["problem_hosts"] = {
    "title" : "Problem hosts",
    "description" : "A summary state of all hosts that have problem, with links to problems of those hosts",
    "author" : "Mathias Kettner",
    "render" : lambda: render_hosts("problems"),
    "allowed" : [ "user", "admin", "guest" ],
    "refresh" : 60,
    "styles" : snapin_allhosts_styles,
}

# --------------------------------------------------------------
#  _   _           _     __  __       _        _
# | | | | ___  ___| |_  |  \/  | __ _| |_ _ __(_)_  __
# | |_| |/ _ \/ __| __| | |\/| |/ _` | __| '__| \ \/ /
# |  _  | (_) \__ \ |_  | |  | | (_| | |_| |  | |>  <
# |_| |_|\___/|___/\__| |_|  |_|\__,_|\__|_|  |_/_/\_\
#
# --------------------------------------------------------------
def render_hostmatrix():
    html.live.set_prepend_site(True)
    query = "GET hosts\nColumns: name state has_been_checked worst_service_state scheduled_downtime_depth\nFilter: custom_variable_names < _REALNAME\n"
    hosts = html.live.query(query)
    html.live.set_prepend_site(False)
    hosts.sort()

    # Choose smallest square number large enough
    # to show all hosts
    num_hosts = len(hosts)
    n = 1
    while n*n < num_hosts:
        n += 1

    rows = num_hosts / n
    lastcols = num_hosts % n
    if lastcols > 0:
        rows += 1

    style = 'height: %d; ' % (snapin_width)
    if rows > 10:
        style += "border-collapse: collapse;"
    html.write('<table class=hostmatrix style="%s"\n' % style)
    col = 1
    row = 1
    for site, host, state, has_been_checked, worstsvc, downtimedepth in hosts:
        if col == 1:
            html.write("<tr>")
        if downtimedepth > 0:
            s = "d"
        elif not has_been_checked:
            s = "p"
        elif worstsvc == 2 or state == 1:
            s = 2
        elif worstsvc == 3 or state == 2:
            s = 3
        elif worstsvc == 1:
            s = 1
        else:
            s = 0
        url = "view.py?view_name=host&site=%s&host=%s" % (htmllib.urlencode(site), htmllib.urlencode(host))
        html.write('<td class="state state%s"><a href="%s" title="%s" target="main"></a></td>' % (s, url, host))
        if col == n or (row == rows and n == lastcols):
            html.write("<tr>\n")
            col = 1
            row += 1
        else:
            col += 1
    html.write("</table>")


sidebar_snapins["hostmatrix"] = {
    "title"       : "Host Matrix",
    "description" : "A matrix showing s colored square for each host",
    "author"      : "Mathias Kettner",
    "render"      : render_hostmatrix,
    "allowed"     : [ "user", "admin", "guest" ],
    "refresh"     : 10,
    "styles"      : """
table.hostmatrix { width: %d; cell-spacing: 1px; }
table.hostmatrix a { display: block; width: 100%%; height: 100%%; }
table.hostmatrix td { border: 1px solid white; }
""" % snapin_width

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
        sitenames = config.allsites().keys()
        sitenames.sort()
        for sitename in sitenames:
            site = config.site(sitename)
            state = html.site_status[sitename]["state"]
            if state == "disabled":
                switch = "on"
                text = site["alias"]
                title = "Site %s is switched off" % site["alias"]
            else:
                switch = "off"
		try:
		    linkview = config.sitestatus_link_view
		except:
		    linkview = "sitehosts"
                text = link(site["alias"], "view.py?view_name=%s&site=%s" % (linkview, sitename))
                ex = html.site_status[sitename].get("exception")
                shs = html.site_status[sitename].get("status_host_state")

                if ex:
                    title = ex
                else:
                    title = "Site %s is online" % site["alias"]

            html.write("<tr><td class=left>%s</td>" % text)
            onclick = "switch_site('_site_switch=%s:%s')" % (sitename, switch)
            html.write("<td class=\"state %s\">" % state)
            html.write('<a title="%s" href="#" onclick="%s">%s</a></td>' % (title, onclick, state))
            html.write("</tr>\n")
        html.write("</table>\n")


sidebar_snapins["sitestatus"] = {
  "title" : "Site status",
  "description" : "Connection state of each site and button for enabling and disabling the site connection",
  "author" : "Mathias Kettner",
  "render" : render_sitestatus,
  "allowed" : [ "user", "admin" ],
  "refresh" : 90,
  "styles" : """
.snapin table.sitestate {
    width: %dpx;
}

.snapin table.sitestate td {
    padding: 1px 0px;
    text-align: right;
}

.snapin table.sitestate td a {
    font-weight: bold;
    -moz-border-radius: 4px;
    margin: 0px;
    padding: 0px 0px;
    text-align: center;
    display: block;
}
.snapin table.sitestate td.left a {
    text-align: left;
    font-weight: normal;
}

.snapin table.sitestate td.state {
    width: 60px;
    font-size: 7pt;
}
.snapin table.sitestate td.left {
    text-align: left;
}

.snapin table.sitestate td.state a {
    border-width: 1px;
    border-style: solid;
}
.snapin table.sitestate td.online a   { background-color: #3c0; color: #fff; border-color: #0f0; }
.snapin table.sitestate td.disabled a { background-color: #666; color: #ccc; border-color: #888; }
.snapin table.sitestate td.dead a     { background-color: #c00; color: #f88; border-color: #f44; }
.snapin table.sitestate td.waiting a  { background-color: #666; color: #fff; border-color: #ccc; }
.snapin table.sitestate td.down a     { background-color: #f00; color: #fff; border-color: #800; }
.snapin table.sitestate td.unreach a  { background-color: #f80; color: #fff; border-color: #840; }
.snapin table.sitestate td.unknown a  { background-color: #26c; color: #fff; border-color: #44f; }
""" % snapin_width
}


# --------------------------------------------------------------
#    _____          _   _           _                             _
#   |_   _|_ _  ___| |_(_) ___ __ _| |   _____   _____ _ ____   _(_) _____      __
#     | |/ _` |/ __| __| |/ __/ _` | |  / _ \ \ / / _ \ '__\ \ / / |/ _ \ \ /\ / /
#     | | (_| | (__| |_| | (_| (_| | | | (_) \ V /  __/ |   \ V /| |  __/\ V  V /
#     |_|\__,_|\___|\__|_|\___\__,_|_|  \___/ \_/ \___|_|    \_/ |_|\___| \_/\_/
#
# --------------------------------------------------------------
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
        "StatsAnd: 3\n" \
        "Filter: custom_variable_names < _REALNAME\n"

    service_query = \
        "GET services\n" \
        "Stats: state >= 0\n" \
        "Stats: state > 0\n" \
        "Stats: scheduled_downtime_depth = 0\n" \
        "Stats: host_scheduled_downtime_depth = 0\n" \
        "Stats: host_state = 0\n" \
        "StatsAnd: 4\n" \
        "Stats: state > 0\n" \
        "Stats: scheduled_downtime_depth = 0\n" \
        "Stats: host_scheduled_downtime_depth = 0\n" \
        "Stats: acknowledged = 0\n" \
        "Stats: host_state = 0\n" \
        "StatsAnd: 5\n" \
        "Filter: host_custom_variable_names < _REALNAME\n"

    # ACHTUNG: Stats-Filter so anpassen, dass jeder Host gezaehlt wird.

    try:
        hstdata = html.live.query_summed_stats(host_query)
        svcdata = html.live.query_summed_stats(service_query)
    except livestatus.MKLivestatusNotFoundError:
        html.write("<center>No data from any site</center>")
        return
    html.write("<table class=tacticaloverview cellspacing=2 cellpadding=0 border=0>\n")
    for title, data, view, what in [
            ("Hosts",    hstdata, 'hostproblems', 'host'),
            ("Services", svcdata, 'svcproblems',  'service'),
            ]:
        html.write("<tr><th>%s</th><th>Problems</th><th>Unhandled</th></tr>\n" % title)
        html.write("<tr>")

        html.write('<td class=total><a target="main" href="view.py?view_name=all%ss">%d</a></td>' % (what, data[0]))
        unhandled = False
        for value in data[1:]:
            if value > 0:
                href = "view.py?view_name=" + view
                if unhandled:

                    href += "&is_%s_acknowledged=0" % what
                text = link(str(value), href)
            else:
                text = str(value)
            html.write('<td class="%s">%s</td>' % (value == 0 and " " or "states prob", text))
            unhandled = True
        html.write("</tr>\n")
    html.write("</table>\n")

sidebar_snapins["tactical_overview"] = {
    "title" : "Tactical Overview",
    "description" : "The total number of hosts and service with and without problems",
    "author" : "Mathias Kettner",
    "refresh" : 10,
    "render" : render_tactical_overview,
    "allowed" : [ "user", "admin", "guest" ],
    "styles" : """
table.tacticaloverview {
   border-collapse: separate;
   /*border-spacing: 5px 2px;*/
   width: %dpx;
}
table.tacticaloverview th { font-size: 7pt; text-align: left; font-weight: normal; padding: 0px; padding-top: 2px; }
table.tacticaloverview td { text-align: right; border: 1px solid #444; padding: 0px; }
table.tacticaloverview td a { display: block; margin-right: 2px; }
""" % (snapin_width + 5)
}
# table.tacticaloverview td.prob { font-weight: bold; }

# --------------------------------------------------------------
#    ____            __
#   |  _ \ ___ _ __ / _| ___  _ __ _ __ ___   __ _ _ __   ___ ___
#   | |_) / _ \ '__| |_ / _ \| '__| '_ ` _ \ / _` | '_ \ / __/ _ \
#   |  __/  __/ |  |  _| (_) | |  | | | | | | (_| | | | | (_|  __/
#   |_|   \___|_|  |_|  \___/|_|  |_| |_| |_|\__,_|_| |_|\___\___|
#
# --------------------------------------------------------------
def render_performance():
    data = html.live.query("GET status\nColumns: service_checks_rate host_checks_rate external_commands_rate connections_rate forks_rate log_messages_rate cached_log_messages\n")
    html.write("<table class=performance>\n")
    for what, col, format in \
        [("Service checks", 0, "%.2f/s"),
        ("Host checks", 1, "%.2f/s"),
        ("External commands", 2, "%.2f/s"),
        ("Livestatus-connections", 3, "%.2f/s"),
        ("Process creations", 4, "%.2f/s"),
        ("New log messages", 5, "%.2f/s"),
        ("Cached log messages", 6, "%d")]:
       html.write(("<tr><td class=left>%s:</td><td class=right>" + format + "</td></tr>\n") % (what, sum([row[col] for row in data])))
    data = html.live.query("GET status\nColumns: external_command_buffer_slots external_command_buffer_max\n")
    size = sum([row[0] for row in data])
    maxx = sum([row[1] for row in data])
    html.write("<tr><td class=left>Com. buf. max/total</td>"
               "<td class=right>%d / %d</td></tr>" % (maxx, size))
    html.write("</table>\n")

sidebar_snapins["performance"] = {
    "title" : "Server performance",
    "description" : "Live monitor of the overall performance of all monitoring servers",
    "author" : "Mathias Kettner",
    "refresh" : 10,
    "render" : render_performance,
    "allowed" : [ "admin", ],
    "styles" : """
table.performance {
    -moz-border-radius: 5px;
    font-size: 8pt;
    width: %d;
    border-style: solid;
    background-color: #589;
    border-color: #444 #bbb #eee #666;
    border-width: 1px;
    padding: 2px;
}
table.performance td { padding: 0px; }
table.Performance td.right { text-align: right; font-weight: bold; padding: 0px; }

""" % snapin_width
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
    "description" : "A large clock showing the current time of the web server",
    "author" : "Mathias Kettner",
    "refresh" : 30,
    "render" : render_current_time,
    "allowed" : [ "user", "admin", "guest", ],
    "styles" : """
div.time {
   text-align: center;
   font-size: 18pt;
   font-weight: bold;
   border: 1px solid #8cc;
   -moz-border-radius: 10px;
   background-color: #588;
   color: #aff;
   width: %d
}
"""  % (snapin_width - 2)
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
    bulletlink("Documentation", "%snagios/docs/toc.html" % defaults.url_prefix)
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
    "description" : "The classical sidebar of Nagios 3.2.0 with links to your local Nagios instance (no multi site support)",
    "author" : "Mathias Kettner",
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
        ( "process_performance_data", "Performance data"),
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
            url = defaults.url_prefix + ("check_mk/switch_master_state.py?site=%s&switch=%s&state=%d" % (siteid, colname, 1 - colvalue))
            onclick = "get_url('%s', updateContents, 'snapin_master_control')" % url
            enabled = colvalue and "enabled" or "disabled"
            html.write("<tr><td class=left>%s</td><td class=%s><a onclick=\"%s\" href=\"#\">%s</a></td></tr>\n" % (title, enabled, onclick, enabled))
    html.write("</table>")

sidebar_snapins["master_control"] = {
    "title" : "Master control",
    "description" : "Buttons for switching globally states such as enabling checks and notifications",
    "author" : "Mathias Kettner",
    "render" : render_master_control,
    "allowed" : [ "admin", ],
    "styles" : """
div#check_mk_sidebar table.master_control {
    width: %d;
    margin: 0px;
    border-spacing: 0px;
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
    margin-right: 0px;
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
""" % snapin_width
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
        html.live.set_only_sites()
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
    config.save_user_file("bookmarks", bookmarks)

def render_bookmarks():
    bookmarks = load_bookmarks()
    n = 0
    for title, href in bookmarks:
        html.write("<div id=\"bookmark_%d\">" % n)
        iconbutton("delete", "del_bookmark.py?num=%d" % n, "side", "updateContents", 'snapin_bookmarks')
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
    "description" : "A simple and yet practical snapin allowing to create bookmarks to views and other content in the main frame",
    "author" : "Mathias Kettner",
    "render" : render_bookmarks,
    "allowed": [ "user", "admin", "guest" ],
}



# ------------------------------------------------------------
#   ____          _                    _     _       _
#  / ___|   _ ___| |_ ___  _ __ ___   | |   (_)_ __ | | _____
# | |  | | | / __| __/ _ \| '_ ` _ \  | |   | | '_ \| |/ / __|
# | |__| |_| \__ \ || (_) | | | | | | | |___| | | | |   <\__ \
#  \____\__,_|___/\__\___/|_| |_| |_| |_____|_|_| |_|_|\_\___/
#
# ------------------------------------------------------------

def load_customlink_states():
    return config.load_user_file("customlinks", {})

def save_customlink_states(states):
    config.save_user_file("customlinks", states)

def ajax_customlink_openclose(h):
    global html
    html = h

    states = load_customlink_states()
    states[html.var("name")] = html.var("state")
    save_customlink_states(states)

def render_custom_links():
    links = config.custom_links.get(config.role)
    if not links:
        html.write("Please edit <tt>%s</tt> in order to configure which links are shown in this snapin.\n" %
                  (defaults.default_config_dir + "/multisite.mk"))

    def render_list(ids, links):
        states = load_customlink_states()
        n = 0
        for entry in links:
            n += 1
            try:
                if type(entry[1]) == type(True):
                    idss = ids + [str(n)]
                    if states.get(''.join(idss), entry[1] and 'on' or 'off') == 'on': # open
                        display = ""
                        img = "link_folder_open.gif"
                    else:
                        display = "none"
                        img = "link_folder.gif"
                    html.write('<h3 onclick="toggle_folder(this, \'%s\');" ' % ''.join(idss))
                    html.write('onmouseover="this.style.cursor=\'pointer\';" ')
                    html.write('onmouseout="this.style.cursor=\'auto\';">')
                    html.write('<img src="images/%s">' % img)
                    html.write("%s</h3>\n" % entry[0])
                    html.write('<div style="display: %s;" class=sublist>' % display)
                    render_list(idss, entry[2])
                    html.write('</div>\n')
                elif type(entry[1]) == str:
                    if len(entry) > 2:
                        html.write('<img src="images/%s">' % entry[2])
                    else:
                        html.write('<img src="images/link_link.gif">')
                    simplelink(entry[0], entry[1])
                else:
                    html.write("Second part of tuple must be list or string, not %s\n" % str(entry[1]))
            except Exception, e:
                html.write("invalid entry %s: %s<br>\n" % (entry, e))

    render_list([], links)

sidebar_snapins["custom_links"] = {
    "title" : "Custom Links",
    "description" : "This snapin contains custom links which can be configured via the configuration variable <tt>custom_links</tt> in <tt>multisite.mk</tt>",
    "author" : "Mathias Kettner",
    "render" : render_custom_links,
    "allowed" : [ "user", "admin", "guest" ],
    "styles" : """
div#snapin_custom_links {
}
div#snapin_custom_links div.sublist {
    padding-left: 10px;
}
div#snapin_custom_links h3 {
}
div#snapin_custom_links img {
    position: relative;
    top: 3px;
    margin-right: 5px;
}
"""
}
