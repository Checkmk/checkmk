#!/usr/bin/env python

# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.playwright.helpers import PPage


def test_login_works(logged_in_page: PPage) -> None:
    logged_in_page.main_frame.check_page_title("Main dashboard")
