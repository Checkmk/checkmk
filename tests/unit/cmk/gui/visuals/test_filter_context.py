#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

from cmk.gui.type_defs import VisualContext
from cmk.gui.visuals._filter_context import missing_context_filters

# A context that stores the filter value directly instead of the mapping of HTTP variables the
# type demands, as written by older versions or by hand editing
SCALAR_CONTEXT = cast(VisualContext, {"host": "myhost"})


def test_missing_context_filters_reports_scalar_filter_context_as_missing() -> None:
    assert missing_context_filters({"host"}, SCALAR_CONTEXT) == {"host"}
