#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Collection, Container, Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import groupby
from operator import itemgetter
from typing import Any, get_args, Literal, NotRequired, TypedDict, TypeVar

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site
from cmk.ccc.user import UserId

from cmk.utils.global_ident_type import GlobalIdent, PROGRAM_ID_DCD, PROGRAM_ID_QUICK_SETUP
from cmk.utils.password_store import Password
from cmk.utils.rulesets.definition import RuleGroupType
from cmk.utils.rulesets.ruleset_matcher import RuleSpec

from cmk.gui.exceptions import MKAuthException
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.utils.roles import roles_of_user
from cmk.gui.watolib import check_mk_automations
from cmk.gui.watolib.configuration_bundle_store import BundleId, ConfigBundle, ConfigBundleStore
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree, Host
from cmk.gui.watolib.passwords import load_passwords, remove_password, save_password
from cmk.gui.watolib.rulesets import AllRulesets, FolderRulesets, Rule, SingleRulesetRecursively

_T = TypeVar("_T")
IdentFinder = Callable[[GlobalIdent | None], str | None]
Entity = Literal["host", "rule", "password", "dcd"]
Permission = Literal["hosts", "rulesets", "passwords", "dcd_connections"]
CreateFunction = Callable[[], None]

# TODO: deduplicate with cmk/gui/cee/dcd/_store.py
# NOTE: mypy does not allow DCDConnectionSpec to be Mapping here (see TODO for solution)
# TODO: a cee specific configuration bundle should be implemented as the raw edition does not
#  have dcd connections
DCDConnectionSpec = Any
DCDConnectionDict = dict[str, DCDConnectionSpec]


@dataclass(frozen=True)
class DomainDefinition:
    entity: Entity
    permission: Permission


ALL_ENTITIES: set[Entity] = set(get_args(Entity))


def bundle_domains() -> Mapping[RuleGroupType, set[DomainDefinition]]:
    domains: set[DomainDefinition] = {
        DomainDefinition(entity="host", permission="hosts"),
        DomainDefinition(entity="rule", permission="rulesets"),
        DomainDefinition(entity="password", permission="passwords"),
    }

    if DCDConnectionHook.domain_definition is not None:
        domains.update({DCDConnectionHook.domain_definition})

    return {RuleGroupType.SPECIAL_AGENTS: domains}


def _get_affected_entities(bundle_group: str | None) -> set[Entity]:
    if bundle_group is None:
        bundle_domain = None
    else:
        rule_group_type = RuleGroupType(bundle_group.split(":", maxsplit=1)[0])
        bundle_domain = bundle_domains().get(rule_group_type, None)
    return {domain.entity for domain in bundle_domain} if bundle_domain else ALL_ENTITIES


class CreateHost(TypedDict):
    folder: Folder
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
    """

    Remarks for Special agents:
        * when creating a special agent rule, the user may select an existing password. In such,
        cases the password shouldn't be part of the bundle, as deletion of the bundle should leave
        the password untouched.
    """

    hosts: Collection[CreateHost] | None = None
    passwords: Collection[CreatePassword] | None = None
    rules: Collection[CreateRule] | None = None
    dcd_connections: Collection[CreateDCDConnection] | None = None


def _dcd_unsupported(*_args: Any, **_kwargs: Any) -> None:
    raise MKGeneralException("DCD not supported")


class DCDConnectionHook:
    load_dcd_connections: Callable[[], DCDConnectionDict] = lambda: {}
    create_dcd_connection: Callable[[str, DCDConnectionSpec], None] = _dcd_unsupported
    delete_dcd_connection: Callable[[str], None] = _dcd_unsupported
    domain_definition: DomainDefinition | None = None


@dataclass
class BundleReferences:
    hosts: Sequence[Host] | None = None
    passwords: Sequence[tuple[str, Password]] | None = None  # PasswordId, Password
    rules: Sequence[Rule] | None = None
    dcd_connections: Sequence[tuple[str, DCDConnectionSpec]] | None = None


