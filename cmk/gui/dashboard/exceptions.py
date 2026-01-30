#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from http import HTTPStatus

from cmk.gui.exceptions import MKHTTPException


class WidgetRenderError(MKHTTPException):
    """Is raised when a dashboard widget fails to render properly.

    The message is shown to the user as an error, so should be actionable."""

    status = HTTPStatus.BAD_REQUEST.value
