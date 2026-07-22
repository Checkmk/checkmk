#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition
from cmk.gui.form_specs import get_visitor, RawFrontendData, VisitorOptions
from cmk.gui.wato._tracing import ConfigVariableSiteTraceSend
from cmk.gui.watolib.config_domain_name import GlobalSettingsContext
from cmk.livestatus_client import SiteConfigurations
from cmk.rulesets.v1.form_specs import FormSpec


def test_site_trace_send_saving_form_selection_keeps_legacy_disk_format() -> None:
    context = GlobalSettingsContext(
        target_site_id=SiteId("test"),
        edition_of_local_site=Edition.COMMUNITY,
        site_neutral_log_dir=Path("/tmp"),
        site_neutral_var_dir=Path("/tmp"),
        configured_sites=SiteConfigurations({}),
        configured_graph_timeranges=[],
    )
    form_spec = ConfigVariableSiteTraceSend.value_model(context)
    assert isinstance(form_spec, FormSpec)
    visitor = get_visitor(
        form_spec,
        VisitorOptions(migrate_values=False, mask_values=False),
    )
    for choice in ("no_tracing", "local_site"):
        assert visitor.to_disk(RawFrontendData((choice, True))) == choice
