#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Endpoint tests for the agent download / registration token forwarder.

Covers the local vs. remote-site forwarding code paths added so that hosts on
remote sites can use the "Test agent connection" slide-in's token-based agent
download and registration.
"""

import datetime as dt
from collections.abc import Iterator
from typing import Any

import pytest

from livestatus import NetworkSocketDetails, SiteConfiguration

from cmk.ccc.site import SiteId
from cmk.gui.token_auth import (
    AgentDownloadToken,
    AgentRegistrationToken,
    get_token_store,
)
from tests.testlib.gui.web_test_app import SetConfig
from tests.testlib.rest_api_client import ClientRegistry

REMOTE_SITE = SiteId("remote_site")
UNCONNECTED_SITE = SiteId("unconnected")


def _local_site() -> SiteConfiguration:
    return SiteConfiguration(
        id=SiteId("NO_SITE"),
        alias="local",
        socket=("local", None),
        disable_wato=False,
        disabled=False,
        insecure=False,
        url_prefix="/NO_SITE/",
        multisiteurl="",
        persist=False,
        replicate_ec=False,
        replicate_mkps=False,
        replication=None,
        timeout=5,
        user_login=True,
        proxy=None,
        user_attribute_sync_connections="all",
        status_host=None,
        message_broker_port=5672,
        is_trusted=False,
    )


def _remote_site(*, site_id: SiteId, with_secret: bool) -> SiteConfiguration:
    config = SiteConfiguration(
        id=site_id,
        alias=str(site_id),
        socket=(
            "tcp",
            NetworkSocketDetails(
                address=("127.0.0.1", 6790),
                tls=("encrypted", {"verify": True}),
            ),
        ),
        disable_wato=False,
        disabled=False,
        insecure=False,
        url_prefix=f"/{site_id}/",
        multisiteurl=f"http://{site_id}.example/check_mk/",
        persist=False,
        replicate_ec=False,
        replicate_mkps=False,
        replication="slave",
        timeout=5,
        user_login=True,
        proxy=None,
        user_attribute_sync_connections="all",
        status_host=None,
        message_broker_port=5672,
        is_trusted=False,
    )
    if with_secret:
        config["secret"] = "watosecret"
    return config


@pytest.fixture(name="distributed_sites")
def _distributed_sites(set_config: SetConfig) -> Iterator[None]:
    with set_config(
        sites={
            SiteId("NO_SITE"): _local_site(),
            REMOTE_SITE: _remote_site(site_id=REMOTE_SITE, with_secret=True),
            UNCONNECTED_SITE: _remote_site(site_id=UNCONNECTED_SITE, with_secret=False),
        }
    ):
        yield


# ---------------------------------------------------------------------------
# create_agent_download_token
# ---------------------------------------------------------------------------


class TestCreateAgentDownloadToken:
    def test_no_site_id_creates_locally(
        self, clients: ClientRegistry, distributed_sites: None
    ) -> None:
        resp = clients.Agent.create_download_token()
        resp.assert_status_code(201)
        token_id = resp.json["id"]
        stored = get_token_store().verify(f"0:{token_id}", now=dt.datetime.now(dt.UTC))
        assert isinstance(stored.details, AgentDownloadToken)

    def test_local_site_id_creates_locally(
        self, clients: ClientRegistry, distributed_sites: None
    ) -> None:
        resp = clients.Agent.create_download_token(body={"site_id": "NO_SITE"})
        resp.assert_status_code(201)
        token_id = resp.json["id"]
        stored = get_token_store().verify(f"0:{token_id}", now=dt.datetime.now(dt.UTC))
        assert isinstance(stored.details, AgentDownloadToken)

    def test_remote_site_id_forwards(
        self,
        clients: ClientRegistry,
        distributed_sites: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: dict[str, Any] = {}

        def fake_remote_automation(
            *, automation_config: Any, command: str, vars_: list[tuple[str, str]], debug: bool
        ) -> dict[str, str | None]:
            captured["site_id"] = automation_config.site_id
            captured["command"] = command
            captured["vars"] = dict(vars_)
            return {
                "id": "forwarded-token-id",
                "issued_at": "2026-04-27T10:00:00+00:00",
                "expires_at": "2026-05-04T10:00:00+00:00",
            }

        monkeypatch.setattr(
            "cmk.gui.watolib.agent_token_automations.do_remote_automation",
            fake_remote_automation,
        )

        resp = clients.Agent.create_download_token(body={"site_id": REMOTE_SITE})

        resp.assert_status_code(201)
        assert resp.json["id"] == "forwarded-token-id"
        assert resp.json["extensions"]["expires_at"].startswith("2026-05-04")
        assert captured["site_id"] == REMOTE_SITE
        assert captured["command"] == "agent-download-token-create"
        assert "request" in captured["vars"]
        # Local store must remain empty for the forwarded token.
        with pytest.raises(Exception):
            get_token_store().verify(f"0:{resp.json['id']}", now=dt.datetime.now(dt.UTC))

    def test_unknown_site_id_returns_400(
        self, clients: ClientRegistry, distributed_sites: None
    ) -> None:
        resp = clients.Agent.create_download_token(
            body={"site_id": "does_not_exist"}, expect_ok=False
        )
        resp.assert_status_code(400)
        assert "does_not_exist" in resp.json["detail"]

    def test_remote_without_login_returns_502(
        self, clients: ClientRegistry, distributed_sites: None
    ) -> None:
        resp = clients.Agent.create_download_token(
            body={"site_id": UNCONNECTED_SITE}, expect_ok=False
        )
        resp.assert_status_code(502)
        assert "not logged" in resp.json["detail"].lower()


# ---------------------------------------------------------------------------
# create_agent_registration_token
# ---------------------------------------------------------------------------


class TestCreateAgentRegistrationToken:
    @pytest.mark.usefixtures("with_host")
    def test_no_site_id_creates_locally(
        self, clients: ClientRegistry, distributed_sites: None
    ) -> None:
        resp = clients.Agent.create_registration_token(
            body={"host": "heute", "comment": "from test"}
        )
        resp.assert_status_code(201)
        token_id = resp.json["id"]
        stored = get_token_store().verify(f"0:{token_id}", now=dt.datetime.now(dt.UTC))
        assert isinstance(stored.details, AgentRegistrationToken)
        assert stored.details.host_name == "heute"
        assert stored.details.comment == "from test"

    @pytest.mark.usefixtures("with_host")
    def test_remote_site_id_forwards(
        self,
        clients: ClientRegistry,
        distributed_sites: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: dict[str, Any] = {}

        def fake_remote_automation(
            *, automation_config: Any, command: str, vars_: list[tuple[str, str]], debug: bool
        ) -> dict[str, str | None]:
            captured["site_id"] = automation_config.site_id
            captured["command"] = command
            captured["request"] = dict(vars_)["request"]
            return {
                "id": "forwarded-reg-token",
                "issued_at": "2026-04-27T10:00:00+00:00",
                "expires_at": None,
            }

        monkeypatch.setattr(
            "cmk.gui.watolib.agent_token_automations.do_remote_automation",
            fake_remote_automation,
        )

        resp = clients.Agent.create_registration_token(
            body={"host": "heute", "comment": "remote", "site_id": REMOTE_SITE}
        )

        resp.assert_status_code(201)
        assert resp.json["id"] == "forwarded-reg-token"
        assert resp.json["extensions"]["host_name"] == "heute"
        assert resp.json["extensions"]["comment"] == "remote"
        assert resp.json["extensions"]["expires_at"] is None
        assert captured["site_id"] == REMOTE_SITE
        assert captured["command"] == "agent-registration-token-create"
        assert '"host_name":"heute"' in captured["request"]
        assert '"connection_mode":"pull-agent"' in captured["request"]

    @pytest.mark.usefixtures("with_host")
    def test_unknown_site_id_returns_400(
        self, clients: ClientRegistry, distributed_sites: None
    ) -> None:
        resp = clients.Agent.create_registration_token(
            body={"host": "heute", "comment": "x", "site_id": "does_not_exist"},
            expect_ok=False,
        )
        resp.assert_status_code(400)
        assert "does_not_exist" in resp.json["detail"]
