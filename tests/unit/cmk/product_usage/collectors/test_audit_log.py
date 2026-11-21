#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

import cmk.product_usage.collectors.audit_log as audit_log_collector
from cmk.ccc import store
from cmk.product_usage.schema import AuditLog, AuditLogActorClass
from tests.unit.cmk.product_usage.user_store import write_user_store

NO_ENTRIES = AuditLogActorClass(entries=0, last_entry_at=None)


def test_site_without_audit_log_has_no_entries_in_any_actor_class(tmp_path: Path) -> None:
    audit_log = _collect(tmp_path)

    assert audit_log == AuditLog(interactive=NO_ENTRIES, automation=NO_ENTRIES, platform=NO_ENTRIES)


def test_actor_class_has_its_entry_count_and_newest_entry_time(tmp_path: Path) -> None:
    _write_audit_log(
        tmp_path / "wato/log/wato_audit.log",
        [_Entry(user_id="-", time=1767790000), _Entry(user_id="-", time=1767789000)],
    )

    audit_log = _collect(tmp_path)

    assert audit_log.platform == AuditLogActorClass(entries=2, last_entry_at=1767790000)


def test_actor_class_includes_the_entries_of_rotated_audit_logs(tmp_path: Path) -> None:
    log_dir = tmp_path / "wato/log"
    _write_audit_log(log_dir / "wato_audit.log.2026-01-05", [_Entry(user_id="-", time=1767571200)])
    _write_audit_log(
        log_dir / "wato_audit.log.2026-01-05-2", [_Entry(user_id="-", time=1767574800)]
    )
    _write_audit_log(log_dir / "wato_audit.log", [_Entry(user_id="-", time=1767790000)])

    audit_log = _collect(tmp_path)

    assert audit_log.platform == AuditLogActorClass(entries=3, last_entry_at=1767790000)


@pytest.mark.parametrize(
    "malformed_line",
    [
        pytest.param("{'time': 1767789500, 'user_id': '-'", id="truncated"),
        pytest.param("['-', 1767789500]", id="not a dict"),
        pytest.param("{'user_id': '-'}", id="no time"),
        pytest.param("{'time': 'yesterday', 'user_id': '-'}", id="time not a number"),
    ],
)
def test_actor_class_skips_malformed_audit_log_lines(tmp_path: Path, malformed_line: str) -> None:
    _write_audit_log(
        tmp_path / "wato/log/wato_audit.log",
        [
            _Entry(user_id="-", time=1767789000),
            malformed_line,
            _Entry(user_id="-", time=1767790000),
        ],
    )

    audit_log = _collect(tmp_path)

    assert audit_log.platform == AuditLogActorClass(entries=2, last_entry_at=1767790000)


def test_actor_class_skips_an_audit_log_line_that_is_not_valid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "wato/log/wato_audit.log"
    _write_audit_log(
        path, [_Entry(user_id="-", time=1767789000), _Entry(user_id="-", time=1767790000)]
    )
    with path.open("ab") as f:
        # A crash during the write cut the line in the middle of the "ü"
        f.write(b"{'time': 1767790500, 'user_id': '-', 'text': ('str', 'Modified host M\xc3")

    audit_log = _collect(tmp_path)

    assert audit_log.platform == AuditLogActorClass(entries=2, last_entry_at=1767790000)


@pytest.mark.parametrize(
    ("user_id", "connector"),
    [
        pytest.param("jane@acme.com", "cognito", id="cognito user"),
        pytest.param("cmkadmin", "htpasswd", id="local user"),
    ],
)
def test_existing_user_that_is_no_automation_user_is_interactive(
    tmp_path: Path, user_id: str, connector: str
) -> None:
    write_user_store(tmp_path, {user_id: {"connector": connector}})
    _write_audit_log(
        tmp_path / "wato/log/wato_audit.log", [_Entry(user_id=user_id, time=1767790000)]
    )

    audit_log = _collect(tmp_path)

    assert audit_log == AuditLog(
        interactive=AuditLogActorClass(entries=1, last_entry_at=1767790000),
        automation=NO_ENTRIES,
        platform=NO_ENTRIES,
    )


def test_existing_automation_user_is_automation(tmp_path: Path) -> None:
    write_user_store(tmp_path, {"ansible": {"connector": "htpasswd"}})
    _write_automation_user_flag(tmp_path, "ansible")
    _write_audit_log(
        tmp_path / "wato/log/wato_audit.log", [_Entry(user_id="ansible", time=1767790000)]
    )

    audit_log = _collect(tmp_path)

    assert audit_log == AuditLog(
        interactive=NO_ENTRIES,
        automation=AuditLogActorClass(entries=1, last_entry_at=1767790000),
        platform=NO_ENTRIES,
    )


