#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from uuid import uuid4

from livestatus import SiteId

from cmk.ccc.site import omd_site

from cmk.utils.global_ident_type import GlobalIdent, PROGRAM_ID_QUICK_SETUP
from cmk.utils.hostaddress import HostName
from cmk.utils.password_store import Password as StorePassword
from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.rulesets.ruleset_matcher import RuleConditionsSpec, RuleOptionsSpec, RuleSpec

from cmk.gui.config import active_config
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.quick_setup.v0_unstable.definitions import (
    QSHostName,
    QSHostPath,
    QSSiteSelection,
    UniqueBundleIDStr,
)
from cmk.gui.quick_setup.v0_unstable.predefined._common import (
    _collect_params_with_defaults_from_form_data,
    _collect_passwords_from_form_data,
    _find_id_in_form_data,
)
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData
from cmk.gui.site_config import site_is_local
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.watolib.automations import (
    fetch_service_discovery_background_job_status,
)
from cmk.gui.watolib.configuration_bundles import (
    BundleId,
    ConfigBundle,
    create_config_bundle,
    CreateBundleEntities,
    CreateDCDConnection,
    CreateHost,
    CreatePassword,
    CreateRule,
    delete_config_bundle,
)
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import (
    _normalize_folder_name,
    Folder,
    folder_tree,
    Host,
)
from cmk.gui.watolib.passwords import load_passwords
from cmk.gui.watolib.services import (
    DiscoveryAction,
    get_check_table,
    perform_fix_all,
)

from cmk.rulesets.v1.form_specs import Dictionary


class DCDHook:
    create_dcd_connections: Callable[
        [BundleId, SiteId, HostName, Folder], list[CreateDCDConnection]
    ] = lambda *_args: []


def _normalize_folder_path_str(folder_path: str) -> str:
    r"""Normalizes a folder representation

    Args:
        folder_id:
            A representation of a folder.

    Examples:

        >>> _normalize_folder_path_str("\\")
        ''

        >>> _normalize_folder_path_str("~")
        ''

        >>> _normalize_folder_path_str("/foo/bar")
        'foo/bar'

        >>> _normalize_folder_path_str("\\foo\\bar")
        'foo/bar'

        >>> _normalize_folder_path_str("~foo~bar")
        'foo/bar'

        >>> _normalize_folder_path_str("/foo/bar/")
        'foo/bar'

    Returns:
        The normalized representation.

    """

    if folder_path in ["/", "~", "\\", ""]:
        return ""

    prev = folder_path
    separators = ["\\", "~"]
    while True:
        for sep in separators:
            folder_path = folder_path.replace(sep, "/")
        if prev == folder_path:
            break
        prev = folder_path
    if len(folder_path) > 1 and folder_path.endswith("/"):
        folder_path = folder_path[:-1]

    if folder_path.startswith("/"):
        folder_path = folder_path[1:]

    return folder_path


def sanitize_folder_path(folder_path: str) -> Folder:
    """Attempt to get the folder from the folder path. If the folder does not exist, create it.
    Returns the folder object."""
    tree = folder_tree()
    sanitized_folder_path = _normalize_folder_path_str(folder_path)
    if sanitized_folder_path == "":
        return tree.root_folder()
    if sanitized_folder_path in tree.all_folders():
        return tree.all_folders()[sanitized_folder_path]

    folder = tree.root_folder()
    for title in sanitized_folder_path.split("/"):
        name = _normalize_folder_name(title)
        folder = (
            folder.subfolder_by_title(title)
            or folder.subfolder(name)
            or folder.create_subfolder(
                name=name,
                title=title,
                attributes={},
            )
        )
    return folder


def create_special_agent_host_from_form_data(
    host_name: HostName,
    site_id: SiteId,
    folder: Folder,
) -> CreateHost:
    return CreateHost(
        name=host_name,
        folder=folder,
        attributes=HostAttributes(
            tag_address_family="no-ip",
            tag_agent="special-agents",
            tag_piggyback="auto-piggyback",
            tag_snmp_ds="no-snmp",
            site=site_id,
        ),
    )


def create_passwords(
    passwords: Mapping[str, str],
    rulespec_name: str,
    bundle_id: BundleId,
) -> Sequence[CreatePassword]:
    return [
        CreatePassword(
            id=pw_id,
            spec=StorePassword(
                title=f"{bundle_id}_password",
                comment="",
                docu_url="",
                password=password,
                owned_by=None,
                shared_with=[],
            ),
        )
        for pw_id, password in passwords.items()
    ]


def create_rule(
    params: Mapping[str, object],
    host_name: str,
    host_path: str,
    rulespec_name: str,
    bundle_id: BundleId,
    site_id: str,
) -> CreateRule:
    return CreateRule(
        folder=host_path,
        ruleset=rulespec_name,
        spec=RuleSpec(
            value=params,
            id=str(uuid4()),
            locked_by=GlobalIdent(
                site_id=site_id,
                program_id=PROGRAM_ID_QUICK_SETUP,
                instance_id=bundle_id,
            ),
            condition=RuleConditionsSpec(
                host_tags={},
                host_label_groups=[],
                host_name=[host_name],
                host_folder=host_path,
            ),
            options=RuleOptionsSpec(disabled=False, description=""),
        ),
    )


def create_and_save_special_agent_bundle(
    special_agent_name: str,
    parameter_form: Dictionary,
    all_stages_form_data: ParsedFormData,
) -> str:
    return _create_and_save_special_agent_bundle(
        special_agent_name=special_agent_name,
        all_stages_form_data=all_stages_form_data,
        collect_params=_collect_params_with_defaults_from_form_data,
        parameter_form=parameter_form,
    )


