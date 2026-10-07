#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.gui.type_defs import ColumnSpec
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.page_edit_view import (
    join_painters_of_datasource,
    view_editor_column_spec,
    view_editor_general_properties,
)
from tests.unit.cmk.gui.helpers.painter_context_test_helper import make_painter_context


def _a_join_painter_name() -> str:
    # Any real join painter will do; picking one at runtime keeps the test from
    # failing on an unrelated "unknown painter" validation error.
    return sorted(join_painters_of_datasource("hosts"))[0]


@pytest.mark.usefixtures("request_context")
def test_column_spec_join_column_without_join_value_is_a_user_error() -> None:
    # Adding a "Joined column" in the view editor without filling in the service it
    # joins on. The user must get a validation error on that field, not a crash.
    user_permissions = UserPermissions({}, {}, {}, [])
    vs = view_editor_column_spec("columns", "hosts", make_painter_context(user_permissions))

    with pytest.raises(MKUserError) as excinfo:
        vs.validate_value(
            {
                "columns": [
                    ColumnSpec(
                        _column_type="join_column",
                        name=_a_join_painter_name(),
                        join_value="",
                        column_title="",
                    )
                ]
            },
            "columns",
        )

    # The error must point at the join value field, not at some unrelated element.
    assert "join_value" in (excinfo.value.varname or "")


@pytest.mark.usefixtures("request_context")
def test_the_view_editor_offers_the_automatic_page_reload() -> None:
    properties = view_editor_general_properties("hosts", allow_browser_reload=True)

    assert "browser_reload" in properties.default_value()


@pytest.mark.usefixtures("request_context")
def test_the_view_editor_without_browser_reload_hides_the_automatic_page_reload() -> None:
    properties = view_editor_general_properties("hosts", allow_browser_reload=False)

    assert "browser_reload" not in properties.default_value()
