#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from pathlib import Path

import pytest
from pydantic import UUID4

from cmk.agent_receiver.agent_receiver.models import (
    AgentUpdateAuthorization,
    ConnectionMode,
    R4RStatus,
    RequestForRegistration,
)
from cmk.agent_receiver.agent_receiver.utils import (
    agent_update_authorization,
    NotRegisteredException,
    R4R,
    RegisteredHost,
)
from cmk.agent_receiver.lib.config import get_config

pytestmark = pytest.mark.usefixtures("setup_site_context")


def test_host_not_registered(uuid: UUID4) -> None:
    with pytest.raises(NotRegisteredException):
        RegisteredHost(uuid)


def test_pull_host_registered(tmp_path: Path, uuid: UUID4) -> None:
    config = get_config()
    source = config.agent_output_dir / str(uuid)
    target_dir = tmp_path / "hostname"
    source.symlink_to(target_dir)

    host = RegisteredHost(uuid)

    assert host.name == "hostname"
    assert host.connection_mode is ConnectionMode.PULL
    assert host.source_path == source


def test_push_host_registered(tmp_path: Path, uuid: UUID4) -> None:
    config = get_config()
    source = config.agent_output_dir / str(uuid)
    target_dir = tmp_path / "push-agent" / "hostname"
    source.symlink_to(target_dir)

    host = RegisteredHost(uuid)

    assert host.name == "hostname"
    assert host.connection_mode is ConnectionMode.PUSH
    assert host.source_path == source


def test_r4r(uuid: UUID4) -> None:
    r4r = R4R(
        status=R4RStatus.NEW,
        request=RequestForRegistration(
            uuid=uuid,
            username="harry",
            agent_labels={"a": "b"},
            agent_cert="cert",
        ),
    )
    r4r.write()

    config = get_config()
    expected_path = config.r4r_dir / f"NEW/{uuid}.json"
    assert expected_path.is_file()
    access_time_before_read = expected_path.stat().st_atime

    time.sleep(0.01)
    read_r4r = R4R.read(uuid)
    assert r4r == read_r4r
    assert expected_path.stat().st_atime > access_time_before_read


def test_r4r_raises(uuid: UUID4) -> None:
    with pytest.raises(FileNotFoundError, match="No request for registration with UUID"):
        R4R.read(uuid)


def _write_registration_file(uuid: UUID4, content: str) -> None:
    (registrations_dir := get_config().registrations_dir).mkdir(parents=True, exist_ok=True)
    (registrations_dir / f"{uuid}.json").write_text(content)


def test_a_registration_that_permits_updates_is_authorized(uuid: UUID4) -> None:
    """CMK-39504: the registration response reports agent_update_authorization from the registration file of the UUID."""
    _write_registration_file(
        uuid,
        '{"agent_updates_permitted": true, "subject": "automation",'
        ' "registration_route": "register", "registered_at": 1760000000.0}',
    )

    assert agent_update_authorization(uuid) is AgentUpdateAuthorization.AUTHORIZED


def test_a_registration_without_the_permission_is_not_permitted(uuid: UUID4) -> None:
    """CMK-39504: the registration response reports agent_update_authorization from the registration file of the UUID."""
    _write_registration_file(
        uuid,
        '{"agent_updates_permitted": false, "subject": "automation",'
        ' "registration_route": "register", "registered_at": 1760000000.0}',
    )

    assert agent_update_authorization(uuid) is AgentUpdateAuthorization.NOT_PERMITTED


def test_a_registration_without_a_result_is_unavailable(uuid: UUID4) -> None:
    """CMK-39504: the registration response reports unavailable when the registration file is missing or holds no result."""
    _write_registration_file(
        uuid,
        '{"agent_updates_permitted": null, "subject": "automation",'
        ' "registration_route": "register", "registered_at": 1760000000.0}',
    )

    assert agent_update_authorization(uuid) is AgentUpdateAuthorization.UNAVAILABLE


def test_an_unreadable_registration_file_is_unavailable(uuid: UUID4) -> None:
    """CMK-39504: the registration response reports unavailable when the registration file is missing or holds no result."""
    (registrations_dir := get_config().registrations_dir).mkdir(parents=True, exist_ok=True)
    (registrations_dir / f"{uuid}.json").write_bytes(b'{"agent_updates_permitted": \xff')

    assert agent_update_authorization(uuid) is AgentUpdateAuthorization.UNAVAILABLE


def test_a_registration_without_a_file_is_unavailable(uuid: UUID4) -> None:
    """CMK-39504: the registration response reports unavailable when the registration file is missing or holds no result."""
    assert agent_update_authorization(uuid) is AgentUpdateAuthorization.UNAVAILABLE
