#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.ccc.store import DimSerializer, ObjectStore
from cmk.update_config.plugins.actions.signing_key_states import migrate_signing_key_states


def test_int_keys_migrated_to_str(tmp_path: Path) -> None:
    state_file = tmp_path / "signing_key_states.mk"
    store = ObjectStore(state_file, serializer=DimSerializer())
    store.write_obj({1: 85, 2: 45})

    migrate_signing_key_states(state_file)

    assert store.read_obj(default={}) == {"1": 85, "2": 45}


def test_str_keys_unchanged(tmp_path: Path) -> None:
    state_file = tmp_path / "signing_key_states.mk"
    store = ObjectStore(state_file, serializer=DimSerializer())
    store.write_obj({"1": 85, "2": 45})
    mtime_before = state_file.stat().st_mtime

    migrate_signing_key_states(state_file)

    assert store.read_obj(default={}) == {"1": 85, "2": 45}
    assert state_file.stat().st_mtime == mtime_before


def test_missing_file(tmp_path: Path) -> None:
    state_file = tmp_path / "signing_key_states.mk"
    migrate_signing_key_states(state_file)

    assert not state_file.exists()


def test_empty_dict(tmp_path: Path) -> None:
    state_file = tmp_path / "signing_key_states.mk"
    store = ObjectStore(state_file, serializer=DimSerializer())
    store.write_obj({})

    migrate_signing_key_states(state_file)

    assert store.read_obj(default={}) == {}
