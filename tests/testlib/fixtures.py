#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import pytest  # type: ignore[import]

from testlib.web_session import CMKWebSession
from testlib.event_console import CMKEventConsole


@pytest.fixture(scope="module")
def web(site):
    web = CMKWebSession(site)
    web.login()
    web.enforce_non_localized_gui()
    return web


@pytest.fixture(scope="module")
def ec(site, web):
    return CMKEventConsole(site)
