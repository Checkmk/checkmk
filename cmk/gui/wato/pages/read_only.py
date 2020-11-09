#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""WATO can be set into read only mode manually using this mode"""

import time

import cmk.utils.store as store

import cmk.gui.userdb as userdb
import cmk.gui.config as config
import cmk.gui.watolib as watolib
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.page_menu import (
    PageMenu,
    make_simple_form_page_menu,
)

from cmk.gui.valuespec import (
    Tuple,
    FixedValue,
    Alternative,
    ListOf,
    TextAreaUnicode,
    Dictionary,
    AbsoluteDate,
)

from cmk.gui.plugins.wato import (
    WatoMode,
    ActionResult,
    mode_registry,
    flash,
    redirect,
    mode_url,
)


@mode_registry.register
class ModeManageReadOnly(WatoMode):
    @classmethod
    def name(cls):
        return "read_only"

    @classmethod
    def permissions(cls):
        return ["set_read_only"]

    def __init__(self):
        super(ModeManageReadOnly, self).__init__()
        self._settings = config.wato_read_only

    def title(self):
        return _("Manage configuration read only mode")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            breadcrumb,
            form_name="read_only",
            button_name="_save",
        )

    def action(self) -> ActionResult:
        settings = self._vs().from_html_vars("_read_only")
        self._vs().validate_value(settings, "_read_only")
        self._settings = settings

        self._save()
        flash(_("Saved read only settings"))
        return redirect(mode_url("read_only"))

    def _save(self):
        store.save_to_mk_file(watolib.multisite_dir() + "read_only.mk",
                              "wato_read_only",
                              self._settings,
                              pprint_value=config.wato_pprint_config)

    def page(self):
        html.p(
            _("The WATO configuration can be set to read only mode for all users that are not "
              "permitted to ignore the read only mode. All users that are permitted to set the "
              "read only can disable it again when another permitted user enabled it before."))
        html.begin_form("read_only", method="POST")
        self._vs().render_input("_read_only", self._settings)
        html.hidden_fields()
        html.end_form()

    def _vs(self):
        return Dictionary(title=_("Read only mode"),
                          optional_keys=False,
                          render="form",
                          elements=[
                              ("enabled",
                               Alternative(title=_("Enabled"),
                                           elements=[
                                               FixedValue(
                                                   False,
                                                   title=_("Disabled "),
                                                   totext="Not enabled",
                                               ),
                                               FixedValue(
                                                   True,
                                                   title=_("Enabled permanently"),
                                                   totext=_("Enabled until disabling"),
                                               ),
                                               Tuple(title=_("Enabled in time range"),
                                                     elements=[
                                                         AbsoluteDate(
                                                             title=_("Start"),
                                                             include_time=True,
                                                         ),
                                                         AbsoluteDate(
                                                             title=_("Until"),
                                                             include_time=True,
                                                             default_value=time.time() + 3600,
                                                         ),
                                                     ])
                                           ])),
                              ("rw_users",
                               ListOf(
                                   userdb.UserSelection(),
                                   title=_("Can still edit"),
                                   help=_("Users listed here are still allowed to modify things."),
                                   movable=False,
                                   add_label=_("Add user"),
                                   default_value=[config.user.id],
                               )),
                              ("message", TextAreaUnicode(
                                  title=_("Message"),
                                  rows=3,
                              )),
                          ])
