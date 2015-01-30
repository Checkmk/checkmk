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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import views, time, defaults, dashboard
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

def visuals_by_topic(permitted_visuals,
        default_order = [ _("Overview"), _("Hosts"), _("Host Groups"), _("Services"), _("Service Groups"),
                         _("Business Intelligence"), _("Problems"), _("Addons") ]):
    s = [ (_u(visual.get("topic") or _("Other")), _u(visual.get("title")), name, 'painters' in visual)
          for name, visual
          in permitted_visuals
          if not visual["hidden"] and not visual.get("mobile")]

    s.sort()

    result = []
    for topic in default_order:
        result.append((topic, s))

    rest = list(set([ t for (t, _t, _v, _i) in s if t not in default_order ]))
    rest.sort()
    for topic in rest:
        if topic:
            result.append((topic, s))

    return result

def render_views():
    views.load_views()
    dashboard.load_dashboards()

    def render_topic(topic, s):
        first = True
        for t, title, name, is_view in s:
            if is_view and config.visible_views and name not in config.visible_views:
                continue
            if is_view and config.hidden_views and name in config.hidden_views:
                continue
            if t == topic:
                if first:
                    html.begin_foldable_container("views", topic, False, topic, indent=True)
                    first = False
                if is_view:
                    bulletlink(title, "view.py?view_name=%s" % name, onclick = "return wato_views_clicked(this)")
                else:
                    bulletlink(title, 'dashboard.py?name=%s' % name, onclick = "return wato_views_clicked(this)")
        if not first: # at least one item rendered
            html.end_foldable_container()

    for topic, s in visuals_by_topic(views.permitted_views().items() + dashboard.permitted_dashboards().items()):
        render_topic(topic, s)

    links = []
    if config.may("general.edit_views"):
        if config.debug:
            links.append((_("EXPORT"), "export_views.py"))
        links.append((_("EDIT"), "edit_views.py"))
        footnotelinks(links)

sidebar_snapins["views"] = {
    "title" : _("Views"),
    "description" : _("Links to global views and dashboards"),
    "render" : render_views,
    "allowed" : [ "user", "admin", "guest" ],
}

#   .--Dashboards----------------------------------------------------------.
#   |        ____            _     _                         _             |
#   |       |  _ \  __ _ ___| |__ | |__   ___   __ _ _ __ __| |___         |
#   |       | | | |/ _` / __| '_ \| '_ \ / _ \ / _` | '__/ _` / __|        |
#   |       | |_| | (_| \__ \ | | | |_) | (_) | (_| | | | (_| \__ \        |
#   |       |____/ \__,_|___/_| |_|_.__/ \___/ \__,_|_|  \__,_|___/        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def render_dashboards():
    dashboard.load_dashboards()

    def render_topic(topic, s, foldable = True):
        first = True
        for t, title, name, is_view in s:
            if t == topic:
                if first:
                    if foldable:
                        html.begin_foldable_container("dashboards", topic, False, topic, indent=True)
                    else:
                        html.write('<ul>')
                    first = False
                bulletlink(title, 'dashboard.py?name=%s' % name, onclick = "return wato_views_clicked(this)")

        if not first: # at least one item rendered
            if foldable:
                html.end_foldable_container()
            else:
                html.write('<ul>')

    by_topic = visuals_by_topic(dashboard.permitted_dashboards().items(), default_order = [ _('Overview') ])
    topics = [ topic for topic, entry in by_topic ]

    if len(topics) < 2:
        render_topic(by_topic[0][0], by_topic[0][1], foldable = False)

    else:
        for topic, s in by_topic:
            render_topic(topic, s)

    links = []
    if config.may("general.edit_dashboards"):
        if config.debug:
            links.append((_("EXPORT"), "export_dashboards.py"))
        links.append((_("EDIT"), "edit_dashboards.py"))
        footnotelinks(links)

