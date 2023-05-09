#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

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

        assert config.user.id is not None
        user_groups = userdb.contactgroups_of_user(config.user.id)

        entries = self.filter_editable_entries(entries)
        entries.update({k: v for k, v in entries.items() if v["shared_with"] in user_groups})
        return entries

    def filter_editable_entries(self, entries):
        if config.user.may("wato.edit_all_predefined_conditions"):
            return entries

        assert config.user.id is not None
        user_groups = userdb.contactgroups_of_user(config.user.id)
        return {k: v for k, v in entries.items() if v["owned_by"] in user_groups}

    def choices(self):
        return [(ident, entry["title"])
                for ident, entry in self.filter_usable_entries(self.load_for_reading()).items()]