def valid_special_agent_bundle(bundle: BundleReferences) -> bool:
    host_conditions = bundle.hosts is not None and len(bundle.hosts) == 1
    rule_conditions = bundle.rules is not None and len(bundle.rules) == 1
    password_conditions = bundle.passwords is None or len(bundle.passwords) == 1
    if not host_conditions or not rule_conditions or not password_conditions:
        return False
    return True


def identify_bundle_references(
    bundle_group: str | None,
    bundle_ids: set[BundleId],
    *,
    rulespecs_hint: set[str] | None = None,
) -> Mapping[BundleId, BundleReferences]:
    """Identify the configuration references of the configuration bundles.

    NOTE: This may not return all references, as individual entities may not be accessible by the
    current user. (Like passwords)"""
    bundle_id_finder = _prepare_id_finder(PROGRAM_ID_QUICK_SETUP, bundle_ids)
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
                finder=bundle_id_finder,
                dcd_connections=DCDConnectionHook.load_dcd_connections(),
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


def identify_single_bundle_references(
    bundle_id: BundleId, bundle_group: str | None = None
) -> BundleReferences:
    """Get references for a single bundle.
    If the bundle group is unknown, the bundle will be loaded first."""
    group = bundle_group or read_config_bundle(bundle_id)["group"]
    references = identify_bundle_references(group, {bundle_id})
    return references[bundle_id]


def read_config_bundle(bundle_id: BundleId) -> ConfigBundle:
    store = ConfigBundleStore()
    all_bundles = store.load_for_reading()
    if bundle_id in all_bundles:
        return all_bundles[bundle_id]

    raise MKGeneralException(f'Configuration bundle "{bundle_id}" does not exist.')


def edit_config_bundle_configuration(
    bundle_id: BundleId, bundle: ConfigBundle, pprint_value: bool
) -> None:
    store = ConfigBundleStore()
    all_bundles = store.load_for_modification()
    if bundle_id not in all_bundles:
        raise MKGeneralException(f'Configuration bundle "{bundle_id}" does not exist.')
    all_bundles[bundle_id] = bundle
    store.save(all_bundles, pprint_value)


def _validate_and_prepare_create_calls(
    bundle_ident: GlobalIdent,
    entities: CreateBundleEntities,
    *,
    user_id: UserId | None,
    pprint_value: bool,
    use_git: bool,
    debug: bool,
) -> list[CreateFunction]:
    create_functions = []
    if entities.passwords:
        create_functions.append(
            _prepare_create_passwords(
                bundle_ident,
                entities.passwords,
                load_passwords(),
                user_id=user_id,
                pprint_value=pprint_value,
                use_git=use_git,
            )
        )
    if entities.hosts:
        create_functions.append(
            _prepare_create_hosts(bundle_ident, entities.hosts, pprint_value=pprint_value)
        )
    if entities.rules:
        create_functions.append(
            _prepare_create_rules(
                bundle_ident, entities.rules, pprint_value=pprint_value, debug=debug
            )
        )
    if entities.dcd_connections:
        create_functions.append(
            _prepare_create_dcd_connections(
                bundle_ident,
                entities.dcd_connections,
                DCDConnectionHook.load_dcd_connections(),
            )
        )
    return create_functions


def create_config_bundle(
    bundle_id: BundleId,
    bundle: ConfigBundle,
    entities: CreateBundleEntities,
    *,
    user_id: UserId | None,
    pprint_value: bool,
    use_git: bool,
    debug: bool,
) -> None:
    bundle_ident = GlobalIdent(
        site_id=omd_site(), program_id=bundle["program_id"], instance_id=bundle_id
    )
    store = ConfigBundleStore()
    all_bundles = store.load_for_modification()
    if bundle_id in all_bundles:
        raise MKGeneralException(f'Configuration bundle "{bundle_id}" already exists.')

    try:
        create_functions = _validate_and_prepare_create_calls(
            bundle_ident,
            entities,
            user_id=user_id,
            pprint_value=pprint_value,
            use_git=use_git,
            debug=debug,
        )
    except Exception as e:
        raise MKGeneralException(
            f'Configuration bundle "{bundle_id}" failed validation: {e}'
        ) from e

    all_bundles[bundle_id] = bundle
    store.save(all_bundles, pprint_value)
    try:
        for create_function in create_functions:
            create_function()
    except Exception as e:
        delete_config_bundle(
            bundle_id,
            user_id=user_id,
            pprint_value=pprint_value,
            use_git=use_git,
            debug=debug,
        )
        raise MKGeneralException(f'Failed to create configuration bundle "{bundle_id}"') from e


