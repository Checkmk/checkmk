#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view import View
from cmk.gui.views.store import get_all_views
from cmk.web.utils.request_cache import RequestCache
from tests.unit.cmk.gui.helpers.painter_context_test_helper import make_painter_context


@pytest.fixture(name="view")
def view_fixture(request_context: None) -> View:  # noqa: ARG001  # Unused fixtures are needed for setup side effects
    view_name = "allhosts"
    view_spec = get_all_views()[(UserId.builtin(), view_name)].copy()
    return View(
        view_name,
        view_spec,
        view_spec.get("context", {}),
        make_painter_context(UserPermissions({}, {}, {}, [])),
        RequestCache(Config()),
    )
