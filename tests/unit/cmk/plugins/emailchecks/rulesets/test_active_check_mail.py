#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.emailchecks.rulesets.active_check_mail import rule_spec_mail
from cmk.rulesets.v1.form_specs import Dictionary


@pytest.mark.parametrize(
    "cleanup, expected",
    [
        pytest.param(("delete", "delete"), ("delete", "delete"), id="delete"),
        pytest.param(("move", "INBOX/Processed"), ("move", "INBOX/Processed"), id="move"),
        pytest.param(("move", "1"), ("move", "1"), id="move to folder that looks like a literal"),
        pytest.param(("delete", None), ("delete", "delete"), id="delete from 2.5.0p3"),
        pytest.param(
            ("move", "('delete', 'delete')"),
            ("delete", "delete"),
            id="delete from 2.4.0p22",
        ),
        pytest.param(
            ("move", "('move', \"('move', 'INBOX')\")"),
            ("move", "INBOX"),
            id="move from 2.4.0p22",
        ),
    ],
)
def test_migrate_cleanup(cleanup: object, expected: object) -> None:
    forward_form = rule_spec_mail.parameter_form().elements["forward"].parameter_form
    assert isinstance(forward_form, Dictionary)
    cleanup_form = forward_form.elements["cleanup"].parameter_form
    assert cleanup_form.migrate is not None

    assert cleanup_form.migrate(cleanup) == expected
