#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.splunk.rulesets.license_state import rule_spec_check_parameters
from cmk.rulesets.v1.form_specs import Dictionary


@pytest.mark.parametrize(
    ["value", "expected"],
    [
        pytest.param(
            (1209600, 604800),
            ("fixed", (1209600, 604800)),
            id="2.3 rule",
        ),
        pytest.param(
            (1209600, 0),
            ("fixed", (1209600, 0)),
            id="2.3 rule, zero crit level",
        ),
        pytest.param(
            ("fixed", (1209600, 604800)),
            ("fixed", (1209600, 604800)),
            id="2.4 rule",
        ),
    ],
)
def test_migrate_expiration_time(value: object, expected: object) -> None:
    form = rule_spec_check_parameters.parameter_form()
    assert isinstance(form, Dictionary)
    migrate = form.elements["expiration_time"].parameter_form.migrate
    assert migrate is not None
    assert migrate(value) == expected
