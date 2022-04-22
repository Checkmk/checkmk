#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from uuid import UUID

import pytest

from cmk.utils.agent_registration import get_r4r_filepath, UUIDLink, UUIDLinkManager
from cmk.utils.paths import (
    data_source_push_agent_dir,
    r4r_declined_dir,
    r4r_discoverable_dir,
    r4r_new_dir,
    r4r_pending_dir,
    r4r_ready_dir,
    received_outputs_dir,
)
from cmk.utils.type_defs import HostName


class TestUUIDLink:
    @pytest.fixture
    def link(self, tmp_path: Path) -> UUIDLink:
        return UUIDLink(tmp_path / "59e631e9-de89-40d6-9662-ba54569a24fb", tmp_path / "hostname")

    def test_uuid(self, link: UUIDLink) -> None:
        assert isinstance(link.uuid, UUID)

    def test_hostname(self, link: UUIDLink) -> None:
        assert isinstance(link.hostname, HostName)

    def test_unlink_nonexisiting_target(self, link: UUIDLink) -> None:
        link.source.symlink_to(link.target)

        assert not link.target.exists()
        link.unlink_target()

    def test_unlink_nonexisiting_source(self, link: UUIDLink) -> None:
        assert not link.source.exists()
        link.unlink_source()


def test_uuid_link_manager_create_link():
    hostname = "my-hostname"
    raw_uuid = "59e631e9-de89-40d6-9662-ba54569a24fb"

    uuid_link_manager = UUIDLinkManager(
        received_outputs_dir=received_outputs_dir,
        data_source_dir=data_source_push_agent_dir,
    )
    uuid_link_manager.create_link(hostname, UUID(raw_uuid), create_target_dir=False)

    assert len(list(received_outputs_dir.iterdir())) == 1
    assert not data_source_push_agent_dir.exists()

    link = next(iter(uuid_link_manager))

    assert link.source == received_outputs_dir.joinpath(raw_uuid)
    assert link.target == data_source_push_agent_dir.joinpath(hostname)


def test_uuid_link_manager_create_link_and_target_dir():
    hostname = "my-hostname"
    raw_uuid = "59e631e9-de89-40d6-9662-ba54569a24fb"

    uuid_link_manager = UUIDLinkManager(
        received_outputs_dir=received_outputs_dir,
        data_source_dir=data_source_push_agent_dir,
    )
    uuid_link_manager.create_link(hostname, UUID(raw_uuid), create_target_dir=True)

    assert len(list(received_outputs_dir.iterdir())) == 1
    assert len(list(data_source_push_agent_dir.iterdir())) == 1

    link = next(iter(uuid_link_manager))

    assert link.source == received_outputs_dir.joinpath(raw_uuid)
    assert link.target == data_source_push_agent_dir.joinpath(hostname)


def test_uuid_link_manager_create_existing_link():
    hostname = "my-hostname"
    raw_uuid = "59e631e9-de89-40d6-9662-ba54569a24fb"

    uuid_link_manager = UUIDLinkManager(
        received_outputs_dir=received_outputs_dir,
        data_source_dir=data_source_push_agent_dir,
    )
    uuid_link_manager.create_link(hostname, UUID(raw_uuid), create_target_dir=False)
    # second time should be no-op, at least not fail
    uuid_link_manager.create_link(hostname, UUID(raw_uuid), create_target_dir=False)


def test_uuid_link_manager_create_link_to_different_uuid():
    hostname = "my-hostname"
    raw_uuid_old = "59e631e9-de89-40d6-9662-ba54569a24fb"
    raw_uuid_new = "db1ea77f-330e-4fb5-b59e-925f55290533"

    uuid_link_manager = UUIDLinkManager(
        received_outputs_dir=received_outputs_dir,
        data_source_dir=data_source_push_agent_dir,
    )
    uuid_link_manager.create_link(hostname, UUID(raw_uuid_old), create_target_dir=False)
    uuid_link_manager.create_link(hostname, UUID(raw_uuid_new), create_target_dir=False)

    assert len(list(received_outputs_dir.iterdir())) == 1
    assert not data_source_push_agent_dir.exists()

    link = next(iter(uuid_link_manager))

    assert link.source == received_outputs_dir.joinpath(raw_uuid_new)
    assert link.target == data_source_push_agent_dir.joinpath(hostname)


