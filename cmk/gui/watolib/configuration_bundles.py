#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from pathlib import Path
from typing import (
    Callable,
    get_args,
    Iterable,
    Literal,
    Mapping,
    NewType,
    NotRequired,
    Sequence,
    TypedDict,
    TypeVar,
)

from cmk.utils.global_ident_type import GlobalIdent, PROGRAM_ID_QUICK_SETUP
from cmk.utils.password_store import Password
from cmk.utils.rulesets.definition import RuleGroupType

from cmk.gui.watolib.hosts_and_folders import Folder, Host
from cmk.gui.watolib.passwords import load_passwords
from cmk.gui.watolib.rulesets import AllRulesets, Rule
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSingleConfigFile
from cmk.gui.watolib.utils import multisite_dir

_T = TypeVar("_T")
BundleId = NewType("BundleId", str)
IDENT_FINDER = Callable[[GlobalIdent | None], BundleId | None]
ENTITIES = Literal["host", "rule", "password", "dcd"]
ALL_ENTITIES: set[ENTITIES] = set(get_args(ENTITIES))
BUNDLE_DOMAINS: Mapping[RuleGroupType, set[ENTITIES]] = {
    RuleGroupType.SPECIAL_AGENTS: {"host", "rule", "password", "dcd"}
}


def _get_affected_entities(bundle_group: str) -> set[ENTITIES]:
    rule_group_type = RuleGroupType(bundle_group.split(":", maxsplit=1)[0])
    return BUNDLE_DOMAINS.get(rule_group_type, ALL_ENTITIES)


@dataclass
class BundleReferences:
    # TODO: introduce dcd
    hosts: Sequence[Host] | None = None
    passwords: Sequence[tuple[str, Password]] | None = None  # PasswordId, Password
    rules: Sequence[Rule] | None = None


def identify_bundle_references(
    bundle_group: str, bundle_ids: set[BundleId]
) -> Mapping[BundleId, BundleReferences]:
    """Identify the configuration references of the configuration bundles."""
    bundle_id_finder = prepare_bundle_id_finder(PROGRAM_ID_QUICK_SETUP, bundle_ids)
    affected_entities = _get_affected_entities(bundle_group)
    bundle_rule_ids = (
        _collect_many(
            collect_rules(
                finder=bundle_id_finder,
                rules=AllRulesets.load_all_rulesets().get(bundle_group).get_rules(),
            )
        )
        if "rule" in affected_entities
        else {}
    )
    bundle_password_ids = (
        _collect_many(collect_passwords(finder=bundle_id_finder, passwords=load_passwords()))
        if "password" in affected_entities
        else {}
    )
    bundle_hosts = (
        _collect_many(collect_hosts(finder=bundle_id_finder, hosts=Host.all().values()))
        if "host" in affected_entities
        else {}
    )
    return {
        bundle_id: BundleReferences(
            hosts=bundle_hosts.get(bundle_id),
            passwords=bundle_password_ids.get(bundle_id),
            rules=bundle_rule_ids.get(bundle_id),
        )
        for bundle_id in bundle_ids
    }


def _collect_many(values: Iterable[tuple[BundleId, _T]]) -> Mapping[BundleId, Sequence[_T]]:
    mapping: dict[BundleId, list[_T]] = {}
    for bundle_id, value in values:
        if bundle_id in mapping:
            mapping[bundle_id].append(value)
        else:
            mapping[bundle_id] = [value]

    return mapping


def collect_hosts(finder: IDENT_FINDER, hosts: Iterable[Host]) -> Iterable[tuple[BundleId, Host]]:
    for host in hosts:
        if bundle_id := finder(host.locked_by()):
            yield bundle_id, host


def collect_passwords(
    finder: IDENT_FINDER, passwords: Mapping[str, Password]
) -> Iterable[tuple[BundleId, tuple[str, Password]]]:
    for password_id, password in passwords.items():
        if bundle_id := finder(password.get("locked_by")):
            yield bundle_id, (password_id, password)


def collect_rules(
    finder: IDENT_FINDER, rules: Iterable[tuple[Folder, int, Rule]]
) -> Iterable[tuple[BundleId, Rule]]:
    for _folder, _idx, rule in rules:
        if bundle_id := finder(rule.locked_by):
            yield bundle_id, rule


def prepare_bundle_id_finder(bundle_program_id: str, bundle_ids: set[BundleId]) -> IDENT_FINDER:
    def find_matching_bundle_id(
        ident: GlobalIdent | None,
    ) -> BundleId | None:
        if (
            ident is not None
            and ident["program_id"] == bundle_program_id
            and ident["instance_id"] in bundle_ids
        ):
            return BundleId(ident["instance_id"])
        return None

    return find_matching_bundle_id


class ConfigBundle(TypedDict):
    """
    A configuration bundle is a collection of configs which are managed together by this bundle.
    Each underlying config must have the locked_by attribute set to the id of the bundle. We
    explicitly avoid double references here to keep the data model simple. The group and program
    combination should determine which configuration objects are potentially part of the bundle.
    """

    # General properties
    title: str
    comment: str

    # Bundle specific properties
    group: str
    program_id: Literal["quick_setup"]
    customer: NotRequired[str]  # CME specific


class ConfigBundleStore(WatoSingleConfigFile[dict[BundleId, ConfigBundle]]):
    def __init__(self) -> None:
        super().__init__(
            config_file_path=Path(multisite_dir()) / "configuration_bundles.mk",
            config_variable="configuration_bundles",
            spec_class=dict[BundleId, ConfigBundle],
        )


def register(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(ConfigBundleStore())
