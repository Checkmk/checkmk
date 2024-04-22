#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path
from typing import Any, Mapping

from pydantic import BaseModel

from cmk.utils import paths
from cmk.utils.config_validation_layer.groups import (
    AllGroupSpecs,
    GroupAliasesModel,
    GroupConfigsModel,
    GroupName,
    GroupSpec,
    GroupSpecs,
)
from cmk.utils.config_validation_layer.type_defs import remove_omitted

from cmk.gui.hooks import request_memoize
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoPydanticConfigFile


def load_host_group_information() -> GroupSpecs:
    return load_group_information()["host"]


def load_service_group_information() -> GroupSpecs:
    return load_group_information()["service"]


def load_contact_group_information() -> GroupSpecs:
    return load_group_information()["contact"]


@request_memoize()
def load_group_information() -> AllGroupSpecs:
    aliases = GroupAliasConfigFile().load_for_reading()
    configs = GroupsConfigFile().load_for_reading()

    # Merge information from Checkmk and Multisite worlds together
    return {
        "host": _combine_configs(aliases.define_hostgroups, configs.multisite_hostgroups),
        "service": _combine_configs(aliases.define_servicegroups, configs.multisite_servicegroups),
        "contact": _combine_configs(aliases.define_contactgroups, configs.multisite_contactgroups),
    }


def _get_group_spec(alias: str, config: BaseModel | None) -> GroupSpec:
    spec = GroupSpec(alias=alias)
    if config:
        spec.update(remove_omitted(config.model_dump()))
    return spec


def _combine_configs(
    alias_mapping: dict[GroupName, str],
    config_mapping: Mapping[GroupName, BaseModel],
) -> GroupSpecs:
    return {
        group_id: _get_group_spec(alias, config_mapping.get(group_id))
        for group_id, alias in alias_mapping.items()
    }


def save_group_information(
    all_groups: AllGroupSpecs,
    custom_default_config_dir: str | None = None,
) -> None:
    config_dir = Path(
        custom_default_config_dir if custom_default_config_dir else paths.default_config_dir
    )
    GroupAliasConfigFile(config_dir).save_group_aliases(all_groups)
    GroupsConfigFile(config_dir).save_group_configs(all_groups)

    load_group_information.cache_clear()  # type: ignore[attr-defined]


class GroupAliasConfigFile(WatoPydanticConfigFile[GroupAliasesModel]):

    def __init__(self, config_dir: Path | None = None) -> None:
        if config_dir is None:
            config_dir = Path(paths.default_config_dir)
        super().__init__(
            config_file_path=config_dir / "conf.d" / "wato" / "groups.mk",
            model_class=GroupAliasesModel,
        )

    def save_group_aliases(self, all_groups: AllGroupSpecs) -> None:
        self.validate_and_save(
            {
                f"define_{group_type}groups": {
                    group_id: group_spec["alias"] for group_id, group_spec in groups.items()
                }
                for group_type, groups in all_groups.items()
            }
        )


class GroupsConfigFile(WatoPydanticConfigFile[GroupConfigsModel]):

    def __init__(self, config_dir: Path | None = None) -> None:
        if config_dir is None:
            config_dir = Path(paths.default_config_dir)
        super().__init__(
            config_file_path=config_dir / "multisite.d" / "wato" / "groups.mk",
            model_class=GroupConfigsModel,
        )

    @staticmethod
    def _group_spec_for_configs_file(groups_spec: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in groups_spec.items() if key != "alias"}

    def save_group_configs(self, all_groups: AllGroupSpecs) -> None:
        self.validate_and_save(
            {
                f"multisite_{group_type}groups": {
                    group_id: self._group_spec_for_configs_file(group_spec)
                    for group_id, group_spec in groups.items()
                }
                for group_type, groups in all_groups.items()
            }
        )


def register(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(GroupAliasConfigFile())
    config_file_registry.register(GroupsConfigFile())
