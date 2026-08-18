#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

import pytest

from cmk.gui.type_defs import VisualContext
from cmk.gui.visuals._page_edit_visual import _visual_spec_single


def test_visual_spec_single_to_valuespec_keeps_a_well_formed_context() -> None:
    spec = _visual_spec_single("host")

    assert spec.to_valuespec(cast(VisualContext, {"host": {"host": "myhost"}})) == {
        "host": "myhost"
    }


@pytest.mark.xfail(strict=True, reason="Crash group 3955: AttributeError in to_valuespec")
def test_visual_spec_single_to_valuespec_skips_scalar_filter_context() -> None:
    # A context that stores the filter value directly instead of the mapping of HTTP
    # variables the type demands, as written by older versions or by hand editing
    spec = _visual_spec_single("host")

    assert spec.to_valuespec(cast(VisualContext, {"host": "myhost"})) == {}