sidebar_snapins["dashboards"] = {
    "title"       : _("Dashboards"),
    "description" : _("Links to all dashboards"),
    "render"      : render_dashboards,
    "allowed"     : [ "user", "admin", "guest" ],
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
        url = "view.py?view_name=%sgroup&%sgroup=%s" % (what, what, html.urlencode(name))
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
        view = "problemsofhost"
        # Exclude hosts and services in downtime
        svc_query = "GET services\nColumns: host_name\n"\
                    "Filter: state > 0\nFilter: scheduled_downtime_depth = 0\n"\
                    "Filter: host_scheduled_downtime_depth = 0\nAnd: 3"
        problem_hosts = set(map(lambda x: x[1], html.live.query(svc_query)))

        query += "Filter: state > 0\nFilter: scheduled_downtime_depth = 0\nAnd: 2\n"
        for host in problem_hosts:
            query += "Filter: name = %s\n" % host
        query += "Or: %d\n" % (len(problem_hosts) + 1)

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
        html.write(link(host, target + ("&host=%s&site=%s" % (html.urlencode(host), html.urlencode(site)))))
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
    "description" : _("A summary state of all hosts that have a problem, with links to problems of those hosts"),
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
        url = "view.py?view_name=host&site=%s&host=%s" % (html.urlencode(site), html.urlencode(host))
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

        for sitename, sitealias in config.sorted_sites():
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
                           "log_messages_rate cached_log_messages\n")
    for what, col, format in \
        [("Service checks",        0, "%.2f/s"),
        ("Host checks",            1, "%.2f/s"),
        ("External commands",      2, "%.2f/s"),
        ("Livestatus-conn.",       3, "%.2f/s"),
        ("Process creations",      4, "%.2f/s"),
        ("New log messages",       5, "%.2f/s"),
        ("Cached log messages",    6, "%d")]:
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
    "title" : _("Service Speed-O-Meter"),
    "description" : _("A gadget that shows your current service check rate in relation to "
                      "the scheduled check rate. If the Speed-O-Meter shows a speed "
                      "of 100 percent, all service checks are being executed in exactly "
                      "the rate that is desired."),
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
        ( "enable_flap_detection",    _("Flap Detection" )),
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
        is_cmc = html.site_status[siteid]["program_version"].startswith("Check_MK ")
        html.write("<table class=master_control>\n")
        for i, (colname, title) in enumerate(items):
            # Do not show event handlers on Check_MK Micro Core
            if is_cmc and colname == 'enable_event_handlers':
                continue

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
        iconbutton("delete", "del_bookmark.py?num=%d" % n, "side", "updateContents", 'snapin_bookmarks', css_class = 'bookmark')
        iconbutton("edit", "edit_bookmark.py?num=%d" % n, "main", css_class = 'bookmark')
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
        states = html.get_tree_states('customlinks')
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



#Example Sidebar:
#Heading1:
#   * [[link1]]
#   * [[link2]]
#
#----
#
#Heading2:
#   * [[link3]]
#   * [[link4]]

def render_wiki():
    filename = defaults.omd_root + '/var/dokuwiki/data/pages/sidebar.txt'
    html.javascript("""
    function wiki_search()
    {
        var oInput = document.getElementById('wiki_search_field');
        top.frames["main"].location.href =
           "/%s/wiki/doku.php?do=search&id=" + escape(oInput.value);
    }
    """ % defaults.omd_site)

    html.write('<form id="wiki_search" onSubmit="wiki_search()">')
    html.write('<input id="wiki_search_field" type="text" name="wikisearch"></input>\n')
    html.icon_button("#", _("Search"), "wikisearch", onclick="wiki_search();")
    html.write('</form>')
    html.write('<div id="wiki_side_clear"></div>')

    start_ul = True
    ul_started = False
    try:
        title = None
        for line in file(filename).readlines():
            line = line.strip()
            if line == "":
                if ul_started == True:
                    html.end_foldable_container()
                    start_ul = True
                    ul_started = False
            elif line.endswith(":"):
                title = line[:-1]
            elif line == "----":
                pass
                # html.write("<br>")

            elif line.startswith("*"):
                if start_ul == True:
                    if title:
                         html.begin_foldable_container("wikisnapin", title, True, title, indent=True)
                    else:
                        html.write('<ul>')
                    start_ul = False
                    ul_started = True

                erg = re.findall('\[\[(.*)\]\]', line)
                if len(erg) == 0:
                    continue
                erg = erg[0].split('|')
                if len(erg) > 1:
                    link = erg[0]
                    name = erg[1]
                else:
                    link = erg[0]
                    name = erg[0]

                if link.startswith("http://") or link.startswith("https://"):
                    simplelink(name, link, "_blank")
                else:
                    erg = name.split(':')
                    if len(erg) > 0:
                        name = erg[-1]
                    else:
                        name = erg[0]
                    bulletlink(name, "/%s/wiki/doku.php?id=%s" % (defaults.omd_site, link))

            else:
                html.write(line)

        if ul_started == True:
            html.write("</ul>")
    except IOError:
        html.write("<p>To get a navigation menu, you have to create a <a href='/%s/wiki/doku.php?id=%s' "
                   "target='main'>sidebar</a> in your wiki first.</p>" % (defaults.omd_site, _("sidebar")))

