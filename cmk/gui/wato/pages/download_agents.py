#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Simple download page for the builtin agents and plugins"""

import os
import glob
import sys

from typing import (  # pylint: disable=unused-import
    List, Dict, Text, Optional,
)
import six

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path

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

        self._download_table(_("Packaged Agents"), {}, packed)

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

        file_titles = {}
        other_sections = []
        for root, _dirs, files in os.walk(cmk.utils.paths.agents_dir):
            file_paths = []
            relpath = root.split('agents')[1]
            if relpath not in banned_paths:
                title = titles.get(relpath, relpath)
                for filename in files:
                    if filename == "CONTENTS":
                        file_titles.update(self._read_agent_contents_file(root))

                    path = root + '/' + filename
                    if path not in packed and 'deprecated' not in path:
                        file_paths.append(path)

                other_sections.append((title, file_paths))

        for title, file_paths in sorted(other_sections):
            useful_file_paths = [
                p for p in file_paths
                if file_titles.get(p, "") is not None and not p.endswith("/CONTENTS")
            ]
            file_titles.update(self._read_plugin_inline_comments(useful_file_paths))
            if useful_file_paths:
                self._download_table(title, file_titles, sorted(useful_file_paths))
        html.close_div()

    def _download_table(self, title, file_titles, paths):
        # type: (Text, Dict[str, Optional[Text]], List[str]) -> None
        forms.header(title)
        forms.container()
        for path in paths:
            os_path = path
            relpath = path.replace(cmk.utils.paths.agents_dir + '/', '')
            filename = path.split('/')[-1]
            title = file_titles.get(os_path, filename) or u""

            file_size = os.stat(os_path).st_size

            # FIXME: Rename classes etc. to something generic
            html.open_div(class_="ruleset")
            html.open_div(style="width:300px;", class_="text")
            html.a(title, href="agents/%s" % relpath)
            html.span("." * 200, class_="dots")
            html.close_div()
            html.div(cmk.utils.render.fmt_bytes(file_size), style="width:60px;", class_="rulecount")
            html.close_div()
            html.close_div()
        forms.end()

    def _read_plugin_inline_comments(self, file_paths):
        # type: (List[str]) -> Dict[str, Optional[Text]]
        comment_prefixes = ["# ", "REM ", "$!# "]
        windows_bom = b"\xef\xbb\xbf"
        file_titles = {}  # type: Dict[str, Optional[Text]]
        for path in file_paths:
            with open(path, "rb") as f:
                first_bytes = f.read(500)

            if first_bytes.startswith(windows_bom):
                first_bytes = first_bytes[len(windows_bom):]

            first_lines = six.ensure_text(first_bytes).splitlines()
            for line in first_lines:
                for prefix in comment_prefixes:
                    if line.startswith(prefix) and len(line) > len(prefix) and line[len(
                            prefix)].isalpha():
                        file_titles[path] = line[len(prefix):].strip()
                        break
                if path in file_titles:
                    break
        return file_titles

    def _read_agent_contents_file(self, root):
        # type: (str) -> Dict[str, Optional[Text]]
        file_titles = {}  # type: Dict[str, Optional[Text]]
        with Path(root, "CONTENTS").open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    file_name, title = line.split(None, 1)
                    if title == "(hide)":
                        file_titles[root + "/" + file_name] = None
                    else:
                        file_titles[root + "/" + file_name] = title
        return file_titles
