#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
from functools import partial
from uuid import uuid4

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site, SiteId

from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.quick_setup.v0_unstable.definitions import (
    QSHostName,
    QSHostPath,
    QSSiteSelection,
    UniqueBundleIDStr,
)
from cmk.gui.quick_setup.v0_unstable.predefined._common import (
    _collect_passwords_from_form_data,
    _create_diag_special_agent_input,
    _find_id_in_form_data,
)
from cmk.gui.quick_setup.v0_unstable.predefined._utils import (
    existing_folder_from_path,
    normalize_folder_path_str,
)
from cmk.gui.quick_setup.v0_unstable.setups import CallableValidator, ProgressLogger, StepStatus
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    GeneralStageErrors,
    ParsedFormData,
    QuickSetupId,
)
from cmk.gui.watolib.automations import make_automation_config
from cmk.gui.watolib.check_mk_automations import diag_special_agent
from cmk.gui.watolib.configuration_bundle_store import ConfigBundleStore, is_locked_by_quick_setup
from cmk.gui.watolib.hosts_and_folders import _normalize_folder_name, folder_tree, Host
from cmk.gui.watolib.passwords import load_passwords

from cmk.rulesets.v1.form_specs import Dictionary, Password


def validate_test_connection_custom_collect_params(
    rulespec_name: str,
    parameter_form: Dictionary,
    custom_collect_params: Callable[[ParsedFormData, Dictionary], Mapping[str, object]],
    error_message: str | None = None,
) -> CallableValidator:
    return partial(
        _validate_test_connection,
        rulespec_name,
        parameter_form,
        custom_collect_params,
        error_message,
        debug=active_config.debug,
    )


def validate_non_quick_setup_password(parameter_form: Dictionary) -> CallableValidator:
    return partial(_validate_non_quick_setup_password, parameter_form)


def _validate_non_quick_setup_password(
    parameter_form: Dictionary,
    _quick_setup_id: QuickSetupId,
    all_stages_form_data: ParsedFormData,
    _progress_logger: ProgressLogger,
) -> GeneralStageErrors:
    general_errors: GeneralStageErrors = []
    possible_expected_password_keys = [
        key
        for key in parameter_form.elements.keys()
        if isinstance(parameter_form.elements[key].parameter_form, Password)
    ]

    for form_data in all_stages_form_data.values():
        if not isinstance(form_data, dict):
            continue

        for form_spec_id, form_spec_value in form_data.items():
            if not (
                form_spec_id in possible_expected_password_keys
                and form_spec_value[0] == "cmk_postprocessed"
                and form_spec_value[1] == "stored_password"
            ):
                continue

            pw_from_store = load_passwords()[form_spec_value[2][0]]
            if ("locked_by" in pw_from_store) and (
                is_locked_by_quick_setup(pw_from_store["locked_by"])
            ):
                general_errors.append(
                    f'Password with title "{pw_from_store["title"]}" is locked by a Quick '
                    "Setup and cannot be used."
                )

    return general_errors


def _validate_test_connection(
    rulespec_name: str,
    parameter_form: Dictionary,
    collect_params: Callable[[ParsedFormData, Dictionary], Mapping[str, object]],
    error_message: str | None,
    _quick_setup_id: QuickSetupId,
    all_stages_form_data: ParsedFormData,
    progress_logger: ProgressLogger,
    *,
    debug: bool,
) -> GeneralStageErrors:
    general_errors: GeneralStageErrors = []
    progress_logger.log_new_progress_step("parse_config", "Parse the connection configuration data")
    site_id = _find_id_in_form_data(all_stages_form_data, QSSiteSelection)
    host_name = _find_id_in_form_data(all_stages_form_data, QSHostName) or str(uuid4())
    params = collect_params(all_stages_form_data, parameter_form)
    passwords = _collect_passwords_from_form_data(all_stages_form_data, parameter_form)
    progress_logger.update_progress_step_status("parse_config", StepStatus.COMPLETED)
    progress_logger.log_new_progress_step(
        "test_connection", "Use input data to test connection to datasource"
    )
    output = diag_special_agent(
        make_automation_config(active_config.sites[SiteId(site_id) if site_id else omd_site()]),
        _create_diag_special_agent_input(
            rulespec_name=rulespec_name,
            host_name=host_name,
            passwords=passwords,
            params=params,
        ),
        debug=debug,
    )
    progress_logger.update_progress_step_status("test_connection", StepStatus.COMPLETED)
    progress_logger.log_new_progress_step(
        "evaluate_connection_result", "Evaluate test connection result"
    )

    for result in output.results:
        if result.return_code != 0:
            # Pass on either the first line of output for known connection test errors or the last
            # line in all other cases
            output_lines: list[str] = result.response.split("\n")
            relevant_output = (
                output_lines[0]
                if output_lines[0].startswith("Agent exited with code 2: Connection failed")
                else output_lines[-1]
            )
            if error_message:
                general_errors.append(error_message)
            general_errors.append(relevant_output)
    progress_logger.update_progress_step_status("evaluate_connection_result", StepStatus.COMPLETED)
    return general_errors


def validate_unique_id(
    _quick_setup_id: QuickSetupId,
    stages_form_data: ParsedFormData,
    _progress_logger: ProgressLogger,
) -> GeneralStageErrors:
    bundle_id = _find_id_in_form_data(stages_form_data, UniqueBundleIDStr)
    if bundle_id is None:
        return [f"Expected the key '{UniqueBundleIDStr}' in the form data."]

    if bundle_id in ConfigBundleStore().load_for_reading():
        return [f'Configuration bundle "{bundle_id}" already exists.']

    return []


def validate_host_name_doesnt_exists(
    _quick_setup_id: QuickSetupId,
    stages_form_data: ParsedFormData,
    _progress_logger: ProgressLogger,
) -> GeneralStageErrors:
    host_name = _find_id_in_form_data(stages_form_data, QSHostName)
    assert host_name is not None
    host = Host.host(HostName(host_name))
    if host:
        return [
            _(
                "A host with the name %s already exists in the folder %s. "
                "Please choose a different host name."
            )
            % (host_name, host.folder().alias_path())
        ]

    return []


def validate_host_path_permissions(
    _quick_setup_id: QuickSetupId,
    stages_form_data: ParsedFormData,
    _progress_logger: ProgressLogger,
) -> GeneralStageErrors:
    host_path = _find_id_in_form_data(stages_form_data, QSHostPath)
    assert host_path is not None

    sanitized_folder_path = normalize_folder_path_str(host_path)
    if folder := existing_folder_from_path(sanitized_folder_path):
        has_permissions = folder.permissions.may("write")
    else:
        # If the folder does not exist, we need to check if the user has permissions to create it
        # in the potential parent folder
        folder = folder_tree().root_folder()
        for title in sanitized_folder_path.split("/"):
            name = _normalize_folder_name(title)
            potential_sub_folder = folder.subfolder_by_title(title) or folder.subfolder(name)
            if potential_sub_folder is None:
                break
            folder = potential_sub_folder
        has_permissions = folder.permissions.may("write")

    if not has_permissions:
        return [
            _(
                "You do not have permission to create a new host in the folder %s. "
                "Please choose a different folder."
            )
            % (folder.alias_path())
        ]
    return []
