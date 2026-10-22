#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""A registration decides about the agent updates of a host, and the latest one wins."""

import json
from collections.abc import Iterator
from contextlib import ExitStack
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path

import pytest
import requests

from tests.system.agent_updates.install_step._agent import AGENT_USER, IntegratedUpdaterAgent
from tests.system.agent_updates.install_step._controller import (
    connection_uuid,
    installed_hash,
    register_for_updates,
    UPDATE_HOST,
)
from tests.testlib.system.agent import get_package_type
from tests.testlib.system.host_under_test import HostUnderTest
from tests.testlib.system.site import Site

pytestmark = pytest.mark.skip_if_faked_artifacts

_REGISTRATIONS_DIR = Path("var", "agent-receiver", "registrations")
_UUID_LINKS_DIR = Path("var", "agent-receiver", "received-outputs")
_SECURITY_LOG = Path("var", "log", "security.log")
_UNAUTHORIZED_UPDATE_REQUEST = "agent update request of an unauthorized UUID refused"
_UPDATE_PERMISSIONS = ("wato.download_all_agents", "wato.download_agents")


@dataclass(frozen=True)
class _User:
    name: str
    password: str


@pytest.fixture(name="registrar_without_update_permission")
def _registrar_without_update_permission(site: Site) -> Iterator[_User]:
    """A user who may register every host, but may download no agent."""
    role, user = "au_registrar", _User("au-registrar", "au-registrar-password")
    with ExitStack() as cleanup:
        # The callbacks run in reverse order, so the activation comes after both deletions.
        cleanup.callback(
            site.openapi.changes.activate_and_wait_for_completion, force_foreign_changes=True
        )
        site.openapi.user_role.create(
            "agent_registration", role, "Registrar without agent downloads"
        )
        cleanup.callback(site.openapi.user_role.delete, role)
        site.openapi.user_role.edit_permissions(role, dict.fromkeys(_UPDATE_PERMISSIONS, "no"))
        site.openapi.users.create(
            user.name, user.name, user.password, "au-registrar@example.com", [], roles=[role]
        )
        cleanup.callback(site.openapi.users.delete, user.name)
        site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)
        yield user


def _registration(site: Site, uuid: str) -> dict[str, object] | None:
    path = _REGISTRATIONS_DIR / f"{uuid}.json"
    if not site.file_exists(path):
        return None
    registration: dict[str, object] = json.loads(site.read_file(path))
    return registration


def _refused_uuids(site: Site) -> list[object]:
    """The UUIDs whose update requests the site's security log records as refused."""
    if not site.file_exists(_SECURITY_LOG):
        return []
    refused = []
    for line in site.read_file(_SECURITY_LOG).splitlines():
        # A line is "<time> [cmk_security.<domain> <pid>] <JSON>". ValueError covers a line
        # without "{" as well as one whose rest is no JSON.
        try:
            event = json.loads(line[line.index("{") :])
        except ValueError:
            continue
        details = event.get("details")
        if (
            event.get("summary") == _UNAUTHORIZED_UPDATE_REQUEST
            and isinstance(details, dict)
            and details.get("host_name") == UPDATE_HOST
        ):
            refused.append(details.get("uuid"))
    return refused


def _register_as(
    host: HostUnderTest, agent: IntegratedUpdaterAgent, site: Site, user: _User
) -> tuple[str, str]:
    """Register as user, and return the UUID of the new connection and what the controller said."""
    registration = register_for_updates(
        host, agent, site, UPDATE_HOST, user=user.name, password=user.password
    )
    return connection_uuid(host, agent, site), registration.stdout + registration.stderr


def _send_update_request(
    host: HostUnderTest, agent: IntegratedUpdaterAgent, site: Site, uuid: str, tmp_path: Path
) -> requests.Response:
    """Send the controller's update request through the connection uuid, with the client
    certificate that the agent user reads from the controller's registry."""
    registry = json.loads(
        host.run(
            ["cat", (agent.controller_dir / "registered_connections.json").as_posix()],
            user=AGENT_USER,
        ).stdout
    )
    connection = next(
        connection
        for connections in (registry.get("pull", {}), registry.get("push", {}))
        for connection in connections.values()
        if connection["uuid"] == uuid
    )
    certificate, key = tmp_path / "certificate.pem", tmp_path / "key.pem"
    certificate.write_text(connection["certificate"])
    key.write_text(connection["private_key"])
    return requests.post(
        f"{site.openapi_agent_receiver.base_url}agent_update/status/{uuid}",
        json={"platform": get_package_type(host), "installed_aghash": installed_hash(host, agent)},
        cert=(certificate.as_posix(), key.as_posix()),
        verify=False,
        timeout=30,
    )


@pytest.mark.usefixtures("update_offer")
def test_a_registration_without_the_permission_replaces_the_authorized_one(
    host: HostUnderTest,
    site: Site,
    integrated_updater_agent: IntegratedUpdaterAgent,
    registrar_without_update_permission: _User,
    tmp_path: Path,
) -> None:
    """TC-AU-081: a second registration by a user without the permission replaces the authorized
    one, and a request through it is refused and logged.

    The agent user holds the certificate of the new connection, so it can send that request
    whatever a correct controller does."""
    authorized_uuid = connection_uuid(host, integrated_updater_agent, site)
    authorized = _registration(site, authorized_uuid)
    assert authorized is not None and authorized["agent_updates_permitted"] is True, (
        f"Precondition: the registration of {authorized_uuid} by cmkadmin records {authorized}"
    )
    new_uuid, _ = _register_as(
        host, integrated_updater_agent, site, registrar_without_update_permission
    )

    response = _send_update_request(host, integrated_updater_agent, site, new_uuid, tmp_path)

    new_registration = _registration(site, new_uuid)
    assert new_registration is not None and new_registration["agent_updates_permitted"] is False, (
        f"The registration of the user without the permission records {new_registration}"
    )
    assert _registration(site, authorized_uuid) is None, (
        f"The registration file of the earlier UUID {authorized_uuid} is still there"
    )
    link = site.path(_UUID_LINKS_DIR / authorized_uuid).as_posix()
    assert site.run(["test", "-L", link], check=False).returncode != 0, (
        f"The link of the earlier UUID {authorized_uuid} is still there"
    )
    assert response.status_code == HTTPStatus.FORBIDDEN, (
        f"The site answered the request through {new_uuid} with {response.status_code}: "
        f"{response.text}"
    )
    assert _refused_uuids(site).count(new_uuid) == 1, (
        f"The security log does not record exactly one refusal of {new_uuid}: "
        f"{_refused_uuids(site)}"
    )
