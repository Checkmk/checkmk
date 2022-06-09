#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Mode for searching hosts"""

from typing import Optional, Type

import cmk.gui.forms as forms
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import make_simple_form_page_menu, PageMenu
from cmk.gui.plugins.wato.utils import configure_attributes, mode_registry
from cmk.gui.plugins.wato.utils.base_modes import redirect, WatoMode
from cmk.gui.type_defs import ActionResult, HTTPVariables, PermissionName
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import TextInput
from cmk.gui.wato.pages.folders import ModeFolder
from cmk.gui.watolib.hosts_and_folders import Folder


@mode_registry.register
class ModeSearch(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "search"

    @classmethod
    def permissions(cls) -> list[PermissionName]:
        return ["hosts"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeFolder

    def __init__(self) -> None:
        super().__init__()
        self._folder = Folder.current()

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Search"),
            breadcrumb,
            form_name="edit_host",
            button_name="_save",
            save_title=_("Submit"),
            save_icon="search",
            save_is_enabled=True,
        )

    def title(self) -> str:
        return _("Search for hosts below %s") % self._folder.title()

    def action(self) -> ActionResult:
        return redirect(
            makeuri_contextless(
                request,
                self._get_search_vars(),
            )
        )

    def _get_search_vars(self) -> HTTPVariables:
        search_vars = {}

        if request.has_var("host_search_host"):
            search_vars["host_search_host"] = request.get_ascii_input_mandatory("host_search_host")

        for varname, value in request.itervars(prefix="host_search_change_"):
            if html.get_checkbox(varname) is False:
                continue

            search_vars[varname] = value

            attr_ident = varname.split("host_search_change_", 1)[1]

            # The URL variable naming scheme is not clear. Try to match with "attr_" prefix
            # and without. We should investigate and clean this up.
            attr_prefix = "host_search_attr_%s" % attr_ident
            search_vars.update(request.itervars(prefix=attr_prefix))
            attr_prefix = "host_search_%s" % attr_ident
            search_vars.update(request.itervars(prefix=attr_prefix))

        for varname, value in request.itervars():
            if varname.startswith(("_", "host_search_")) or varname == "mode":
                continue
            search_vars[varname] = value

        search_vars["mode"] = "folder"

        return list(search_vars.items())

    def page(self) -> None:
        # Show search form
        html.begin_form("edit_host", method="POST")
        html.prevent_password_auto_completion()

        basic_attributes = [
            (
                "host_search_host",
                TextInput(
                    title=_(
                        "Hostname",
                    )
                ),
                "",
            ),
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
