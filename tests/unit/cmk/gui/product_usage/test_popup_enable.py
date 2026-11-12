#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition
from cmk.gui.form_specs import get_visitor, RawFrontendData, VisitorOptions
from cmk.gui.product_usage_analytics.global_config import (
    make_product_usage_analytics_config_variable,
)
from cmk.gui.product_usage_analytics.popup import ENABLED_CHOICE_ID
from cmk.gui.watolib.config_domain_name import GlobalSettingsContext
from cmk.livestatus_client import SiteConfigurations
from cmk.rulesets.v1.form_specs import Dictionary


def test_enabling_in_the_popup_stores_enabled_in_the_global_setting() -> None:
    form_spec = make_product_usage_analytics_config_variable().value_model(
        GlobalSettingsContext(
            target_site_id=SiteId("mysite"),
            edition_of_local_site=Edition.COMMUNITY,
            site_neutral_log_dir=Path("/tmp"),
            site_neutral_var_dir=Path("/tmp"),
            configured_sites=SiteConfigurations({}),
            configured_graph_timeranges=[],
            folder_choices=lambda: [("", "Main")],
        )
    )
    assert isinstance(form_spec, Dictionary)
    visitor = get_visitor(
        form_spec.elements["enabled"].parameter_form,
        VisitorOptions(migrate_values=False, mask_values=False),
    )

    stored = visitor.to_disk(RawFrontendData(ENABLED_CHOICE_ID))

    assert stored == "enabled"
