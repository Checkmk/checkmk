#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.form_specs.private import DatePicker
from cmk.gui.form_specs.vue import (
    get_visitor,
    IncomingData,
    RawDiskData,
    RawFrontendData,
    VisitorOptions,
)


@pytest.mark.parametrize(
    ["value", "expected_value", "has_validation_error"],
    [
        [
            RawFrontendData("1979-02-01"),
            "1979-02-01",
            False,
        ],
        [RawDiskData("1979-02-01"), "1979-02-01", False],
        [RawDiskData("1979-22-01"), "", True],
        [RawDiskData(23), "", True],
        [RawFrontendData(23), "", True],
    ],
)
def test_date_picker(value: IncomingData, expected_value: str, has_validation_error: bool) -> None:
    visitor = get_visitor(DatePicker(), VisitorOptions(migrate_values=True, mask_values=False))
    validation_errors = visitor.validate(value)
    assert (len(validation_errors) > 0) == has_validation_error
    if has_validation_error:
        with pytest.raises(MKGeneralException):
            visitor.to_disk(value)
