#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.playwright.helpers import PPage


def test_login_works(logged_in_page: PPage) -> None:
    logged_in_page.main_area.check_page_title("Main dashboard")
