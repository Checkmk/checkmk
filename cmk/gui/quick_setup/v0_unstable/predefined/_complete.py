#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from uuid import uuid4

from livestatus import SiteId

from cmk.utils.global_ident_type import GlobalIdent, PROGRAM_ID_QUICK_SETUP
from cmk.utils.hostaddress import HostName
from cmk.utils.password_store import Password as StorePassword
from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.rulesets.ruleset_matcher import RuleConditionsSpec, RuleSpec

from cmk.gui.http import request

# TODO: find a location for these imports (maybe cmk.gui.quick_setup.v0_unstable.predefined._common)
from cmk.gui.quick_setup.to_frontend import (
    _collect_params_with_defaults_from_form_data,
    _collect_passwords_from_form_data,
    _find_unique_id,
)
from cmk.gui.quick_setup.v0_unstable.definitions import UniqueBundleIDStr
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.wato.pages.activate_changes import ModeActivateChanges
from cmk.gui.watolib.configuration_bundles import (
    BundleId,
    ConfigBundle,
    create_config_bundle,
    CreateBundleEntities,
    CreateHost,
    CreatePassword,
    CreateRule,
)
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import Host
from cmk.gui.watolib.services import get_check_table, perform_fix_all

from cmk.ccc.site import omd_site


def create_host_from_form_data(
    host_name: HostName,
    host_path: str,
) -> CreateHost:
    return CreateHost(
        name=host_name,
        folder=host_path,
        attributes=HostAttributes(
            tag_address_family="no-ip",
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
        ),
    )


def create_and_save_special_agent_bundle(
    special_agent_name: str,
    all_stages_form_data: ParsedFormData,
) -> str:
    return _create_and_save_special_agent_bundle(
        special_agent_name=special_agent_name,
        all_stages_form_data=all_stages_form_data,
        collect_params=_collect_params_with_defaults_from_form_data,
    )


def create_and_save_special_agent_bundle_custom_collect_params(
    special_agent_name: str,
    all_stages_form_data: ParsedFormData,
    custom_collect_params: Callable[[ParsedFormData, str], Mapping[str, object]],
) -> str:
    return _create_and_save_special_agent_bundle(
        special_agent_name=special_agent_name,
        all_stages_form_data=all_stages_form_data,
        collect_params=custom_collect_params,
    )


def _create_and_save_special_agent_bundle(
    special_agent_name: str,
    all_stages_form_data: ParsedFormData,
    collect_params: Callable[[ParsedFormData, str], Mapping[str, object]],
) -> str:
    rulespec_name = RuleGroup.SpecialAgents(special_agent_name)
    bundle_id = _find_unique_id(form_data=all_stages_form_data, target_key=UniqueBundleIDStr)
    if bundle_id is None:
        raise ValueError("No bundle id found")

    host_name = all_stages_form_data[FormSpecId("host_data")]["host_name"]
    host_path = all_stages_form_data[FormSpecId("host_data")]["host_path"]

    site_selection = _find_unique_id(all_stages_form_data, "site_selection")
    params = collect_params(all_stages_form_data, rulespec_name)
    passwords = _collect_passwords_from_form_data(all_stages_form_data, rulespec_name)

    # TODO: DCD still to be implemented cmk-18341
    create_config_bundle(
        bundle_id=BundleId(bundle_id),
        bundle=ConfigBundle(
            title=f"{bundle_id}_config",
            comment="",
            group=rulespec_name,
            program_id=PROGRAM_ID_QUICK_SETUP,
        ),
        entities=CreateBundleEntities(
            hosts=[create_host_from_form_data(host_name=HostName(host_name), host_path=host_path)],
            passwords=create_passwords(
                passwords=passwords,
                rulespec_name=rulespec_name,
                bundle_id=BundleId(bundle_id),
            ),
            rules=[
                create_rule(
                    params=params,
                    host_name=host_name,
                    host_path=host_path,
                    rulespec_name=rulespec_name,
                    bundle_id=BundleId(bundle_id),
                    site_id=SiteId(site_selection) if site_selection else omd_site(),
                )
            ],
        ),
    )

    # TODO: config sync

    host: Host = Host.load_host(host_name)
    perform_fix_all(
        discovery_result=get_check_table(host=host, action=host_name, raise_errors=False),
        host=host,
        raise_errors=False,
    )

    return makeuri_contextless(
        request,
        [("mode", ModeActivateChanges.name())],
        filename="wato.py",
    )
