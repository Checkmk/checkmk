#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from omdlib.admin_mail import write_admin_mail_forward


def test_write_admin_mail_forward_sets_address(tmp_path: Path) -> None:
    write_admin_mail_forward("_", tmp_path, {"ADMIN_MAIL": "admin@example.com"})
    assert (tmp_path / ".forward").read_text() == "admin@example.com\n"


def test_write_admin_mail_forward_clear_removes(tmp_path: Path) -> None:
    (tmp_path / ".forward").write_text("old@example.com\n")
    write_admin_mail_forward("_", tmp_path, {"ADMIN_MAIL": ""})
    assert not (tmp_path / ".forward").exists()


def test_write_admin_mail_forward_clear_when_absent(tmp_path: Path) -> None:
    write_admin_mail_forward("_", tmp_path, {"ADMIN_MAIL": ""})
    assert not (tmp_path / ".forward").exists()
