#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.pylint.checker_cmk_module_layers import Component, COMPONENTS


def test_no_component_masked_by_more_general_component():
    # These are not actual components (anymore) but rather scopes where certain
    # dependencies are tolerated (desired or not is a different question).
    # This tests makes sure that no general rule masks a more specific one.
    seen_components = set[Component]()
    for component, _allowed_imports in COMPONENTS:
        shadowed = {c for c in seen_components if component.is_below(c)}
        seen_components.add(component)
        assert not shadowed
