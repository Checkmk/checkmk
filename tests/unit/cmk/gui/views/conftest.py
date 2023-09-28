#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.view import View
from cmk.gui.views.store import multisite_builtin_views


@pytest.fixture(name="view")
def view_fixture(request_context: None) -> View:
    view_name = "allhosts"
    view_spec = multisite_builtin_views[view_name].copy()
    return View(view_name, view_spec, view_spec.get("context", {}))
