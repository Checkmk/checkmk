#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from datetime import datetime, timedelta, UTC
from http import HTTPStatus

import pytest
from dateutil.relativedelta import relativedelta
from fastapi.testclient import TestClient

from cmk.relay_protocols.tasks import FetchAdHocTask, TaskListResponse
from cmk.testlib.agent_receiver import certs as certslib
from cmk.testlib.agent_receiver.clients import (
    RelayClient,
    RelayRegistrationClient,
    SiteClient,
)
from cmk.testlib.agent_receiver.relay import random_relay_id
from cmk.testlib.agent_receiver.site_mock import OP, SiteMock, User


def test_a_relay_can_be_registered(
    site: SiteMock,
    test_client: TestClient,
    user: User,
) -> None:
    """Verify that a relay can be registered with the agent receiver and tasks can be retrieved for it.

    Test steps:
    1. Register a relay with the agent receiver
    2. Create a config folder for the relay
    3. Verify that tasks can be retrieved for the registered relay
    """
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])

    reg = RelayRegistrationClient(test_client, site.site_name)
    reg.register("relay1", relay_id, user)

    relay = RelayClient(test_client, site.site_name, relay_id)
    relay.apply_config(site.push_config([relay_id]))

    resp = relay.get_tasks()
    assert resp.status_code == HTTPStatus.OK


def test_registering_a_relay_does_not_affect_other_relays(
    site: SiteMock,
    test_client: TestClient,
    user: User,
) -> None:
    """Verify that registering a new relay does not affect tasks belonging to other already registered relays.

    Test steps:
    1. Register first relay and push a task to it
    2. Register second relay
    3. Verify first relay's task remains unaffected
    """
    relay_1_id = random_relay_id()
    relay_2_id = random_relay_id()
    site.set_scenario([], [(relay_1_id, OP.ADD), (relay_2_id, OP.ADD)])

    reg = RelayRegistrationClient(test_client, site.site_name)
    reg.register("relay1", relay_1_id, user)

    relay_1 = RelayClient(test_client, site.site_name, relay_1_id)
    relay_1.apply_config(site.push_config([relay_1_id]))

    site_op = SiteClient(test_client, site.site_name)
    site_op.create_task(relay_1_id, FetchAdHocTask(payload=".."))

    reg.register("relay2", relay_2_id, user)

    relay_1.apply_config(site.push_config([relay_1_id, relay_2_id]))

    tasks_resp = relay_1.get_tasks()
    assert tasks_resp.status_code == HTTPStatus.OK
    tasks_A = TaskListResponse.model_validate(tasks_resp.json())
    assert len(tasks_A.tasks) == 1


def test_relay_registration_rejected_on_remote_site(
    site: SiteMock,
    test_client: TestClient,
    user: User,
) -> None:
    """Verify that relay registration is rejected when the agent receiver runs on a remote site.

    Test steps:
    1. Configure the site as a remote site by creating distributed.mk
    2. Attempt to register a relay
    3. Verify registration is rejected with 403 and an informative error message
    """
    reg = RelayRegistrationClient(test_client, site.site_name)

    distributed_mk = site.omd_root / "etc/omd/distributed.mk"
    distributed_mk.write_text("is_wato_remote_site = True\n")

    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])

    resp = reg.register_with_user(relay_id, "relay1", user)

    assert resp.status_code == HTTPStatus.FORBIDDEN
    assert "remote site" in resp.json()["detail"].lower()


def test_relay_registration_allowed_on_central_site_in_distributed_setup(
    site: SiteMock,
    test_client: TestClient,
    user: User,
) -> None:
    """Verify that relay registration is allowed on a central site in a distributed setup.

    Test steps:
    1. Configure the site as a central site by creating distributed.mk with is_wato_remote_site = False
    2. Register a relay
    3. Verify registration succeeds
    """
    reg = RelayRegistrationClient(test_client, site.site_name)

    distributed_mk = site.omd_root / "etc/omd/distributed.mk"
    distributed_mk.write_text("is_wato_remote_site = False\n")

    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])

    resp = reg.register_with_user(relay_id, "relay1", user)

    assert resp.status_code == HTTPStatus.OK


def test_a_relay_can_be_registered_with_token_auth(
    site: SiteMock,
    test_client: TestClient,
) -> None:
    """Verify that a relay can be registered using CMK-TOKEN authentication.

    Test steps:
    1. Register a relay using a CMK-TOKEN authorization header
    2. Verify registration succeeds with 200
    """
    reg = RelayRegistrationClient(test_client, site.site_name)

    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])
    resp = reg.register_with_token(
        relay_id, "token-relay", token="0:550e8400-e29b-41d4-a716-446655440000"
    )
    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["relay_id"] == relay_id


def test_certificate_validity_period(
    site: SiteMock,
    test_client: TestClient,
    user: User,
) -> None:
    """Verify that the certificate returned by the registration endpoint has the desired
    validity period.

    Test steps:
    1. Register a relay with the agent receiver
    2. Check the validity of the returned certificate
    """
    reg = RelayRegistrationClient(test_client, site.site_name)

    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])
    resp = reg.register_with_user(relay_id, "relay1", user)
    assert resp.status_code == HTTPStatus.OK

    # Verify that the certificate has correct validity period bounds.
    now = datetime.now(tz=UTC)
    cert = certslib.read_certificate(resp.json()["client_cert"])
    assert cert.not_valid_before <= now
    assert cert.not_valid_before >= now - timedelta(minutes=1)
    assert cert.not_valid_after <= now + relativedelta(months=3)


@pytest.mark.parametrize(
    "malformed_relay_id",
    [
        pytest.param("../../etc/passwd", id="path_traversal_dotdot"),
        pytest.param("valid-prefix/../../../etc", id="path_traversal_mixed"),
        pytest.param("relay;--", id="special_chars"),
        pytest.param("relay/with/slashes", id="forward_slashes"),
        pytest.param("not-a-uuid", id="plain_string"),
    ],
)
def test_registration_rejects_non_uuid_relay_id(
    site: SiteMock,
    test_client: TestClient,
    user: User,
    malformed_relay_id: str,
) -> None:
    """reject relay_id values that are not valid UUIDs.

    Test steps:
    1. Attempt to register a relay with a non-UUID relay_id
    2. Verify the request is rejected with 422 Unprocessable Entity
    """
    reg = RelayRegistrationClient(test_client, site.site_name)

    site.set_scenario([], [(malformed_relay_id, OP.ADD)])
    resp = reg.register_with_user(malformed_relay_id, "relay", user)
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
