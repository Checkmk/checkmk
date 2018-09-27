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

# TODO: Split this file into single snapin or topic files

# TODO: Refactor all snapins to the new snapin API and move page handlers
#       from sidebar.py to the snapin objects that need these pages.

import time

import cmk.paths
import cmk.store as store

import cmk.gui.config as config
import cmk.gui.views as views
import cmk.gui.dashboard as dashboard
import cmk.gui.pagetypes as pagetypes
import cmk.gui.table as table
import cmk.gui.sites as sites
import cmk.gui.watolib as watolib
# TODO: Cleanup star import
from cmk.gui.valuespec import *
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _u, _
from cmk.gui.globals import html
from cmk.gui.log import logger

from . import (
    sidebar_snapins,
    visuals_by_topic,
    bulletlink,
    link,
    footnotelinks,
    snapin_width,
    render_link,
    snapin_site_choice,
    nagioscgilink,
    heading,
    simplelink,
)

#.
#   .--Views---------------------------------------------------------------.
#   |                    __     ___                                        |
#   |                    \ \   / (_) _____      _____                      |
#   |                     \ \ / /| |/ _ \ \ /\ / / __|                     |
#   |                      \ V / | |  __/\ V  V /\__ \                     |
#   |                       \_/  |_|\___| \_/\_/ |___/                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def render_views():
    views.load_views()
    dashboard.load_dashboards()

    def render_topic(topic, entries):
        first = True
        for t, title, name, is_view in entries:
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
                elif "?name=" in name:
                    bulletlink(title, name)
                else:
                    bulletlink(title, 'dashboard.py?name=%s' % name, onclick = "return wato_views_clicked(this)")

        # TODO: One day pagestypes should handle the complete snapin.
        # for page_type in pagetypes.all_page_types().values():
        #     if issubclass(page_type, pagetypes.PageRenderer):
        #         for t, title, url in page_type.sidebar_links():
        #             if t == topic:
        #                 bulletlink(title, url)

        if not first: # at least one item rendered
            html.end_foldable_container()

    # TODO: One bright day drop this whole visuals stuff and only use page_types
    page_type_topics = {}
    for page_type in pagetypes.all_page_types().values():
        if issubclass(page_type, pagetypes.PageRenderer):
            for t, title, url in page_type.sidebar_links():
                page_type_topics.setdefault(t, []).append((t, title, url, False))

    visuals_topics_with_entries = visuals_by_topic(views.permitted_views().items() + dashboard.permitted_dashboards().items())
    all_topics_with_entries = []
    for topic, entries in visuals_topics_with_entries:
        if topic in page_type_topics:
            entries = entries + page_type_topics[topic]
            del page_type_topics[topic]
        all_topics_with_entries.append((topic, entries))

    all_topics_with_entries += sorted(page_type_topics.items())

    for topic, entries in all_topics_with_entries:
        render_topic(topic, entries)


    links = []
    if config.user.may("general.edit_views"):
        if config.debug:
            links.append((_("Export"), "export_views.py"))
        links.append((_("Edit"), "edit_views.py"))
        footnotelinks(links)

sidebar_snapins["views"] = {
    "title" : _("Views"),
    "description" : _("Links to global views and dashboards"),
    "render" : render_views,
    "allowed" : [ "user", "admin", "guest" ],
}

#.
#   .--Dashboards----------------------------------------------------------.
#   |        ____            _     _                         _             |
#   |       |  _ \  __ _ ___| |__ | |__   ___   __ _ _ __ __| |___         |
#   |       | | | |/ _` / __| '_ \| '_ \ / _ \ / _` | '__/ _` / __|        |
#   |       | |_| | (_| \__ \ | | | |_) | (_) | (_| | | | (_| \__ \        |
#   |       |____/ \__,_|___/_| |_|_.__/ \___/ \__,_|_|  \__,_|___/        |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def render_dashboards():
    dashboard.load_dashboards()

    def render_topic(topic, s, foldable = True):
        first = True
        for t, title, name, _is_view in s:
            if t == topic:
                if first:
                    if foldable:
                        html.begin_foldable_container("dashboards", topic, False, topic, indent=True)
                    else:
                        html.open_ul()
                    first = False
                bulletlink(title, 'dashboard.py?name=%s' % name, onclick = "return wato_views_clicked(this)")

        if not first: # at least one item rendered
            if foldable:
                html.end_foldable_container()
            else:
                html.open_ul()

    by_topic = visuals_by_topic(dashboard.permitted_dashboards().items(), default_order = [ _('Overview') ])
    topics = [ topic for topic, _entry in by_topic ]

    if len(topics) < 2:
        render_topic(by_topic[0][0], by_topic[0][1], foldable = False)

    else:
        for topic, s in by_topic:
            render_topic(topic, s)

    links = []
    if config.user.may("general.edit_dashboards"):
        if config.debug:
            links.append((_("Export"), "export_dashboards.py"))
        links.append((_("Edit"), "edit_dashboards.py"))
        footnotelinks(links)

