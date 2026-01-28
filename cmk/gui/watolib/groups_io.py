#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast, Literal, NotRequired, TypedDict

from cmk.utils import paths

from cmk.gui.groups import AllGroupSpecs, GroupName, GroupSpec, GroupSpecs, GroupType
from cmk.gui.hooks import request_memoize
from cmk.gui.sites import live
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoMultiConfigFile

NothingOrChoices = Literal["nothing"] | tuple[Literal["choices"], Sequence[str]]


class PermittedPath(TypedDict):
    visible_raw_path: str
    attributes: NotRequired[NothingOrChoices]
    columns: NotRequired[NothingOrChoices]
    nodes: NotRequired[NothingOrChoices]


InventoryPaths = Literal["allow_all", "forbid_all"] | tuple[Literal["paths"], list[PermittedPath]]


class GroupAliases(TypedDict):
    define_hostgroups: dict[GroupName, str]
    define_servicegroups: dict[GroupName, str]
    define_contactgroups: dict[GroupName, str]


class GroupConfig(TypedDict):
    customer: NotRequired[str | None]


class ContactGroupConfig(GroupConfig):
    inventory_paths: NotRequired[InventoryPaths]
    nagvis_maps: NotRequired[list[str]]


class GroupConfigs(TypedDict):
    multisite_hostgroups: dict[GroupName, GroupConfig]
    multisite_servicegroups: dict[GroupName, GroupConfig]
    multisite_contactgroups: dict[GroupName, ContactGroupConfig]


def all_groups(group_type: GroupType) -> list[tuple[str, str]]:
    """Returns a list of host/service/contact groups (pairs of name/alias)

    Groups are collected via livestatus from all sites. In case no alias is defined
    the name is used as second element. The list is sorted by lower case alias in the first place.
    """
    query = "GET %sgroups\nCache: reload\nColumns: name alias\n" % group_type
    groups = cast(list[tuple[str, str]], live().query(query))
    all_groups = load_group_information()[group_type]

    def _compute_alias(name: str, alias: str) -> str:
        if (group := all_groups.get(name)) and (alias_from_group := group.get("alias")):
            return alias_from_group
        return alias or name

    # The dict() removes duplicate group names. Aliases don't need be deduplicated.
    return sorted(
        [(name, _compute_alias(name, alias)) for name, alias in dict(groups).items()],
        key=lambda e: e[1].lower(),
    )


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
        "host": _combine_configs(aliases["define_hostgroups"], configs["multisite_hostgroups"]),
        "service": _combine_configs(
            aliases["define_servicegroups"], configs["multisite_servicegroups"]
        ),
        "contact": _combine_configs(
            aliases["define_contactgroups"], configs["multisite_contactgroups"]
        ),
    }


def _get_group_spec(alias: str, config: GroupConfig | None) -> GroupSpec:
    spec: GroupSpec = GroupSpec(alias=alias)
    if config:
        spec.update(config)
    return spec


def _combine_configs(
    alias_mapping: dict[GroupName, str],
    config_mapping: Mapping[GroupName, GroupConfig],
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


class GroupAliasConfigFile(WatoMultiConfigFile[GroupAliases]):
    def __init__(self, config_dir: Path | None = None) -> None:
        if config_dir is None:
            config_dir = Path(paths.default_config_dir)
        super().__init__(
            config_file_path=config_dir / "conf.d" / "wato" / "groups.mk",
            spec_class=GroupAliases,
            load_default=lambda: GroupAliases(
                define_hostgroups={}, define_servicegroups={}, define_contactgroups={}
            ),
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


class GroupsConfigFile(WatoMultiConfigFile[GroupConfigs]):
    def __init__(self, config_dir: Path | None = None) -> None:
        if config_dir is None:
            config_dir = Path(paths.default_config_dir)
        super().__init__(
            config_file_path=config_dir / "multisite.d" / "wato" / "groups.mk",
            spec_class=GroupConfigs,
            load_default=lambda: GroupConfigs(
                multisite_hostgroups={}, multisite_servicegroups={}, multisite_contactgroups={}
            ),
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
