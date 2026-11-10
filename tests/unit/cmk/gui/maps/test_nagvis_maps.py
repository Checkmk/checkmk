#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.maps.gui._images import import_icon
from cmk.maps.gui.nagvis_maps import ShapeCopies

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
_OTHER_PNG = b"\x89PNG\r\n\x1a\n" + b"\x01" * 16


def test_a_shape_whose_name_another_image_got_meanwhile_is_named() -> None:
    shapes = ShapeCopies(contents={"cloud.png": _PNG}, used={"cloud.png"})
    import_icon("cloud.png", _OTHER_PNG)

    (warning,) = shapes.store()

    assert "cloud.png" in warning
    assert shapes.added == []
