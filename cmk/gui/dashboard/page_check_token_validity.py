#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.gui import http
from cmk.gui.exceptions import MKUserError
from cmk.gui.pages import PageContext, PageResult
from cmk.gui.token_auth import AuthToken, DashboardToken

from .token_util import DashboardTokenAuthenticatedJsonPage


class CheckTokenValidityPage(DashboardTokenAuthenticatedJsonPage):
    """Page to check the validity of a shared dashboard token."""

    @override
    def _get(self, token: AuthToken, token_details: DashboardToken, ctx: PageContext) -> PageResult:
        """Return success if the token is valid."""
        return None

    @override
    def _handle_exception(self, exception: Exception, ctx: PageContext) -> None:
        if isinstance(exception, MKUserError):
            http.response.status_code = 403
            return
        super()._handle_exception(exception, ctx)
