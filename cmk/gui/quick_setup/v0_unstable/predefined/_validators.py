#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
from functools import partial
from uuid import uuid4

from livestatus import SiteId

from cmk.ccc.site import omd_site

from cmk.utils.hostaddress import HostName

from cmk.gui.i18n import _
from cmk.gui.quick_setup.v0_unstable.definitions import (
    QSHostName,
    QSSiteSelection,
    UniqueBundleIDStr,
)
from cmk.gui.quick_setup.v0_unstable.predefined._common import (
    _collect_params_with_defaults_from_form_data,
    _collect_passwords_from_form_data,
    _create_diag_special_agent_input,
    _find_id_in_form_data,
)
from cmk.gui.quick_setup.v0_unstable.setups import CallableValidator, ProgressLogger, StepStatus
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    GeneralStageErrors,
    ParsedFormData,
    QuickSetupId,
)
from cmk.gui.watolib.check_mk_automations import diag_special_agent
from cmk.gui.watolib.configuration_bundles import ConfigBundleStore
from cmk.gui.watolib.hosts_and_folders import Host

from cmk.rulesets.v1.form_specs import Dictionary


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
    )


def validate_test_connection(
    rulespec_name: str,
    parameter_form: Dictionary,
    error_message: str | None = None,
) -> CallableValidator:
    return partial(
        _validate_test_connection,
        rulespec_name,
        parameter_form,
        _collect_params_with_defaults_from_form_data,
        error_message,
    )


def _validate_test_connection(
    rulespec_name: str,
    parameter_form: Dictionary,
    collect_params: Callable[[ParsedFormData, Dictionary], Mapping[str, object]],
    error_message: str | None,
    _quick_setup_id: QuickSetupId,
    all_stages_form_data: ParsedFormData,
    progress_logger: ProgressLogger,
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
        SiteId(site_id) if site_id else omd_site(),
        _create_diag_special_agent_input(
            rulespec_name=rulespec_name, host_name=host_name, passwords=passwords, params=params
        ),
    )
    progress_logger.update_progress_step_status("test_connection", StepStatus.COMPLETED)
    progress_logger.log_new_progress_step(
        "evaluate_connection_result", "Evaluate test connection result"
    )
    for result in output.results:
        if result.return_code != 0:
            if error_message:
                general_errors.append(error_message)
            # Do not show long output
            general_errors.append(result.response.split("\n")[-1])
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
