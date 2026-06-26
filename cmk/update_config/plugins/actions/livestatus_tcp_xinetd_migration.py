#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from shutil import copy2
from typing import override

from cmk.ccc.site import omd_site
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.lib.livestatus_tcp_xinetd_migration import (
    xinetd_has_local_modifications,
)
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.paths import omd_root


class CleanUpLivestatusXinetdConf(UpdateAction):
    @override
    def __call__(
        self, logger: Logger, site_root: Path | None = None, site_id: str | None = None
    ) -> None:
        if site_root is None:
            site_root = Path(omd_root)
        if site_id is None:
            site_id = omd_site()

        deprecated_xinetd_config_file = site_root / "etc/mk-livestatus/xinetd.conf"
        if xinetd_has_local_modifications(site_root, site_id):
            # Xinetd has local modifications but since we
            # passed the PreAction the user confirmed this is ok
            # Creating a backup just in case.
            deprecated_xinetd_config_file_backup = site_root / "etc/mk-livestatus/xinetd.conf.bak"
            copy2(deprecated_xinetd_config_file, deprecated_xinetd_config_file_backup)
            logger.info(
                "Local modifications to xinetd config detected. Creating backup at %s",
                deprecated_xinetd_config_file_backup,
            )

        # Both deprecated files can now be safely removed.
        (site_root / "etc/mk-livestatus/xinetd.conf").unlink(missing_ok=True)
        (site_root / "etc/xinetd.d/mk-livestatus").unlink(missing_ok=True)


action = CleanUpLivestatusXinetdConf(
    name="clean_up_livestatus_xinetd_conf",
    title="Clean up old Livestatus xinetd Configuration",
    sort_index=1,
    expiry_version=ExpiryVersion.CMK_310,
)
update_action_registry.register(action)
