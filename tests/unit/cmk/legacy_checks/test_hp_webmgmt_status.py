#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.legacy_checks.hp_webmgmt_status import check_hp_webmgmt_status


@pytest.mark.parametrize(
    "section",
    [
        pytest.param(
            [
                [["1", "3"]],  # health entries
                [],  # model subtable missing
                [],  # serial subtable missing
            ],
            id="missing-model-and-serial-rows",
        ),
        pytest.param(
            [
                [["1", "3"]],  # health entries
                [[]],  # model row without columns
                [[]],  # serial row without columns
            ],
            id="missing-model-and-serial-columns",
        ),
    ],
)
def test_check_hp_webmgmt_status_missing_model_and_serial(
    section: list[list[list[str]]],
) -> None:
    assert list(check_hp_webmgmt_status("1", section))
