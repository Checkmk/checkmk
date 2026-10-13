#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest

from cmk.gui.type_defs import Row
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.icon import IconConfig
from cmk.gui.views.icon.builtin import PredictionIcon


def _rendered(
    perf_data: str, what: Literal["host", "service"] = "service"
) -> None | object | tuple[object, ...]:
    return PredictionIcon.render(
        what,
        Row(
            {
                "site": "heute",
                "host_name": "h",
                "service_description": "svc",
                "service_perf_data": perf_data,
                "host_perf_data": perf_data,
            }
        ),
        [],
        {},
        UserPermissions({}, {}, {}, []),
        IconConfig(
            wato_enabled=True,
            mkeventd_enabled=True,
            multisite_draw_ruleicon=True,
            staleness_threshold=1.5,
            debug=True,
        ),
    )


def _url_of(rendered: None | object | tuple[object, ...]) -> str:
    assert isinstance(rendered, tuple)
    return str(rendered[2])


@pytest.mark.usefixtures("request_context")
def test_a_service_predicted_on_a_metric_offers_the_icon() -> None:
    assert _rendered("util=1;;;; predict_util=2;;;;") is not None


@pytest.mark.usefixtures("request_context")
def test_a_service_predicted_on_a_lower_level_offers_the_icon() -> None:
    assert _rendered("util=1;;;; predict_lower_util=2;;;;") is not None


@pytest.mark.usefixtures("request_context")
def test_a_service_without_a_prediction_offers_no_icon() -> None:
    assert _rendered("util=1;;;; load1=2;;;;") is None


@pytest.mark.usefixtures("request_context")
def test_a_metric_merely_starting_like_a_prediction_offers_no_icon() -> None:
    assert _rendered("predictions_total=1;;;;") is None


@pytest.mark.usefixtures("request_context")
def test_a_host_offers_no_icon() -> None:
    assert _rendered("predict_util=2;;;;", what="host") is None


@pytest.mark.usefixtures("request_context")
def test_the_link_names_no_metric_because_the_page_shows_every_one() -> None:
    assert "dsname" not in _url_of(_rendered("predict_lower_util=2;;;;"))


@pytest.mark.usefixtures("request_context")
def test_the_link_carries_the_service_the_prediction_belongs_to() -> None:
    assert "service=svc" in _url_of(_rendered("predict_util=2;;;;"))