def create_and_save_special_agent_bundle_custom_collect_params(
    special_agent_name: str,
    parameter_form: Dictionary,
    all_stages_form_data: ParsedFormData,
    custom_collect_params: Callable[[ParsedFormData, Dictionary], Mapping[str, object]],
) -> str:
    return _create_and_save_special_agent_bundle(
        special_agent_name=special_agent_name,
        parameter_form=parameter_form,
        all_stages_form_data=all_stages_form_data,
        collect_params=custom_collect_params,
    )


def _find_bundle_id(all_stages_form_data: ParsedFormData) -> BundleId:
    bundle_id = _find_id_in_form_data(form_data=all_stages_form_data, target_key=UniqueBundleIDStr)
    if bundle_id is None:
        raise ValueError("No bundle id found")
    return BundleId(bundle_id)


def _convert_explicit_passwords_to_stored_passwords(
    rule_params: Mapping, explicit_password_ids: set[str]
) -> Mapping[str, object]:
    """Passwords that are explicitly set in the form data are replaced with a reference to the
    password to be created in the password store

    Notes:
        * assumed that the password store entry will get the same id as the password id
        * assumed that passwords are not part of a list and only a direct entry in a dictionary
    """
    params_with_converted_passwords: dict = {}
    for key, value in rule_params.items():
        match value:
            case dict():
                params_with_converted_passwords[key] = (
                    _convert_explicit_passwords_to_stored_passwords(value, explicit_password_ids)
                )
            case ("cmk_postprocessed", "explicit_password", (pw_id, _password)):
                if pw_id in explicit_password_ids:
                    password_store_reference = ("cmk_postprocessed", "stored_password", (pw_id, ""))
                    params_with_converted_passwords[key] = password_store_reference
                else:
                    params_with_converted_passwords[key] = value
            case _:
                params_with_converted_passwords[key] = value
    return params_with_converted_passwords


def _create_and_save_special_agent_bundle(
    special_agent_name: str,
    parameter_form: Dictionary,
    all_stages_form_data: ParsedFormData,
    collect_params: Callable[[ParsedFormData, Dictionary], Mapping[str, object]],
) -> str:
    rulespec_name = RuleGroup.SpecialAgents(special_agent_name)
    bundle_id = _find_bundle_id(all_stages_form_data)

    host_name = _find_id_in_form_data(all_stages_form_data, QSHostName)
    host_path = _find_id_in_form_data(all_stages_form_data, QSHostPath)

    if host_name is None or host_path is None:
        raise ValueError("Host name or host path not found in form data")

    site_selection = _find_id_in_form_data(all_stages_form_data, QSSiteSelection)
    site_id = SiteId(site_selection) if site_selection else omd_site()
    params = collect_params(all_stages_form_data, parameter_form)

    collected_passwords = _collect_passwords_from_form_data(all_stages_form_data, parameter_form)

    stored_passwords = load_passwords()
    # We need to filter out the passwords that are already stored in the password store since they
    # should be independent of the configuration bundle
    explicit_passwords = {
        pwid: pw for pwid, pw in collected_passwords.items() if pwid not in stored_passwords
    }
    params = _convert_explicit_passwords_to_stored_passwords(params, set(explicit_passwords.keys()))

    # TODO: The sanitize function is likely to change once we have a folder FormSpec.
    folder = sanitize_folder_path(host_path)
    validated_host_name = HostName(host_name)
    create_config_bundle(
        bundle_id=bundle_id,
        bundle=ConfigBundle(
            title=f"{bundle_id}_config",
            comment="",
            group=rulespec_name,
            program_id=PROGRAM_ID_QUICK_SETUP,
        ),
        entities=CreateBundleEntities(
            hosts=[
                create_special_agent_host_from_form_data(
                    host_name=validated_host_name, folder=folder, site_id=site_id
                )
            ],
            passwords=create_passwords(
                passwords=explicit_passwords,
                rulespec_name=rulespec_name,
                bundle_id=bundle_id,
            ),
            rules=[
                create_rule(
                    params=params,
                    host_name=validated_host_name,
                    host_path=folder.path(),
                    rulespec_name=rulespec_name,
                    bundle_id=bundle_id,
                    site_id=site_id,
                )
            ],
            dcd_connections=DCDHook.create_dcd_connections(
                bundle_id, site_id, validated_host_name, folder
            ),
        ),
    )
    try:
        host: Host = Host.load_host(HostName(host_name))
        if not site_is_local(active_config, site_id):
            get_check_table(host, DiscoveryAction.REFRESH, raise_errors=False)
            snapshot = fetch_service_discovery_background_job_status(site_id, host_name)
            if not snapshot.exists:
                raise Exception(
                    _("Could not find a running service discovery for host %s on remote site %s")
                    % (host_name, site_id)
                )
            while snapshot.is_active:
                snapshot = fetch_service_discovery_background_job_status(site_id, host_name)

        check_table = get_check_table(host, DiscoveryAction.FIX_ALL, raise_errors=False)
        perform_fix_all(
            discovery_result=check_table,
            host=host,
            raise_errors=False,
        )
    except Exception as e:
        delete_config_bundle(BundleId(bundle_id))
        raise e

    return makeuri_contextless(
        request,
        [
            ("mode", "changelog"),
            ("origin", "quick_setup"),
            ("special_agent_name", special_agent_name),
        ],
        filename="wato.py",
    )
