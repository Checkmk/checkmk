#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.type_defs import UserSpec

from cmk.update_config.plugins.actions.user_attributes import (
    _add_or_update_locked_attr,
    _update_disable_notifications,
)


@pytest.mark.parametrize(
    ["old", "expected_new"],
    [
        pytest.param(
            {"disable_notifications": True},
            {"disable_notifications": {"disable": True}},
        ),
        pytest.param({"disable_notifications": False}, {"disable_notifications": {}}),
        pytest.param({"disable_notifications": {}}, {"disable_notifications": {}}),
        pytest.param({}, {}),
    ],
)
def test_update_disable_notifications(old: UserSpec, expected_new: UserSpec) -> None:
    _update_disable_notifications(old)
    assert old == expected_new


@pytest.mark.parametrize(
    ["pre_update", "post_update"],
    [
        pytest.param({}, {"locked": False}),
        pytest.param({"locked": True}, {"locked": True}),
        pytest.param({"locked": False}, {"locked": False}),
        pytest.param({"locked": None}, {"locked": False}),
    ],
)
def test_add_or_update_locked_attr(pre_update: UserSpec, post_update: UserSpec) -> None:
    _add_or_update_locked_attr(pre_update)
    assert pre_update == post_update
