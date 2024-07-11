#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from itertools import groupby
from operator import itemgetter
from pathlib import Path
from typing import (
    Any,
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
from cmk.utils.hostaddress import HostName
from cmk.utils.password_store import Password
from cmk.utils.rulesets.definition import RuleGroupType
from cmk.utils.rulesets.ruleset_matcher import RuleSpec

from cmk.gui.watolib import check_mk_automations
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree, Host
from cmk.gui.watolib.passwords import load_passwords, remove_password, save_password
from cmk.gui.watolib.rulesets import AllRulesets, FolderRulesets, Rule, SingleRulesetRecursively
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSingleConfigFile
from cmk.gui.watolib.utils import multisite_dir

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site

_T = TypeVar("_T")
BundleId = NewType("BundleId", str)
IdentFinder = Callable[[GlobalIdent | None], BundleId | None]
Entity = Literal["host", "rule", "password", "dcd"]
Permission = Literal["hosts", "rulesets", "passwords", "dcd_connections"]

# TODO: deduplicate with cmk/gui/cee/dcd/_store.py
DCDConnectionSpec = dict[str, Any]
DCDConnectionDict = dict[str, DCDConnectionSpec]


@dataclass(frozen=True)
class DomainDefinition:
    entity: Entity
    permission: Permission


ALL_ENTITIES: set[Entity] = set(get_args(Entity))
BUNDLE_DOMAINS: Mapping[RuleGroupType, set[DomainDefinition]] = {
    RuleGroupType.SPECIAL_AGENTS: {
        DomainDefinition(entity="host", permission="hosts"),
        DomainDefinition(entity="rule", permission="rulesets"),
        DomainDefinition(entity="password", permission="passwords"),
        DomainDefinition(entity="dcd", permission="dcd_connections"),
    }
}


def _get_affected_entities(bundle_group: str) -> set[Entity]:
    rule_group_type = RuleGroupType(bundle_group.split(":", maxsplit=1)[0])
    bundle_domain = BUNDLE_DOMAINS.get(rule_group_type, None)
    return set(domain.entity for domain in bundle_domain) if bundle_domain else ALL_ENTITIES


class CreateHost(TypedDict):
    folder: str
    name: HostName
    attributes: HostAttributes
    cluster_nodes: NotRequired[Sequence[HostName]]


class CreatePassword(TypedDict):
    id: str
    spec: Password


class CreateRule(TypedDict):
    folder: str
    ruleset: str
    spec: RuleSpec[object]


class CreateDCDConnection(TypedDict):
    id: str
    spec: DCDConnectionSpec


@dataclass
class CreateBundleEntities:
    hosts: Iterable[CreateHost] | None = None
    passwords: Iterable[CreatePassword] | None = None
    rules: Iterable[CreateRule] | None = None
    dcd_connections: Iterable[CreateDCDConnection] | None = None


def _dcd_unsupported(*_args: Any, **_kwargs: Any) -> None:
    raise MKGeneralException("DCD not supported")


class DCDConnectionHook:
    load_dcd_connections: Callable[[], DCDConnectionDict] = lambda: {}
    create_dcd_connection: Callable[[str, DCDConnectionSpec], None] = _dcd_unsupported
    delete_dcd_connection: Callable[[str], None] = _dcd_unsupported


@dataclass
class BundleReferences:
    hosts: Sequence[Host] | None = None
    passwords: Sequence[tuple[str, Password]] | None = None  # PasswordId, Password
    rules: Sequence[Rule] | None = None
    dcd_connections: Sequence[tuple[str, DCDConnectionSpec]] | None = None


def identify_bundle_references(
    bundle_group: str, bundle_ids: set[BundleId], *, rulespecs_hint: set[str] | None = None
) -> Mapping[BundleId, BundleReferences]:
    """Identify the configuration references of the configuration bundles."""
    bundle_id_finder = _prepare_bundle_id_finder(PROGRAM_ID_QUICK_SETUP, bundle_ids)
    affected_entities = _get_affected_entities(bundle_group)

    bundle_rule_ids = (
        _collect_many(
            _collect_rules(finder=bundle_id_finder, rules=_iter_all_rules(rulespecs_hint))
        )
        if "rule" in affected_entities
        else {}
    )
    bundle_password_ids = (
        _collect_many(_collect_passwords(finder=bundle_id_finder, passwords=load_passwords()))
        if "password" in affected_entities
        else {}
    )
    bundle_hosts = (
        _collect_many(_collect_hosts(finder=bundle_id_finder, hosts=Host.all().values()))
        if "host" in affected_entities
        else {}
    )
    bundle_dcd_connections = (
        _collect_many(
            _collect_dcd_connections(
                finder=bundle_id_finder, dcd_connections=DCDConnectionHook.load_dcd_connections()
            )
        )
        if "dcd" in affected_entities
        else {}
    )
    return {
        bundle_id: BundleReferences(
            hosts=bundle_hosts.get(bundle_id),
            passwords=bundle_password_ids.get(bundle_id),
            rules=bundle_rule_ids.get(bundle_id),
            dcd_connections=bundle_dcd_connections.get(bundle_id),
        )
        for bundle_id in bundle_ids
    }


def create_config_bundle(
    bundle_id: BundleId, bundle: "ConfigBundle", entities: CreateBundleEntities
) -> None:
    bundle_ident = GlobalIdent(
        site_id=omd_site(), program_id=bundle["program_id"], instance_id=bundle_id
    )
    store = ConfigBundleStore()
    all_bundles = store.load_for_modification()
    if bundle_id in all_bundles:
        raise MKGeneralException(f'Configuration bundle "{bundle_id}" already exists.')
    all_bundles[bundle_id] = bundle
    store.save(all_bundles)

    if entities.passwords:
        _create_passwords(bundle_ident, entities.passwords)
    if entities.hosts:
        _create_hosts(bundle_ident, entities.hosts)
    if entities.rules:
        _create_rules(bundle_ident, entities.rules)
    if entities.dcd_connections:
        _create_dcd_connections(bundle_ident, entities.dcd_connections)


def delete_config_bundle(bundle_id: BundleId) -> None:
    store = ConfigBundleStore()
    all_bundles = store.load_for_modification()
    if (bundle := all_bundles.pop(bundle_id, None)) is None:
        raise MKGeneralException(f'Configuration bundle "{bundle_id}" does not exist.')

    references = identify_bundle_references(bundle["group"], {bundle_id})[bundle_id]
    # delete resources in inverse order to create, as rules may reference hosts for example
    if references.rules:
        _delete_rules(references.rules)
    if references.hosts:
        _delete_hosts(references.hosts)
    if references.passwords:
        _delete_passwords(references.passwords)
    if references.dcd_connections:
        _delete_dcd_connections(references.dcd_connections)


def _collect_many(values: Iterable[tuple[BundleId, _T]]) -> Mapping[BundleId, Sequence[_T]]:
    mapping: dict[BundleId, list[_T]] = {}
    for bundle_id, value in values:
        if bundle_id in mapping:
            mapping[bundle_id].append(value)
        else:
            mapping[bundle_id] = [value]

    return mapping


def _collect_hosts(finder: IdentFinder, hosts: Iterable[Host]) -> Iterable[tuple[BundleId, Host]]:
    for host in hosts:
        if bundle_id := finder(host.locked_by()):
            yield bundle_id, host


def _get_host_attributes(bundle_ident: GlobalIdent, params: CreateHost) -> HostAttributes:
    attributes = params["attributes"]
    attributes["locked_by"] = [
        bundle_ident["site_id"],
        bundle_ident["program_id"],
        bundle_ident["instance_id"],
    ]
    return attributes


def _create_hosts(bundle_ident: GlobalIdent, hosts: Iterable[CreateHost]) -> None:
    folder_getter = itemgetter("folder")
    hosts_sorted_by_folder: list[CreateHost] = sorted(hosts, key=folder_getter)
    folder_and_valid_hosts = []
    for folder_name, hosts_iter in groupby(
        hosts_sorted_by_folder, key=folder_getter
    ):  # type: str, Iterable[CreateHost]
        folder = folder_tree().folder(folder_name)
        folder.prepare_create_hosts()
        valid_hosts = [
            (
                host["name"],
                folder.verify_and_update_host_details(
                    host["name"],
                    _get_host_attributes(bundle_ident, host),
                ),
                host.get("cluster_nodes"),
            )
            for host in hosts_iter
        ]
        folder_and_valid_hosts.append((folder, valid_hosts))

    for folder, valid_hosts in folder_and_valid_hosts:
        folder.create_validated_hosts(valid_hosts)


def _delete_hosts(hosts: Iterable[Host]) -> None:
    folder_getter = itemgetter(0)
    folders_and_hosts = sorted(
        ((host.folder(), host) for host in hosts),
        key=folder_getter,
    )
    for folder, host_iter in groupby(
        folders_and_hosts, key=folder_getter
    ):  # type: Folder, Iterable[tuple[Folder, Host]]
        host_names = [host.name() for _folder, host in host_iter]
        folder.delete_hosts(
            host_names, automation=check_mk_automations.delete_hosts, allow_locked_deletion=True
        )


def _collect_passwords(
    finder: IdentFinder, passwords: Mapping[str, Password]
) -> Iterable[tuple[BundleId, tuple[str, Password]]]:
    for password_id, password in passwords.items():
        if bundle_id := finder(password.get("locked_by")):
            yield bundle_id, (password_id, password)


def _create_passwords(bundle_ident: GlobalIdent, passwords: Iterable[CreatePassword]) -> None:
    for password in passwords:
        spec = password["spec"]
        spec["locked_by"] = bundle_ident
        save_password(password["id"], spec, new_password=True)


def _delete_passwords(passwords: Iterable[tuple[str, Password]]) -> None:
    for password_id, _password in passwords:
        remove_password(password_id)


def _iter_all_rules(rulespecs: set[str] | None) -> Iterable[tuple[Folder, int, Rule]]:
    if rulespecs:
        for rulespec in rulespecs:
            ruleset = SingleRulesetRecursively.load_single_ruleset_recursively(rulespec).get(
                rulespec
            )
            yield from ruleset.get_rules()

    else:
        all_rulesets = AllRulesets.load_all_rulesets()
        for ruleset in all_rulesets.get_rulesets().values():
            yield from ruleset.get_rules()


def _collect_rules(
    finder: IdentFinder, rules: Iterable[tuple[Folder, int, Rule]]
) -> Iterable[tuple[BundleId, Rule]]:
    for _folder, _idx, rule in rules:
        if bundle_id := finder(rule.locked_by):
            yield bundle_id, rule


def _create_rules(bundle_ident: GlobalIdent, rules: Iterable[CreateRule]) -> None:
    # sort by folder, then ruleset
    sorted_rules = sorted(rules, key=itemgetter("folder", "ruleset"))
    for folder_name, rule_iter_outer in groupby(
        sorted_rules, key=itemgetter("folder")
    ):  # type: str, Iterable[CreateRule]
        folder = folder_tree().folder(folder_name)
        rulesets = FolderRulesets.load_folder_rulesets(folder)

        for ruleset_name, rule_iter_inner in groupby(
            rule_iter_outer, key=itemgetter("ruleset")
        ):  # type: str, Iterable[CreateRule]
            ruleset = rulesets.get(ruleset_name)
            for create_rule in rule_iter_inner:
                rule = Rule.from_config(folder, ruleset, create_rule["spec"])
                rule.locked_by = bundle_ident
                ruleset.append_rule(folder, rule)

        rulesets.save_folder()


def _delete_rules(rules: Iterable[Rule]) -> None:
    folder_getter = itemgetter(0)
    sorted_rules = sorted(((rule.folder, rule) for rule in rules), key=folder_getter)
    for folder, rule_iter in groupby(
        sorted_rules, key=folder_getter
    ):  # type: Folder, Iterable[tuple[Folder, Rule]]
        rulesets = FolderRulesets.load_folder_rulesets(folder)
        for _folder, rule in rule_iter:
            # the rule objects loaded into `rulesets` are different instances
            ruleset = rulesets.get(rule.ruleset.name)
            actual_rule = ruleset.get_rule_by_id(rule.id)
            rulesets.get(rule.ruleset.name).delete_rule(actual_rule)

        rulesets.save_folder()


def _collect_dcd_connections(
    finder: IdentFinder, dcd_connections: DCDConnectionDict
) -> Iterable[tuple[BundleId, tuple[str, DCDConnectionSpec]]]:
    for connection_id, connection in dcd_connections.items():
        if bundle_id := finder(connection.get("locked_by")):
            yield bundle_id, (connection_id, connection)


def _create_dcd_connections(
    bundle_ident: GlobalIdent, dcd_connections: Iterable[CreateDCDConnection]
) -> None:
    for dcd_connection in dcd_connections:
        spec = dcd_connection["spec"]
        spec["locked_by"] = bundle_ident
        DCDConnectionHook.create_dcd_connection(dcd_connection["id"], spec)


def _delete_dcd_connections(dcd_connections: Iterable[tuple[str, DCDConnectionSpec]]) -> None:
    for dcd_connection_id, _spec in dcd_connections:
        DCDConnectionHook.delete_dcd_connection(dcd_connection_id)


def _prepare_bundle_id_finder(bundle_program_id: str, bundle_ids: set[BundleId]) -> IdentFinder:
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
