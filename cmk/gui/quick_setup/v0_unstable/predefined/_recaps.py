#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from functools import partial

from livestatus import SiteId

from cmk.ccc.site import omd_site

from cmk.automations.results import SpecialAgentDiscoveryPreviewResult

from cmk.checkengine.discovery import CheckPreviewEntry

from cmk.gui.form_specs.vue.form_spec_visitor import serialize_data_for_frontend
from cmk.gui.form_specs.vue.visitors import DataOrigin
from cmk.gui.i18n import ungettext
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.quick_setup.v0_unstable.predefined._common import (
    _collect_params_with_defaults_from_form_data,
    _collect_passwords_from_form_data,
    _create_diag_special_agent_input,
    _find_unique_id,
    _match_service_interest,
    build_quick_setup_formspec_map,
)
from cmk.gui.quick_setup.v0_unstable.setups import CallableRecap
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    ParsedFormData,
    QuickSetupId,
    ServiceInterest,
    StageIndex,
)
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecRecap, ListOfWidgets, Text, Widget
from cmk.gui.watolib.check_mk_automations import special_agent_discovery_preview


def recaps_form_spec(
    quick_setup_id: QuickSetupId,
    stage_index: StageIndex,
    parsed_form_data: ParsedFormData,
) -> Sequence[Widget]:

    quick_setup = quick_setup_registry.get(quick_setup_id)
    if quick_setup is None:
        raise ValueError(f"Quick setup with id {quick_setup_id} not found")

    quick_setup_formspec_map = build_quick_setup_formspec_map([quick_setup.stages[stage_index]])

    return [
        FormSpecRecap(
            id=form_spec_id,
            form_spec=serialize_data_for_frontend(
                form_spec=quick_setup_formspec_map[form_spec_id],
                field_id=form_spec_id,
                origin=DataOrigin.DISK,
                do_validate=False,
                value=form_data,
            ),
        )
        for form_spec_id, form_data in parsed_form_data.items()
        if form_spec_id in quick_setup_formspec_map
    ]


def recap_service_discovery_custom_collect_params(
    rulespec_name: str,
    services_of_interest: Sequence[ServiceInterest],
    custom_collect_params: Callable[[ParsedFormData, str], Mapping[str, object]],
) -> CallableRecap:
    return partial(
        _recap_service_discovery,
        rulespec_name,
        services_of_interest,
        custom_collect_params,
    )


def recap_service_discovery(
    rulespec_name: str,
    services_of_interest: Sequence[ServiceInterest],
) -> CallableRecap:
    return partial(
        _recap_service_discovery,
        rulespec_name,
        services_of_interest,
        _collect_params_with_defaults_from_form_data,
    )


def _recap_service_discovery(
    rulespec_name: str,
    services_of_interest: Sequence[ServiceInterest],
    collect_params: Callable[[ParsedFormData, str], Mapping[str, object]],
    _quick_setup_id: QuickSetupId,
    _stage_index: StageIndex,
    all_stages_form_data: ParsedFormData,
) -> Sequence[Widget]:
    params = collect_params(all_stages_form_data, rulespec_name)
    passwords = _collect_passwords_from_form_data(all_stages_form_data, rulespec_name)
    site_id = _find_unique_id(all_stages_form_data, "site_selection")
    host_name = _find_unique_id(all_stages_form_data, "host_name")

    service_discovery_result = special_agent_discovery_preview(
        SiteId(site_id) if site_id else omd_site(),
        _create_diag_special_agent_input(
            rulespec_name=rulespec_name, host_name=host_name, passwords=passwords, params=params
        ),
    )
    check_preview_entry_by_service_interest, others = _check_preview_entry_by_service_interest(
        services_of_interest, service_discovery_result
    )
    items: list[Widget] = [
        Text(
            text=f"{len(check_preview_entries)} {service_interest.label}",
        )
        for service_interest, check_preview_entries in check_preview_entry_by_service_interest.items()
    ]
    if len(others) >= 1:
        items.append(Text(text=ungettext("%s other service", "%s other services", len(others))))

    return [ListOfWidgets(items=items, list_type="check")]


def _check_preview_entry_by_service_interest(
    services_of_interest: Sequence[ServiceInterest],
    service_discovery_result: SpecialAgentDiscoveryPreviewResult,
) -> tuple[Mapping[ServiceInterest, list[CheckPreviewEntry]], list[CheckPreviewEntry]]:
    check_preview_entry_by_service_interest: Mapping[ServiceInterest, list[CheckPreviewEntry]] = {
        si: [] for si in services_of_interest
    }
    others: list[CheckPreviewEntry] = []
    for check_preview_entry in service_discovery_result.check_table:
        if matching_services_interests := _match_service_interest(
            check_preview_entry, services_of_interest
        ):
            check_preview_entry_by_service_interest[matching_services_interests].append(
                check_preview_entry
            )
        else:
            others.append(check_preview_entry)
    return check_preview_entry_by_service_interest, others
