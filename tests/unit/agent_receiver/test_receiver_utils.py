#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from pathlib import Path
from uuid import UUID

import pytest
from agent_receiver import site_context
from agent_receiver.models import ConnectionMode
from agent_receiver.utils import NotRegisteredException, RegisteredHost, update_file_access_time


def test_host_not_registered(uuid: UUID) -> None:
    with pytest.raises(NotRegisteredException):
        RegisteredHost(uuid)


def test_pull_host_registered(tmp_path: Path, uuid: UUID) -> None:
    source = site_context.agent_output_dir() / str(uuid)
    target_dir = tmp_path / "hostname"
    source.symlink_to(target_dir)

    host = RegisteredHost(uuid)

    assert host.name == "hostname"
    assert host.connection_mode is ConnectionMode.PULL
    assert host.source_path == source


def test_push_host_registered(tmp_path: Path, uuid: UUID) -> None:
    source = site_context.agent_output_dir() / str(uuid)
    target_dir = tmp_path / "push-agent" / "hostname"
    source.symlink_to(target_dir)

    host = RegisteredHost(uuid)

    assert host.name == "hostname"
    assert host.connection_mode is ConnectionMode.PUSH
    assert host.source_path == source


def test_update_file_access_time_success(tmp_path: Path) -> None:
    file_path = tmp_path / "my_file"
    file_path.touch()

    old_access_time = file_path.stat().st_atime
    time.sleep(0.01)
    update_file_access_time(file_path)
    new_access_time = file_path.stat().st_atime

    assert new_access_time > old_access_time


def test_update_file_access_time_no_file(tmp_path: Path) -> None:
    update_file_access_time(tmp_path / "my_file")
