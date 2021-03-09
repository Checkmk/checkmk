#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""WATO can be set into read only mode manually using this mode"""

import time

import cmk.utils.store as store

import cmk.gui.userdb as userdb
import cmk.gui.config as config
import cmk.gui.watolib as watolib
from cmk.gui.i18n import _
from cmk.gui.globals import html

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
    mode_registry,
    global_buttons,
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

    def buttons(self):
        global_buttons()
        html.context_button(_("Back"), watolib.folder_preserving_link([("mode", "globalvars")]),
                            "back")

    def action(self):
        settings = self._vs().from_html_vars("_read_only")
        self._vs().validate_value(settings, "_read_only")
        self._settings = settings

        self._save()

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
        html.button('_save', _('Save'), 'submit')
        html.hidden_fields()
        html.end_form()

    def _vs(self):
        return Dictionary(title=_("Read only mode"),
                          optional_keys=False,
                          render="form",
                          elements=[
                              ("enabled",
                               Alternative(title=_("Enabled"),
                                           style="dropdown",
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
