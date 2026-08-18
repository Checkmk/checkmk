#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.gui import view_breadcrumbs
from cmk.gui.type_defs import ViewSpec
from cmk.gui.utils.roles import UserPermissions

ALLHOSTS_VIEW_SPEC = cast(
    ViewSpec,
    {"title": "All hosts", "topic": "overview", "single_infos": [], "add_context_to_title": False},
)


def test_make_host_breadcrumb_without_permission_for_the_host_view(
    monkeypatch: pytest.MonkeyPatch, request_context: None
) -> None:
    # The user may see the host list, but not the host home page view
    monkeypatch.setattr(
        view_breadcrumbs, "get_permitted_views", lambda: {"allhosts": ALLHOSTS_VIEW_SPEC}
    )

    breadcrumb = view_breadcrumbs.make_host_breadcrumb(
        HostName("myhost"), UserPermissions({}, {}, {}, [])
    )

    assert [item.title for item in breadcrumb][-2:] == ["All hosts", "myhost"]
