#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from pathlib import Path
from uuid import UUID

from agent_receiver import constants
from agent_receiver.models import HostTypeEnum
from agent_receiver.utils import Host, site_name_prefix, update_file_access_time
from pytest_mock import MockerFixture


def test_host_not_registered(uuid: UUID) -> None:
    host = Host(uuid)

    assert host.registered is False
    assert host.hostname is None
    assert host.host_type is None


def test_pull_host_registered(tmp_path: Path, uuid: UUID) -> None:
    source = constants.AGENT_OUTPUT_DIR / str(uuid)
    target_dir = tmp_path / "hostname"
    source.symlink_to(target_dir)

    host = Host(uuid)

    assert host.registered is True
    assert host.hostname == "hostname"
    assert host.host_type is HostTypeEnum.PULL
    assert host.source_path == source


def test_push_host_registered(tmp_path: Path, uuid: UUID) -> None:
    source = constants.AGENT_OUTPUT_DIR / str(uuid)
    target_dir = tmp_path / "hostname"
    target_dir.touch()
    source.symlink_to(target_dir)

    host = Host(uuid)

    assert host.registered is True
    assert host.hostname == "hostname"
    assert host.host_type is HostTypeEnum.PUSH
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


def test_site_name_prefix(mocker: MockerFixture) -> None:
    assert site_name_prefix("my_app") == "/NO_SITE/my_app"
    mocker.patch("os.getenv", return_value=None)
    assert site_name_prefix("my_app") == "/my_app"
