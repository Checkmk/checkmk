#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from logging import Logger
from typing import override

from cmk.ccc.site import get_omd_config
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.paths import omd_root


class UpdateCoreConfig(UpdateAction):
    """Ensure we have a fresh Micro Core config after all update actions were executed"""

    @override
    def __call__(self, logger: Logger) -> None:
        if get_omd_config(omd_root)["CONFIG_CORE"] == "none":
            return  # No core config is needed in this case
        subprocess.check_call(["cmk", "-U"], shell=False)


update_action_registry.register(
    UpdateCoreConfig(
        name="update_core_config",
        title="Update core config",
        sort_index=999,  # Run at the end
    )
)
