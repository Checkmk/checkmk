#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Any

import cmk.gui.userdb as userdb
from cmk.gui.logged_in import user
from cmk.gui.watolib.simple_config_file import WatoSimpleConfigFile
from cmk.gui.watolib.utils import wato_root_dir

# TODO: Next replace with TypedDict
PredefinedConditionSpec = dict[str, Any]


class PredefinedConditionStore(WatoSimpleConfigFile[PredefinedConditionSpec]):
    def __init__(self) -> None:
        super().__init__(
            config_file_path=Path(wato_root_dir()) / "predefined_conditions.mk",
            config_variable="predefined_conditions",
        )

    def filter_usable_entries(self, entries):
        if user.may("wato.edit_all_predefined_conditions"):
            return entries

        assert user.id is not None
        user_groups = userdb.contactgroups_of_user(user.id)

        entries = self.filter_editable_entries(entries)
        entries.update({k: v for k, v in entries.items() if v["shared_with"] in user_groups})
        return entries

    def filter_editable_entries(self, entries):
        if user.may("wato.edit_all_predefined_conditions"):
            return entries

        assert user.id is not None
        user_groups = userdb.contactgroups_of_user(user.id)
        return {k: v for k, v in entries.items() if v["owned_by"] in user_groups}

    def choices(self):
        return [
            (ident, entry["title"])
            for ident, entry in self.filter_usable_entries(self.load_for_reading()).items()
        ]
