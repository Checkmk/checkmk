#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.gui import view_breadcrumbs
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.type_defs import ViewSpec
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view import View

HOST_BREADCRUMB = Breadcrumb([BreadcrumbItem("myhost", "view.py?view_name=host", None)])


def _single_service_view_without_service_context() -> View:
    # A single service view that was opened with a host but no service filter, e.g. through a
    # hand written or outdated bookmark
    return View(
        "svcproblems",
        cast(ViewSpec, {"single_infos": ["host", "service"], "datasource": "services"}),
        {"host": {"host": "myhost"}},
        UserPermissions({}, {}, {}, []),
    )


def test_host_hierarchy_breadcrumb_stops_at_host_without_service_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        view_breadcrumbs, "make_host_breadcrumb", lambda *_args, **_kwargs: HOST_BREADCRUMB
    )

    assert (
        view_breadcrumbs._host_hierarchy_breadcrumb(_single_service_view_without_service_context())
        == HOST_BREADCRUMB
    )


ALLHOSTS_VIEW_SPEC = cast(
    ViewSpec,
    {"title": "All hosts", "topic": "overview", "single_infos": [], "add_context_to_title": False},
)


@pytest.mark.xfail(strict=True, reason="Crash group 4245: KeyError in make_host_breadcrumb")
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
