#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from uuid import UUID

from cmk.utils.agent_registration import UUIDLinkManager


def test_uuid_link_manager_create_link(tmp_path):
    hostname = "my-hostname"
    raw_uuid = "59e631e9-de89-40d6-9662-ba54569a24fb"

    receive_outputs_dir = Path(tmp_path).joinpath("receive_outputs")
    data_source_dir = Path(tmp_path).joinpath("data_source_cache/push_agents")

    uuid_link_manager = UUIDLinkManager(
        receive_outputs_dir=receive_outputs_dir,
        data_source_dir=data_source_dir,
    )
    uuid_link_manager.create_link(hostname, UUID(raw_uuid))

    assert len(list(receive_outputs_dir.iterdir())) == 1
    assert len(list(data_source_dir.iterdir())) == 1

    link = next(iter(uuid_link_manager))

    assert str(link.source) == "{0}/receive_outputs/{1}".format(tmp_path, raw_uuid)
    assert str(link.target) == "{0}/data_source_cache/push_agents/{1}".format(tmp_path, hostname)


def test_uuid_link_manager_create_link_to_different_uuid(tmp_path):
    hostname = "my-hostname"
    raw_uuid_old = "59e631e9-de89-40d6-9662-ba54569a24fb"
    raw_uuid_new = "db1ea77f-330e-4fb5-b59e-925f55290533"

    receive_outputs_dir = Path(tmp_path).joinpath("receive_outputs")
    data_source_dir = Path(tmp_path).joinpath("data_source_cache/push_agents")

    uuid_link_manager = UUIDLinkManager(
        receive_outputs_dir=receive_outputs_dir,
        data_source_dir=data_source_dir,
    )
    uuid_link_manager.create_link(hostname, UUID(raw_uuid_old))
    uuid_link_manager.create_link(hostname, UUID(raw_uuid_new))

    assert len(list(receive_outputs_dir.iterdir())) == 1
    assert len(list(data_source_dir.iterdir())) == 1

    link = next(iter(uuid_link_manager))

    assert str(link.source) == "{0}/receive_outputs/{1}".format(tmp_path, raw_uuid_new)
    assert str(link.target) == "{0}/data_source_cache/push_agents/{1}".format(tmp_path, hostname)


def test_uuid_link_manager_update_links(tmp_path):
    hostname = "my-hostname"
    raw_uuid = "59e631e9-de89-40d6-9662-ba54569a24fb"

    receive_outputs_dir = Path(tmp_path).joinpath("receive_outputs")
    data_source_dir = Path(tmp_path).joinpath("data_source_cache/push_agents")

    uuid_link_manager = UUIDLinkManager(
        receive_outputs_dir=receive_outputs_dir,
        data_source_dir=data_source_dir,
    )
    uuid_link_manager.create_link(hostname, UUID(raw_uuid))
    uuid_link_manager.update_links({hostname: {"cmk_agent_connection": "push-agent"}})

    assert len(list(receive_outputs_dir.iterdir())) == 1
    assert len(list(data_source_dir.iterdir())) == 1

    link = next(iter(uuid_link_manager))

    assert str(link.source) == "{0}/receive_outputs/{1}".format(tmp_path, raw_uuid)
    assert str(link.target) == "{0}/data_source_cache/push_agents/{1}".format(tmp_path, hostname)


def test_uuid_link_manager_update_links_no_links_yet(tmp_path):
    receive_outputs_dir = Path(tmp_path).joinpath("receive_outputs")
    data_source_dir = Path(tmp_path).joinpath("data_source_cache/push_agents")

    uuid_link_manager = UUIDLinkManager(
        receive_outputs_dir=receive_outputs_dir,
        data_source_dir=data_source_dir,
    )
    uuid_link_manager.update_links({})

    assert not receive_outputs_dir.exists()
    assert not data_source_dir.exists()


def test_uuid_link_manager_update_links_no_host(tmp_path):
    hostname = "my-hostname"
    raw_uuid = "59e631e9-de89-40d6-9662-ba54569a24fb"

    receive_outputs_dir = Path(tmp_path).joinpath("receive_outputs")
    data_source_dir = Path(tmp_path).joinpath("data_source_cache/push_agents")

    uuid_link_manager = UUIDLinkManager(
        receive_outputs_dir=receive_outputs_dir,
        data_source_dir=data_source_dir,
    )
    uuid_link_manager.create_link(hostname, UUID(raw_uuid))
    uuid_link_manager.update_links({})

    assert list(receive_outputs_dir.iterdir()) == []
    assert list(data_source_dir.iterdir()) == []


def test_uuid_link_manager_update_links_no_push_host(tmp_path):
    hostname = "my-hostname"
    raw_uuid = "59e631e9-de89-40d6-9662-ba54569a24fb"

    receive_outputs_dir = Path(tmp_path).joinpath("receive_outputs")
    data_source_dir = Path(tmp_path).joinpath("data_source_cache/push_agents")

    uuid_link_manager = UUIDLinkManager(
        receive_outputs_dir=receive_outputs_dir,
        data_source_dir=data_source_dir,
    )
    uuid_link_manager.create_link(hostname, UUID(raw_uuid))
    uuid_link_manager.update_links({hostname: {}})

    assert len(list(receive_outputs_dir.iterdir())) == 1
    assert list(data_source_dir.iterdir()) == []

    link = next(iter(uuid_link_manager))

    assert str(link.source) == "{0}/receive_outputs/{1}".format(tmp_path, raw_uuid)
    assert str(link.target) == "{0}/data_source_cache/push_agents/{1}".format(tmp_path, hostname)