if defaults.omd_root:
    sidebar_snapins["wiki"] = {
        "title" : _("Wiki"),
        "description" : _("Shows the Wiki Navigation of the OMD Site"),
        "render" : render_wiki,
        "allowed" : [ "admin", "user", "guest" ],
        "styles" : """
        #snapin_container_wiki div.content {
            font-weight: bold;
            color: white;
        }

        #snapin_container_wiki div.content p {
            font-weight: normal;
        }

        #wiki_navigation {
            text-align: left;
        }

        #wiki_search {
            width: 232px;
            padding: 0;
        }

        #wiki_side_clear {
            clear: both;
        }

        #wiki_search img.iconbutton {
            width: 33px;
            height: 26px;
            margin-top: -25px;
            left: 196px;
            float: left;
            position: relative;
            z-index:100;
        }

        #wiki_search input {
            margin:  0;
            padding: 0px 5px;
            font-size: 8pt;
            width: 194px;
            height: 25px;
            background-image: url("images/quicksearch_field_bg.png");
            background-repeat: no-repeat;
            -moz-border-radius: 0px;
            border-style: none;
            float: left;
        }
        """
    }

#   .--Virt. Host Tree-----------------------------------------------------.
#   |  __     ___      _       _   _           _     _____                 |
#   |  \ \   / (_)_ __| |_    | | | | ___  ___| |_  |_   _| __ ___  ___    |
#   |   \ \ / /| | '__| __|   | |_| |/ _ \/ __| __|   | || '__/ _ \/ _ \   |
#   |    \ V / | | |  | |_ _  |  _  | (_) \__ \ |_    | || | |  __/  __/   |
#   |     \_/  |_|_|   \__(_) |_| |_|\___/|___/\__|   |_||_|  \___|\___|   |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def compute_tag_tree(taglist):
    html.live.set_prepend_site(True)
    query = "GET hosts\n" \
            "Columns: host_name state num_services_ok num_services_warn num_services_crit num_services_unknown custom_variables"
    hosts = html.live.query(query)
    html.live.set_prepend_site(False)
    hosts.sort()

    def get_tag_group_value(groupentries, tags):
        for entry in groupentries:
            if entry[0] in tags:
                return entry[0], entry[1] # tag, title
        # Not found -> try empty entry
        for entry in groupentries:
            if entry[0] == None:
                return None, entry[1]

        # No empty entry found -> get default (i.e. first entry)
        return groupentries[0][:2]

    # Prepare list of host tag groups and topics
    taggroups = {}
    topics = {}
    for entry in config.wato_host_tags:
        grouptitle           = entry[1]
        if '/' in grouptitle:
            topic, grouptitle = grouptitle.split("/", 1)
            topics.setdefault(topic, []).append(entry)

        groupname            = entry[0]
        group                = entry[2]
        taggroups[groupname] = group

    tree = {}
    for site, host_name, state, num_ok, num_warn, num_crit, num_unknown, custom_variables in hosts:
        # make state reflect the state of the services + host
        have_svc_problems = False
        if state:
            state += 1 # shift 1->2 (DOWN->CRIT) and 2->3 (UNREACH->UNKNOWN)
        if num_crit:
            state = 2
            have_svc_problems = True
        elif num_unknown:
            if state != 2:
                state = 3
            have_svc_problems = True
        elif num_warn:
            if not state:
                state = 1
            have_svc_problems = True

        tags = custom_variables.get("TAGS", []).split()

        tree_entry = tree # Start at top node

        # Now go through the levels of the tree. Each level may either be
        # - a tag group id, or
        # - "topic:" plus the name of a tag topic. That topic should only contain
        #   checkbox tags.
        # The problem with the "topic" entries is, that a host may appear several
        # times!

        current_branches = [ tree ]

        for tag in taglist:
            new_current_branches = []
            for tree_entry in current_branches:
                if tag.startswith("topic:"):
                    topic = tag[6:]
                    if topic in topics: # Could have vanished
                        # Iterate over all host tag groups with that topic
                        for entry in topics[topic]:
                            grouptitle  = entry[1].split("/", 1)[1]
                            group       = entry[2]
                            for tagentry in group:
                                tag_value, tag_title = tagentry[:2]
                                if tag_value in tags:
                                    new_current_branches.append(tree_entry.setdefault((tag_title, tag_value), {}))

                else:
                    if tag not in taggroups:
                        continue # Configuration error. User deleted tag group after configuring his tree
                    tag_value, tag_title = get_tag_group_value(taggroups[tag], tags)
                    new_current_branches.append(tree_entry.setdefault((tag_title, tag_value), {}))

            current_branches = new_current_branches

        for tree_entry in new_current_branches:
            if not tree_entry:
                tree_entry.update({
                    "_num_hosts" : 0,
                    "_state"     : 0,
                })
            tree_entry["_num_hosts"] += 1
            tree_entry["_svc_problems"] = tree_entry.get("_svc_problems", False) or have_svc_problems
            if state == 2 or tree_entry["_state"] == 2:
                tree_entry["_state"] = 2
            else:
                tree_entry["_state"] = max(state, tree_entry["_state"])

    return tree

