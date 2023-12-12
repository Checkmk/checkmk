#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from pathlib import Path

import pytest
from pydantic import UUID4

from cmk.agent_receiver import site_context
from cmk.agent_receiver.models import ConnectionMode, R4RStatus, RequestForRegistration
from cmk.agent_receiver.utils import NotRegisteredException, R4R, RegisteredHost


def test_host_not_registered(uuid: UUID4) -> None:
    with pytest.raises(NotRegisteredException):
        RegisteredHost(uuid)


def test_pull_host_registered(tmp_path: Path, uuid: UUID4) -> None:
    source = site_context.agent_output_dir() / str(uuid)
    target_dir = tmp_path / "hostname"
    source.symlink_to(target_dir)

    host = RegisteredHost(uuid)

    assert host.name == "hostname"
    assert host.connection_mode is ConnectionMode.PULL
    assert host.source_path == source


def test_push_host_registered(tmp_path: Path, uuid: UUID4) -> None:
    source = site_context.agent_output_dir() / str(uuid)
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

    expected_path = site_context.r4r_dir() / "NEW" / f"{uuid}.json"
    assert expected_path.is_file()
    access_time_before_read = expected_path.stat().st_atime

    time.sleep(0.01)
    read_r4r = R4R.read(uuid)
    assert r4r == read_r4r
    assert expected_path.stat().st_atime > access_time_before_read


def test_r4r_raises(uuid: UUID4) -> None:
    with pytest.raises(FileNotFoundError, match="No request for registration with UUID"):
        R4R.read(uuid)
