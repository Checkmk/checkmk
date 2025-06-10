#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.utils.hostaddress import HostName
from cmk.utils.log import VERBOSE

from cmk.gui.watolib.check_mk_automations import delete_hosts
from cmk.gui.watolib.hosts_and_folders import FolderTree

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class RemoveInvalidHost(UpdateAction):
    @override
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        for _folder_path, folder in FolderTree().all_folders().items():
            if folder.has_host(HostName("")):
                folder.delete_hosts(
                    [HostName("")],
                    automation=delete_hosts,
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
