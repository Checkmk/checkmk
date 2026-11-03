#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Re-save the conf.d files every edition writes that extend variables they never define

See cmk.update_config.plugins.lib.selfbootstrap_conf_d_files.
"""

from collections.abc import Sequence

from cmk.gui.oauth2_connections.watolib.store import OAuth2ConnectionsConfigFile
from cmk.gui.watolib.groups_io import GroupAliasConfigFile
from cmk.gui.watolib.notifications import (
    NotificationParameterConfigFile,
    NotificationRuleConfigFile,
)
from cmk.gui.watolib.password_store import PasswordStore
from cmk.gui.watolib.predefined_conditions import PredefinedConditionStore
from cmk.gui.watolib.tag_config_file import TagConfigFile
from cmk.gui.watolib.timeperiods import TimePeriodsConfigFile
from cmk.gui.watolib.users import ContactsConfigFile
from cmk.gui.watolib.utils import multisite_dir
from cmk.update_config.internal import ExpiryVersion
from cmk.update_config.plugins.lib.selfbootstrap_conf_d_files import (
    ExtendOnlyFile,
    resave_config_file,
    SelfbootstrapConfDFiles,
)
from cmk.update_config.registry import update_action_registry


def _resave_tags(pprint_value: bool) -> None:
    # TagConfigFile reads the GUI copy and writes both files; without the GUI copy it would
    # replace the base file by an empty tag config.
    if not (gui_tags := multisite_dir() / "tags.mk").exists():
        raise FileNotFoundError(f"{gui_tags} is missing, cannot regenerate the base tags file")
    config_file = TagConfigFile()
    config_file.save(config_file.load_for_modification(), pprint_value)


def _resave_passwords(pprint_value: bool) -> None:
    # The merged password file is written by the core config update at the end of the update.
    store = PasswordStore()
    store.save(store.load_for_modification(), pprint_value, update_merged_file=False)


COMMUNITY_EXTEND_ONLY_FILES: Sequence[ExtendOnlyFile] = (
    resave_config_file("contacts.mk", ContactsConfigFile),
    ExtendOnlyFile(name="tags.mk", resave=_resave_tags),
    resave_config_file("groups.mk", GroupAliasConfigFile),
    resave_config_file("notifications.mk", NotificationRuleConfigFile),
    resave_config_file("notification_parameter.mk", NotificationParameterConfigFile),
    ExtendOnlyFile(name="passwords.mk", resave=_resave_passwords),
    resave_config_file("timeperiods.mk", TimePeriodsConfigFile),
    resave_config_file("predefined_conditions.mk", PredefinedConditionStore),
    resave_config_file("oauth2_connections.mk", OAuth2ConnectionsConfigFile),
)
"""The files written below conf.d/wato by every edition"""


update_action_registry.register(
    SelfbootstrapConfDFiles(
        name="selfbootstrap_conf_d_files",
        title="Make the generated conf.d files define their variables",
        sort_index=31,
        files=COMMUNITY_EXTEND_ONLY_FILES,
        expiry_version=ExpiryVersion.CMK_310,
    )
)
