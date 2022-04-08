#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
import subprocess
from pathlib import Path
from typing import Dict, List

import cmk.utils.version as cmk_version

from cmk.gui.globals import html  # pylint: disable=cmk-module-layer-violation

# Does not detect the module hierarchy correctly. Imports are fine.
from cmk.gui.i18n import _  # pylint: disable=cmk-module-layer-violation

from cmk.gui.plugins.sidebar.utils import (  # pylint: disable=cmk-module-layer-violation # isort: skip
    SidebarSnapin,
    snapin_registry,
)


def nav_modules_path() -> Path:
    return Path("/usr/share/cma/webconf/nav_modules")


@snapin_registry.register
class SidebarSnapinCMAWebconf(SidebarSnapin):
    @staticmethod
    def type_name() -> str:
        return "webconf"

    @classmethod
    def title(cls) -> str:
        return _("Checkmk Appliance")

    @classmethod
    def description(cls) -> str:
        return _("Access to the Checkmk Appliance Web Configuration")

    @classmethod
    def allowed_roles(cls) -> List[str]:
        return ["admin"]

    def show(self) -> None:
        if not cmk_version.is_cma():
            return

        base_url = "/webconf/"

        self._iconlink(_("Main Menu"), base_url, "home")

        try:
            nav_modules = self._load_nav_modules()
        except RuntimeError as e:
            html.show_error(str(e))
            return

        for module in nav_modules:
            url = base_url + module["page"]
            self._iconlink(module["title"], url, module["icon"])

    def _load_nav_modules(self) -> List[Dict[str, str]]:
        """Since CMA 1.5.6 the navigation items are stored in a JSON file"""
        if nav_modules_path().exists():
            return self._load_nav_modules_from_json()
        return self._load_nav_modules_from_old_firmware()

    def _load_nav_modules_from_json(self) -> List[Dict[str, str]]:
        modules = []
        for file_path in sorted(nav_modules_path().glob("*.json")):
            modules += json.loads(file_path.read_text())
        return modules

    def _load_nav_modules_from_old_firmware(self) -> List[Dict[str, str]]:
        """Keep this for compatibility with older Appliance versions

        The cma_nav-Module was a Python 2.7 module that is globally deployed by the CMA firmware.
        With the Python 3 migration of the appliance (with version 1.5.6) we have changed that to a
        declarative file (see nav_modules_path()).

        This can be replaced with an simple incompatibility warning message with Checkmk 2.3.
        """
        p = subprocess.Popen(  # pylint:disable=consider-using-with
            ["/usr/bin/python2.7"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            shell=False,
            close_fds=True,
        )
        stdout, stderr = p.communicate(
            "\n".join(
                [
                    "import imp",
                    'cma_nav = imp.load_source("cma_nav", "/usr/lib/python2.7/cma_nav.py")',
                    "print(cma_nav.modules())",
                ]
            )
        )

        if stderr:
            raise RuntimeError(_("Failed to render navigation: %s") % stderr)
        return [
            {"page": e[0], "icon": e[1], "title": e[2], "help": e[3]}
            for e in ast.literal_eval(stdout)
        ]

    # Our version of iconlink -> the images are located elsewhere
    def _iconlink(self, text: str, url: str, icon: str) -> None:
        html.open_a(class_=["iconlink", "link"], target="main", href=url)
        html.icon("/webconf/images/icon_%s.png" % icon, cssclass="inline")
        html.write_text(text)
        html.close_a()
        html.br()
