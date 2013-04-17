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

import views, time, defaults, dashboard
import weblib
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
    html.write(_("Version: ") + defaults.check_mk_version)
    html.write("<ul>")
    bulletlink(_("Homepage"),        "http://mathias-kettner.de/check_mk.html")
    bulletlink(_("Documentation"),   "http://mathias-kettner.de/checkmk.html")
    bulletlink(_("Download"),        "http://mathias-kettner.de/check_mk_download.html")
    bulletlink("Mathias Kettner", "http://mathias-kettner.de")
    html.write("</ul>")

sidebar_snapins["about"] = {
    "title" : _("About Check_MK"),
    "description" : _("Version information and Links to Documentation, Homepage and Download of Check_MK"),
    "render" : render_about,
    "allowed" : [ "admin", "user", "guest" ],
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

def views_by_topic():
    s = [ (view.get("topic", _("Other")), view["title"], name)
          for name, view
          in html.available_views.items()
          if not view["hidden"] and not view.get("mobile")]

    # Add all the dashboards to the views list
    s += [ (_('Dashboards'), d['title'] and d['title'] or d_name, d_name)
           for d_name, d
           in dashboard.dashboards.items()
    ]

    s.sort()

    # Enforce a certain order on the topics
    known_topics = [ _('Dashboards'), _("Hosts"), _("Hostgroups"), _("Services"), _("Servicegroups"),
                     _("Business Intelligence"), _("Problems"), _("Addons") ]

    result = []
    for topic in known_topics:
        result.append((topic, s))

    rest = list(set([ t for (t, _t, _v) in s if t not in known_topics ]))
    rest.sort()
    for topic in rest:
        if topic:
            result.append((topic, s))

    return result

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
                    html.begin_foldable_container("views", topic, False, topic, indent=True)
                    first = False
                if topic == _('Dashboards'):
                    bulletlink(title, 'dashboard.py?name=%s' % name)
                else:
                    bulletlink(title, "view.py?view_name=%s" % name)
        if not first: # at least one item rendered
            html.end_foldable_container()

    for topic, s in views_by_topic():
        render_topic(topic, s)

    links = []
    if config.may("general.edit_views"):
        if config.debug:
            links.append((_("EXPORT"), "export_views.py"))
        links.append((_("EDIT"), "edit_views.py"))
        footnotelinks(links)

sidebar_snapins["views"] = {
    "title" : _("Views"),
    "description" : _("Links to all views"),
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
    groups = [(name_to_alias[name].lower(), name_to_alias[name], name) for name in name_to_alias.keys()]
    groups.sort() # sort by Alias in lowercase
    html.write('<ul>')
    for alias_lower, alias, name in groups:
        url = "view.py?view_name=%sgroup&%sgroup=%s" % (what, what, htmllib.urlencode(name))
        bulletlink(alias or name, url)
    html.write('</ul>')

sidebar_snapins["hostgroups"] = {
    "title" : _("Hostgroups"),
    "description" : _("Directs links to all host groups"),
    "render" : lambda: render_groups("host"),
    "restart":     True,
    "allowed" : [ "user", "admin", "guest" ]
}
sidebar_snapins["servicegroups"] = {
    "title" : _("Servicegroups"),
    "description" : _("Direct links to all service groups"),
    "render" : lambda: render_groups("service"),
    "restart":     True,
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
    query = "GET hosts\nColumns: name state worst_service_state\nLimit: 100"
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

    views.load_views()
    target = views.get_context_link(config.user_id, view)
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
    "title" : _("All hosts"),
    "description" : _("A summary state of each host with a link to the view showing its services"),
    "render" : lambda: render_hosts("hosts"),
    "allowed" : [ "user", "admin", "guest" ],
    "refresh" : True,
    "styles" : snapin_allhosts_styles,
}

sidebar_snapins["summary_hosts"] = {
    "title" : _("Summary hosts"),
    "description" : _("A summary state of all summary hosts (summary hosts hold aggregated service states and are a feature of Check_MK)"),
    "render" : lambda: render_hosts("summary"),
    "allowed" : [ "user", "admin", "guest" ],
    "refresh" : True,
    "styles" : snapin_allhosts_styles,
}

sidebar_snapins["problem_hosts"] = {
    "title" : _("Problem hosts"),
    "description" : _("A summary state of all hosts that have problem, with links to problems of those hosts"),
    "render" : lambda: render_hosts("problems"),
    "allowed" : [ "user", "admin", "guest" ],
    "refresh" : True,
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
    query = "GET hosts\n" \
            "Columns: name state has_been_checked worst_service_state scheduled_downtime_depth\n" \
            "Filter: custom_variable_names < _REALNAME\n" \
            "Limit: 901\n"
    hosts = html.live.query(query)
    html.live.set_prepend_site(False)
    hosts.sort()
    if len(hosts) > 900:
        html.write(_("Sorry, I will not display more than 900 hosts."))
        return

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

    # Calculate cell size (Automatic sizing with 100% does not work here)
    # - Get cell spacing: 1px between each cell
    # - Substract the cell spacing for each column from the total width
    # - Then divide the total width through the number of columns
    # - Then get the full-digit width of the cell and summarize the rest
    #   to be substracted from the cell width
    # This is not a 100% solution but way better than having no links
    cell_spacing = 1
    cell_size = ((snapin_width - cell_spacing * (n+1)) / n)
    cell_size, cell_size_rest = divmod(cell_size, 1)
    style = 'width:%spx' % (snapin_width - n * cell_size_rest)

    html.write('<table class="content_center hostmatrix" cellspacing="0" style="border-collapse:collapse;%s">\n' % style)
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
        html.write('<td class="state state%s"><a href="%s" title="%s" target="main" style="width:%spx;height:%spx;"></a></td>' %
                                                                                           (s, url, host, cell_size, cell_size))
        if col == n or (row == rows and n == lastcols):
            html.write("<tr>\n")
            col = 1
            row += 1
        else:
            col += 1
    html.write("</table>")


sidebar_snapins["hostmatrix"] = {
    "title"       : _("Host Matrix"),
    "description" : _("A matrix showing a colored square for each host"),
    "render"      : render_hostmatrix,
    "allowed"     : [ "user", "admin", "guest" ],
    "refresh"     : True,
    "styles"      : """
table.hostmatrix { border-spacing: 0;  }
table.hostmatrix tr { padding: 0; border-spacing: 0; }
table.hostmatrix a { display: block; width: 100%; height: 100%; line-height: 100%; }
table.hostmatrix td { border: 1px solid #123a4a; padding: 0; border-spacing: 0; }
    """

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

        # Sort the list of sitenames by sitealias
        sitenames = []
        for sitename, site in config.allsites().iteritems():
            sitenames.append((sitename, site['alias']))
        sitenames = sorted(sitenames, key=lambda k: k[1], cmp = lambda a,b: cmp(a.lower(), b.lower()))

        for sitename, sitealias in sitenames:
            site = config.site(sitename)
            if sitename not in html.site_status or "state" not in html.site_status[sitename]:
                state = "missing"
                text = _("Missing site")
                title = _("Site %s does not exist") % sitename
            else:
                state = html.site_status[sitename]["state"]
                if state == "disabled":
                    switch = "on"
                    text = site["alias"]
                    title = _("Site %s is switched off") % site["alias"]
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
            html.write("<td class=state>")
            html.icon_button("#", _("%s this site") % (state == "disabled" and "enable" or "disable"),
                             "sitestatus_%s" % state, onclick=onclick)
            html.write("</tr>\n")
        html.write("</table>\n")


sidebar_snapins["sitestatus"] = {
  "title" : _("Site status"),
  "description" : _("Connection state of each site and button for enabling and disabling the site connection"),
  "render" : render_sitestatus,
  "allowed" : [ "user", "admin" ],
  "refresh" : True,
  "styles" : """
table.sitestate {
    width: %dpx;
}

table.sitestate td {
    padding: 1px 0px;
    text-align: right;
}

table.sitestate td.left {
    text-align: left;
}

div.snapin table.sitestate td img.iconbutton {
    width: 60px;
    height: 16px;
}

table.sitestate td.left a {
    text-align: left;
    font-weight: normal;
}

table.sitestate td.state {
    width: 60px;
    font-size: 7pt;
}

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
    html.write("<table class=\"content_center tacticaloverview\" cellspacing=2 cellpadding=0 border=0>\n")
    for title, data, view, what in [
            (_("Hosts"),    hstdata, 'hostproblems', 'host'),
            (_("Services"), svcdata, 'svcproblems',  'service'),
            ]:
        html.write("<tr><th>%s</th><th>%s</th><th>%s</th></tr>\n" % (title, _('Problems'), _('Unhandled')))
        html.write("<tr>")

        html.write('<td class=total><a target="main" href="view.py?view_name=all%ss">%d</a></td>' % (what, data[0]))
        unhandled = False
        for value in data[1:]:
            href = "view.py?view_name=" + view
            if unhandled:
                href += "&is_%s_acknowledged=0" % what
            text = link(str(value), href)
            html.write('<td class="%s">%s</td>' % (value == 0 and " " or "states prob", text))
            unhandled = True
        html.write("</tr>\n")
    html.write("</table>\n")

sidebar_snapins["tactical_overview"] = {
    "title" : _("Tactical Overview"),
    "description" : _("The total number of hosts and service with and without problems"),
    "refresh" : True,
    "render" : render_tactical_overview,
    "allowed" : [ "user", "admin", "guest" ],
    "styles" : """
table.tacticaloverview {
   border-collapse: separate;
   /**
    * Don't use border-spacing. It is not supported by IE8 with compat mode and older IE versions.
    * Better set cellspacing in HTML code. This works in all browsers.
    * border-spacing: 5px 2px;
    */
   width: %dpx;
   margin-top: -7px;
}
table.tacticaloverview th {
    font-size: 8pt;
    line-height: 7pt;
    text-align: left;
    color: #123a4a;
    font-weight: normal;
    padding: 0;
    padding-top: 2px;
    vertical-align: bottom;
}
table.tacticaloverview td {
    width: 33.3%%;
    text-align: right;
    /* border: 1px solid #123a4a; */
    background-color: #6da1b8;
    padding: 0px;
    height: 14px;
    /* box-shadow: 1px 0px 1px #386068; */
}
table.tacticaloverview td.prob {
    box-shadow: 0px 0px 4px #ffd000;
}
table.tacticaloverview a { display: block; margin-right: 2px; }
""" % snapin_width
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
    def write_line(left, right):
        html.write("<tr><td class=left>%s</td>"
                   "<td class=right><strong>%s</strong></td></tr>" % (left, right))

    html.write("<table class=\"content_center performance\">\n")

    data = html.live.query("GET status\nColumns: service_checks_rate host_checks_rate "
                           "external_commands_rate connections_rate forks_rate "
                           "livechecks_rate livecheck_overflows_rate "
                           "log_messages_rate cached_log_messages\n")
    for what, col, format in \
        [("Service checks",        0, "%.2f/s"),
        ("Host checks",            1, "%.2f/s"),
        ("External commands",      2, "%.2f/s"),
        ("Livestatus-conn.",       3, "%.2f/s"),
        ("Process creations",      4, "%.2f/s"),
        ("Livechecks",             5, "%.2f/s"),
        ("Livecheck overflows",    6, "%.2f/s"),
        ("New log messages",       7, "%.2f/s"),
        ("Cached log messages",    8, "%d")]:
        write_line(what + ":", format % sum([row[col] for row in data]))

    if len(config.allsites()) == 1:
        data = html.live.query("GET status\nColumns: external_command_buffer_slots "
                               "external_command_buffer_max\n")
        size = sum([row[0] for row in data])
        maxx = sum([row[1] for row in data])
        write_line(_('Com. buf. max/total'), "%d / %d" % (maxx, size))


    html.write("</table>\n")

sidebar_snapins["performance"] = {
    "title" : _("Server performance"),
    "description" : _("Live monitor of the overall performance of all monitoring servers"),
    "refresh" : True,
    "render" : render_performance,
    "allowed" : [ "admin", ],
    "styles" : """
table.performance {
    width: %dpx;
    -moz-border-radius: 5px;
    background-color: #589;
    /* background-color: #6da1b8;*/
    border-style: solid;
    border-color: #444 #bbb #eee #666;
    /* The border needs to be substracted from the width */
    border-width: 1px;
}
table.performance td {
    padding: 0px 2px;
    font-size: 8pt;
}
table.performance td.right {
    text-align: right;
    padding: 0px;
    padding-right: 1px;
    white-space: nowrap;
}

""" % (snapin_width - 2)
}

#.
#   .----------------------------------------------------------------------.
#   |    ____                      _                      _                |
#   |   / ___| _ __   ___  ___  __| | ___  _ __ ___   ___| |_ ___ _ __     |
#   |   \___ \| '_ \ / _ \/ _ \/ _` |/ _ \| '_ ` _ \ / _ \ __/ _ \ '__|    |
#   |    ___) | |_) |  __/  __/ (_| | (_) | | | | | |  __/ ||  __/ |       |
#   |   |____/| .__/ \___|\___|\__,_|\___/|_| |_| |_|\___|\__\___|_|       |
#   |         |_|                                                          |
#   '----------------------------------------------------------------------'
def render_speedometer():
    html.write("<div class=speedometer>");
    html.write('<img id=speedometerbg src="images/speedometer.png">')
    html.write('<canvas width=228 height=136 id=speedometer></canvas>')
    html.write("</div>")

    html.javascript("""
function show_speed(percentage) {
    var canvas = document.getElementById('speedometer');
    if (!canvas)
        return;

    var context = canvas.getContext('2d');
    if (!context)
        return;

    if (percentage > 100.0)
        percentage = 100.0;

    var orig_x = 116;
    var orig_y = 181;
    var angle_0   = 232.0;
    var angle_100 = 307.0;
    var angle = angle_0 + (angle_100 - angle_0) * percentage / 100.0;
    var angle_rad = angle / 360.0 * Math.PI * 2;
    var length = 120;
    var end_x = orig_x + (Math.cos(angle_rad) * length);
    var end_y = orig_y + (Math.sin(angle_rad) * length);

    context.clearRect(0, 0, 228, 136);
    context.beginPath();
    context.moveTo(orig_x, orig_y);
    context.lineTo(end_x, end_y);
    context.closePath();
    context.shadowOffsetX = 2;
    context.shadowOffsetY = 2;
    context.shadowBlur = 2;
    context.stroStyle = "#000000";
    context.stroke();
    context = null;
}

function speedometer_show_speed(last_perc, program_start, scheduled_rate)
{
    try {
        text = get_url_sync("sidebar_ajax_speedometer.py" +
                            "?last_perc=" + last_perc +
                            "&scheduled_rate=" + scheduled_rate +
                            "&program_start=" + program_start);
        code = eval(text);
        scheduled_rate = code[0];
        program_start    = code[1];
        percentage       = code[2];
        last_perc        = code[3];
        title            = code[4];

        oDiv = document.getElementById('speedometer');

        // Terminate reschedule when the speedometer div does not exist anymore
        // (e.g. the snapin has been removed)
        if (!oDiv)
            return;

        oDiv.title = title
        oDiv = document.getElementById('speedometerbg');
        oDiv.title = title
        oDiv = null;

        move_needle(last_perc, percentage); // 50 * 100ms = 5s = refresh time
    } catch(ie) {
        // Ignore errors during re-rendering. Proceed with reschedule...
    }

    // large timeout for fetching new data via Livestatus
    setTimeout("speedometer_show_speed("
        + percentage       + ","
        + program_start    + ","
        + scheduled_rate + ");", 5000);
}

var needle_timeout = null;

function move_needle(from_perc, to_perc)
{
    new_perc = from_perc * 0.9 + to_perc * 0.1;
    show_speed(new_perc);
    if (needle_timeout != null)
        clearTimeout(needle_timeout);
    needle_timeout = setTimeout("move_needle(" + new_perc + "," +  to_perc + ");", 50);
}


speedometer_show_speed(0, 0, 0);

""")



sidebar_snapins["speedometer"] = {
    "title" : _("Speed-O-Meter"),
    "description" : _("A gadget that shows your current check rate in relation to "
                      "the scheduled check rate. If the Speed-O-Meter shows a speed "
                      "of 100 percent, then all checks are being executed in exactly "
                      "the rate that is configured (via check_interval)"),
    "render" : render_speedometer,
    "allowed" : [ "admin", ],
    "styles" : """
div.speedometer {
    position: relative;
    top: 0px;
    left: 0px;
    height: 223px;
}
img#speedometerbg {
    position: absolute;
    top: 0px;
    left: 0px;
}
canvas#speedometer {
    position: absolute;
    top: 0px;
    left: 0px;
}
"""}




#.
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
    "title" : _("Server time"),
    "description" : _("A large clock showing the current time of the web server"),
    "refresh" : True,
    "render" : render_current_time,
    "allowed" : [ "user", "admin", "guest", ],
    "styles" : """
div.time {
   text-align: center;
   font-size: 18pt;
   font-weight: bold;
   /* The border needs to be substracted from the width */
   border: 1px solid #8cc;
   -moz-border-radius: 10px;
   background-color: #588;
   color: #aff;
   width: %dpx;
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
    html.write('<ul>')
    bulletlink("Home", "http://www.nagios.org")
    bulletlink("Documentation", "%snagios/docs/toc.html" % defaults.url_prefix)
    html.write('</ul>')
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
            html.write('</ul>')
            heading(entry)
            html.write('<ul>')
        else:
            ref, text = entry
            if text[0] == "*":
                html.write("<ul class=link>")
                nagioscgilink(text[1:], ref)
                html.write("</ul>")
            else:
                nagioscgilink(text, ref)

sidebar_snapins["nagios_legacy"] = {
    "title" : _("Old Nagios GUI"),
    "description" : _("The classical sidebar of Nagios 3.2.0 with links to your local Nagios instance (no multi site support)"),
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
        ( "enable_notifications",     _("Notifications" )),
        ( "execute_service_checks",   _("Service checks" )),
        ( "execute_host_checks",      _("Host checks" )),
        ( "enable_event_handlers",    _("Event handlers" )),
        ( "process_performance_data", _("Performance data" )),
        ]

    html.live.set_prepend_site(True)
    data = html.live.query("GET status\nColumns: %s" % " ".join([ i[0] for i in items ]))
    html.live.set_prepend_site(False)
    for siteline in data:
        siteid = siteline[0]
        if siteid:
            sitealias = html.site_status[siteid]["site"]["alias"]
            html.begin_foldable_container("master_control", siteid, True, sitealias)
        html.write("<table class=master_control>\n")
        for i, (colname, title) in enumerate(items):
            colvalue = siteline[i + 1]
            url = defaults.url_prefix + ("check_mk/switch_master_state.py?site=%s&switch=%s&state=%d" % (siteid, colname, 1 - colvalue))
            onclick = "get_url('%s', updateContents, 'snapin_master_control')" % url
            html.write("<tr><td class=left>%s</td><td>" % title)
            html.icon_button("#", _("Switch %s %s") % (title, colvalue and "off" or "on"),
                             "snapin_switch_" + (colvalue and "on" or "off"), onclick=onclick)
            html.write("</td></tr>")
            # html.write("<a onclick=\"%s\" href=\"#\">%s</a></td></tr>\n" % (title, enabled, onclick, enabled))
        html.write("</table>")
        if siteid:
            html.end_foldable_container()

sidebar_snapins["master_control"] = {
    "title" : _("Master control"),
    "description" : _("Buttons for switching globally states such as enabling checks and notifications"),
    "render" : render_master_control,
    "allowed" : [ "admin", ],
    "styles" : """
div.snapin table.master_control {
    width: 100%;
    margin: 0px 0px 0px 0px;
    border-spacing: 0px;
}

div.snapin table.master_control td {
    padding: 0px 0px;
    text-align: right;
}

div.snapin table.master_control td.left a {
    text-align: left;
    font-size: 8pt;
    font-weight: normal;
}

div.snapin table.master_control td.left {
    text-align: left;
}

div.snapin table.master_control td img.iconbutton {
    width: 60px;
    height: 16px;
}

"""
}

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
        html.write("<div class=bookmark id=\"bookmark_%d\">" % n)
        iconbutton(_("delete"), "del_bookmark.py?num=%d" % n, "side", "updateContents", 'snapin_bookmarks', css_class = 'bookmark')
        iconbutton(_("edit"), "edit_bookmark.py?num=%d" % n, "main", css_class = 'bookmark')
        html.write(link(title, href))
        html.write("</div>")
        n += 1

    html.write("<div class=footnotelink><a href=\"#\" onclick=\"addBookmark()\">%s</a></div>\n" % _('Add Bookmark'))


sidebar_snapins["bookmarks"] = {
    "title" : _("Bookmarks"),
    "description" : _("A simple and yet practical snapin allowing to create bookmarks to views and other content in the main frame"),
    "render" : render_bookmarks,
    "allowed": [ "user", "admin", "guest" ],
    "styles" : """
div.bookmark {
    width: 230px;
    max-width: 230px;
    overflow: hidden;
    text-overflow: ellipsis;
    -o-text-overflow: ellipsis;
    white-space: nowrap;
    color: white;
}
"""
}



# ------------------------------------------------------------
#   ____          _                    _     _       _
#  / ___|   _ ___| |_ ___  _ __ ___   | |   (_)_ __ | | _____
# | |  | | | / __| __/ _ \| '_ ` _ \  | |   | | '_ \| |/ / __|
# | |__| |_| \__ \ || (_) | | | | | | | |___| | | | |   <\__ \
#  \____\__,_|___/\__\___/|_| |_| |_| |_____|_|_| |_|_|\_\___/
#
# ------------------------------------------------------------

def render_custom_links():
    links = config.custom_links.get(config.user_baserole_id)
    if not links:
        html.write((_("Please edit <tt>%s</tt> in order to configure which links are shown in this snapin.") %
                  (defaults.default_config_dir + "/multisite.mk")) + "\n")
        return

    def render_list(ids, links):
        states = weblib.get_tree_states('customlinks')
        n = 0
        for entry in links:
            n += 1
            try:
                if type(entry[1]) == type(True):
                    idss = ids + [str(n)]
                    is_open = entry[1]
                    id = '/'.join(idss)
                    html.begin_foldable_container("customlinks", id, isopen=entry[1], title=entry[0])
                    render_list(idss, entry[2])
                    html.end_foldable_container()
                elif type(entry[1]) == str:
                    frame = len(entry) > 3 and entry[3] or "main"
                    if len(entry) > 2 and entry[2]:
                        html.write('<img src="images/%s">' % entry[2])
                    else:
                        html.write('<img src="images/link_link.gif">')
                    simplelink(entry[0], entry[1], frame)
                else:
                    html.write(_("Second part of tuple must be list or string, not %s\n") % str(entry[1]))
            except Exception, e:
                html.write(_("invalid entry %s: %s<br>\n") % (entry, e))

    render_list([], links)

sidebar_snapins["custom_links"] = {
    "title" : _("Custom Links"),
    "description" : _("This snapin contains custom links which can be configured via the configuration variable <tt>custom_links</tt> in <tt>multisite.mk</tt>"),
    "render" : render_custom_links,
    "allowed" : [ "user", "admin", "guest" ],
    "styles" : """
#snapin_custom_links div.sublist {
    padding-left: 10px;
}
#snapin_custom_links img {
    margin-right: 5px;
}
"""
}
