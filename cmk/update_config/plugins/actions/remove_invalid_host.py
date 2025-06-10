#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.ccc.hostaddress import HostName

from cmk.utils.log import VERBOSE

from cmk.gui.config import active_config
from cmk.gui.watolib.check_mk_automations import delete_hosts
from cmk.gui.watolib.hosts_and_folders import FolderTree

from cmk.update_config.registry import update_action_registry, UpdateAction


class RemoveInvalidHost(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        for folder_path, folder in FolderTree().all_folders().items():
            if folder.has_host(HostName("")):
                folder.delete_hosts(
                    [HostName("")],
                    automation=delete_hosts,
                    pprint_value=active_config.wato_pprint_config,
                    debug=active_config.debug,
                )
                logger.log(
                    VERBOSE,
                    f"Deleting host with empty host name from folder {folder.path()}",
                )


update_action_registry.register(
    RemoveInvalidHost(
        name="remove_invalid_host",
        title="Remove invalid host",
        sort_index=155,
    )
)
