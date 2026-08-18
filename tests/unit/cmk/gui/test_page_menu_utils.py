#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.page_menu_utils import host_availability_url


def test_availability_points_at_the_legacy_view_not_at_the_asking_page() -> None:
    """The entry's default URL is the asking page's own, which cannot render availability."""
    url = host_availability_url("myhost", "mysite")

    assert url.startswith("view.py?")
    assert "view_name=host" in url
    assert "host=myhost" in url
    assert "site=mysite" in url
    assert "mode=availability" in url
