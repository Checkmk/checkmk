#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from omdlib.skel_permissions import load_skel_permissions_from


def test_load_skel_permissions_from(tmp_path: Path) -> None:
    pfile = tmp_path / "skel.permissions"
    pfile.open("w", encoding="utf-8").write("bla 755\nblub 644\n")
    assert load_skel_permissions_from(str(pfile)) == {"bla": 493, "blub": 420}
