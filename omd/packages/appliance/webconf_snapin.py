#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
import subprocess
from pathlib import Path

import cmk.ccc.version as cmk_version

from cmk.gui.htmllib.html import html  # pylint: disable=cmk-module-layer-violation

# Does not detect the module hierarchy correctly. Imports are fine.
from cmk.gui.i18n import _  # pylint: disable=cmk-module-layer-violation
from cmk.gui.sidebar import (  # pylint: disable=cmk-module-layer-violation
    SidebarSnapin,
    snapin_registry,
)


def nav_modules_path() -> Path:
    return Path("/usr/share/cma/webconf/nav_modules")


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
    def allowed_roles(cls) -> list[str]:
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

    def _load_nav_modules(self) -> list[dict[str, str]]:
        """Since CMA 1.5.6 the navigation items are stored in a JSON file"""
        if nav_modules_path().exists():
            return self._load_nav_modules_from_json()
        return self._load_nav_modules_from_old_firmware()

    def _load_nav_modules_from_json(self) -> list[dict[str, str]]:
        modules = []
        for file_path in sorted(nav_modules_path().glob("*.json")):
            modules += json.loads(file_path.read_text())
        return modules

    def _load_nav_modules_from_old_firmware(self) -> list[dict[str, str]]:
        """Keep this for compatibility with older Appliance versions

        The cma_nav-Module was a Python 2.7 module that is globally deployed by the CMA firmware.
        With the Python 3 migration of the appliance (with version 1.5.6) we have changed that to a
        declarative file (see nav_modules_path()).

        This can be replaced with an simple incompatibility warning message with Checkmk 2.3.
        """
        # The cma_nav-Module is a Python 2.7 module that is already installed by the CMA OS.  For
        # the future we should change this to some structured file format, but for the moment we
        # have to deal with existing firmwares. Use some py27 wrapper to produce the needed output.
        completed_process = subprocess.run(
            ["/usr/bin/python2.7"],
            capture_output=True,
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
            return []

        return [
            {"page": e[0], "icon": e[1], "title": e[2], "help": e[3]}
            for e in ast.literal_eval(completed_process.stdout)
        ]

    # Our version of iconlink -> the images are located elsewhere
    def _iconlink(self, text: str, url: str, icon: str) -> None:
        html.open_a(class_=["iconlink", "link"], target="main", href=url)
        html.icon("/webconf/images/icon_%s.png" % icon, cssclass="inline")
        html.write_text_permissive(text)
        html.close_a()
        html.br()


snapin_registry.register(SidebarSnapinCMAWebconf)
