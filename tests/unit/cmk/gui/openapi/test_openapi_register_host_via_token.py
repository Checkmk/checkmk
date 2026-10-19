#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Endpoint tests for host registration via a one-time agent registration token.

The token has two independent one-time uses (host registration and agent updater
registration). This endpoint consumes the host registration use; the token is only
revoked once both uses are consumed.
"""

import datetime as dt
import json
from http import HTTPStatus
from uuid import UUID, uuid4

import pytest
from dateutil.relativedelta import relativedelta
from werkzeug.datastructures import ETags

import cmk.utils.paths
from cmk.ccc.hostaddress import HostName
from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.logged_in import LoggedInNobody
from cmk.gui.openapi.api_endpoints.host_config_internal.models.request_models import RegisterHost
from cmk.gui.openapi.api_endpoints.host_config_internal.register_host_via_token import (
    register_host_via_token_v1,
)
from cmk.gui.openapi.framework import ApiContext, APIVersion
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.token_auth import AgentRegistrationToken, AuthToken, get_token_store
from cmk.gui.token_auth._store import TokenRevoked
from cmk.utils.agent_registration import get_r4r_filepath, UUIDLinkManager
from tests.testlib.unit.fake_site import LoggedSecurityEvent
from tests.testlib.unit.rest_api_client import ClientRegistry


def _issue_token(host_name: str) -> AuthToken:
    return get_token_store().issue(
        token_details=AgentRegistrationToken(host_name=HostName(host_name)),
        issuer=UserId("issuer"),
        now=dt.datetime.now(dt.UTC),
        valid_for=relativedelta(days=1),
    )


def _links() -> dict[UUID, HostName]:
    return {
        link.uuid: link.hostname
        for link in UUIDLinkManager(
            received_outputs_dir=cmk.utils.paths.received_outputs_dir,
            data_source_dir=cmk.utils.paths.data_source_push_agent_dir,
            r4r_discoverable_dir=cmk.utils.paths.r4r_discoverable_dir,
            uuid_lookup_dir=cmk.utils.paths.uuid_lookup_dir,
        )
    }


def _register_with_authenticated_token(token: AuthToken) -> None:
    register_host_via_token_v1(
        ApiContext.new(
            config=Config(),
            version=APIVersion.INTERNAL,
            etag_if_match=ETags(),
            host_url="http://localhost/",
            user=LoggedInNobody(),
            token=token,
        ),
        HostName("heute"),
        RegisterHost(uuid=uuid4()),
    )


@pytest.mark.usefixtures("with_host")
class TestRegisterHostViaToken:
    def test_success_consumes_host_registration_use(self, clients: ClientRegistry) -> None:
        token = _issue_token("heute")

        resp = clients.HostConfig.register_via_token("heute", f"0:{token.token_id}", str(uuid4()))

        resp.assert_status_code(HTTPStatus.OK)
        stored = get_token_store().verify(f"0:{token.token_id}", now=dt.datetime.now(dt.UTC))
        assert isinstance(stored.details, AgentRegistrationToken)
        assert stored.details.host_registration_completed_at is not None
        assert stored.details.updater_registration_completed_at is None
        assert not stored.revoked
        # The remaining (updater registration) use is only valid for a grace period
        assert stored.valid_until is not None
        assert stored.valid_until <= dt.datetime.now(dt.UTC) + dt.timedelta(minutes=10)

    def test_second_host_registration_is_rejected(self, clients: ClientRegistry) -> None:
        token = _issue_token("heute")
        clients.HostConfig.register_via_token("heute", f"0:{token.token_id}", str(uuid4()))

        resp = clients.HostConfig.register_via_token(
            "heute", f"0:{token.token_id}", str(uuid4()), expect_ok=False
        )

        resp.assert_status_code(HTTPStatus.FORBIDDEN)
        assert resp.json["title"] == "Token already used"

    def test_both_uses_consumed_revokes_token(self, clients: ClientRegistry) -> None:
        token = _issue_token("heute")
        get_token_store().consume_agent_registration_use(
            token.token_id, "updater_registration", dt.datetime.now(dt.UTC)
        )

        resp = clients.HostConfig.register_via_token("heute", f"0:{token.token_id}", str(uuid4()))

        resp.assert_status_code(HTTPStatus.OK)
        with pytest.raises(TokenRevoked):
            get_token_store().verify(f"0:{token.token_id}", now=dt.datetime.now(dt.UTC))

    def test_revoked_token_is_rejected(self, clients: ClientRegistry) -> None:
        token = _issue_token("heute")
        get_token_store().revoke(token.token_id)

        resp = clients.HostConfig.register_via_token(
            "heute", f"0:{token.token_id}", str(uuid4()), expect_ok=False
        )

        resp.assert_status_code(HTTPStatus.UNAUTHORIZED)

    def test_token_for_different_host_is_rejected(self, clients: ClientRegistry) -> None:
        token = _issue_token("other_host")

        resp = clients.HostConfig.register_via_token(
            "heute", f"0:{token.token_id}", str(uuid4()), expect_ok=False
        )

        resp.assert_status_code(HTTPStatus.FORBIDDEN)
        assert "different host" in resp.json["detail"]

    def test_a_uuid_that_is_already_linked_is_refused_without_consuming_a_use(
        self, clients: ClientRegistry
    ) -> None:
        """CMK-40803 AC-1"""
        uuid = str(uuid4())
        clients.HostConfig.register("example.com", uuid)
        token = _issue_token("heute")

        resp = clients.HostConfig.register_via_token(
            "heute", f"0:{token.token_id}", uuid, expect_ok=False
        )

        resp.assert_status_code(HTTPStatus.CONFLICT)
        assert _links() == {UUID(uuid): HostName("example.com")}
        stored = get_token_store().verify(f"0:{token.token_id}", now=dt.datetime.now(dt.UTC))
        assert isinstance(stored.details, AgentRegistrationToken)
        assert stored.details.host_registration_completed_at is None

    def test_a_uuid_of_an_open_request_is_refused_without_consuming_a_use(
        self, clients: ClientRegistry, security_events: list[LoggedSecurityEvent]
    ) -> None:
        """CMK-40803 AC-5"""
        uuid = uuid4()
        cmk.utils.paths.r4r_pending_dir.mkdir(parents=True)
        get_r4r_filepath(cmk.utils.paths.r4r_pending_dir, uuid).write_text(
            json.dumps(
                {
                    "uuid": str(uuid),
                    "username": "my-username",
                    "agent_labels": {},
                    "agent_cert": "cert",
                }
            )
        )
        token = _issue_token("heute")

        resp = clients.HostConfig.register_via_token(
            "heute", f"0:{token.token_id}", str(uuid), expect_ok=False
        )

        resp.assert_status_code(HTTPStatus.CONFLICT)
        assert [
            event.details
            for event in security_events
            if event.summary == "registration of a UUID with an open request refused"
        ] == [{"host_name": "heute", "uuid": str(uuid)}]
        stored = get_token_store().verify(f"0:{token.token_id}", now=dt.datetime.now(dt.UTC))
        assert isinstance(stored.details, AgentRegistrationToken)
        assert stored.details.host_registration_completed_at is None

    def test_of_two_registrations_with_one_token_only_the_first_links_its_uuid(
        self, clients: ClientRegistry
    ) -> None:
        """CMK-40803 AC-3: The second registration holds the token as its authentication read it, before the first registration consumed the use."""
        token_as_both_authentications_read_it = _issue_token("heute")
        first_uuid = uuid4()
        clients.HostConfig.register_via_token(
            "heute", f"0:{token_as_both_authentications_read_it.token_id}", str(first_uuid)
        )

        with pytest.raises(ProblemException):
            _register_with_authenticated_token(token_as_both_authentications_read_it)

        assert _links() == {first_uuid: HostName("heute")}

    def test_a_token_deleted_after_the_authentication_is_rejected(self) -> None:
        token = _issue_token("heute")
        get_token_store().delete(token.token_id)

        with pytest.raises(ProblemException) as exc_info:
            _register_with_authenticated_token(token)

        assert exc_info.value.code == HTTPStatus.UNAUTHORIZED

    def test_a_token_expired_after_the_authentication_is_rejected(self) -> None:
        token = get_token_store().issue(
            token_details=AgentRegistrationToken(host_name=HostName("heute")),
            issuer=UserId("issuer"),
            now=dt.datetime.now(dt.UTC) - dt.timedelta(days=2),
            valid_for=relativedelta(days=1),
        )

        with pytest.raises(ProblemException) as exc_info:
            _register_with_authenticated_token(token)

        assert exc_info.value.code == HTTPStatus.UNAUTHORIZED
