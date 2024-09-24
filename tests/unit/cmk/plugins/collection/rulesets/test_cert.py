#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.version import Edition

from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec

from cmk.plugins.collection.rulesets.cert import (
    ensure_service_name_in_connections,
    migrate_from_old_signature_keys,
    rule_spec_cert,
)


@pytest.mark.parametrize(
    "raw_value, expected_value",
    [
        pytest.param(
            (
                {
                    "connections": [{"address": "host", "port": 100}],
                    "standard_settings": {"port": 50},
                }
            ),
            (
                {
                    "connections": [
                        {
                            "address": "host",
                            "port": 100,
                            "service_name": {"name": "host:100", "prefix": "auto"},
                        }
                    ],
                    "standard_settings": {"port": 50},
                }
            ),
            id="single service",
        ),
        pytest.param(
            ({"connections": [{"address": "host"}], "standard_settings": {"port": 50}}),
            (
                {
                    "connections": [
                        {
                            "address": "host",
                            "service_name": {"name": "host:50", "prefix": "auto"},
                        }
                    ],
                    "standard_settings": {"port": 50},
                }
            ),
            id="single service without port",
        ),
        pytest.param(
            (
                {
                    "connections": [
                        {"address": "host1", "port": 55},
                        {"address": "host2"},
                        {
                            "address": "host3",
                            "port": 7,
                            "individual_settings": {
                                "response_time": ("fixed", (0.1, 0.2)),
                                "validity": {
                                    "remaining": ("fixed", (3456000.0, 1728000.0)),
                                    "self_signed": False,
                                },
                                "cert_details": {"serialnumber": "asdasd"},
                            },
                        },
                    ],
                    "standard_settings": {"port": 443},
                }
            ),
            (
                {
                    "connections": [
                        {
                            "address": "host1",
                            "port": 55,
                            "service_name": {"name": "host1:55", "prefix": "auto"},
                        },
                        {
                            "address": "host2",
                            "service_name": {"name": "host2:443", "prefix": "auto"},
                        },
                        {
                            "address": "host3",
                            "individual_settings": {
                                "cert_details": {"serialnumber": "asdasd"},
                                "response_time": ("fixed", (0.1, 0.2)),
                                "validity": {
                                    "remaining": ("fixed", (3456000.0, 1728000.0)),
                                    "self_signed": False,
                                },
                            },
                            "port": 7,
                            "service_name": {"name": "host3:7", "prefix": "auto"},
                        },
                    ],
                    "standard_settings": {"port": 443},
                }
            ),
            id="multiple services",
        ),
    ],
)
def test_rulespec_migration(
    raw_value: dict[str, object], expected_value: dict[str, object] | None
) -> None:
    assert ensure_service_name_in_connections(raw_value) == expected_value

    validating_rule_spec = convert_to_legacy_rulespec(rule_spec_cert, Edition.CRE, lambda x: x)
    validating_rule_spec.valuespec.validate_datatype(raw_value, "")
    validating_rule_spec.valuespec.validate_value(raw_value, "")


@pytest.mark.parametrize(
    "raw_value, expected_value",
    [
        pytest.param(
            ("rsa", ("sha3_224", "sha3_224")),
            ("RSA_WITH_SHA224", "1.2.840.113549.1.1.14"),
            id="Signature rsa",
        ),
        pytest.param(
            ("ed25519", None),
            ("ED25519", "1.3.101.112"),
            id="Signature ed25519",
        ),
        pytest.param(
            ("rsassa_pss", ("sha3_384", "sha3_384")),
            ("RSASSA_PSS", "1.2.840.113549.1.1.10"),
            id="Signature rsassa_pss",
        ),
    ],
)
def test_cert_signature_migration(
    raw_value: tuple[str, object], expected_value: tuple[str, object] | None
) -> None:
    assert migrate_from_old_signature_keys(raw_value) == expected_value
