#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.form_specs import (
    DEFAULT_VALUE,
    get_visitor,
    RawDiskData,
    registration,
    VisitorOptions,
)
from cmk.gui.form_specs.visitors import register_visitor_class
from cmk.gui.watolib.password_visitor import PasswordVisitor
from cmk.plugins.veeam.rulesets.special_agent import rule_spec_special_agent_veeam
from cmk.rulesets.v1.form_specs import Password

PASSWORD = ("cmk_postprocessed", "explicit_password", ("veeam-password", "secret"))

BASE_RULE = {
    "port": 9419,
    "user": "monitoring",
    "password": PASSWORD,
    "disable_cert_verification": False,
}


@pytest.fixture
def _register_form_spec_visitors() -> None:
    registration.register()
    # The v1 Password form spec's visitor is registered in watolib, not by the
    # default form-spec registration.
    register_visitor_class(Password, PasswordVisitor)


def _validate(rule: dict[str, object]) -> None:
    visitor = get_visitor(
        rule_spec_special_agent_veeam.parameter_form(),
        VisitorOptions(migrate_values=True, mask_values=False),
    )
    assert visitor.validate(RawDiskData(rule)) == []


@pytest.mark.usefixtures("_register_form_spec_visitors")
@pytest.mark.parametrize(
    "connection",
    [
        pytest.param(("ip_address", None), id="IP address of the host"),
        pytest.param(("host_name", None), id="name of the host"),
        pytest.param(("custom_address", "backup.example.com"), id="custom address"),
    ],
)
def test_every_connection_choice_is_accepted(connection: tuple[str, str | None]) -> None:
    _validate({**BASE_RULE, "connection": connection})


@pytest.mark.usefixtures("_register_form_spec_visitors")
@pytest.mark.parametrize(
    "disable_cert_verification",
    [
        pytest.param(False, id="verify the certificate"),
        pytest.param(True, id="skip verification"),
    ],
)
def test_both_certificate_choices_are_accepted(disable_cert_verification: bool) -> None:
    _validate(
        {
            **BASE_RULE,
            "connection": ("ip_address", None),
            "disable_cert_verification": disable_cert_verification,
        }
    )


@pytest.mark.usefixtures("_register_form_spec_visitors")
def test_the_port_is_prefilled_with_the_veeam_default() -> None:
    port_form = rule_spec_special_agent_veeam.parameter_form().elements["port"].parameter_form
    visitor = get_visitor(port_form, VisitorOptions(migrate_values=False, mask_values=False))

    assert visitor.to_disk(DEFAULT_VALUE) == 9419