def tag_tree_worst_state(tree):
    if "_state" in tree:
        return tree["_state"]
    else:
        states = map(tag_tree_worst_state, tree.values())
        for x in states:
            if x == 2:
                return 2
        return max(states)

def tag_tree_has_svc_problems(tree):
    if "_svc_problems" in tree:
        return tree["_svc_problems"]
    else:
        for x in tree.values():
            if tag_tree_has_svc_problems(x):
                return True
        return False

def tag_tree_url(taggroups, taglist, viewname):
    urlvars = [("view_name", viewname), ("filled_in", "filter")]
    if viewname == "svcproblems":
        urlvars += [ ("st1", "on"), ("st2", "on"), ("st3", "on") ]

    for nr, (group, tag) in enumerate(zip(taggroups, taglist)):
        if group.startswith("topic:"):
            # Find correct tag group for this tag
            for entry in config.wato_host_tags:
                for tagentry in entry[2]:
                    if tagentry[0] == tag: # Found our tag
                        taggroup = entry[0]
                        urlvars.append(("host_tag_%d_grp" % nr, taggroup))
                        urlvars.append(("host_tag_%d_op" % nr, "is"))
                        urlvars.append(("host_tag_%d_val" % nr, tag))
                        break
        else:
            urlvars.append(("host_tag_%d_grp" % nr, group))
            urlvars.append(("host_tag_%d_op" % nr, "is"))
            urlvars.append(("host_tag_%d_val" % nr, tag or ""))
    return html.makeuri_contextless(urlvars, "view.py")

def tag_tree_bullet(state, path, leaf):
    code = '<div class="tagtree %sstatebullet state%d">&nbsp;</div>' % ((leaf and "leaf " or ""), state)
    if not leaf:
        code = '<a title="%s" href="javascript:virtual_host_tree_enter(%r);">' % \
           (_("Display the tree only below this node"), "|".join(path)) + code + "</a>"
    return code + " "


def is_tag_subdir(path, cwd):
    if not cwd:
        return True
    elif not path:
        return False
    elif path[0] != cwd[0]:
        return False
    else:
        return is_tag_subdir(path[1:], cwd[1:])

def render_tag_tree_level(taggroups, path, cwd, title, tree):
    if not is_tag_subdir(path, cwd) and not is_tag_subdir(cwd, path):
        return

    if path != cwd and is_tag_subdir(path, cwd):
        bullet = tag_tree_bullet(tag_tree_worst_state(tree), path, False)
        if tag_tree_has_svc_problems(tree):
            # We cannot use html.plug() here, since this is not (yet)
            # reentrant and it is used by the sidebar snapin updater.
            # So we need to duplicate the code of icon_button here:
            bullet += ('<a target="main" onfocus="if (this.blur) this.blur();" href="%s">'
                       '<img align=absmiddle class=iconbutton title="%s" src="images/button_svc_problems_lo.png" '
                       'onmouseover="hilite_icon(this, 1)" onmouseout="hilite_icon(this, 0)"></a>' % (
                        tag_tree_url(taggroups, path, "svcproblems"),
                       _("Show the service problems contained in this branch")))


        if path:
            html.begin_foldable_container("tag-tree", ".".join(map(str, path)), False, bullet + title)

    items = tree.items()
    items.sort()

    for nr, ((title, tag), subtree) in enumerate(items):
        subpath = path + [tag or ""]
        url = tag_tree_url(taggroups, subpath, "allhosts")
        if "_num_hosts" in subtree:
            title += " (%d)" % subtree["_num_hosts"]
        href = '<a target=main href="%s">%s</a>' % (url, html.attrencode(title))
        if "_num_hosts" in subtree:

            if is_tag_subdir(path, cwd):
                html.write(tag_tree_bullet(subtree["_state"], subpath, True))
                if subtree.get("_svc_problems"):
                    url = tag_tree_url(taggroups, subpath, "svcproblems")
                    html.icon_button(url, _("Show the service problems contained in this branch"),
                            "svc_problems", target="main")
                html.write(href)
                html.write("<br>")
        else:
            render_tag_tree_level(taggroups, subpath, cwd, href, subtree)

    if path and path != cwd and is_tag_subdir(path, cwd):
        html.end_foldable_container()

