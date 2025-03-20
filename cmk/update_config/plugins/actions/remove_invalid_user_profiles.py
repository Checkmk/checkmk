#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shutil
from logging import Logger

from cmk.utils import tty
from cmk.utils.paths import profile_dir

from cmk.gui.userdb import load_contacts, load_multisite_users

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class RemoveInvalidUserProfiles(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        """
        In previous versions of checkmk, user profiles were created when invalid login
        attempts were made. These invalid user profiles would then cause raise an exception
        when updating to 2.2.  This action will remove any user profiles that do not correspond
        to a valid user in the system before running the ValidateUserIds action.
        """
        valid_usernames = set(list(load_contacts()) + list(load_multisite_users()))
        user_profile_dirs = {pd.name for pd in profile_dir.iterdir() if pd.is_dir()}
        for invalid_profile_dir in user_profile_dirs - valid_usernames:
            shutil.rmtree(profile_dir / invalid_profile_dir)
            logger.error(
                f"\t{tty.warn} Removed invalid user profile from disk: '{invalid_profile_dir}'{tty.normal}"
            )


update_action_registry.register(
    RemoveInvalidUserProfiles(
        name="remove_invalid_user_profiles_from_disk",
        title="Remove invalid user profiles from disk",
        sort_index=4,  # Must run before ValidateUserIds
        continue_on_failure=False,
    )
)
