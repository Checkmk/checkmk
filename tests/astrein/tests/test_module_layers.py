#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path

from tests.astrein.checker_module_layers import ModuleLayersChecker
from tests.astrein.config.module_layers_config import (
    CLEAN_PLUGIN_FAMILIES,
    Component,
    COMPONENTS,
)


def test_no_component_masked_by_more_general_component() -> None:
    """Ensure no component shadows another in the COMPONENTS mapping.

    This test verifies that component hierarchies are properly ordered so that
    more specific components aren't masked by more general ones.
    """
    seen: set[Component] = set()
    for component in COMPONENTS:
        shadowed = {c for c in seen if component.is_below(c)}
        assert not shadowed, f"Component {component} is shadowed by {shadowed}"
        seen.add(component)


def test_clean_plugin_families_list_up_to_date() -> None:
    """Ensure all plugin families in CLEAN_PLUGIN_FAMILIES exist.

    This test verifies that the list of clean plugin families is up to date
    and all listed families have corresponding directories in the filesystem.
    """
    # Get repository root by walking up from this test file
    test_file = Path(__file__).resolve()
    repo_root = test_file.parent.parent.parent.parent.parent

    # Check that repo_root looks correct (should contain cmk/plugins/)
    plugins_dir = repo_root / "cmk" / "plugins"
    assert plugins_dir.exists(), f"Expected plugins directory at {plugins_dir}"

    for family in CLEAN_PLUGIN_FAMILIES:
        family_dir = plugins_dir / family
        assert family_dir.exists(), (
            f"Plugin family '{family}' listed in CLEAN_PLUGIN_FAMILIES "
            f"does not have a corresponding directory at {family_dir}"
        )


def test_inline_suppression_support() -> None:
    """Test that inline suppressions are respected by the checker."""
    test_file = Path(__file__).resolve()
    repo_root = test_file.parent.parent.parent.parent.parent

    # Test code with suppressed and unsuppressed violations
    source_code = """from cmk.base.config import something  # astrein: disable=cmk-module-layer-violation

# astrein: disable=cmk-module-layer-violation
from cmk.gui.something import other

from cmk.checkengine.plugins import Plugin
"""

    # Parse and check
    tree = ast.parse(source_code)
    test_file_path = repo_root / "cmk" / "test_suppression.py"

    checker = ModuleLayersChecker(test_file_path, repo_root, source_code)
    errors = checker.check(tree)

    # Only the last import (line 6) should produce an error
    assert len(errors) == 1
    assert errors[0].line == 6
