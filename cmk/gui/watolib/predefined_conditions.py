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

from pathlib2 import Path

import cmk.gui.config as config
import cmk.gui.userdb as userdb
from cmk.gui.watolib.simple_config_file import WatoSimpleConfigFile
from cmk.gui.watolib.utils import wato_root_dir


class PredefinedConditionStore(WatoSimpleConfigFile):
    def __init__(self):
        super(PredefinedConditionStore,
              self).__init__(config_file_path=Path(wato_root_dir()) / "predefined_conditions.mk",
                             config_variable="predefined_conditions")

    def filter_usable_entries(self, entries):
        if config.user.may("wato.edit_all_predefined_conditions"):
            return entries

        user_groups = userdb.contactgroups_of_user(config.user.id)

        entries = self.filter_editable_entries(entries)
        entries.update(dict([(k, v) for k, v in entries.items() if v["shared_with"] in user_groups
                            ]))
        return entries

    def filter_editable_entries(self, entries):
        if config.user.may("wato.edit_all_predefined_conditions"):
            return entries

        user_groups = userdb.contactgroups_of_user(config.user.id)
        return dict([(k, v) for k, v in entries.items() if v["owned_by"] in user_groups])

    def choices(self):
        return [(ident, entry["title"])
                for ident, entry in self.filter_usable_entries(self.load_for_reading()).items()]
