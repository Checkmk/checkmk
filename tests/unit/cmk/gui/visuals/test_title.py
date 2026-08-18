#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

from cmk.gui.type_defs import Visual
from cmk.gui.visuals import visual_title

# A saved visual from before the "Context information" option existed, so it carries no
# add_context_to_title key
VISUAL_WITHOUT_ADD_CONTEXT_TO_TITLE = cast(Visual, {"title": "My view", "single_infos": []})


def test_visual_title_without_add_context_to_title(request_context: None) -> None:
    assert visual_title("view", VISUAL_WITHOUT_ADD_CONTEXT_TO_TITLE, {}) == "My view"
