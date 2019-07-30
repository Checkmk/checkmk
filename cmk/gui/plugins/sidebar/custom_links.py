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

import cmk.utils.paths
import cmk.gui.config as config
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.plugins.sidebar import (
    SidebarSnapin,
    snapin_registry,
    simplelink,
)


@snapin_registry.register
class CustomLinks(SidebarSnapin):
    @staticmethod
    def type_name():
        return "custom_links"

    @classmethod
    def title(cls):
        return _("Custom Links")

    @classmethod
    def description(cls):
        return _("This snapin contains custom links which can be "
                 "configured via the configuration variable "
                 "<tt>custom_links</tt> in <tt>multisite.mk</tt>")

    def show(self):
        links = config.custom_links.get(config.user.baserole_id)
        if not links:
            html.write_text((_(
                "Please edit <tt>%s</tt> in order to configure which links are shown in this snapin."
            ) % (cmk.utils.paths.default_config_dir + "/multisite.mk")) + "\n")
            return

        def render_list(ids, links):
            n = 0
            for entry in links:
                n += 1
                try:
                    if isinstance(entry[1], type(True)):
                        idss = ids + [str(n)]
                        id_ = '/'.join(idss)
                        html.begin_foldable_container("customlinks",
                                                      id_,
                                                      isopen=entry[1],
                                                      title=entry[0])
                        render_list(idss, entry[2])
                        html.end_foldable_container()
                    elif isinstance(entry[1], str):
                        frame = entry[3] if len(entry) > 3 else "main"

                        if len(entry) > 2 and entry[2]:
                            icon_file = entry[2]

                            # Old configs used files named "link_<name>.gif". Those .gif files have
                            # been removed from Check_MK. Replacing such images with the default icon
                            if icon_file.endswith(".gif"):
                                icon_name = "link"
                            else:
                                icon_name = icon_file.rsplit(".", 1)[0].replace("icon_", "")
                        else:
                            icon_name = "link"

                        linktext = HTML(html.render_icon(icon_name) + " " + entry[0])

                        simplelink(linktext, entry[1], frame)
                    else:
                        html.write_text(
                            _("Second part of tuple must be list or string, not %s\n") %
                            str(entry[1]))
                except Exception as e:
                    html.write_text(_("invalid entry %s: %s<br>\n") % (entry, e))

        render_list([], links)
