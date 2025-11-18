#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from livestatus import SiteConfigurations

from cmk.ccc.site import SiteId
from cmk.gui.cmkcert import (
    _run_cmkcert,
    CertificateType,
)
from cmk.gui.config import Config


@pytest.fixture(name="certificate_directory")
def fixture_certificate_directory(tmp_path: Path) -> Path:
    return tmp_path


def _site_id():
    return "test_site"


def _dummy_certificate():
    return """-----BEGIN CERTIFICATE-----
MIICRjCCAa+gAwIBAgIUIzp8u+4nxaYgZwyOUGJS8j/4yUAwDQYJKoZIhvcNAQEN
BQAwOzEdMBsGA1UEAwwUU2l0ZSAndjI1MCcgbG9jYWwgQ0ExGjAYBgNVBAoMEUNo
ZWNrbWsgU2l0ZSB2MjUwMCAXDTI1MDgwODA3MjExN1oYDzIwNTIxMjIzMDcyMTE3
WjA7MR0wGwYDVQQDDBRTaXRlICd2MjUwJyBsb2NhbCBDQTEaMBgGA1UECgwRQ2hl
Y2ttayBTaXRlIHYyNTAwgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAMn1UiDK
NT3B/woiOEqV0nDpoZf6RND98UsFVf7QmzYnsRoSCKulFpJOmLLJqcZWnNhPPR+s
AuFrOMC9BXdOQFCRG48XzHN8tP3tbNHFt4F6hGLJMZCXmeAolxeGBxcY1eYLxuw0
CD61mjy043ft/C+Qxg6paxdi2eaBeveyFySxAgMBAAGjRTBDMBIGA1UdEwEB/wQI
MAYBAf8CAQAwHQYDVR0OBBYEFIQRSx/cHJE904wSPdCC4QwVqyREMA4GA1UdDwEB
/wQEAwIBBjANBgkqhkiG9w0BAQ0FAAOBgQBc3tkQmugWuO7Xyj5EQ9Je3SxUYKR6
qU5sQQ76fOT9hRcQvhszZKqRFj2flvNs/lCf1JMrOGbBgAWceGmrlubaJgK/MGbf
eGAPlxJ2poGukdPO/ae6pEDcwK7zz6nA2PxmvcAZmm5/BAlxA7NYjJaXG/TPcOBh
51Q0/VZEBkeOUw==
-----END CERTIFICATE-----"""


def _dummy_key():
    return """-----BEGIN PRIVATE KEY-----
MIICeAIBADANBgkqhkiG9w0BAQEFAASCAmIwggJeAgEAAoGBAMn1UiDKNT3B/woi
OEqV0nDpoZf6RND98UsFVf7QmzYnsRoSCKulFpJOmLLJqcZWnNhPPR+sAuFrOMC9
BXdOQFCRG48XzHN8tP3tbNHFt4F6hGLJMZCXmeAolxeGBxcY1eYLxuw0CD61mjy0
43ft/C+Qxg6paxdi2eaBeveyFySxAgMBAAECgYAGDWAEs4qc6y9lclkVgx/nWlkJ
YOqnCLUudl55YG8GVHIuQdQYsL3YbJqO4RRBaV8R7G38gP8lGj19KSz8wk+TDN8c
4J0Rg0C4RqjEyzH0ePA7Z/sUqOWUZVLZevNBxSvOTnTLe22Gz2X1eyITxh83QpLm
hXVhZc5L+KGW9+gdQQJBAPFihTqnOyJxKCLAdCL3Ai6sAmwFBcEtfxpLJI3o5ctX
hNpYk/wtvUwmcboHZPOdwlXZENqZvYSnw8cZpNf2dR0CQQDWL6+zLlPxsm4d9W5T
JKWAacxDTU5cIJwdg+SoP/0bwbTXWTyORZ59Kim6yXJdkEyryN+FULfSw+RNNQ7g
gP2lAkEAjyWe3r6nqfAzHhDFjqqvR6BIO2jrFbl2Y9BmGCYiiGkZZycac3Voig1O
akTSUEqhIan9fbWol0+qIZuKj2wf3QJBAKz5f/zF+lckkZeyQTH2U458YtErmo/+
afXQMZbLbp6+9kxALg58HP3aUi8eRzVWtwS4ygNBZ+NX/oV3xxb6NV0CQQDlv4oH
G0tQIZb1B4/CrCbBnh69L0RGt3h7y906lRuVV0Ng/Mj5Sj8R+R/wVqEcNylRXhSE
VXzJSdPU5tH3gi42
-----END PRIVATE KEY-----"""


@pytest.fixture(name="dummy_site_ca")
def fixture_dummy_site_ca() -> str:
    return f"{_dummy_key()}\n{_dummy_certificate()}"


def test_site_ca_doesnt_exist(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        _run_cmkcert(
            omd_root=tmp_path,
            site_id=_site_id(),
            target_certificate="site",
            expiry=90,
            finalize=True,
        )


@pytest.mark.parametrize(
    "target_certificate, target_cert_path",
    [
        ("site-ca", Path("etc/ssl/ca.pem")),
        ("site", Path(f"etc/ssl/sites/{_site_id()}.pem")),
        ("agent-ca", Path("etc/ssl/agents/ca.pem")),
    ],
)
@patch("cmk.gui.cmkcert.load_config")
@patch("cmk.gui.cmkcert.load_configuration_settings")
@patch("cmk.gui.cmkcert.save_global_settings")
@patch("cmk.gui.cmkcert._changes")
def test_replace(  # type: ignore[misc]
    mock__changes: Mock,
    mock_save_global_settings: Mock,
    mock_load_configuration_settings: Mock,
    mock_load_config: Mock,
    tmp_path: Path,
    target_certificate: CertificateType,
    target_cert_path: str,
    dummy_site_ca: str,
) -> None:
    mock_load_configuration_settings.return_value = {
        "trusted_certificate_authorities": {"trusted_cas": [], "use_system_wide_cas": False}
    }
    mock_load_config.return_value = Config(
        sites=SiteConfigurations(
            {
                SiteId("test_site"): {
                    "alias": "Local site test_site",
                    "disable_wato": True,
                    "disabled": False,
                    "id": SiteId("test_site"),
                    "insecure": False,
                    "message_broker_port": 5672,
                    "multisiteurl": "",
                    "persist": False,
                    "proxy": None,
                    "replicate_ec": False,
                    "replicate_mkps": False,
                    "replication": None,
                    "socket": ("local", None),
                    "status_host": None,
                    "timeout": 5,
                    "url_prefix": "/test_site/",
                    "user_login": True,
                    "user_sync": "all",
                    "is_trusted": True,
                }
            }
        )
    )

    if target_certificate in ["site", "site-ca"]:
        site_ca_path = tmp_path / Path("etc/ssl/ca.pem")
        site_ca_path.parent.mkdir(parents=True, exist_ok=True)
        site_ca_path.write_text(dummy_site_ca)

    _run_cmkcert(
        omd_root=tmp_path,
        site_id=_site_id(),
        target_certificate=target_certificate,
        expiry=90,
        finalize=False,
    )

    if target_certificate == "site-ca":
        mock_save_global_settings.assert_called_once()
        mock__changes.add_change.assert_called_once()

    # site-ca rotation requires a second call with finalize=True to complete the rotation
    if target_certificate == "site-ca":
        _run_cmkcert(
            omd_root=tmp_path,
            site_id=_site_id(),
            target_certificate=target_certificate,
            expiry=90,
            finalize=True,
        )

    assert "BEGIN CERTIFICATE" in (tmp_path / target_cert_path).read_text()
