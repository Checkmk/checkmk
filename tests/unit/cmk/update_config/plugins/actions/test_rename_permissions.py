#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.gui.role_types import UserRoleBase
from cmk.update_config.plugins.actions.rename_permissions import rename_permissions

_LOGGER = logging.getLogger(__name__)

_OLD = "general.query_metric_backend_from_custom_graph_editor"
_NEW = "general.query_telemetry_metrics_from_custom_graph_editor"


@pytest.mark.parametrize(
    "permissions, expected_permissions, expected_changed",
    [
        pytest.param({_OLD: False}, {_NEW: False}, True, id="renamed"),
        pytest.param({"general.use": True}, {"general.use": True}, False, id="unrelated-kept"),
    ],
)
def test_rename_permissions(
    permissions: dict[str, bool],
    expected_permissions: dict[str, bool],
    expected_changed: bool,
) -> None:
    roles: dict[str, UserRoleBase] = {"role": {"alias": "Role", "permissions": permissions}}

    assert rename_permissions(roles, _LOGGER) is expected_changed
    assert roles["role"]["permissions"] == expected_permissions
