#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest
from werkzeug.test import create_environ

from cmk.gui.config import get_default_config, make_config_object
from cmk.gui.context import AppContext, RequestContext
from cmk.gui.ctx_stack import app_stack, request_stack
from cmk.gui.display_options import DisplayOptions
from cmk.gui.globals import PrependURLFilter
from cmk.gui.http import Request, Response
from cmk.gui.logged_in import LoggedInNobody
from cmk.gui.utils.output_funnel import OutputFunnel
from cmk.gui.utils.script_helpers import session_wsgi_app


@pytest.fixture
def with_request_context():
    environ = create_environ()
    resp = Response()
    with AppContext(session_wsgi_app(debug=False), stack=app_stack()), RequestContext(
        req=Request(environ),
        resp=resp,
        funnel=OutputFunnel(resp),
        config_obj=make_config_object(get_default_config()),
        user=LoggedInNobody(),
        display_options=DisplayOptions(),
        stack=request_stack(),
        url_filter=PrependURLFilter(),
    ):
        yield
