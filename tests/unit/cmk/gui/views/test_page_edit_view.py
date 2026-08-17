#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.gui.type_defs import ColumnSpec
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.page_edit_view import join_painters_of_datasource, view_editor_column_spec


def _a_join_painter_name(user_permissions: UserPermissions) -> str:
    # Any real join painter will do; picking one at runtime keeps the test from
    # failing on an unrelated "unknown painter" validation error.
    return sorted(join_painters_of_datasource("hosts", user_permissions))[0]


@pytest.mark.usefixtures("request_context")
@pytest.mark.xfail(
    strict=True, reason="Crash report 7b5174bc-85ca-11f1-ba93-0222456d7c48: ValueError"
)
def test_column_spec_join_column_without_join_value_is_a_user_error() -> None:
    # Adding a "Joined column" in the view editor without filling in the service it
    # joins on. The user must get a validation error on that field, not a crash.
    user_permissions = UserPermissions({}, {}, {}, [])
    vs = view_editor_column_spec("columns", "hosts", user_permissions)

    with pytest.raises(MKUserError):
        vs.validate_value(
            {
                "columns": [
                    ColumnSpec(
                        _column_type="join_column",
                        name=_a_join_painter_name(user_permissions),
                        join_value="",
                        column_title="",
                    )
                ]
            },
            "columns",
        )
