#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.form_specs import (
    DEFAULT_VALUE,
    get_visitor,
    IncomingData,
    RawDiskData,
    RawFrontendData,
    VisitorOptions,
)
from cmk.gui.form_specs.unstable import LegacyValueSpec
from cmk.gui.valuespec import Integer, TextInput


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize("value", [DEFAULT_VALUE, RawDiskData("foo")])
def test_legacy_valuespec_data_carries_varprefix_of_its_html(value: IncomingData) -> None:
    visitor = get_visitor(
        LegacyValueSpec.wrap(TextInput()),
        VisitorOptions(migrate_values=True, mask_values=False),
    )

    _spec, data = visitor.to_vue(value)

    assert isinstance(data, dict)
    assert f'name="{data["varprefix"]}"' in data["input_html"]


@pytest.mark.usefixtures("request_context")
def test_legacy_valuespec_rerenders_invalid_input_under_posted_varprefix() -> None:
    visitor = get_visitor(
        LegacyValueSpec.wrap(Integer()),
        VisitorOptions(migrate_values=True, mask_values=False),
    )

    _spec, data = visitor.to_vue(
        RawFrontendData({"varprefix": "posted", "input_context": {"posted": "not a number"}})
    )

    assert isinstance(data, dict)
    assert data["varprefix"] == "posted"
    assert 'name="posted"' in data["input_html"]