def delete_config_bundle(
    bundle_id: BundleId,
    *,
    user_id: UserId | None,
    pprint_value: bool,
    use_git: bool,
    debug: bool,
) -> None:
    store = ConfigBundleStore()
    all_bundles = store.load_for_modification()
    if (bundle := all_bundles.pop(bundle_id, None)) is None:
        raise MKGeneralException(f'Configuration bundle "{bundle_id}" does not exist.')

    references = identify_bundle_references(bundle["group"], {bundle_id})[bundle_id]
    # First check permissions for all the needed deletions
    user_may_delete_config_bundle_objects(bundle_id, references)

    # we have to delete the bundle itself first, so the overview page doesn't error out
    # when someone refreshes it while the deletion is in progress
    store.save(all_bundles, pprint_value)
    delete_config_bundle_objects(
        references,
        user_id=user_id,
        pprint_value=pprint_value,
        use_git=use_git,
        debug=debug,
    )


def user_may_delete_config_bundle_objects(
    bundle_id: BundleId,
    references: BundleReferences,
) -> None:
    bundle = read_config_bundle(bundle_id)
    owned_by = bundle.get("owned_by")

    # Only admins may delete bundles which were created by an admin
    if owned_by and "admin" in roles_of_user(UserId(owned_by)) and "admin" not in user.role_ids:
        raise MKAuthException(
            _(
                "You are not permitted to perform this action. Only an admin is permitted to "
                "delete a bundle which was created by an admin."
            )
        )

    # Adhere to the structure used in delete_config_bundle_objects()
    if references.rules:
        pass
    if references.hosts:
        _user_may_delete_hosts(references.hosts)
    if references.passwords:
        _user_may_delete_passwords(owned_by)
    if references.dcd_connections:
        _user_may_delete_hosts(
            (
                host
                for _dcd_id, host in _collect_hosts(
                    _prepare_id_finder(
                        PROGRAM_ID_DCD,
                        {dcd_id for dcd_id, _spec in references.dcd_connections},
                    ),
                    Host.all().values(),
                )
            )
        )


def delete_config_bundle_objects(
    references: BundleReferences,
    *,
    user_id: UserId | None,
    pprint_value: bool,
    use_git: bool,
    debug: bool,
) -> None:
    # delete resources in inverse order to create, as rules may reference hosts for example
    if references.rules:
        _delete_rules(references.rules, pprint_value=pprint_value, debug=debug)
    if references.hosts:
        _delete_hosts(references.hosts, pprint_value=pprint_value, debug=debug)
    if references.passwords:
        _delete_passwords(
            references.passwords,
            user_id=user_id,
            pprint_value=pprint_value,
            use_git=use_git,
        )
    if references.dcd_connections:
        _delete_dcd_connections(references.dcd_connections, pprint_value=pprint_value, debug=debug)


def _collect_many(values: Iterable[tuple[str, _T]]) -> Mapping[BundleId, Sequence[_T]]:
    mapping: dict[BundleId, list[_T]] = {}
    for bundle_id_str, value in values:
        bundle_id = BundleId(bundle_id_str)
        if bundle_id in mapping:
            mapping[bundle_id].append(value)
        else:
            mapping[bundle_id] = [value]

    return mapping


def _collect_hosts(finder: IdentFinder, hosts: Iterable[Host]) -> Iterable[tuple[str, Host]]:
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


