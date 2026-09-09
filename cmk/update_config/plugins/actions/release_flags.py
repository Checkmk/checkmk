#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.gui.release_flags.global_config import ConfigDomainReleaseFlags
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction


class UpdateReleaseFlags(UpdateAction):
    """Drop flags from release_flag.json that are no longer declared.

    ReleaseFlagConfig has extra="ignore", so loading drops unknown keys.
    Saving what was loaded rewrites the file without them.
    """

    @override
    def __call__(self, logger: Logger) -> None:
        domain = ConfigDomainReleaseFlags()
        if not domain.config_file(site_specific=False).exists():
            return
        domain.save(domain.load_full_config())


update_action_registry.register(
    UpdateReleaseFlags(
        name="release_flags",
        title="Release flags: Remove flags that no longer exist",
        sort_index=100,  # can run whenever
        expiry_version=ExpiryVersion.NEVER,
    )
)
