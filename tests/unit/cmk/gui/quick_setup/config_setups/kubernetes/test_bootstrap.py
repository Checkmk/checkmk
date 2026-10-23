#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta, UTC
from pathlib import Path

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.crypto.certificate import CertificateWithPrivateKey
from cmk.gui.quick_setup.config_setups.kubernetes.bootstrap import (
    issue_push_token,
    local_push_registration,
    push_receiver_url,
)
from cmk.gui.token_auth import AgentRegistrationToken, get_token_store, TokenStore
from cmk.utils import paths
from cmk.utils.agent_registration import HostAgentConnectionMode


@pytest.fixture
def site_ca() -> CertificateWithPrivateKey:
    ca = CertificateWithPrivateKey.generate_self_signed(
        common_name="test-site-ca", organization="Checkmk", key_size=1024, is_ca=True
    )
    paths.root_cert_file.parent.mkdir(parents=True, exist_ok=True)
    paths.root_cert_file.write_bytes(
        ca.private_key.dump_pem(password=None).bytes + ca.certificate.dump_pem().bytes
    )
    site_conf = paths.omd_root / "etc" / "omd" / "site.conf"
    site_conf.parent.mkdir(parents=True, exist_ok=True)
    site_conf.write_text("CONFIG_AGENT_RECEIVER_PORT='8001'\n", encoding="utf-8")
    return ca


@pytest.mark.usefixtures("with_admin_login", "site_ca")
def test_push_registration_uses_local_ca_port_and_token_store() -> None:

    registration = local_push_registration(
        HostName("cluster"), UserId("admin"), push_supported=True
    )

    token = get_token_store().verify(registration.registration_token, now=datetime.now(UTC))
    assert token.issuer == "admin"
    assert isinstance(token.details, AgentRegistrationToken)
    assert token.details.host_name == "cluster"
    assert token.details.connection_mode == HostAgentConnectionMode.PUSH
    assert token.valid_until == token.issued_at + timedelta(hours=1)
    assert registration.port == 8001
    assert registration.registration_token not in repr(registration)


@pytest.mark.usefixtures("with_admin_login")
def test_push_registration_exports_certificate_without_private_key(
    site_ca: CertificateWithPrivateKey,
) -> None:
    registration = local_push_registration(
        HostName("cluster"), UserId("admin"), push_supported=True
    )

    assert registration.site_ca_certificate == site_ca.certificate.dump_pem().bytes.decode("utf-8")
    assert "PRIVATE KEY" not in registration.model_dump_json()


@pytest.mark.usefixtures("with_admin_login")
def test_unsupported_push_registration_is_rejected_before_reading_site_credentials() -> None:
    # No CA or receiver configuration is present: the capability check must happen first.
    with pytest.raises(ValueError, match="does not support push mode"):
        local_push_registration(HostName("cluster"), UserId("admin"), push_supported=False)


def test_push_token_is_scoped_to_source_host_and_expires(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "tokens")
    now = datetime(2026, 9, 10, tzinfo=UTC)

    token = issue_push_token(
        host_name=HostName("cluster"), issuer=UserId("admin"), token_store=store, now=now
    )

    assert token.details == AgentRegistrationToken(
        host_name=HostName("cluster"),
        connection_mode=HostAgentConnectionMode.PUSH,
        comment="Kubernetes Quick Setup",
    )
    assert token.issuer == UserId("admin")
    assert token.valid_until == now + timedelta(hours=1)
    with pytest.raises(ValueError, match="expired"):
        store.verify(f"0:{token.token_id}", now + timedelta(hours=2))


@pytest.mark.parametrize(
    "site_url, override, expected_host",
    [
        pytest.param("https://remote.example/site/", None, "remote.example", id="selected-site"),
        pytest.param("", None, "browser.example", id="browser-fallback"),
        pytest.param("https://remote.example/site/", "172.18.0.1", "172.18.0.1", id="override"),
        pytest.param("", "2001:db8::1", "[2001:db8::1]", id="ipv6"),
    ],
)
def test_receiver_url_uses_selected_site_port_and_host(
    site_url: str, override: str | None, expected_host: str
) -> None:
    result = push_receiver_url(
        site_id=SiteId("remote"),
        site_url=site_url,
        browser_host="browser.example",
        port=8001,
        override_host=override,
    )

    assert result == f"https://{expected_host}:8001/remote"
