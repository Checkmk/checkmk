#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Maps stays out of the Customize menu until its page exists.

The menu builder links every declared pagetype to ``<type_name>s.py`` -- for
maps that is ``maps.py``, which is still being merged, so declaring the type
would put a dead link into the menu (the GUI crawl trips over it). Drop this
module when ``cmk.maps.gui`` goes back to ``pagetypes.declare(MapPage)``.
"""

from cmk.gui import pagetypes


def test_map_is_not_offered_in_the_customize_menu(load_plugins: None) -> None:  # noqa: ARG001
    assert "map" not in pagetypes.all_page_types()
