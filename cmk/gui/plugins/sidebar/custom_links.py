#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.paths

from cmk.gui.globals import config, html, user
from cmk.gui.htmllib import foldable_container
from cmk.gui.i18n import _
from cmk.gui.plugins.sidebar.utils import SidebarSnapin, simplelink, snapin_registry
from cmk.gui.utils.escaping import escape_html
from cmk.gui.utils.html import HTML


@snapin_registry.register
class CustomLinks(SidebarSnapin):
    @staticmethod
    def type_name():
        return "custom_links"

    @classmethod
    def title(cls):
        return _("Custom links")

    @classmethod
    def description(cls):
        return _(
            "This snapin contains custom links which can be "
            "configured via the configuration variable "
            "<tt>custom_links</tt> in <tt>multisite.mk</tt>"
        )

    def show(self):
        links = config.custom_links.get(user.baserole_id)
        if not links:
            html.write_text(
                (
                    _(
                        "Please edit <tt>%s</tt> in order to configure which links are shown in this snapin."
                    )
                    % (cmk.utils.paths.default_config_dir + "/multisite.mk")
                )
                + "\n"
            )
            return

        def render_list(ids, links):
            n = 0
            for entry in links:
                n += 1
                try:
                    if isinstance(entry[1], type(True)):
                        idss = ids + [str(n)]
                        id_ = "/".join(idss)
                        with foldable_container(
                            treename="customlinks",
                            id_=id_,
                            isopen=entry[1],
                            title=entry[0],
                            icon="foldable_sidebar",
                        ):
                            render_list(idss, entry[2])
                    elif isinstance(entry[1], str):
                        frame = entry[3] if len(entry) > 3 else "main"

                        if len(entry) > 2 and entry[2]:
                            icon_file = entry[2]

                            # Old configs used files named "link_<name>.gif". Those .gif files have
                            # been removed from Checkmk. Replacing such images with the default icon
                            if icon_file.endswith(".gif"):
                                icon_name = "link"
                            else:
                                icon_name = icon_file.rsplit(".", 1)[0].replace("icon_", "")
                        else:
                            icon_name = "link"

                        linktext = html.render_icon(icon_name) + HTML(" ") + escape_html(entry[0])

                        simplelink(linktext, entry[1], frame)
                    else:
                        html.write_text(
                            _("Second part of tuple must be list or string, not %s\n")
                            % str(entry[1])
                        )
                except Exception as e:
                    html.write_text(_("invalid entry %s: %s<br>\n") % (entry, e))

        render_list([], links)
