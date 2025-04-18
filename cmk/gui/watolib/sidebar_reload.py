#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from flask import has_request_context

from cmk.gui.ctx_stack import g


def need_sidebar_reload():
    if not has_request_context():
        return  # Silently accept inactive request context (e.g. non-gui call and tests)
    g.need_sidebar_reload = True


def is_sidebar_reload_needed() -> bool:
    return "need_sidebar_reload" in g and g.need_sidebar_reload
