#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

from cmk.update_config.plugins.actions.create_instance_id import UPDATE_INSTANCE_ID
from cmk.utils.licensing.helper import get_instance_id_file_path, load_instance_id

LOGGER = logging.getLogger(__name__)


def test_update_instance_id(tmp_path: Path) -> None:
    instance_id_file_path = get_instance_id_file_path(tmp_path)
    assert not instance_id_file_path.exists()
    UPDATE_INSTANCE_ID(LOGGER, tmp_path)
    previous = instance_id_file_path.read_text()
    assert load_instance_id(instance_id_file_path) is not None
    UPDATE_INSTANCE_ID(LOGGER, tmp_path)
    assert previous == instance_id_file_path.read_text()  # check idempotent
