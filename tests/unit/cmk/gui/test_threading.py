#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from multiprocessing.pool import ThreadPool

import flask
from flask.globals import request

from cmk.gui.config import active_config
from cmk.gui.utils.request_context import copy_request_context


def _run_in_thread(attr: str) -> tuple[bool, str]:
    return getattr(active_config, attr), request.url


def test_thread_pool_request_context(flask_app: flask.Flask) -> None:

    path = "/NO_SITE/check_mk/index.html"
    with flask_app.test_request_context(path):
        flask_app.preprocess_request()

        size = 20
        with ThreadPool(size) as pool:
            results = pool.map(
                copy_request_context(_run_in_thread),
                ["debug"] * size,
            )

    assert len(results) == size
    for debug, url in results:
        assert not debug
        assert url.endswith(path)
