#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

from cmk.gui.type_defs import VisualContext
from cmk.gui.visuals._filter_context import context_to_uri_vars, missing_context_filters

# A context that stores the filter value directly instead of the mapping of HTTP variables the
# type demands, as written by older versions or by hand editing
SCALAR_CONTEXT = cast(VisualContext, {"host": "myhost"})


def test_missing_context_filters_reports_scalar_filter_context_as_missing() -> None:
    assert missing_context_filters({"host"}, SCALAR_CONTEXT) == {"host"}


def test_context_to_uri_vars_skips_scalar_filter_context() -> None:
    # The well formed entries must still reach the URL; only the unusable one is dropped
    context = cast(VisualContext, {"host": "myhost", "service": {"service": "CPU"}})

    assert context_to_uri_vars(context) == [("service", "CPU")]
