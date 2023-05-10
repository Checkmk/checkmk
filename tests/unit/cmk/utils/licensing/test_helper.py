#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from uuid import UUID

from cmk.utils.licensing.helper import get_instance_id_file_path, load_instance_id, save_instance_id


def test_save_instance_id(tmp_path: Path) -> None:
    instance_id = UUID("bb28ec27-4f77-409f-982e-92df861b25be")

    instance_id_file_path = get_instance_id_file_path(tmp_path)
    assert not instance_id_file_path.exists()

    save_instance_id(file_path=instance_id_file_path, instance_id=instance_id)
    assert instance_id_file_path.exists()
    assert load_instance_id(instance_id_file_path) == instance_id


def test_save_instance_id_twice(tmp_path: Path) -> None:
    instance_id_1 = UUID("bb28ec27-4f77-409f-982e-92df861b25be")
    instance_id_2 = UUID("e65f2f7b-abcb-400c-9859-b5571b3d2679")

    instance_id_file_path = get_instance_id_file_path(tmp_path)
    assert not instance_id_file_path.exists()

    save_instance_id(file_path=instance_id_file_path, instance_id=instance_id_1)
    assert instance_id_file_path.exists()
    assert load_instance_id(instance_id_file_path) == instance_id_1

    save_instance_id(file_path=instance_id_file_path, instance_id=instance_id_2)
    assert instance_id_file_path.exists()
    assert load_instance_id(instance_id_file_path) == instance_id_2
