#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Simple download page for the builtin agents and plugins"""

import os
import glob

from typing import (  # pylint: disable=unused-import
    List, Text,
)

import cmk.utils.paths
import cmk.utils.render

import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
from cmk.gui.i18n import _
from cmk.gui.globals import html

from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
    global_buttons,
)


@mode_registry.register
class ModeDownloadAgents(WatoMode):
    @classmethod
    def name(cls):
        # type: () -> str
        return "download_agents"

    @classmethod
    def permissions(cls):
        # type: () -> List[str]
        return ["download_agents"]

    def title(self):
        # type: () -> Text
        return _("Agents and Plugins")

    def buttons(self):
        # type: () -> None
        global_buttons()
        if watolib.has_agent_bakery():
            html.context_button(_("Baked agents"),
                                watolib.folder_preserving_link([("mode", "agents")]),
                                "download_agents")
        html.context_button(_("Release Notes"), "version.py", "mk")

    def page(self):
        # type: () -> None
        html.open_div(class_="rulesets")
        packed = glob.glob(cmk.utils.paths.agents_dir + "/*.deb") \
                + glob.glob(cmk.utils.paths.agents_dir + "/*.rpm") \
                + glob.glob(cmk.utils.paths.agents_dir + "/windows/c*.msi")

        self._download_table(_("Packaged Agents"), packed)

        titles = {
            '': _('Linux/Unix Agents'),
            '/plugins': _('Linux/Unix Agents - Plugins'),
            '/cfg_examples': _('Linux/Unix Agents - Example Configurations'),
            '/cfg_examples/systemd': _('Linux Agent - Example configuration using with systemd'),
            '/windows': _('Windows Agent'),
            '/windows/plugins': _('Windows Agent - Plugins'),
            '/windows/mrpe': _('Windows Agent - MRPE Scripts'),
            '/windows/cfg_examples': _('Windows Agent - Example Configurations'),
            '/windows/ohm': _('Windows Agent - OpenHardwareMonitor (headless)'),
            '/z_os': _('z/OS'),
            '/sap': _('SAP R/3'),
        }

        banned_paths = [
            '/bakery',
            '/special',
            '/windows/msibuild',
            '/windows/msibuild/patches',
            '/windows/sections',
        ]

        other_sections = []
        for root, _dirs, files in os.walk(cmk.utils.paths.agents_dir):
            file_paths = []
            relpath = root.split('agents')[1]
            if relpath not in banned_paths:
                title = titles.get(relpath, relpath)
                for filename in files:
                    path = root + '/' + filename
                    if path not in packed and 'deprecated' not in path:
                        file_paths.append(path)

                other_sections.append((title, file_paths))

        for title, file_paths in sorted(other_sections):
            useful_file_paths = [p for p in file_paths if not p.endswith("/CONTENTS")]
            if useful_file_paths:
                self._download_table(title, sorted(useful_file_paths))
        html.close_div()

    def _download_table(self, title, paths):
        # type: (Text, List[str]) -> None
        forms.header(title)
        forms.container()
        for path in paths:
            os_path = path
            relpath = path.replace(cmk.utils.paths.agents_dir + '/', '')
            filename = path.split('/')[-1]

            file_size = os.stat(os_path).st_size

            # FIXME: Rename classes etc. to something generic
            html.open_div(class_="ruleset")
            html.open_div(style="width:300px;", class_="text")
            html.a(filename, href="agents/%s" % relpath)
            html.span("." * 200, class_="dots")
            html.close_div()
            html.div(cmk.utils.render.fmt_bytes(file_size), style="width:60px;", class_="rulecount")
            html.close_div()
            html.close_div()
        forms.end()
