#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest  # type: ignore[import]

from werkzeug.test import create_environ
from cmk.gui.display_options import DisplayOptions
from cmk.gui.globals import AppContext, RequestContext
from cmk.gui.http import Request
from testlib.utils import DummyApplication


@pytest.fixture
def with_request_context():
    environ = create_environ()
    with AppContext(DummyApplication(environ, None)), \
            RequestContext(req=Request(environ), display_options=DisplayOptions()):
        yield
