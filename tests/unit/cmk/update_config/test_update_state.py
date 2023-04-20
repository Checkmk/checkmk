#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path

import pytest

from cmk.update_config.update_state import UpdateState


class TestUpdateState:
    def test_load_save(self, tmp_path: Path) -> None:
        update_state = UpdateState.load(tmp_path)
        update_state.setdefault("my_action_1")["my_key"] = "value_1"
        update_state.setdefault("my_action_2")["my_key"] = "value_2"
        update_state.save()

        update_state_2 = UpdateState.load(tmp_path)
        assert update_state_2.setdefault("my_action_1") == {"my_key": "value_1"}
        assert update_state_2.setdefault("my_action_2") == {"my_key": "value_2"}

    def test_non_string_value_raises_during_save(self, tmp_path: Path) -> None:
        update_state = UpdateState.load(tmp_path)
        update_state.setdefault("my_action")["my_key"] = 0.0  # type: ignore[assignment]

        with pytest.raises(TypeError):
            update_state.save()
