#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.cmk.web_test_app import SetConfig

from cmk.ccc.site import omd_site

from cmk.gui.config import active_config
from cmk.gui.form_specs.vue.visitors import DataOrigin, get_visitor, VisitorOptions
from cmk.gui.quick_setup.v0_unstable.definitions import QSSiteSelection
from cmk.gui.quick_setup.v0_unstable.predefined import widgets

from cmk.rulesets.v1.form_specs import FormSpec


@pytest.mark.usefixtures("with_admin_login")
def test_site_selection_accepts_site_named_like_python_keyword(set_config: SetConfig) -> None:
    keyword_site = {**active_config.sites[omd_site()], "id": "global", "alias": "Global"}
    with set_config(sites={**active_config.sites, "global": keyword_site}):
        form_spec = widgets.site_formspec_wrapper().form_spec

    assert isinstance(form_spec, FormSpec)
    errors = get_visitor(form_spec, VisitorOptions(data_origin=DataOrigin.DISK)).validate(
        {QSSiteSelection: "global"}
    )

    assert not errors
