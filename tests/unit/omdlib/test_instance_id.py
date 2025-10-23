#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from uuid import UUID

from omdlib.instance_id import create_instance_id


def _load_instance_id(site_home: Path) -> UUID | None:
    try:
        return UUID((site_home / "etc/omd/instance_id").read_text())
    except (FileNotFoundError, ValueError):
        return None


def test_create_instance_id(tmp_path: Path) -> None:
    instance_id_1 = UUID("bb28ec27-4f77-409f-982e-92df861b25be")
    instance_id_2 = UUID("e65f2f7b-abcb-400c-9859-b5571b3d2679")

    (tmp_path / "etc/omd/").mkdir(parents=True)

    create_instance_id(site_home=tmp_path, instance_id=instance_id_1)
    assert _load_instance_id(tmp_path) == instance_id_1

    create_instance_id(site_home=tmp_path, instance_id=instance_id_2)
    assert _load_instance_id(tmp_path) == instance_id_2
