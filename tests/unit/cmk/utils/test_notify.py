#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from pytest import MonkeyPatch

import cmk.utils.notify
from cmk.ccc.hostaddress import HostName
from cmk.utils.notify import create_notify_host_files, NotificationHostConfig, read_notify_host_file
from cmk.utils.tags import TagGroupID, TagID

NHC = NotificationHostConfig(
    host_labels={"owe": "owe"},
    service_labels={
        "svc": {"lbl": "blub"},
        "svc2": {},
    },
    tags={
        TagGroupID("criticality"): TagID("prod"),
    },
)

NHC_EXPECTED = NotificationHostConfig(
    host_labels={"owe": "owe"},
    service_labels={"svc": {"lbl": "blub"}},
    tags={
        TagGroupID("criticality"): TagID("prod"),
    },
)


def test_create_notify_host_files(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    host_name = HostName("horsthost")
    files = create_notify_host_files({host_name: NHC})
    assert files

    test_file = tmp_path / "file"
    test_file.write_bytes(files[host_name])

    monkeypatch.setattr(
        cmk.utils.notify,
        "make_notify_host_file_path",
        lambda config_path, host_name: test_file,
    )
    assert read_notify_host_file(host_name) == NHC_EXPECTED
