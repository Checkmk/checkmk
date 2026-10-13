#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.ibm_svc.agent_based.ibm_svc_license import (
    check_ibm_svc_license,
    IbmSvcLicenseParams,
    parse_ibm_svc_license,
)

_SECTION = parse_ibm_svc_license(
    [
        ["used_virtualization", "400.00"],
        ["license_virtualization", "412"],
    ]
)


@pytest.mark.parametrize(
    ["params", "expected"],
    [
        pytest.param(
            {"levels": ("absolute", {"warn": 20, "crit": 10})},
            [
                Result(
                    state=State.WARN,
                    summary="used 400 out of 412 licenses (warn/crit at 392/402)",
                ),
                Metric("licenses", 400.0, levels=(392.0, 402.0), boundaries=(0.0, 412.0)),
            ],
            id="absolute",
        ),
        pytest.param(
            {"levels": ("percentage", {"warn": 5.0, "crit": 2.0})},
            [
                Result(
                    state=State.WARN,
                    summary="used 400 out of 412 licenses (warn/crit at 391/403)",
                ),
                Metric(
                    "licenses",
                    400.0,
                    levels=(391.4, 403.76),
                    boundaries=(0.0, 412.0),
                ),
            ],
            id="percentage",
        ),
        pytest.param(
            {"levels": ("crit_on_all", None)},
            [
                Result(state=State.OK, summary="used 400 out of 412 licenses"),
                Metric("licenses", 400.0, levels=(412.0, 412.0), boundaries=(0.0, 412.0)),
            ],
            id="crit-on-all",
        ),
        pytest.param(
            {"levels": ("always_ok", None)},
            [
                Result(state=State.OK, summary="used 400 out of 412 licenses"),
                Metric("licenses", 400.0, boundaries=(0.0, 412.0)),
            ],
            id="always-ok",
        ),
    ],
)
def test_check_ibm_svc_license(
    params: IbmSvcLicenseParams, expected: Sequence[Result | Metric]
) -> None:
    assert list(check_ibm_svc_license("virtualization", params, _SECTION)) == expected


def test_check_ibm_svc_license_all_used_is_critical() -> None:
    section = parse_ibm_svc_license(
        [["used_virtualization", "412.00"], ["license_virtualization", "412"]]
    )
    result, _metric = check_ibm_svc_license(
        "virtualization", {"levels": ("crit_on_all", None)}, section
    )
    assert result == Result(
        state=State.CRIT, summary="used 412 out of 412 licenses (warn/crit at 412/412)"
    )
