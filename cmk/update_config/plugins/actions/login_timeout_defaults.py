#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.gui.watolib.global_settings import load_configuration_settings, save_global_settings_raw
from cmk.update_config.internal import ExpiryVersion, UpdateAction
from cmk.update_config.registry import update_action_registry


class UpdateLoginTimeoutDefaults(UpdateAction):
    """
    In 3.0 we are adding user timeout on failed authentication but still allowing full lockout.
    We are setting timeout to be our default and disabling lockout, however for existing sites
    that are updating from 2.5 we will keep lockout enabled and disable timeout to not change
    how clients sites already work.
    """

    @override
    def __call__(self, logger: Logger) -> None:
        updated_global_settings = dict(load_configuration_settings(full_config=True))
        if "timeout_on_logon_failures" not in updated_global_settings:
            updated_global_settings["timeout_on_logon_failures"] = False
            save_global_settings_raw(updated_global_settings)


update_action_registry.register(
    UpdateLoginTimeoutDefaults(
        name="update_login_timeout_defaults",
        title="Preserve logon-failure lockout/timeout behavior across upgrade",
        sort_index=100,  # should not matter
        expiry_version=ExpiryVersion.CMK_310,
    )
)
