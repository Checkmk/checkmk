#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.watolib.rulespecs import rulespec_registry
from cmk.utils.rulesets.definition import RuleGroup


def test_discovered_path_count_survives_the_ruleset_transform() -> None:
    valuespec = rulespec_registry[RuleGroup.CheckgroupParameters("multipath")].valuespec

    transformed = valuespec.transform_value({"discovered_paths": 4})

    assert transformed == {"discovered_paths": 4}
