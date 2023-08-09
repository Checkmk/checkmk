#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import http.client

from cmk.gui.exceptions import HTTPRedirect

from ._registry import mode_registry


def mode_url(mode_name: str, **kwargs: str) -> str:
    """Returns an URL pointing to the given Setup mode

    To be able to link some modes, there are context information needed, which are need to be
    gathered from the current request variables.
    """
    return mode_registry[mode_name].mode_url(**kwargs)


def redirect(location: str, code: int = http.client.FOUND) -> HTTPRedirect:
    """Returns an object triggering a redirect to another page
    Similar to flasks redirect method.
    """
    return HTTPRedirect(location, code=code)
