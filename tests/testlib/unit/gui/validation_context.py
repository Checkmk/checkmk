#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from werkzeug.datastructures import ETags

from cmk.gui.config import Config
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.openapi.framework import ApiContext, APIVersion
from cmk.gui.openapi.framework.model.validation_context import RequestValidationContext


def make_api_context(config: Config, user: LoggedInUser) -> ApiContext:
    """An ApiContext like the framework builds it for a request."""
    return ApiContext.new(
        config=config,
        version=APIVersion.UNSTABLE,
        etag_if_match=ETags(),
        host_url="http://localhost/",
        user=user,
        token=None,
    )


def make_validation_context(config: Config, user: LoggedInUser) -> RequestValidationContext:
    """The validation context to pass as `context` when validating an API model in a test."""
    return RequestValidationContext(make_api_context(config, user))
