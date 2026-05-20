#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from typing import Any, cast

from cmk.ccc.site import SiteId
from cmk.gui.watolib.site_changes import ChangeSpec, SiteChanges
from cmk.update_config.plugins.actions.migrate_site_changes_schema import (
    _migrate_record,
    MigrateSiteChangesSchema,
)


def _legacy_record(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "id": "abc",
        "action_name": "edit-host",
        "text": "Changed host",
        "object": None,
        "user_id": "cmkadmin",
        "domains": ["check_mk"],
        "time": 1.0,
        "need_sync": True,
        "need_restart": True,
        "has_been_activated": False,
        "prevent_discard_changes": False,
    }
    defaults.update(overrides)
    return defaults


def test_migrate_record_translates_need_to_force() -> None:
    record = _legacy_record(need_sync=False, need_restart=True)
    changed = _migrate_record(record)
    assert changed is True
    assert record["force_sync"] is False
    assert record["force_restart"] is True
    assert "need_sync" not in record
    assert "need_restart" not in record


def test_migrate_record_drops_has_been_activated() -> None:
    record = _legacy_record(has_been_activated=True)
    _migrate_record(record)
    assert "has_been_activated" not in record


def test_migrate_record_adds_default_force_apache_reload() -> None:
    record = _legacy_record()
    _migrate_record(record)
    assert record["force_apache_reload"] is False


def test_migrate_record_idempotent_on_new_schema() -> None:
    record = {
        "id": "abc",
        "action_name": "edit-host",
        "text": "x",
        "object": None,
        "user_id": "cmkadmin",
        "domains": ["check_mk"],
        "time": 1.0,
        "force_sync": True,
        "force_restart": False,
        "force_apache_reload": True,
        "prevent_discard_changes": False,
    }
    snapshot = dict(record)
    assert _migrate_record(record) is False
    assert record == snapshot


def test_action_migrates_persisted_records() -> None:
    site_id = SiteId("test_site")
    store = SiteChanges(site_id)
    store.append(cast("ChangeSpec", _legacy_record(id="r1")))
    store.append(cast("ChangeSpec", _legacy_record(id="r2", need_restart=False)))
    try:
        MigrateSiteChangesSchema(
            name="x",
            title="x",
            sort_index=0,
            expiry_version=None,  # type: ignore[arg-type]
        )(logging.getLogger("test"))

        migrated = list(store.read())
        assert len(migrated) == 2
        for record in migrated:
            assert "need_sync" not in record
            assert "need_restart" not in record
            assert "has_been_activated" not in record
            assert "force_sync" in record
            assert "force_restart" in record
            assert "force_apache_reload" in record
    finally:
        store.clear()
        store._path.unlink(missing_ok=True)


def test_action_no_op_when_directory_missing(tmp_path: Any, monkeypatch: Any) -> None:
    # Pointing wato_var_dir at an empty / non-existent directory must not
    # raise.
    monkeypatch.setattr(
        "cmk.update_config.plugins.actions.migrate_site_changes_schema.wato_var_dir",
        lambda: tmp_path / "does-not-exist",
    )
    MigrateSiteChangesSchema(
        name="x",
        title="x",
        sort_index=0,
        expiry_version=None,  # type: ignore[arg-type]
    )(logging.getLogger("test"))
