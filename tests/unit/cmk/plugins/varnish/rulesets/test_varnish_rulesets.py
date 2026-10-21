#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.varnish.rulesets import varnish
from cmk.plugins.varnish.rulesets.varnish import (
    rule_spec_varnish_backend,
    rule_spec_varnish_cache_hit_ratio,
    rule_spec_varnish_fetch,
)
from cmk.rulesets.v1.form_specs import Dictionary, SimpleLevels
from cmk.rulesets.v1.rule_specs import CheckParameters


def _migrate(rule_spec: CheckParameters, key: str, value: object) -> object:
    form = rule_spec.parameter_form()
    assert isinstance(form, Dictionary)
    levels = form.elements[key].parameter_form
    assert isinstance(levels, SimpleLevels) and levels.migrate is not None
    return levels.migrate(value)


def test_migrate_legacy_rate_levels() -> None:
    assert _migrate(rule_spec_varnish_backend, "busy", (1.0, 2.5)) == ("fixed", (1.0, 2.5))


def test_migrate_legacy_ratio_levels() -> None:
    assert _migrate(rule_spec_varnish_cache_hit_ratio, "levels_lower", (70.0, 60.0)) == (
        "fixed",
        (70.0, 60.0),
    )


@pytest.mark.parametrize(
    "rule_spec",
    [v for k, v in vars(varnish).items() if k.startswith("rule_spec_")],
)
def test_parameter_form(rule_spec: CheckParameters) -> None:
    assert isinstance(rule_spec.parameter_form(), Dictionary)


def test_migrate_legacy_fetch_keys() -> None:
    form = rule_spec_varnish_fetch.parameter_form()
    assert form.migrate is not None
    assert form.migrate({"1xx": (1.0, 2.0), "bad": (3.0, 4.0)}) == {
        "fetch_1xx": (1.0, 2.0),
        "bad": (3.0, 4.0),
    }
