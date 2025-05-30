#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from livestatus import SiteConfiguration

from cmk.ccc.site import SiteId

from cmk.gui.form_specs.vue.form_spec_visitor import serialize_data_for_frontend
from cmk.gui.form_specs.vue.visitors import DataOrigin
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.quick_setup.v0_unstable.predefined._common import (
    build_formspec_map_from_stages,
)
from cmk.gui.quick_setup.v0_unstable.setups import ProgressLogger
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    ParsedFormData,
    QuickSetupId,
    StageIndex,
)
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecRecap, Widget


def recaps_form_spec(
    quick_setup_id: QuickSetupId,
    stage_index: StageIndex,
    parsed_form_data: ParsedFormData,
    _progress_logger: ProgressLogger,
    site_configs: Mapping[SiteId, SiteConfiguration],
    debug: bool,
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
