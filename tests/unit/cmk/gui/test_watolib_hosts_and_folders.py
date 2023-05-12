#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import time
import uuid

import freezegun
import pytest

from tests.testlib import on_time

from cmk.utils.type_defs import UserId

from cmk.gui.watolib.hosts_and_folders import Folder


def test_new_empty_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uuid, "uuid4", lambda: uuid.UUID("a8098c1a-f86e-11da-bd1a-00112444be1e"))
    with on_time("2018-01-10 02:00:00", "CET"):
        folder = Folder(
            name="bla",
            title="Bla",
            attributes={},
        )
    assert folder.name() == "bla"
    assert folder.id() == "a8098c1af86e11dabd1a00112444be1e"
    assert folder.title() == "Bla"
    assert folder.attributes() == {
        "meta_data": {
            "created_at": 1515549600.0,
            "created_by": None,
            "updated_at": 1515549600.0,
        }
    }


def test_new_loaded_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uuid, "uuid4", lambda: uuid.UUID("c6bda767ae5c47038f73d8906fb91bb4"))

    with on_time("2018-01-10 02:00:00", "CET"):
        folder1 = Folder(name="folder1", parent_folder=Folder.root_folder())
        folder1.persist_instance()
        Folder.invalidate_caches()

    # TODO: Why do we have to set the name here?
    folder = Folder(name="bla", folder_path="/folder1")
    assert folder.name() == "bla"
    assert folder.id() == "c6bda767ae5c47038f73d8906fb91bb4"
    assert folder.title() == "folder1"
    assert folder.attributes() == {
        "meta_data": {
            "created_at": 1515549600.0,
            "created_by": None,
            "updated_at": 1515549600.0,
        }
    }


@pytest.mark.parametrize(
    "allowed,last_end,next_time",
    [
        (((0, 0), (24, 0)), None, 1515549600.0),
        (
            ((0, 0), (24, 0)),
            1515549600.0,
            1515549900.0,
        ),
        (((20, 0), (24, 0)), None, 1515610800.0),
        ([((0, 0), (2, 0)), ((20, 0), (22, 0))], None, 1515610800.0),
        ([((0, 0), (2, 0)), ((20, 0), (22, 0))], 1515621600.0, 1515625200.0),
    ],
)
def test_next_network_scan_at(
    allowed: object,
    last_end: float | None,
    next_time: float,
) -> None:
    folder = Folder(
        name="bla",
        title="Bla",
        attributes={
            "network_scan": {
                "exclude_ranges": [],
                "ip_ranges": [("ip_range", ("10.3.1.1", "10.3.1.100"))],
                "run_as": UserId("cmkadmin"),
                "scan_interval": 300,
                "set_ipaddress": True,
                "tag_criticality": "offline",
                "time_allowed": allowed,
            },
            "network_scan_result": {
                "end": last_end,
            },
        },
    )

    with on_time("2018-01-10 02:00:00", "CET"):
        assert folder.next_network_scan_at() == next_time


@pytest.mark.usefixtures("request_context")
def test_folder_times() -> None:
    root = Folder.root_folder()

    with freezegun.freeze_time(datetime.datetime(2020, 2, 2, 2, 2, 2)):
        current = time.time()
        Folder(name="test", parent_folder=root).save()
        folder = Folder(name="test", folder_path="")
        folder.save()

    meta_data = folder.attributes()["meta_data"]
    assert int(meta_data["created_at"]) == int(current)
    assert int(meta_data["updated_at"]) == int(current)

    folder.persist_instance()
    assert int(meta_data["updated_at"]) > int(current)
