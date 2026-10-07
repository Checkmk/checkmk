#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from werkzeug.test import create_environ

from cmk.gui.config import Config
from cmk.gui.display_options import DisplayOptions
from cmk.gui.http import Request, Response
from cmk.gui.painter import PainterContext
from cmk.gui.painter.helpers import RenderLink
from cmk.gui.painter_options import PainterOptions
from cmk.gui.theme import make_theme
from cmk.gui.utils.roles import UserPermissions


def make_painter_context(user_permissions: UserPermissions) -> PainterContext:
    request = Request(create_environ())
    return PainterContext(
        config=Config(),
        request=request,
        painter_options=PainterOptions(),
        theme=make_theme(validate_choices=False),
        url_renderer=RenderLink(request, Response(), DisplayOptions()),
        user_permissions=user_permissions,
    )