def test_automation_user_created_before_2_4_is_automation(tmp_path: Path) -> None:
    write_user_store(tmp_path, {"ansible": {"connector": "htpasswd"}})
    # Before 2.4, the automation secret was the only indicator of an automation user
    secret = tmp_path / "web/ansible/automation.secret"
    secret.parent.mkdir(parents=True)
    secret.write_text("secret")
    _write_audit_log(
        tmp_path / "wato/log/wato_audit.log", [_Entry(user_id="ansible", time=1767790000)]
    )

    audit_log = _collect(tmp_path)

    assert audit_log.automation == AuditLogActorClass(entries=1, last_entry_at=1767790000)


def test_platform_user_is_platform_also_when_it_is_an_automation_user(tmp_path: Path) -> None:
    write_user_store(tmp_path, {"api_user": {"connector": "htpasswd"}})
    _write_automation_user_flag(tmp_path, "api_user")
    _write_audit_log(
        tmp_path / "wato/log/wato_audit.log", [_Entry(user_id="api_user", time=1767790000)]
    )

    audit_log = _collect(tmp_path, platform_user_ids=frozenset({"api_user"}))

    assert audit_log == AuditLog(
        interactive=NO_ENTRIES,
        automation=NO_ENTRIES,
        platform=AuditLogActorClass(entries=1, last_entry_at=1767790000),
    )


def test_deleted_user_with_an_email_address_as_id_is_interactive(tmp_path: Path) -> None:
    _write_audit_log(
        tmp_path / "wato/log/wato_audit.log", [_Entry(user_id="jane@acme.com", time=1767790000)]
    )

    audit_log = _collect(tmp_path)

    assert audit_log == AuditLog(
        interactive=AuditLogActorClass(entries=1, last_entry_at=1767790000),
        automation=NO_ENTRIES,
        platform=NO_ENTRIES,
    )


def test_deleted_user_with_another_id_is_automation(tmp_path: Path) -> None:
    _write_audit_log(
        tmp_path / "wato/log/wato_audit.log", [_Entry(user_id="ansible", time=1767790000)]
    )

    audit_log = _collect(tmp_path)

    assert audit_log == AuditLog(
        interactive=NO_ENTRIES,
        automation=AuditLogActorClass(entries=1, last_entry_at=1767790000),
        platform=NO_ENTRIES,
    )


def test_platform_user_is_platform_also_when_it_is_not_in_the_user_store(tmp_path: Path) -> None:
    _write_audit_log(
        tmp_path / "wato/log/wato_audit.log", [_Entry(user_id="api_user", time=1767790000)]
    )

    audit_log = _collect(tmp_path, platform_user_ids=frozenset({"api_user"}))

    assert audit_log == AuditLog(
        interactive=NO_ENTRIES,
        automation=NO_ENTRIES,
        platform=AuditLogActorClass(entries=1, last_entry_at=1767790000),
    )


def test_audit_log_carries_no_user_id(tmp_path: Path) -> None:
    write_user_store(tmp_path, {"jane@acme.com": {"connector": "cognito"}})
    _write_audit_log(
        tmp_path / "wato/log/wato_audit.log",
        [
            _Entry(user_id="jane@acme.com", time=1767789000),
            _Entry(user_id="ansible", time=1767790000),
        ],
    )

    dumped = _collect(tmp_path).model_dump_json()

    assert "jane@acme.com" not in dumped
    assert "ansible" not in dumped


def _collect(site_dir: Path, platform_user_ids: frozenset[str] = frozenset()) -> AuditLog:
    return audit_log_collector.collect(
        var_dir=site_dir, default_config_dir=site_dir, platform_user_ids=platform_user_ids
    )


@dataclass(frozen=True, kw_only=True)
class _Entry:
    user_id: str
    time: int


def _write_audit_log(path: Path, entries: Sequence[_Entry | str]) -> None:
    """Write the entries in the format of the GUI's audit log store, a str as it is"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{_line(entry)}\n" for entry in entries))


def _line(entry: _Entry | str) -> str:
    if isinstance(entry, str):
        return entry
    return repr(
        {
            "time": entry.time,
            "object_ref": None,
            "user_id": entry.user_id,
            "action": "edit-host",
            "text": ("str", "Modified host"),
            "diff_text": None,
        }
    )


def _write_automation_user_flag(var_dir: Path, user_id: str) -> None:
    """Mark the user as an automation user, in the format of the GUI's user store"""
    path = var_dir / "web" / user_id / "automation_user.mk"
    path.parent.mkdir(parents=True, exist_ok=True)
    store.save_object_to_file(path, True)
