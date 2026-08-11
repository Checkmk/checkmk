#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.generic_agent_options.rulesets.agent_controller import (
    _validate_certificate,
    migrate,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError


@pytest.mark.parametrize(
    "value,expected",
    [
        # Old format: (True, {}) tuple
        (
            {"agent_ctl_enabled": (True, {})},
            {"agent_ctl_enabled": ("enabled", {})},
        ),
        # Old format: (True, {"detect_proxy": True}) tuple
        (
            {"agent_ctl_enabled": (True, {"detect_proxy": True})},
            {"agent_ctl_enabled": ("enabled", {"detect_proxy": True})},
        ),
        # Old format: (False, None) tuple
        (
            {"agent_ctl_enabled": (False, None)},
            {"agent_ctl_enabled": ("disabled", None)},
        ),
        # Already migrated: enabled
        (
            {"agent_ctl_enabled": ("enabled", {})},
            {"agent_ctl_enabled": ("enabled", {})},
        ),
        # Already migrated: disabled
        (
            {"agent_ctl_enabled": ("disabled", None)},
            {"agent_ctl_enabled": ("disabled", None)},
        ),
        # No agent_ctl_enabled key: pass through
        (
            {"other_key": "value"},
            {"other_key": "value"},
        ),
    ],
)
def test_migrate(value: object, expected: object) -> None:
    assert migrate(value) == expected


_CERT_PEM = """-----BEGIN CERTIFICATE-----
MIIDJzCCAg+gAwIBAgIUZdMlfmyW9c/sQmsj2JvQGcETY6swDQYJKoZIhvcNAQEL
BQAwKTEnMCUGA1UEAwweU2l0ZSAnaGV1dGVfcmVtb3RlXzEnIGxvY2FsIENBMCAX
DTIyMTAyMTE5NTY0OVoYDzMwMjEwMjIxMTk1NjQ5WjApMScwJQYDVQQDDB5TaXRl
ICdoZXV0ZV9yZW1vdGVfMScgbG9jYWwgQ0EwggEiMA0GCSqGSIb3DQEBAQUAA4IB
DwAwggEKAoIBAQDIFNGAu9upENKMjtyjwWBSpNzCizY8x7GWcdCVmQtIMxnmPu7d
+/zvKdSraVVRiL14BH3entj852YYbPxhUWWyamzUZULZMPykADsiT+ZDqGnqlvbr
N2tDos2r6TG17ttLbSxEa+q7nbJbW606yxNuTzBpD1ab5SoRZDH8wqv52ZRl7e2t
PQEgjE6ZP549BNCei80cNpUXmBxsOZ9nkR0/1iTlKweOYZ2rFOkQ4QnDhWYW3luK
npkjFPuFnYkf6LoTo5Bb/LNUynHWAU+C6ODt5X1wB2G2pM9VZeQX98j262wY73DZ
9zKp97y5OWbjG9YqPGFbnXM9jMydbsugYQllAgMBAAGjRTBDMB0GA1UdDgQWBBS8
wu/OK33wfinksRH8PZAryiA+sDASBgNVHRMBAf8ECDAGAQH/AgEAMA4GA1UdDwEB
/wQEAwIBBjANBgkqhkiG9w0BAQsFAAOCAQEAThknEL61UjfmPSmnxzTPIWyva/L0
txxzrxEYDG0hfS/qKvDo/FLMOLzf6EUH+XAYJyCuZYmUl0Xiw89q4eZ2835v/vUq
4VAukxMPZA2cDXHeTfXOOf5VtZ243T/EcFfKjYnXHFUFJSczFV0D0vVDpLt/kSsu
kuTuk3AqVUemMu7hZcT3JisfiXIT+qXRpgYWeDBSLm1vVHRHkBAokwNu+tBpLlRA
A1ibM7hmJZTxbJgFHh6FSLDG+pTEl1Ou6fa4EBTLYl150Z7apkxyOzsDRFPyIbln
lfkHm8yFtG6XWfPWVd2KhVvAd41qpa/jwPQbyXo6rqfR4MfhbAgGtxI+gA==
-----END CERTIFICATE-----
"""


def test_validate_certificate() -> None:
    _validate_certificate(_CERT_PEM)


@pytest.mark.parametrize("value", ["not a certificate", _CERT_PEM.replace("MII", "XXX")])
def test_validate_certificate_rejects(value: str) -> None:
    with pytest.raises(ValidationError):
        _validate_certificate(value)
