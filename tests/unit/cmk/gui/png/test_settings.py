#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest

from cmk.gui.graphing import GraphRenderOptions
from cmk.gui.png import GraphDisplayConfigImage


@pytest.mark.parametrize(
    "show_title, expected",
    [
        pytest.param("inline", True, id="title on the graph area"),
        pytest.param(True, True, id="title"),
        pytest.param(False, False, id="no title"),
    ],
)
def test_image_config_shows_the_title_requested_by_the_options(
    show_title: bool | Literal["inline"], expected: bool
) -> None:
    config = GraphDisplayConfigImage.from_options(GraphRenderOptions(show_title=show_title))

    assert config.show_title is expected
