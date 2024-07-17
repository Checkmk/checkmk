#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Callable, Iterable, Literal, Mapping, NewType, NotRequired, TypedDict

from cmk.utils.global_ident_type import GlobalIdent, PROGRAM_ID_QUICK_SETUP
from cmk.utils.password_store import Password

from cmk.gui.watolib.hosts_and_folders import Folder, Host
from cmk.gui.watolib.passwords import load_passwords
from cmk.gui.watolib.rulesets import AllRulesets, Rule
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSingleConfigFile
from cmk.gui.watolib.utils import multisite_dir

from cmk.ccc.exceptions import MKGeneralException

BundleId = NewType("BundleId", str)
IDENT_FINDER = Callable[[GlobalIdent | None], BundleId | None]


class SpecialAgentBundleReferences(TypedDict):
    # TODO: introduce dcd
    host: Host
    password: tuple[str, Password] | None  # PasswordId, Password
    special_agent_rule: Rule


def identify_special_agent_bundle_references(
    bundle_group: str, bundle_ids: set[BundleId]
) -> Mapping[BundleId, SpecialAgentBundleReferences]:
    """Identify the configuration references of the special agent based configuration bundles.

    Assumptions currently made (this could change in the future if necessary):
        * one bundle references exactly one host, one special agent rule and optionally one
        password and dcd config
        * it is therefore a config error if multiple entities of the same config type are
        referenced by the same bundle
    """
    bundles: dict[BundleId, SpecialAgentBundleReferences] = {}
    bundle_id_finder = prepare_bundle_id_finder(PROGRAM_ID_QUICK_SETUP, bundle_ids)
    bundle_rule_ids = dict(
        collect_rules(
            finder=bundle_id_finder,
            rules=AllRulesets.load_all_rulesets().get(bundle_group).get_rules(),
        )
    )
    bundle_password_ids = dict(
        collect_passwords(finder=bundle_id_finder, passwords=load_passwords())
    )

    for bundle_id, host in collect_hosts(finder=bundle_id_finder, hosts=Host.all().values()):
        bundles[bundle_id] = {
            "host": host,
            "password": bundle_password_ids.get(bundle_id),
            "special_agent_rule": bundle_rule_ids[bundle_id],
        }

    if len(bundles) != len(bundle_ids):
        raise MKGeneralException("Not all bundle ids could be resolved")

    return bundles


def collect_hosts(finder: IDENT_FINDER, hosts: Iterable[Host]) -> Iterable[tuple[BundleId, Host]]:
    seen_ids: set[BundleId] = set()
    for host in hosts:
        if bundle_id := finder(host.locked_by()):
            if bundle_id in seen_ids:
                raise MKGeneralException(
                    f"One bundle should reference only one host, but bundle {bundle_id} references multiple hosts"
                )
            seen_ids.add(bundle_id)
            yield bundle_id, host


def collect_passwords(
    finder: IDENT_FINDER, passwords: Mapping[str, Password]
) -> Iterable[tuple[BundleId, tuple[str, Password]]]:
    seen_ids: set[BundleId] = set()
    for password_id, password in passwords.items():
        if bundle_id := finder(password.get("locked_by")):
            if bundle_id in seen_ids:
                raise MKGeneralException(
                    f"One bundle should reference only one password, but bundle {bundle_id} references multiple passwords"
                )
            seen_ids.add(bundle_id)
            yield bundle_id, (password_id, password)


def collect_rules(
    finder: IDENT_FINDER, rules: Iterable[tuple[Folder, int, Rule]]
) -> Iterable[tuple[BundleId, Rule]]:
    seen_ids: set[BundleId] = set()
    for _folder, _idx, rule in rules:
        if bundle_id := finder(rule.locked_by):
            if bundle_id in seen_ids:
                raise MKGeneralException(
                    f"One bundle should reference only one rule, but bundle {bundle_id} references multiple rules"
                )
            seen_ids.add(bundle_id)
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
