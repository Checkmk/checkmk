#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error,unused-import
else:
    from pathlib2 import Path  # pylint: disable=import-error,unused-import

import cmk.gui.config as config
import cmk.gui.userdb as userdb
from cmk.gui.watolib.simple_config_file import WatoSimpleConfigFile
from cmk.gui.watolib.utils import wato_root_dir


class PasswordStore(WatoSimpleConfigFile):
    def __init__(self):
        super(PasswordStore, self).__init__(config_file_path=Path(wato_root_dir()) / "passwords.mk",
                                            config_variable="stored_passwords")

    def filter_usable_entries(self, entries):
        if config.user.may("wato.edit_all_passwords"):
            return entries

        user_groups = userdb.contactgroups_of_user(config.user.id)

        passwords = self.filter_editable_entries(entries)
        passwords.update(
            dict([(k, v) for k, v in entries.items() if v["shared_with"] in user_groups]))
        return passwords

    def filter_editable_entries(self, entries):
        if config.user.may("wato.edit_all_passwords"):
            return entries

        user_groups = userdb.contactgroups_of_user(config.user.id)
        return dict([(k, v) for k, v in entries.items() if v["owned_by"] in user_groups])
