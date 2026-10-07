#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.ibm_mq.rulesets.ibm_mq_queues import rule_spec_ibm_mq_queues
from cmk.rulesets.v1.form_specs import Dictionary

_NO_LEVELS = ("no_levels", None)


def _migrate(element: str, value: object) -> object:
    form = rule_spec_ibm_mq_queues.parameter_form()
    assert isinstance(form, Dictionary)
    assert (migrate := form.elements[element].parameter_form.migrate) is not None
    return migrate(value)


# fmt: off
@pytest.mark.parametrize(
    "element, value, expected",
    [
        pytest.param("curdepth", (None, None), _NO_LEVELS, id="ignored queue depth"),
        pytest.param("curdepth", (100, 500), ("fixed", (100, 500)), id="queue depth"),
        pytest.param("curdepth_perc", (None, None), _NO_LEVELS, id="ignored queue depth in %"),
        pytest.param("curdepth_perc", (80.0, 90.0), ("fixed", (80.0, 90.0)), id="queue depth in %"),
        pytest.param("msgage", (1800, 3600), ("fixed", (1800.0, 3600.0)), id="oldest message age"),
        pytest.param("lgetage", (60, 120), ("fixed", (60.0, 120.0)), id="last get age"),
        pytest.param("lputage", (60, 120), ("fixed", (60.0, 120.0)), id="last put age"),
    ],
)
# fmt: on
def test_levels_keep_their_values(element: str, value: object, expected: object) -> None:
    assert _migrate(element, value) == expected


# fmt: off
@pytest.mark.parametrize(
    "element, value, expected",
    [
        pytest.param("ipprocs", {"upper": (4, 8)}, {"lower": _NO_LEVELS, "upper": ("fixed", (4, 8))}, id="input upper only"),
        pytest.param("opprocs", {"lower": (3, 1)}, {"lower": ("fixed", (3, 1)), "upper": _NO_LEVELS}, id="output lower only"),
        pytest.param("opprocs", {}, {"lower": _NO_LEVELS, "upper": _NO_LEVELS}, id="output none"),
    ],
)
# fmt: on
def test_handle_levels_left_out_become_no_levels(
    element: str, value: object, expected: object
) -> None:
    assert _migrate(element, value) == expected


def test_migrated_handle_levels_stay_unchanged() -> None:
    levels = {"lower": ("fixed", (3, 1)), "upper": ("fixed", (10, 20))}

    assert _migrate("ipprocs", levels) == levels
