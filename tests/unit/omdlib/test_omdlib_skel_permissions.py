#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

from pathlib import Path

from pytest import MonkeyPatch

import omdlib.skel_permissions


def test_read_skel_permissions(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    pfile = tmp_path / "skel.permissions"
    pfile.open("w", encoding="utf-8").write("bla 755\nblub 644\n")

    monkeypatch.setattr(
        omdlib.skel_permissions, "skel_permissions_file_path", lambda v: "%s" % (pfile)
    )

    assert omdlib.skel_permissions.read_skel_permissions() == {"bla": 493, "blub": 420}
