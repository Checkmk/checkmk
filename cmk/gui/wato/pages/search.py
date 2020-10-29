#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Mode for searching hosts"""

from typing import Optional, Type

import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
from cmk.gui.valuespec import TextAscii

from cmk.gui.plugins.wato.utils import mode_registry, configure_attributes
from cmk.gui.plugins.wato.utils.base_modes import WatoMode, ActionResult
from cmk.gui.wato.pages.folders import ModeFolder
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.page_menu import (
    PageMenu,
    make_simple_form_page_menu,
)

from cmk.gui.globals import html
from cmk.gui.i18n import _


@mode_registry.register
class ModeSearch(WatoMode):
    @classmethod
    def name(cls):
        return "search"

    @classmethod
    def permissions(cls):
        return ["hosts"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeFolder

    def __init__(self):
        super(ModeSearch, self).__init__()
        self._folder = watolib.Folder.current()

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(breadcrumb,
                                          form_name="edit_host",
                                          button_name="_local",
                                          save_title=_("Search"),
                                          save_icon="search",
                                          save_is_enabled=True)

    def title(self):
        return _("Search for hosts below %s") % self._folder.title()

    def action(self) -> ActionResult:
        self._remove_unused_search_vars()
        return "folder"

    def _remove_unused_search_vars(self):
        """Reduce the HTTP vars (html.request.vars) to the amount of necessary attributes

        The form submits all variables which may result in a too big collection for being
        used as URL variables. Once we are here we can analyze the attribute checkboxes and
        remove all HTTP variables that are related to not checked checkboxes for preventing
        the too long URLs.
        """
        keep_vars = {}

        if html.request.has_var("host_search_host"):
            keep_vars["host_search_host"] = html.request.get_ascii_input_mandatory(
                "host_search_host")

        for varname, value in html.request.itervars(prefix="host_search_change_"):
            if html.get_checkbox(varname) is False:
                continue

            keep_vars[varname] = value

            attr_ident = varname.split("host_search_change_", 1)[1]

            # The URL variable naming scheme is not clear. Try to match with "attr_" prefix
            # and without. We should investigate and clean this up.
            attr_prefix = "host_search_attr_%s" % attr_ident
            keep_vars.update(html.request.itervars(prefix=attr_prefix))
            attr_prefix = "host_search_%s" % attr_ident
            keep_vars.update(html.request.itervars(prefix=attr_prefix))

        html.request.del_vars("host_search_")
        for varname, value in keep_vars.items():
            html.request.set_var(varname, value)

    def page(self):
        # Show search form
        html.begin_form("edit_host", method="POST")
        html.prevent_password_auto_completion()

        basic_attributes = [
            ("host_search_host", TextAscii(title=_("Hostname",)), ""),
        ]
        html.set_focus("host_search_host")

        # Attributes
        configure_attributes(
            new=False,
            hosts={},
            for_what="host_search",
            parent=None,
            varprefix="host_search_",
            basic_attributes=basic_attributes,
        )

        forms.end()
        html.hidden_field("host_search", "1")
        html.hidden_fields()
        html.end_form()
