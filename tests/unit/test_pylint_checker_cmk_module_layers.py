#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.pylint.checker_cmk_module_layers import CLEAN_PLUGIN_FAMILIES, Component, COMPONENTS
from tests.testlib.common.repo import repo_path


def test_no_component_masked_by_more_general_component() -> None:
    # These are not actual components (anymore) but rather scopes where certain
    # dependencies are tolerated (desired or not is a different question).
    # This tests makes sure that no general rule masks a more specific one.
    seen_components = set[Component]()
    for component in COMPONENTS:
        shadowed = {c for c in seen_components if component.is_below(c)}
        seen_components.add(component)
        assert not shadowed


def test_clean_plugin_families_list_up_to_date() -> None:
    """make sure we remove plugin families that don't exist

    (anymore, because they've been moved into a package)
    """
    assert not {
        family
        for family in CLEAN_PLUGIN_FAMILIES
        if not (repo_path() / f"cmk/plugins/{family}").exists()
    }
