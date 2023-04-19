#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from logging import Logger

from cmk.gui.watolib.hosts_and_folders import CREFolder

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState

UNUSED_ATTRIBUTES = [
    "snmp_v3_credentials",  # added by host diagnose page
    "hostname",  # added by host diagnose page
]


class RemoveUnusedHostAttributes(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        touched_folders: list[CREFolder] = []

        for _name, host in CREFolder.root_folder().all_hosts_recursively().items():
            for attribute in UNUSED_ATTRIBUTES:
                logger.debug(f"Rewriting {host.name()}.")
                if host.attribute(attribute):
                    logger.debug(f"Removing attribute: {attribute}")
                    host.remove_attribute(attribute)
                    touched_folders.append(host.folder())

        for folder in touched_folders:
            folder.save_hosts()


update_action_registry.register(
    RemoveUnusedHostAttributes(
        name="unused_host_attribute", title="Remove unused host attributes.", sort_index=40
    )
)
