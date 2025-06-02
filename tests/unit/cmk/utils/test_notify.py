#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest import MonkeyPatch

from cmk.ccc.hostaddress import HostName

import cmk.utils.notify
from cmk.utils.config_path import VersionedConfigPath
from cmk.utils.notify import NotificationHostConfig, read_notify_host_file, write_notify_host_file
from cmk.utils.tags import TagGroupID, TagID


@pytest.mark.parametrize(
    "versioned_config_path, host_name, config, expected",
    [
        pytest.param(
            Path(VersionedConfigPath(1)),
            "horsthost",
            NotificationHostConfig(
                host_labels={"owe": "owe"},
                service_labels={
                    "svc": {"lbl": "blub"},
                    "svc2": {},
                },
                tags={
                    TagGroupID("criticality"): TagID("prod"),
                },
            ),
            NotificationHostConfig(
                host_labels={"owe": "owe"},
                service_labels={"svc": {"lbl": "blub"}},
                tags={
                    TagGroupID("criticality"): TagID("prod"),
                },
            ),
        )
    ],
)
def test_write_and_read_notify_host_file(
    versioned_config_path: Path,
    host_name: HostName,
    config: NotificationHostConfig,
    expected: NotificationHostConfig,
    monkeypatch: MonkeyPatch,
) -> None:
    notify_labels_path: Path = versioned_config_path / "notify" / "host_config"
    monkeypatch.setattr(
        cmk.utils.notify,
        "_get_host_file_path",
        lambda *args, **kw: notify_labels_path,
    )

    write_notify_host_file(versioned_config_path, {host_name: config})

    assert notify_labels_path.exists()

    monkeypatch.setattr(
        cmk.utils.notify,
        "_get_host_file_path",
        lambda *args, **kw: notify_labels_path / host_name,
    )
    assert read_notify_host_file(host_name) == expected
