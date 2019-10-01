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

import re
import cmk.utils.paths
import cmk.gui.config as config
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.plugins.sidebar import (
    SidebarSnapin,
    snapin_registry,
    bulletlink,
    simplelink,
)


@snapin_registry.register
class Wiki(SidebarSnapin):
    @staticmethod
    def type_name():
        return "wiki"

    @classmethod
    def title(cls):
        return _("Wiki")

    @classmethod
    def description(cls):
        return _("Shows the Wiki Navigation of the OMD Site")

    def show(self):
        filename = cmk.utils.paths.omd_root + '/var/dokuwiki/data/pages/sidebar.txt'
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
            for line in open(filename).readlines():
                line = line.strip()
                if line == "":
                    if ul_started:
                        html.end_foldable_container()
                        start_ul = True
                        ul_started = False
                elif line.endswith(":"):
                    title = line[:-1]
                elif line == "----":
                    pass
                    # html.br()

                elif line.startswith("*"):
                    if start_ul:
                        if title:
                            html.begin_foldable_container("wikisnapin",
                                                          title,
                                                          True,
                                                          title,
                                                          indent=True)
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

            if ul_started:
                html.close_ul()
        except IOError:
            sidebar = html.render_a("sidebar",
                                    href="/%s/wiki/doku.php?id=%s" %
                                    (config.omd_site(), _("sidebar")),
                                    target="main")
            html.write_html("<p>To get a navigation menu, you have to create a %s in your wiki first.</p>"\
                                                                               % sidebar)
