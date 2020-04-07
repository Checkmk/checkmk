#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from werkzeug.test import create_environ

from cmk.gui import htmllib
from cmk.gui.globals import html, request, RequestContext, AppContext
from cmk.gui.http import Request
from cmk.update_config import DummyApplication


def test_del_vars():
    environ = dict(create_environ(),
                   REQUEST_URI='',
                   QUERY_STRING='foo=foo&_username=foo&_password=bar&bar=bar')
    with AppContext(DummyApplication(environ, None)), \
            RequestContext(htmllib.html(Request(environ))):
        # First we hit the cached property so we can see that the underlying Request object
        # actually got replaced later.
        _ = request.args
        _ = html.request.args

        html.request.set_var("foo", "123")

        html.del_var_from_env("_username")
        html.del_var_from_env("_password")

        # Make test independent of dict sorting
        assert html.request.query_string in ['foo=foo&bar=bar', 'bar=bar&foo=foo']

        assert '_password' not in html.request.args
        assert '_username' not in html.request.args

        # Check the request local proxied version too.
        # Make test independent of dict sorting
        assert request.query_string in ['foo=foo&bar=bar', 'bar=bar&foo=foo']
        assert '_password' not in request.args
        assert '_username' not in request.args

        assert html.request.var("foo") == "123"
