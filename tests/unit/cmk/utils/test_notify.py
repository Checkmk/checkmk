#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from pytest import MonkeyPatch

import cmk.utils.notify
from cmk.ccc.hostaddress import HostName
from cmk.utils.notify import (
    build_descendants_map,
    create_notify_host_files,
    MAX_HOST_DESCENDANTS,
    NotificationHostConfig,
    read_notify_host_file,
)
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
    descendants=(HostName("childA"), HostName("childB")),
)

NHC_EXPECTED = NotificationHostConfig(
    host_labels={"owe": "owe"},
    service_labels={"svc": {"lbl": "blub"}},
    tags={
        TagGroupID("criticality"): TagID("prod"),
    },
    descendants=(HostName("childA"), HostName("childB")),
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


def test_build_descendants_map_simple_tree() -> None:
    parents = {
        HostName("root"): (),
        HostName("a"): (HostName("root"),),
        HostName("b"): (HostName("root"),),
        HostName("a1"): (HostName("a"),),
    }
    descendants = build_descendants_map(parents)
    assert set(descendants[HostName("root")]) == {
        HostName("a"),
        HostName("b"),
        HostName("a1"),
    }
    # BFS: direct children before grandchildren
    root_descendants = descendants[HostName("root")]
    assert root_descendants.index(HostName("a")) < root_descendants.index(HostName("a1"))
    assert root_descendants.index(HostName("b")) < root_descendants.index(HostName("a1"))
    assert descendants[HostName("a")] == (HostName("a1"),)
    assert descendants[HostName("a1")] == ()


def test_build_descendants_map_diamond_dedupes() -> None:
    # root → {a, b}; a, b → leaf. leaf must appear only once.
    parents = {
        HostName("root"): (),
        HostName("a"): (HostName("root"),),
        HostName("b"): (HostName("root"),),
        HostName("leaf"): (HostName("a"), HostName("b")),
    }
    descendants = build_descendants_map(parents)
    root_desc = list(descendants[HostName("root")])
    assert root_desc.count(HostName("leaf")) == 1


def test_build_descendants_map_handles_cycles() -> None:
    # Pathological cycle a→b→a; resolution must terminate without dupes.
    parents = {
        HostName("a"): (HostName("b"),),
        HostName("b"): (HostName("a"),),
    }
    descendants = build_descendants_map(parents)
    assert descendants[HostName("a")] == (HostName("b"),)
    assert descendants[HostName("b")] == (HostName("a"),)


def test_build_descendants_map_caps_at_max() -> None:
    # Linear chain longer than the cap; first host's list must be truncated.
    chain_length = MAX_HOST_DESCENDANTS + 50
    parents: dict[HostName, tuple[HostName, ...]] = {HostName("h0"): ()}
    for i in range(1, chain_length):
        parents[HostName(f"h{i}")] = (HostName(f"h{i - 1}"),)
    descendants = build_descendants_map(parents)
    assert len(descendants[HostName("h0")]) == MAX_HOST_DESCENDANTS


def test_build_descendants_map_unknown_parent_ignored() -> None:
    # Reference to a host not in the input — should not crash, just no children.
    parents = {
        HostName("orphan"): (HostName("missing"),),
    }
    descendants = build_descendants_map(parents)
    assert descendants[HostName("orphan")] == ()
