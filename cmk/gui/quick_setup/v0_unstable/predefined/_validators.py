#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
from functools import partial

from livestatus import SiteId

from cmk.ccc.site import omd_site

from cmk.gui.quick_setup.v0_unstable.definitions import UniqueBundleIDStr
from cmk.gui.quick_setup.v0_unstable.predefined._common import (
    _collect_params_with_defaults_from_form_data,
    _collect_passwords_from_form_data,
    _create_diag_special_agent_input,
    _find_unique_id,
)
from cmk.gui.quick_setup.v0_unstable.setups import CallableValidator
from cmk.gui.quick_setup.v0_unstable.type_defs import GeneralStageErrors, ParsedFormData
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId
from cmk.gui.watolib.check_mk_automations import diag_special_agent
from cmk.gui.watolib.configuration_bundles import ConfigBundleStore

from cmk.rulesets.v1.form_specs import FormSpec


def validate_test_connection_custom_collect_params(
    rulespec_name: str, custom_collect_params: Callable[[ParsedFormData, str], Mapping[str, object]]
) -> CallableValidator:
    return partial(
        _validate_test_connection,
        rulespec_name,
        custom_collect_params,
    )


def validate_test_connection(rulespec_name: str) -> CallableValidator:
    return partial(
        _validate_test_connection,
        rulespec_name,
        _collect_params_with_defaults_from_form_data,
    )


def _validate_test_connection(
    rulespec_name: str,
    collect_params: Callable[[ParsedFormData, str], Mapping[str, object]],
    all_stages_form_data: ParsedFormData,
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> GeneralStageErrors:
    general_errors: GeneralStageErrors = []
    site_id = _find_unique_id(all_stages_form_data, "site_selection")
    host_name = _find_unique_id(all_stages_form_data, "host_name")
    params = collect_params(all_stages_form_data, rulespec_name)
    passwords = _collect_passwords_from_form_data(all_stages_form_data, rulespec_name)
    output = diag_special_agent(
        SiteId(site_id) if site_id else omd_site(),
        _create_diag_special_agent_input(
            rulespec_name=rulespec_name, host_name=host_name, passwords=passwords, params=params
        ),
    )
    for result in output.results:
        if result.return_code != 0:
            general_errors.append(result.response)
    return general_errors


def validate_unique_id(
    stages_form_data: ParsedFormData,
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> GeneralStageErrors:
    bundle_id = _find_unique_id(stages_form_data, UniqueBundleIDStr)
    if bundle_id is None:
        return [f"Expected the key '{UniqueBundleIDStr}' in the form data"]

    if bundle_id in ConfigBundleStore().load_for_reading():
        return [f'Configuration bundle "{bundle_id}" already exists.']

    return []
