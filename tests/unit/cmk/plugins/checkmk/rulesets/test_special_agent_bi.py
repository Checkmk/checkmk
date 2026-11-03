#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.form_specs import get_visitor, RawDiskData, registration, VisitorOptions
from cmk.plugins.checkmk.rulesets.bi import rule_spec_special_agent_bi


@pytest.fixture
def _register_form_spec_visitors() -> None:
    registration.register()


@pytest.mark.usefixtures("_register_form_spec_visitors")
def test_aggr_group_prefix_unknown_to_local_site_is_valid() -> None:
    visitor = get_visitor(
        rule_spec_special_agent_bi.parameter_form(),
        VisitorOptions(migrate_values=True, mask_values=True),
    )
    assert not visitor.validate(
        RawDiskData(
            {
                "options": [
                    {
                        "site": ("local", None),
                        "filter": {"aggr_group_prefix": ["GROUP_OF_OTHER_CUSTOMER"]},
                    }
                ]
            }
        )
    )
