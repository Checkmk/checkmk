#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest import MonkeyPatch

import cmk.utils.notify
from cmk.utils.config_path import VersionedConfigPath
from cmk.utils.hostaddress import HostName
from cmk.utils.labels import CollectedHostLabels
from cmk.utils.notify import read_notify_host_file, write_notify_host_file


@pytest.mark.parametrize(
    "versioned_config_path, host_name, host_labels, expected",
    [
        pytest.param(
            VersionedConfigPath(1),
            "horsthost",
            CollectedHostLabels(
                host_labels={"owe": "owe"},
                service_labels={
                    "svc": {"lbl": "blub"},
                    "svc2": {},
                },
            ),
            CollectedHostLabels(
                host_labels={"owe": "owe"},
                service_labels={"svc": {"lbl": "blub"}},
            ),
        )
    ],
)
def test_write_and_read_notify_host_file(
    versioned_config_path: VersionedConfigPath,
    host_name: HostName,
    host_labels: CollectedHostLabels,
    expected: CollectedHostLabels,
    monkeypatch: MonkeyPatch,
) -> None:
    notify_labels_path: Path = Path(versioned_config_path) / "notify" / "labels"
    monkeypatch.setattr(
        cmk.utils.notify,
        "_get_host_file_path",
        lambda *args, **kw: notify_labels_path,
    )

    write_notify_host_file(
        versioned_config_path,
        {host_name: host_labels},
    )

    assert notify_labels_path.exists()

    monkeypatch.setattr(
        cmk.utils.notify,
        "_get_host_file_path",
        lambda *args, **kw: notify_labels_path / host_name,
    )
    assert read_notify_host_file(host_name) == expected