sidebar_snapins["dashboards"] = {
    "title"       : _("Dashboards"),
    "description" : _("Links to all dashboards"),
    "render"      : render_dashboards,
    "allowed"     : [ "user", "admin", "guest" ],
}

#.
#   .--Groups--------------------------------------------------------------.
#   |                    ____                                              |
#   |                   / ___|_ __ ___  _   _ _ __  ___                    |
#   |                  | |  _| '__/ _ \| | | | '_ \/ __|                   |
#   |                  | |_| | | | (_) | |_| | |_) \__ \                   |
#   |                   \____|_|  \___/ \__,_| .__/|___/                   |
#   |                                        |_|                           |
#   '----------------------------------------------------------------------'

def render_groups(what):
    html.open_ul()
    for name, alias in sites.all_groups(what):
        url = "view.py?view_name=%sgroup&%sgroup=%s" % (what, what, html.urlencode(name))
        bulletlink(alias or name, url)
    html.close_ul()

sidebar_snapins["hostgroups"] = {
    "title" : _("Host Groups"),
    "description" : _("Directs links to all host groups"),
    "render" : lambda: render_groups("host"),
    "restart":     True,
    "allowed" : [ "user", "admin", "guest" ]
}
sidebar_snapins["servicegroups"] = {
    "title" : _("Service Groups"),
    "description" : _("Direct links to all service groups"),
    "render" : lambda: render_groups("service"),
    "restart":     True,
    "allowed" : [ "user", "admin", "guest" ]
}

#.
#   .--Hosts---------------------------------------------------------------.
#   |                       _   _           _                              |
#   |                      | | | | ___  ___| |_ ___                        |
#   |                      | |_| |/ _ \/ __| __/ __|                       |
#   |                      |  _  | (_) \__ \ |_\__ \                       |
#   |                      |_| |_|\___/|___/\__|___/                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def render_hosts(mode):
    sites.live().set_prepend_site(True)
    query = "GET hosts\nColumns: name state worst_service_state\nLimit: 100\n"
    view = "host"

    if mode == "problems":
        view = "problemsofhost"
        # Exclude hosts and services in downtime
        svc_query = "GET services\nColumns: host_name\n"\
                    "Filter: state > 0\nFilter: scheduled_downtime_depth = 0\n"\
                    "Filter: host_scheduled_downtime_depth = 0\nAnd: 3"
        problem_hosts = {x[1] for x in sites.live().query(svc_query)}

        query += "Filter: state > 0\nFilter: scheduled_downtime_depth = 0\nAnd: 2\n"
        for host in problem_hosts:
            query += "Filter: name = %s\n" % host
        query += "Or: %d\n" % (len(problem_hosts) + 1)

    hosts = sites.live().query(query)
    sites.live().set_prepend_site(False)
    hosts.sort()

    longestname = 0
    for site, host, state, worstsvc in hosts:
        longestname = max(longestname, len(host))
    if longestname > 15:
        num_columns = 1
    else:
        num_columns = 2

    views.load_views()
    target = views.get_context_link(config.user.id, view)
    html.open_table(class_="allhosts")
    col = 1
    for site, host, state, worstsvc in hosts:
        if col == 1:
            html.open_tr()
        html.open_td()

        if state > 0 or worstsvc == 2:
            statecolor = 2
        elif worstsvc == 1:
            statecolor = 1
        elif worstsvc == 3:
            statecolor = 3
        else:
            statecolor = 0
        html.open_div(class_=["statebullet", "state%d" % statecolor])
        html.nbsp()
        html.close_div()
        link(host, target + "&host=%s&site=%s" % (html.urlencode(host), html.urlencode(site)))
        html.close_td()
        if col == num_columns:
            html.close_tr()
            col = 1
        else:
            col += 1

    if col < num_columns:
        html.close_tr()
    html.close_table()

snapin_allhosts_styles = """
  .snapin table.allhosts { width: 100%; }
  .snapin table.allhosts td { width: 50%; padding: 0px 0px; }
"""

sidebar_snapins["hosts"] = {
    "title" : _("All Hosts"),
    "description" : _("A summary state of each host with a link to the view "
                      "showing its services"),
    "render" : lambda: render_hosts("hosts"),
    "allowed" : [ "user", "admin", "guest" ],
    "refresh" : True,
    "styles" : snapin_allhosts_styles,
}

sidebar_snapins["problem_hosts"] = {
    "title" : _("Problem Hosts"),
    "description" : _("A summary state of all hosts that have a problem, with "
                      "links to problems of those hosts"),
    "render" : lambda: render_hosts("problems"),
    "allowed" : [ "user", "admin", "guest" ],
    "refresh" : True,
    "styles" : snapin_allhosts_styles,
}


