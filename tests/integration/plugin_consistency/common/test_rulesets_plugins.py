#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.discover_plugins import discover_all_plugins, PluginGroup
from cmk.rulesets.v1 import entry_point_prefixes


def test_all_parameter_forms_can_be_built(monkeypatch: pytest.MonkeyPatch) -> None:
    """Forms are built lazily, so a form spec the rulesets v1 API rejects
    (e.g. a name that is not a valid identifier) would otherwise only fail
    when it is first instantiated, e.g. during an update.
    """
    # Forms are built in a site context, some prefill the site name.
    monkeypatch.setenv("OMD_SITE", "NO_SITE")
    rule_specs = discover_all_plugins(
        PluginGroup.RULESETS, entry_point_prefixes(), skip_wrong_types=True, raise_errors=True
    ).plugins

    failures = {}
    for location, rule_spec in rule_specs.items():
        if rule_spec.parameter_form is None:
            continue
        try:
            rule_spec.parameter_form()
        except Exception as e:
            failures[str(location)] = repr(e)

    assert not failures
