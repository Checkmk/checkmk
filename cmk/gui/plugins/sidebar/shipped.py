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

import re

import cmk.paths

import cmk.gui.config as config
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.globals import html

from cmk.gui.plugins.sidebar import (
    sidebar_snapins,
    bulletlink,
    simplelink,
)

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
        html.write_text((_(
            "Please edit <tt>%s</tt> in order to configure which links are shown in this snapin.") %
                         (cmk.paths.default_config_dir + "/multisite.mk")) + "\n")
        return

    def render_list(ids, links):
        n = 0
        for entry in links:
            n += 1
            try:
                if isinstance(entry[1], type(True)):
                    idss = ids + [str(n)]
                    id_ = '/'.join(idss)
                    html.begin_foldable_container(
                        "customlinks", id_, isopen=entry[1], title=entry[0])
                    render_list(idss, entry[2])
                    html.end_foldable_container()
                elif isinstance(entry[1], str):
                    frame = entry[3] if len(entry) > 3 else "main"

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
                    html.write_text(
                        _("Second part of tuple must be list or string, not %s\n") % str(entry[1]))
            except Exception as e:
                html.write_text(_("invalid entry %s: %s<br>\n") % (entry, e))

    render_list([], links)


sidebar_snapins["custom_links"] = {
    "title": _("Custom Links"),
    "description": _("This snapin contains custom links which can be "
                     "configured via the configuration variable "
                     "<tt>custom_links</tt> in <tt>multisite.mk</tt>"),
    "render": render_custom_links,
    "allowed": ["user", "admin", "guest"],
    "styles": """
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
        sidebar = html.render_a(
            "sidebar",
            href="/%s/wiki/doku.php?id=%s" % (config.omd_site(), _("sidebar")),
            target="main")
        html.write_html("<p>To get a navigation menu, you have to create a %s in your wiki first.</p>"\
                                                                           % sidebar)


sidebar_snapins["wiki"] = {
    "title": _("Wiki"),
    "description": _("Shows the Wiki Navigation of the OMD Site"),
    "render": render_wiki,
    "allowed": ["admin", "user", "guest"],
    "styles": """
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