def _prepare_create_hosts(
    bundle_ident: GlobalIdent, hosts: Iterable[CreateHost], *, pprint_value: bool
) -> CreateFunction:
    folder_getter = itemgetter("folder")
    hosts_sorted_by_folder: list[CreateHost] = sorted(hosts, key=folder_getter)
    folder_and_valid_hosts = []

    folder: Folder
    for folder, hosts_iter in groupby(hosts_sorted_by_folder, key=folder_getter):
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

    def create() -> None:
        for f, validated_hosts in folder_and_valid_hosts:
            f.create_validated_hosts(validated_hosts, pprint_value=pprint_value)

    return create


def _user_may_delete_hosts(hosts: Iterable[Host]) -> None:
    folder_getter = itemgetter(0)
    folders_and_hosts = sorted(
        ((host.folder(), host) for host in hosts),
        key=folder_getter,
    )
    for folder, host_iter in groupby(folders_and_hosts, key=folder_getter):  # type: Folder, Iterable[tuple[Folder, Host]]
        host_names = [host.name() for _folder, host in host_iter]
        folder.user_may_delete_hosts(
            host_names,
            allow_locked_deletion=True,
        )


def _delete_hosts(hosts: Iterable[Host], *, pprint_value: bool, debug: bool) -> None:
    folder_getter = itemgetter(0)
    folders_and_hosts = sorted(
        ((host.folder(), host) for host in hosts),
        key=folder_getter,
    )
    for folder, host_iter in groupby(folders_and_hosts, key=folder_getter):  # type: Folder, Iterable[tuple[Folder, Host]]
        host_names = [host.name() for _folder, host in host_iter]
        folder.delete_hosts(
            host_names,
            automation=check_mk_automations.delete_hosts,
            allow_locked_deletion=True,
            pprint_value=pprint_value,
            debug=debug,
        )


def _collect_passwords(
    finder: IdentFinder, passwords: Mapping[str, Password]
) -> Iterable[tuple[str, tuple[str, Password]]]:
    for password_id, password in passwords.items():
        if bundle_id := finder(password.get("locked_by")):
            yield bundle_id, (password_id, password)


def _prepare_create_passwords(
    bundle_ident: GlobalIdent,
    create_passwords: Collection[CreatePassword],
    all_passwords: Mapping[str, Password],
    *,
    user_id: UserId | None,
    pprint_value: bool,
    use_git: bool,
) -> CreateFunction:
    for password in create_passwords:
        if password["id"] in all_passwords:
            raise MKGeneralException(f'Password with id "{password["id"]}" already exists.')

    def create() -> None:
        for pw in create_passwords:
            spec = pw["spec"]
            spec["locked_by"] = bundle_ident
            spec["owned_by"] = user.id
            save_password(
                pw["id"],
                spec,
                new_password=True,
                user_id=user_id,
                pprint_value=pprint_value,
                use_git=use_git,
            )

    return create


def _user_may_delete_passwords(
    owned_by: str | None,
) -> None:
    # If the current user is different from the one who created the bundle, they need
    # permission to edit all passwords in order to (find and) delete the password.
    if not user.may("wato.edit_all_passwords"):
        if owned_by and owned_by != user.id:
            raise MKAuthException(_("You are not permitted to perform this action."))


def _delete_passwords(
    passwords: Iterable[tuple[str, Password]],
    *,
    user_id: UserId | None,
    pprint_value: bool,
    use_git: bool,
) -> None:
    for password_id, _password in passwords:
        remove_password(
            password_id,
            user_id=user_id,
            pprint_value=pprint_value,
            use_git=use_git,
        )


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
) -> Iterable[tuple[str, Rule]]:
    for _folder, _idx, rule in rules:
        if bundle_id := finder(rule.locked_by):
            yield bundle_id, rule


