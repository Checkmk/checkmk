#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from functools import partial

from cmk.gui.form_specs.vue.form_spec_visitor import serialize_data_for_frontend
from cmk.gui.form_specs.vue.visitors import DataOrigin
from cmk.gui.i18n import ungettext
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.quick_setup.v0_unstable.predefined._common import (
    _collect_params_with_defaults_from_form_data,
    build_formspec_map_from_stages,
)
from cmk.gui.quick_setup.v0_unstable.predefined._utils import (
    get_service_discovery_preview,
    group_services_by_interest,
)
from cmk.gui.quick_setup.v0_unstable.setups import CallableRecap, ProgressLogger
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    ParsedFormData,
    QuickSetupId,
    ServiceInterest,
    StageIndex,
)
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecRecap, ListOfWidgets, Text, Widget

from cmk.rulesets.v1.form_specs import Dictionary


def recaps_form_spec(
    quick_setup_id: QuickSetupId,
    stage_index: StageIndex,
    parsed_form_data: ParsedFormData,
    _progress_logger: ProgressLogger,
) -> Sequence[Widget]:
    quick_setup = quick_setup_registry.get(quick_setup_id)
    if quick_setup is None:
        raise ValueError(f"Quick setup with id {quick_setup_id} not found")

    quick_setup_formspec_map = build_formspec_map_from_stages([quick_setup.stages[stage_index]()])

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
    parameter_form: Dictionary,
    services_of_interest: Sequence[ServiceInterest],
    custom_collect_params: Callable[[ParsedFormData, Dictionary], Mapping[str, object]],
) -> CallableRecap:
    return partial(
        _recap_service_discovery,
        rulespec_name,
        parameter_form,
        services_of_interest,
        custom_collect_params,
    )


def recap_service_discovery(
    rulespec_name: str,
    parameter_form: Dictionary,
    services_of_interest: Sequence[ServiceInterest],
) -> CallableRecap:
    return partial(
        _recap_service_discovery,
        rulespec_name,
        parameter_form,
        services_of_interest,
        _collect_params_with_defaults_from_form_data,
    )


def _recap_service_discovery(
    rulespec_name: str,
    parameter_form: Dictionary,
    services_of_interest: Sequence[ServiceInterest],
    collect_params: Callable[[ParsedFormData, Dictionary], Mapping[str, object]],
    _quick_setup_id: QuickSetupId,
    _stage_index: StageIndex,
    all_stages_form_data: ParsedFormData,
) -> Sequence[Widget]:
    service_discovery_result = get_service_discovery_preview(
        rulespec_name=rulespec_name,
        all_stages_form_data=all_stages_form_data,
        parameter_form=parameter_form,
        collect_params=collect_params,
    )
    check_preview_entry_by_service_interest, others = group_services_by_interest(
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
