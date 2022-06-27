#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from unittest.mock import MagicMock

from cmk.gui import hooks


def test_hooks(logged_in_wsgi_app, mock_livestatus) -> None:
    start_func = MagicMock()
    end_func = MagicMock()
    hooks.register("request-start", start_func)
    hooks.register("request-end", end_func)
    logged_in_wsgi_app.get("/NO_SITE/check_mk/", status=200)

    start_func.assert_called_once()
    end_func.assert_called_once()