#.
#   .--Performance---------------------------------------------------------.
#   |    ____            __                                                |
#   |   |  _ \ ___ _ __ / _| ___  _ __ _ __ ___   __ _ _ __   ___ ___      |
#   |   | |_) / _ \ '__| |_ / _ \| '__| '_ ` _ \ / _` | '_ \ / __/ _ \     |
#   |   |  __/  __/ |  |  _| (_) | |  | | | | | | (_| | | | | (_|  __/     |
#   |   |_|   \___|_|  |_|  \___/|_|  |_| |_| |_|\__,_|_| |_|\___\___|     |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def render_performance():
    only_sites = snapin_site_choice("performance",
                                    config.site_choices())

    def write_line(left, right):
        html.open_tr()
        html.td(left, class_="left")
        html.td(html.render_strong(right), class_="right")
        html.close_tr()

    html.open_table(class_=["content_center", "performance"])

    try:
        sites.live().set_only_sites(only_sites)
        data = sites.live().query(
            "GET status\nColumns: service_checks_rate host_checks_rate "
            "external_commands_rate connections_rate forks_rate "
            "log_messages_rate cached_log_messages\n")
    finally:
        sites.live().set_only_sites(None)

    for what, col, format_str in \
        [("Service checks",         0, "%.2f/s"),
         ("Host checks",            1, "%.2f/s"),
         ("External commands",      2, "%.2f/s"),
         ("Livestatus-conn.",       3, "%.2f/s"),
         ("Process creations",      4, "%.2f/s"),
         ("New log messages",       5, "%.2f/s"),
         ("Cached log messages",    6, "%d")]:
        write_line(what + ":", format_str % sum(row[col] for row in data))

    if only_sites is None and len(config.allsites()) == 1:
        try:
            data = sites.live().query("GET status\nColumns: external_command_buffer_slots "
                                   "external_command_buffer_max\n")
        finally:
            sites.live().set_only_sites(None)
        size = sum([row[0] for row in data])
        maxx = sum([row[1] for row in data])
        write_line(_('Com. buf. max/total'), "%d / %d" % (maxx, size))

    html.close_table()


