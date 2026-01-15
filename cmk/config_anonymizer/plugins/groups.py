#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

from cmk.config_anonymizer.interface import AnonInterface
from cmk.config_anonymizer.step import AnonymizeStep
from cmk.gui.config import Config
from cmk.gui.groups import AllGroupSpecs
from cmk.gui.watolib.groups_io import GroupAliasConfigFile, GroupsConfigFile, load_group_information
from cmk.utils.paths import default_config_dir


def _anonymize_groups(
    all_groups_spec: AllGroupSpecs, anon_interface: AnonInterface
) -> AllGroupSpecs:
    anon_all_groups_spec: AllGroupSpecs = {}
    for group_type, group_specs in all_groups_spec.items():
        match group_type:
            case "host":
                anon_all_groups_spec["host"] = {}
                for group_name, group_spec in group_specs.items():
                    anon_group_name = anon_interface.get_host_group(group_name)
                    anon_all_groups_spec["host"][anon_group_name] = {}
                    for group_spec_key, group_spec_value in group_spec.items():
                        match group_spec_key:
                            case "alias":
                                anon_all_groups_spec["host"][anon_group_name]["alias"] = (
                                    anon_interface.get_host_group_alias(group_spec_value)
                                )
                            case _:
                                raise ValueError(
                                    f"Unknown host group spec {group_spec_key} in {group_specs=}"
                                )
            case "service":
                anon_all_groups_spec["service"] = {}
                for group_name, group_spec in group_specs.items():
                    anon_group_name = anon_interface.get_service_group(group_name)
                    anon_all_groups_spec["service"][anon_group_name] = {}
                    for group_spec_key, group_spec_value in group_spec.items():
                        match group_spec_key:
                            case "alias":
                                anon_all_groups_spec["service"][anon_group_name]["alias"] = (
                                    anon_interface.get_service_group_alias(group_spec_value)
                                )
                            case _:
                                raise ValueError(
                                    f"Unknown service group spec {group_spec_key} in {group_specs=}"
                                )
            case "contact":
                anon_all_groups_spec["contact"] = {}
                for group_name, group_spec in group_specs.items():
                    anon_group_name = (
                        "all"
                        if group_name == "all"
                        else anon_interface.get_contact_group(group_name)
                    )
                    anon_all_groups_spec["contact"][anon_group_name] = {}
                    for group_spec_key, group_spec_value in group_spec.items():
                        match group_spec_key:
                            case "alias":
                                anon_all_groups_spec["contact"][anon_group_name]["alias"] = (
                                    anon_interface.get_contact_group_alias(group_spec_value)
                                )
                            case "inventory_paths":
                                anon_all_groups_spec["contact"][anon_group_name][
                                    "inventory_paths"
                                ] = "allow_all"
                            case "nagvis_maps":
                                anon_all_groups_spec["contact"][anon_group_name]["nagvis_maps"] = [
                                    anon_interface.get_generic_mapping(nagvis_map, "nagvis_map")
                                    for nagvis_map in group_spec_value
                                ]
                            case _:
                                raise ValueError(
                                    f"Unknown contact group spec {group_spec_key}  in {group_specs=}"
                                )

            case _:
                raise ValueError(f"Unknown group type {group_type}")
    return anon_all_groups_spec


class GroupsStep(AnonymizeStep):
    def run(
        self, anon_interface: AnonInterface, active_config: Config, logger: logging.Logger
    ) -> None:
        all_groups_spec = load_group_information()

        anon_all_groups_spec = _anonymize_groups(all_groups_spec, anon_interface)

        anon_config_dir = anon_interface.relative_to_anon_dir(default_config_dir)
        GroupAliasConfigFile(config_dir=anon_config_dir).save_group_aliases(
            anon_all_groups_spec, True
        )
        GroupsConfigFile(config_dir=anon_config_dir).save_group_configs(anon_all_groups_spec, True)


anonymize_step_groups = GroupsStep()
