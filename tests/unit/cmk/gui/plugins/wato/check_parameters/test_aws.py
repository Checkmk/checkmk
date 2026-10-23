#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.plugins.wato.check_parameters.aws import fs_aws_limits
from cmk.rulesets.v1 import Title


def _read_aws_limits_from_disk(disk_data: object) -> object:
    visitor = get_visitor(
        fs_aws_limits(Title("Some resource"), 5),
        VisitorOptions(migrate_values=False, mask_values=False),
    )
    return visitor.to_vue(RawDiskData(disk_data))[1]


@pytest.mark.parametrize(
    "disk_data, frontend_data",
    [
        ((None, None, None), ("alternative_no_levels", [None, None, None])),
        ((None, 80.0, 90.0), ("alternative_levels", [("no_limit", None), 80.0, 90.0])),
        ((100, 80.0, 90.0), ("alternative_levels", [("with_limit", 100), 80.0, 90.0])),
    ],
)
def test_aws_limits_read_the_stored_alternative(disk_data: object, frontend_data: object) -> None:
    assert _read_aws_limits_from_disk(disk_data) == frontend_data


@pytest.mark.parametrize("limit", [True, 1.5, "5"])
def test_aws_limits_reject_a_stored_limit_that_is_no_integer(limit: object) -> None:
    with pytest.raises(MKGeneralException):
        _read_aws_limits_from_disk((limit, 80.0, 90.0))
