#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Does not detect the module hierarchy correctly. Imports are fine.
from cmk.gui.i18n import _  # pylint: disable=cmk-module-layer-violation
from cmk.gui.globals import html  # pylint: disable=cmk-module-layer-violation
from cmk.gui.plugins.sidebar import (  # pylint: disable=cmk-module-layer-violation
    SidebarSnapin, snapin_registry,
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

        import imp
        try:
            cma_nav = imp.load_source("cma_nav", "/usr/lib/python2.7/cma_nav.py")
        except IOError:
            html.show_error(_("Unable to import cma_nav module"))
            return

        base_url = "/webconf/"

        self._iconlink(_("Main Menu"), base_url, "home")

        for url, icon, title, _descr in cma_nav.modules():  # type: ignore[attr-defined]
            url = base_url + url
            self._iconlink(title, url, icon)

    # Our version of iconlink -> the images are located elsewhere
    def _iconlink(self, text, url, icon):
        html.open_a(class_=["iconlink", "link"], target="main", href=url)
        html.icon("/webconf/images/icon_%s.png" % icon, cssclass="inline")
        html.write(text)
        html.close_a()
        html.br()
