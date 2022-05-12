#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import subprocess

import cmk.utils.version as cmk_version

from cmk.gui.htmllib.html import html  # pylint: disable=cmk-module-layer-violation

# Does not detect the module hierarchy correctly. Imports are fine.
from cmk.gui.i18n import _  # pylint: disable=cmk-module-layer-violation

from cmk.gui.plugins.sidebar.utils import (  # pylint: disable=cmk-module-layer-violation # isort: skip
    SidebarSnapin,
    snapin_registry,
)


@snapin_registry.register
class SidebarSnapinCMAWebconf(SidebarSnapin):
    @staticmethod
    def type_name():
        return "webconf"

    @classmethod
    def title(cls):
        return _("Checkmk Appliance")

    @classmethod
    def description(cls):
        return _("Access to the Checkmk Appliance Web Configuration")

    @classmethod
    def allowed_roles(cls):
        return ["admin"]

    def show(self):
        if not cmk_version.is_cma():
            return

        # The cma_nav-Module is a Python 2.7 module that is already installed by the CMA OS.  For
        # the future we should change this to some structured file format, but for the moment we
        # have to deal with existing firmwares. Use some py27 wrapper to produce the needed output.
        completed_process = subprocess.run(
            ["/usr/bin/python2.7"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            shell=False,
            close_fds=True,
            input="\n".join(
                [
                    "import imp",
                    'cma_nav = imp.load_source("cma_nav", "/usr/lib/python2.7/cma_nav.py")',
                    "print(cma_nav.modules())",
                ]
            ),
            check=False,
        )

        if completed_process.stderr:
            html.show_error(_("Failed to render navigation: %s") % completed_process.stderr)
            return

        nav_modules = ast.literal_eval(completed_process.stdout)

        base_url = "/webconf/"

        self._iconlink(_("Main Menu"), base_url, "home")

        for url, icon, title, _descr in nav_modules:
            url = base_url + url
            self._iconlink(title, url, icon)

    # Our version of iconlink -> the images are located elsewhere
    def _iconlink(self, text, url, icon):
        html.open_a(class_=["iconlink", "link"], target="main", href=url)
        html.icon("/webconf/images/icon_%s.png" % icon, cssclass="inline")
        html.write_text(text)
        html.close_a()
        html.br()