@pytest.mark.parametrize("create_target_dir", [True, False])
def test_uuid_link_manager_update_links_host_push(create_target_dir: bool) -> None:
    hostname = "my-hostname"
    raw_uuid = "59e631e9-de89-40d6-9662-ba54569a24fb"

    uuid_link_manager = UUIDLinkManager(
        received_outputs_dir=received_outputs_dir,
        data_source_dir=data_source_push_agent_dir,
    )
    # During link creation the cmk_agent_connection could possibly not be calculated yet,
    # ie. push-agent or other.
    # During links update the target dirs are created for push hosts.
    uuid_link_manager.create_link(hostname, UUID(raw_uuid), create_target_dir=create_target_dir)
    uuid_link_manager.update_links({hostname: {"cmk_agent_connection": "push-agent"}})

    assert len(list(received_outputs_dir.iterdir())) == 1
    assert len(list(data_source_push_agent_dir.iterdir())) == 1

    link = next(iter(uuid_link_manager))

    assert link.source == received_outputs_dir.joinpath(raw_uuid)
    assert link.target == data_source_push_agent_dir.joinpath(hostname)


def test_uuid_link_manager_update_links_no_links_yet():
    uuid_link_manager = UUIDLinkManager(
        received_outputs_dir=received_outputs_dir,
        data_source_dir=data_source_push_agent_dir,
    )
    uuid_link_manager.update_links({})

    assert not received_outputs_dir.exists()
    assert not data_source_push_agent_dir.exists()


def test_uuid_link_manager_update_links_no_host():
    hostname = "my-hostname"
    raw_uuid = "59e631e9-de89-40d6-9662-ba54569a24fb"

    uuid_link_manager = UUIDLinkManager(
        received_outputs_dir=received_outputs_dir,
        data_source_dir=data_source_push_agent_dir,
    )
    uuid_link_manager.create_link(hostname, UUID(raw_uuid), create_target_dir=False)
    uuid_link_manager.update_links({})

    assert list(received_outputs_dir.iterdir()) == []
    assert not data_source_push_agent_dir.exists()


def test_uuid_link_manager_update_links_host_no_push():
    hostname = "my-hostname"
    raw_uuid = "59e631e9-de89-40d6-9662-ba54569a24fb"

    uuid_link_manager = UUIDLinkManager(
        received_outputs_dir=received_outputs_dir,
        data_source_dir=data_source_push_agent_dir,
    )
    uuid_link_manager.create_link(hostname, UUID(raw_uuid), create_target_dir=False)
    uuid_link_manager.update_links({hostname: {}})

    assert len(list(received_outputs_dir.iterdir())) == 1
    assert not data_source_push_agent_dir.exists()

    link = next(iter(uuid_link_manager))

    assert link.source == received_outputs_dir.joinpath(raw_uuid)
    assert link.target == data_source_push_agent_dir.joinpath(hostname)


@pytest.mark.parametrize(
    "folder, has_link",
    [
        (r4r_new_dir, False),
        (r4r_pending_dir, False),
        (r4r_declined_dir, False),
        (r4r_ready_dir, True),
        (r4r_discoverable_dir, True),
    ],
)
def test_uuid_link_manager_update_links_no_host_but_ready_or_discoverable(
    folder: Path,
    has_link: bool,
) -> None:
    hostname = "my-hostname"
    raw_uuid = "59e631e9-de89-40d6-9662-ba54569a24fb"

    folder.mkdir(parents=True, exist_ok=True)
    with get_r4r_filepath(folder, UUID(raw_uuid)).open("w") as f:
        f.write("")

    uuid_link_manager = UUIDLinkManager(
        received_outputs_dir=received_outputs_dir,
        data_source_dir=data_source_push_agent_dir,
    )
    uuid_link_manager.create_link(hostname, UUID(raw_uuid), create_target_dir=False)
    uuid_link_manager.update_links({})

    if has_link:
        assert len(list(received_outputs_dir.iterdir())) == 1
    else:
        assert list(received_outputs_dir.iterdir()) == []

    assert not data_source_push_agent_dir.exists()


def test_uuid_link_manager_unlink_sources():
    hostname_1 = "my-hostname-1"
    raw_uuid_1 = "59e631e9-de89-40d6-9662-ba54569a24fb"
    hostname_2 = "my-hostname-2"
    raw_uuid_2 = "db1ea77f-330e-4fb5-b59e-925f55290533"

    uuid_link_manager = UUIDLinkManager(
        received_outputs_dir=received_outputs_dir,
        data_source_dir=data_source_push_agent_dir,
    )
    uuid_link_manager.create_link(hostname_1, UUID(raw_uuid_1), create_target_dir=False)
    uuid_link_manager.create_link(hostname_2, UUID(raw_uuid_2), create_target_dir=False)

    uuid_link_manager.unlink_sources([hostname_1])

    sources = list(received_outputs_dir.iterdir())
    assert len(sources) == 1
    assert sources[0].name == raw_uuid_2

    assert not data_source_push_agent_dir.exists()
