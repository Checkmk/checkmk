#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, cast

import pytest

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import Request
from cmk.gui.pages import PageContext
from cmk.gui.views.page_ajax_filters import AjaxInitialViewFilters


class _RequestReturning:
    """Stands in for the page's own request so the payload needs no monkeypatching.

    Patching ``get_request`` on the real request would be undone after the request
    context has already closed, which fails the teardown rather than the test.
    """

    def __init__(self, api_request: dict[str, Any]) -> None:
        self._api_request = api_request

    def get_request(self, *_args: object, **_kwargs: object) -> dict[str, Any]:
        return self._api_request


@pytest.mark.xfail(strict=True, reason="Crash group 4109: AssertionError on page_request_vars")
def test_page_reports_a_request_without_page_request_vars(
    request_context: None,
    load_config: Config,
    with_admin_login: UserId,
) -> None:
    # A well formed request for an existing view, but with no page_request_vars entry
    page_request = _RequestReturning({"varprefix": "", "page_name": "allhosts"})
    ctx = PageContext(config=load_config, request=cast(Request, page_request))

    with pytest.raises(MKUserError) as excinfo:
        AjaxInitialViewFilters().page(ctx)

    # Pinned to this varname so an unrelated MKUserError (e.g. the unknown view name
    # raised by _get_context) cannot satisfy the assertion
    assert excinfo.value.varname == "page_request_vars"