def _prepare_create_rules(
    bundle_ident: GlobalIdent, rules: Iterable[CreateRule], *, pprint_value: bool, debug: bool
) -> CreateFunction:
    validated_data = []
    # sort by folder, then ruleset
    sorted_rules = sorted(rules, key=itemgetter("folder", "ruleset"))
    for folder_name, rule_iter_outer in groupby(sorted_rules, key=itemgetter("folder")):  # type: str, Iterable[CreateRule]
        folder = folder_tree().folder(folder_name)
        folder_rulesets = FolderRulesets.load_folder_rulesets(folder)
        folder_rules = []

        for ruleset_name, rule_iter_inner in groupby(rule_iter_outer, key=itemgetter("ruleset")):  # type: str, Iterable[CreateRule]
            ruleset = folder_rulesets.get(ruleset_name)
            existing_ids = {rule.id for _, _, rule in ruleset.get_rules()}
            for create_rule in rule_iter_inner:
                if create_rule["spec"]["id"] in existing_ids:
                    raise MKGeneralException(
                        f'Rule with id "{create_rule["spec"]["id"]}" already exists.'
                    )

                rule = Rule.from_config(folder, ruleset, create_rule["spec"])
                rule.locked_by = bundle_ident
                folder_rules.append(rule)

        validated_data.append((folder, folder_rulesets, folder_rules))

    def create() -> None:
        for f, rulesets, new_rules in validated_data:
            for rule in new_rules:
                index = rule.ruleset.append_rule(f, rule)
                rule.ruleset.add_new_rule_change(index, f, rule)

            rulesets.save_folder(pprint_value=pprint_value, debug=debug)

    return create


def _delete_rules(rules: Iterable[Rule], *, pprint_value: bool, debug: bool) -> None:
    folder_getter = itemgetter(0)
    sorted_rules = sorted(((rule.folder, rule) for rule in rules), key=folder_getter)
    for folder, rule_iter in groupby(sorted_rules, key=folder_getter):  # type: Folder, Iterable[tuple[Folder, Rule]]
        rulesets = FolderRulesets.load_folder_rulesets(folder)
        for _folder, rule in rule_iter:
            # the rule objects loaded into `rulesets` are different instances
            ruleset = rulesets.get(rule.ruleset.name)
            actual_rule = ruleset.get_rule_by_id(rule.id)
            rulesets.get(rule.ruleset.name).delete_rule(actual_rule)

        rulesets.save_folder(pprint_value=pprint_value, debug=debug)


def _collect_dcd_connections(
    finder: IdentFinder, dcd_connections: DCDConnectionDict
) -> Iterable[tuple[str, tuple[str, DCDConnectionSpec]]]:
    for connection_id, connection in dcd_connections.items():
        if bundle_id := finder(connection.get("locked_by")):
            yield bundle_id, (connection_id, connection)


def _prepare_create_dcd_connections(
    bundle_ident: GlobalIdent,
    new_connections: Collection[CreateDCDConnection],
    current_connections: DCDConnectionDict,
) -> CreateFunction:
    for connection in new_connections:
        if connection["id"] in current_connections:
            raise MKGeneralException(f'DCD Connection with id "{connection["id"]}" already exists.')

    def create() -> None:
        for dcd_connection in new_connections:
            spec = dcd_connection["spec"]
            DCDConnectionHook.create_dcd_connection(
                dcd_connection["id"], {**spec, "locked_by": bundle_ident}
            )

    return create


def _delete_dcd_connections(
    dcd_connections: Sequence[tuple[str, DCDConnectionSpec]], *, pprint_value: bool, debug: bool
) -> None:
    for dcd_connection_id, _spec in dcd_connections:
        DCDConnectionHook.delete_dcd_connection(dcd_connection_id)

    _delete_hosts(
        (
            host
            for _dcd_id, host in _collect_hosts(
                _prepare_id_finder(PROGRAM_ID_DCD, {dcd_id for dcd_id, _spec in dcd_connections}),
                Host.all().values(),
            )
        ),
        pprint_value=pprint_value,
        debug=debug,
    )


def _prepare_id_finder(program_id: str, instance_ids: Container[str]) -> IdentFinder:
    def find_matching_id(
        ident: GlobalIdent | None,
    ) -> str | None:
        if (
            ident is not None
            and ident["program_id"] == program_id
            and ident["instance_id"] in instance_ids
        ):
            return ident["instance_id"]
        return None

    return find_matching_id
