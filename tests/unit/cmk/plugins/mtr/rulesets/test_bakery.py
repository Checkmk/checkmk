#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.mtr.rulesets.mtr import _address_configuration, migrate
from cmk.rulesets.v1.form_specs import String
from cmk.rulesets.v1.form_specs.validators import ValidationError


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(None, {"deployment": ("do_not_deploy", None)}, id="do_not_deploy"),
        pytest.param(
            {"interval": 60, "mtr_config": [{"hostname": "example.com"}]},
            {"deployment": ("cached", 60.0), "mtr_config": [{"hostname": "example.com"}]},
            id="old_config",
        ),
        pytest.param(
            {
                "deployment": ("cached", 120.0),
                "mtr_config": [{"hostname": "example.com"}],
            },
            {
                "deployment": ("cached", 120.0),
                "mtr_config": [{"hostname": "example.com"}],
            },
            id="already_migrated",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


def _validate_destination_address(address: str) -> None:
    hostname = _address_configuration().elements["hostname"].parameter_form
    assert isinstance(hostname, String)
    for validate in hostname.custom_validate or ():
        validate(address)


@pytest.mark.parametrize(
    "address",
    [
        pytest.param("example.com", id="host name"),
        pytest.param("192.168.178.23", id="IPv4 address"),
        pytest.param("fd91:b666:c6a1:0:1:2:3:e588", id="IPv6 address"),
        pytest.param("2001:db8::1", id="abbreviated IPv6 address"),
        pytest.param("::1", id="IPv6 loopback"),
    ],
)
def test_destination_address_valid(address: str) -> None:
    _validate_destination_address(address)


@pytest.mark.parametrize(
    "address",
    [
        pytest.param("", id="empty"),
        pytest.param("semi;colon", id="semicolon is illegal in service names"),
        pytest.param("fe80::1%eth0", id="IPv6 zone ID is not supported"),
    ],
)
def test_destination_address_invalid(address: str) -> None:
    with pytest.raises(ValidationError):
        _validate_destination_address(address)