sidebar_snapins["performance"] = {
    "title" : _("Server Performance"),
    "description" : _("Live monitor of the overall performance of all monitoring servers"),
    "refresh" : True,
    "render" : render_performance,
    "allowed" : [ "admin", ],
    "styles" : """
#snapin_performance select {
    margin-bottom: 2px;
    width: 100%%;
}
table.performance {
    width: %dpx;
    border-radius: 2px;
    background-color: rgba(0, 0, 0, 0.1);
    border-style: solid;
    border-color: rgba(0, 0, 0, 0.3) rgba(255, 255, 255, 0.3) rgba(255, 255, 255, 0.3) rgba(0, 0, 0, 0.3);
    border-width: 1.5px;
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
#   .--Server Time---------------------------------------------------------.
#   |       ____                             _____ _                       |
#   |      / ___|  ___ _ ____   _____ _ __  |_   _(_)_ __ ___   ___        |
#   |      \___ \ / _ \ '__\ \ / / _ \ '__|   | | | | '_ ` _ \ / _ \       |
#   |       ___) |  __/ |   \ V /  __/ |      | | | | | | | | |  __/       |
#   |      |____/ \___|_|    \_/ \___|_|      |_| |_|_| |_| |_|\___|       |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def render_current_time():
    html.div(time.strftime("%H:%M"), class_="time")

sidebar_snapins["time"] = {
    "title" : _("Server Time"),
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

#.
#   .--Nagios--------------------------------------------------------------.
#   |                    _   _             _                               |
#   |                   | \ | | __ _  __ _(_) ___  ___                     |
#   |                   |  \| |/ _` |/ _` | |/ _ \/ __|                    |
#   |                   | |\  | (_| | (_| | | (_) \__ \                    |
#   |                   |_| \_|\__,_|\__, |_|\___/|___/                    |
#   |                                |___/                                 |
#   '----------------------------------------------------------------------'

def render_nagios():
    html.open_ul()
    bulletlink("Home", "http://www.nagios.org")
    bulletlink("Documentation", "%snagios/docs/toc.html" % config.url_prefix())
    html.close_ul()
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
            html.close_ul()
            heading(entry)
            html.open_ul()
        else:
            ref, text = entry
            if text[0] == "*":
                html.open_ul(class_="link")
                nagioscgilink(text[1:], ref)
                html.close_ul()
            else:
                nagioscgilink(text, ref)

sidebar_snapins["nagios_legacy"] = {
    "title" : _("Old Nagios GUI"),
    "description" : _("The classical sidebar of Nagios 3.2.0 with links to "
                      "your local Nagios instance (no multi site support)"),
    "render" : render_nagios,
    "allowed" : [ "user", "admin", "guest", ],
}

#.
#   .--Custom Links--------------------------------------------------------.
#   |      ____          _                    _     _       _              |
#   |     / ___|   _ ___| |_ ___  _ __ ___   | |   (_)_ __ | | _____       |
#   |    | |  | | | / __| __/ _ \| '_ ` _ \  | |   | | '_ \| |/ / __|      |
#   |    | |__| |_| \__ \ || (_) | | | | | | | |___| | | | |   <\__ \      |
#   |     \____\__,_|___/\__\___/|_| |_| |_| |_____|_|_| |_|_|\_\___/      |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def render_custom_links():
    links = config.custom_links.get(config.user.baserole_id)
    if not links:
        html.write_text((_("Please edit <tt>%s</tt> in order to configure which links are shown in this snapin.") %
                  (cmk.paths.default_config_dir + "/multisite.mk")) + "\n")
        return

    def render_list(ids, links):
        n = 0
        for entry in links:
            n += 1
            try:
                if type(entry[1]) == type(True):
                    idss = ids + [str(n)]
                    id_ = '/'.join(idss)
                    html.begin_foldable_container("customlinks", id_, isopen=entry[1], title=entry[0])
                    render_list(idss, entry[2])
                    html.end_foldable_container()
                elif type(entry[1]) == str:
                    frame =entry[3] if len(entry) > 3 else "main"

                    if len(entry) > 2 and entry[2]:
                        icon_file = entry[2]

                        # Old configs used files named "link_<name>.gif". Those .gif files have
                        # been removed from Check_MK. Replacing such images with the default icon
                        if icon_file.endswith(".gif"):
                            icon_file = "icon_link.png"
                    else:
                        icon_file = "icon_link.png"

                    linktext = HTML(html.render_icon("images/%s" % icon_file) + " " + entry[0])

                    simplelink(linktext, entry[1], frame)
                else:
                    html.write_text(_("Second part of tuple must be list or string, not %s\n") % str(entry[1]))
            except Exception, e:
                html.write_text(_("invalid entry %s: %s<br>\n") % (entry, e))

    render_list([], links)

sidebar_snapins["custom_links"] = {
    "title" : _("Custom Links"),
    "description" : _("This snapin contains custom links which can be "
                      "configured via the configuration variable "
                      "<tt>custom_links</tt> in <tt>multisite.mk</tt>"),
    "render" : render_custom_links,
    "allowed" : [ "user", "admin", "guest" ],
    "styles" : """
#snapin_custom_links div.sublist {
    padding-left: 10px;
}
#snapin_custom_links img {
    margin-right: 5px;
}
#snapin_custom_links img.icon {
    width: 16px;
    height: 16px;
}
"""
}


#.
#   .--Dokuwiki------------------------------------------------------------.
#   |              ____        _                   _ _    _                |
#   |             |  _ \  ___ | | ___   ___      _(_) | _(_)               |
#   |             | | | |/ _ \| |/ / | | \ \ /\ / / | |/ / |               |
#   |             | |_| | (_) |   <| |_| |\ V  V /| |   <| |               |
#   |             |____/ \___/|_|\_\\__,_| \_/\_/ |_|_|\_\_|               |
#   |                                                                      |
#   '----------------------------------------------------------------------'

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
    filename = cmk.paths.omd_root + '/var/dokuwiki/data/pages/sidebar.txt'
    html.javascript("""
    function wiki_search()
    {
        var oInput = document.getElementById('wiki_search_field');
        top.frames["main"].location.href =
           "/%s/wiki/doku.php?do=search&id=" + escape(oInput.value);
    }
    """ % config.omd_site())

    html.open_form(id_="wiki_search", onsubmit="wiki_search();")
    html.input(id_="wiki_search_field", type_="text", name="wikisearch")
    html.icon_button("#", _("Search"), "wikisearch", onclick="wiki_search();")
    html.close_form()
    html.div('', id_="wiki_side_clear")

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
                # html.br()

            elif line.startswith("*"):
                if start_ul == True:
                    if title:
                         html.begin_foldable_container("wikisnapin", title, True, title, indent=True)
                    else:
                        html.open_ul()
                    start_ul = False
                    ul_started = True

                erg = re.findall(r'\[\[(.*)\]\]', line)
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
                    bulletlink(name, "/%s/wiki/doku.php?id=%s" % (config.omd_site(), link))

            else:
                html.write_text(line)

        if ul_started == True:
            html.close_ul()
    except IOError:
        sidebar = html.render_a("sidebar",
                                href="/%s/wiki/doku.php?id=%s" % (config.omd_site(), _("sidebar")),
                                target = "main")
        html.write_html("<p>To get a navigation menu, you have to create a %s in your wiki first.</p>"\
                                                                           % sidebar)

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
