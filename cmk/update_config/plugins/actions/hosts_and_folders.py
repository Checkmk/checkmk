#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from logging import Logger
from typing import Callable, Iterator

from cmk.utils.store.host_storage import ContactgroupName

from cmk.gui.watolib.host_attributes import HostContactGroupSpec
from cmk.gui.watolib.hosts_and_folders import CREFolder, folder_tree, WithAttributes

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState

LegacyContactGroupSpec = tuple[bool, list[ContactgroupName]]


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


def convert_cgroups_from_tuple(
    value: HostContactGroupSpec | LegacyContactGroupSpec,
) -> HostContactGroupSpec:
    """Convert old tuple representation to new dict representation of folder's group settings"""
    if isinstance(value, dict):
        if "use_for_services" in value:
            return value
        return {
            "groups": value["groups"],
            "recurse_perms": value["recurse_perms"],
            "use": value["use"],
            "use_for_services": False,
            "recurse_use": value["recurse_use"],
        }

    return {
        "groups": value[1],
        "recurse_perms": False,
        "use": value[0],
        "use_for_services": False,
        "recurse_use": False,
    }


update_action_registry.register(
    UpdateHostsAndFolders(name="hosts_and_folders", title="Hosts and folders", sort_index=40)
)