virtual_host_tree_js = """
function virtual_host_tree_changed(field)
{
    var tree_conf = field.value;
    // Then send the info to python code via ajax call for persistance
    get_url_sync('sidebar_ajax_tag_tree.py?conf=' + escape(tree_conf));
    refresh_single_snapin("tag_tree");
}

function virtual_host_tree_enter(path)
{
    get_url_sync('sidebar_ajax_tag_tree_enter.py?path=' + escape(path));
    refresh_single_snapin("tag_tree");
}
"""

def render_tag_tree():
    if not config.virtual_host_trees:
        url = 'wato.py?varname=virtual_host_trees&mode=edit_configvar'
        html.write(_('You have not defined any virtual host trees. You can '
                     'do this in the global settings for <a target=main href="%s">Multisite</a>.') % url)
        return

    tree_conf = config.load_user_file("virtual_host_tree", {"tree": 0, "cwd": {}})
    if type(tree_conf) == int:
        tree_conf = {"tree": tree_conf, "cwd":{}} # convert from old style


    choices = [ (str(i), v[0]) for i, v in enumerate(config.virtual_host_trees)]
    html.begin_form("vtree")

    # Give chance to change one level up, if we are in a subtree
    cwd = tree_conf["cwd"].get(tree_conf["tree"])
    if cwd:
        upurl = "javascript:virtual_host_tree_enter(%r)" % "|".join(cwd[:-1])
        html.icon_button(upurl, _("Go up one tree level"), "back")

    html.select("vtree", choices, str(tree_conf["tree"]), onchange = 'virtual_host_tree_changed(this)')
    html.write("<br>")
    html.end_form()
    html.final_javascript(virtual_host_tree_js)

    title, taggroups = config.virtual_host_trees[tree_conf["tree"]]

    tree = compute_tag_tree(taggroups)
    render_tag_tree_level(taggroups, [], cwd, _("Virtual Host Tree"), tree)

sidebar_snapins["tag_tree"] = {
    "title" : _("Virtual Host Tree"),
    "description" : _("This snapin shows tree views of your hosts based on their tag classifications. You "
                      "can configure which tags to use in your global settings of Multisite."),
    "render" : render_tag_tree,
    "refresh" : True,
    "allowed" : [ "admin", "user", "guest" ],
    "styles" : """

#snapin_tag_tree img.iconbutton {
}

#snapin_tag_tree select {
    background-color: #6DA1B8;
    border-color: #123A4A;
    color: #FFFFFF;
    font-size: 8pt;
    height: 19px;
    margin-bottom: 2px;
    margin-top: -2px;
    padding: 0;
    width: 230px;
}

#snapin_tag_tree div.statebullet {
    position: relative;
    top: 3px;
    left: 1px;
    float: none;
    display: inline-block;
    width: 8px;
    height: 8px;
    margin-right: 0px;
    box-shadow: 0px 0px 0.7px #284850;
}

#snapin_tag_tree ul > div.statebullet.leaf {
    margin-left: 16px;
}
#snapin_tag_tree b {
    font-weight: normal;
}

#snapin_tag_tree {
    position: relative;
    top: 0px;
    left: 0px;
}
#snapin_tag_tree form img.iconbutton {
    width: 16px;
    height: 16px;
    float: none;
    display: inline-box;
    position: absolute;
    top: 9px;
    left: 14px;
}
#snapin_tag_tree select {
    width: 198px;
    margin-left: 17px;
}
"""
}
