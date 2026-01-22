#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pytest_mock import MockerFixture

from livestatus import SiteConfigurations

from cmk.ccc.site import SiteId
from cmk.gui.cmkcert import (
    _certificate_path,
    _run_init,
    _run_rotate,
    CertificateType,
)
from cmk.gui.config import Config
from cmk.utils.certs import cert_dir, SiteCA


@pytest.fixture(name="omd_root")
def fixture_omd_root(tmp_path: Path) -> Path:
    return tmp_path / "test_root"


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


def _dummy_cert_with_key() -> str:
    return f"{_dummy_key()}\n{_dummy_certificate()}"


def _create_dummy(omd_root: Path, target_certificate: CertificateType) -> Path:
    cert_path = _certificate_path(
        omd_root=omd_root,
        site_id=_site_id(),
        target_certificate=target_certificate,
    )
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    cert_path.write_text(_dummy_cert_with_key())
    return cert_path


@pytest.fixture(name="site_ca")
def fixture_site_ca(omd_root: Path) -> Path:
    site_ca_path = SiteCA.root_ca_path(cert_dir(omd_root))
    site_ca_path.parent.mkdir(parents=True, exist_ok=True)
    site_ca_path.write_text(_dummy_cert_with_key())
    return site_ca_path


@pytest.fixture(name="agent_ca")
def fixture_agent_ca(omd_root: Path) -> Path:
    agent_ca_path = _certificate_path(
        omd_root=omd_root,
        site_id=_site_id(),
        target_certificate="agent-ca",
    )
    agent_ca_path.parent.mkdir(parents=True, exist_ok=True)
    agent_ca_path.write_text(_dummy_cert_with_key())
    return agent_ca_path


def _test_init(omd_root: Path, target_cert: CertificateType) -> None:
    site_id = _site_id()
    cert_path = _certificate_path(
        omd_root=omd_root,
        site_id=site_id,
        target_certificate=target_cert,
    )

    assert not cert_path.exists()

    _run_init(
        omd_root=omd_root,
        site_id=site_id,
        target_certificate=target_cert,
        key_size=1024,
    )

    assert cert_path.exists()


@pytest.mark.parametrize(
    "target_cert",
    [
        "site-ca",
        "agent-ca",
    ],
)
def test_init_cas(omd_root: Path, target_cert: CertificateType) -> None:
    _test_init(omd_root, target_cert)


def test_init_site(site_ca: Path, omd_root: Path) -> None:
    _create_dummy(omd_root, "site-ca")
    _test_init(omd_root, "site")


@pytest.mark.parametrize(
    "target_certificate",
    [
        "site-ca",
        "agent-ca",
        "site",
    ],
)
def test_init_cert_does_not_replace_existing(
    omd_root: Path, target_certificate: CertificateType
) -> None:
    _create_dummy(omd_root, target_certificate)

    with pytest.raises(ValueError):
        _run_init(
            omd_root=omd_root,
            site_id=_site_id(),
            target_certificate=target_certificate,
            key_size=1024,
        )


def test_rotate_site(mocker: MockerFixture, omd_root: Path, site_ca: Path) -> None:
    mocker.patch("cmk.gui.cmkcert_rotate._site_gui_context").return_value = _mock_site_gui_context(
        mocker
    )
    _create_dummy(omd_root, "site-ca")
    _create_dummy(omd_root, "site")

    _run_rotate(
        omd_root=omd_root,
        site_id=_site_id(),
        target_certificate="site",
        expiry=90,
        finalize=False,
    )

    assert (
        "BEGIN CERTIFICATE"
        in _certificate_path(
            omd_root=omd_root,
            site_id=_site_id(),
            target_certificate="site",
        ).read_text()
    )


def test_rotate_site_wo_site_ca(mocker: MockerFixture, omd_root: Path) -> None:
    mocker.patch("cmk.gui.cmkcert_rotate._site_gui_context").return_value = _mock_site_gui_context(
        mocker
    )

    _create_dummy(omd_root, "site")

    with pytest.raises(FileNotFoundError):
        _run_rotate(
            omd_root=omd_root,
            site_id=_site_id(),
            target_certificate="site",
            expiry=90,
            finalize=True,
        )


def _mock_site_gui_context(mocker: MockerFixture) -> MagicMock:
    mocker.patch("cmk.gui.site_config.site_is_local").return_value = True
    mocker.patch("cmk.gui.watolib.global_settings.load_configuration_settings").return_value = {
        "trusted_certificate_authorities": {"trusted_cas": [], "use_system_wide_cas": False}
    }

    mock_site = SiteConfigurations(
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

    mock_context = MagicMock()
    mock_context.__enter__.return_value = (mock_site, Config(sites=mock_site))
    mock_context.__exit__.return_value = None

    return mock_context


def test_rotate_site_ca(
    mocker: MockerFixture,
    omd_root: Path,
    site_ca: Path,
) -> None:
    mocker.patch("cmk.gui.cmkcert_rotate._site_gui_context").return_value = _mock_site_gui_context(
        mocker
    )

    with patch("cmk.gui.watolib.changes.add_change") as mock_add_change:
        with patch(
            "cmk.gui.watolib.global_settings.save_global_settings"
        ) as mock_save_global_settings:
            _run_rotate(
                omd_root=omd_root,
                site_id=_site_id(),
                target_certificate="site-ca",
                expiry=90,
                finalize=False,
            )
            mock_add_change.assert_called_once()
            mock_save_global_settings.assert_called_once()

    # site-ca rotation requires a second call with finalize=True to complete the rotation
    _run_rotate(
        omd_root=omd_root,
        site_id=_site_id(),
        target_certificate="site-ca",
        expiry=90,
        finalize=True,
    )

    assert "BEGIN CERTIFICATE" in SiteCA.root_ca_path(cert_dir(omd_root)).read_text()
