#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from logging import Logger
from typing import Callable, Iterator

from cmk.gui.watolib.hosts_and_folders import CREFolder, folder_tree, WithAttributes
from cmk.gui.watolib.utils import convert_cgroups_from_tuple

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class UpdateHostsAndFolders(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        save_handlers = replace_legacy_contact_groups(folder_tree().root_folder())

        for handler in save_handlers:
            handler()


def replace_legacy_contact_groups(root_folder: CREFolder) -> Iterator[Callable[[], None]]:
    def replace_contact_groups(obj: WithAttributes) -> bool:
        if obj.has_explicit_attribute("contactgroups"):
            old_value = obj.attribute("contactgroups")
            new_value = convert_cgroups_from_tuple(obj.attribute("contactgroups"))
            if new_value != old_value:
                obj.set_attribute("contactgroups", new_value)
                return True
        return False

    for folder in [root_folder] + root_folder.subfolders_recursively():
        if replace_contact_groups(folder):
            yield folder.save

        replaced_hosts = [replace_contact_groups(host) for host in folder.hosts().values()]
        if any(replaced_hosts):
            yield folder.save_hosts


update_action_registry.register(
    UpdateHostsAndFolders(name="hosts_and_folders", title="Hosts and folders", sort_index=40)
)
