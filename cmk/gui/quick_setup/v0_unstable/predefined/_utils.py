#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence

from livestatus import SiteId

from cmk.ccc.site import omd_site

from cmk.automations.results import SpecialAgentDiscoveryPreviewResult

from cmk.checkengine.discovery import CheckPreviewEntry

from cmk.gui.quick_setup.v0_unstable.definitions import QSHostName, QSSiteSelection
from cmk.gui.quick_setup.v0_unstable.predefined._common import (
    _collect_passwords_from_form_data,
    _create_diag_special_agent_input,
    _find_id_in_form_data,
    _match_service_interest,
)
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    ParsedFormData,
    ServiceInterest,
)
from cmk.gui.watolib.check_mk_automations import special_agent_discovery_preview

from cmk.rulesets.v1.form_specs import Dictionary


def get_service_discovery_preview(
    rulespec_name: str,
    all_stages_form_data: ParsedFormData,
    parameter_form: Dictionary,
    collect_params: Callable[[ParsedFormData, Dictionary], Mapping[str, object]],
) -> SpecialAgentDiscoveryPreviewResult:
    params = collect_params(all_stages_form_data, parameter_form)
    passwords = _collect_passwords_from_form_data(all_stages_form_data, parameter_form)
    site_id = _find_id_in_form_data(all_stages_form_data, QSSiteSelection)
    host_name = _find_id_in_form_data(all_stages_form_data, QSHostName)

    service_discovery_result = special_agent_discovery_preview(
        SiteId(site_id) if site_id else omd_site(),
        _create_diag_special_agent_input(
            rulespec_name=rulespec_name, host_name=host_name, passwords=passwords, params=params
        ),
    )
    return service_discovery_result


def group_services_by_interest(
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
