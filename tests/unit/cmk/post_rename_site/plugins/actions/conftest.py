#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Iterator

import pytest
from flask import Flask

from tests.unit.cmk.gui.conftest import (  # NOQA # pylint: disable=unused-import
    admin_auth_request,
    deactivate_search_index_building_at_requenst_end,
    flask_app,
    gui_cleanup_after_test,
    load_config,
    request_context,
    with_admin,
)

from cmk.gui import http


@pytest.fixture(autouse=True)
def post_rename_request_context(  # pylint: disable=redefined-outer-name
    flask_app: Flask,  # noqa: F811
    gui_cleanup_after_test: None,  # noqa: F811
    admin_auth_request: http.Request,  # noqa: F811
) -> Iterator[None]:
    """This fixture registers a global htmllib.html() instance just like the regular GUI"""
    with flask_app.test_client() as client:
        client.get(admin_auth_request)
        yield
