#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path

from cmk.astrein.checker_module_layers import ModuleLayersChecker
from cmk.astrein.module_layers_config import (
    CLEAN_PLUGIN_FAMILIES,
    Component,
    COMPONENTS,
)


def _make_checker(file_path: str, source_code: str = "") -> ModuleLayersChecker:
    repo_root = Path("/repo")
    full_path = repo_root / file_path
    return ModuleLayersChecker(full_path, repo_root, source_code)


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
    repo_root = test_file.parent.parent.parent.parent
    print(f"Repository root determined as: {repo_root}")  # nosemgrep: disallow-print

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


def test_module_name_for_cmk_base() -> None:
    checker = _make_checker("cmk/base/config.py")
    assert str(checker.module_name) == "cmk.base.config"


def test_module_name_for_cmk_gui_init() -> None:
    checker = _make_checker("cmk/gui/__init__.py")
    assert str(checker.module_name) == "cmk.gui.__init__"


def test_module_name_for_tests_unit() -> None:
    checker = _make_checker("tests/unit/test_foo.py")
    assert str(checker.module_name) == "tests.unit.test_foo"


def test_module_name_for_omdlib() -> None:
    checker = _make_checker("omd/packages/omd/omdlib/foo.py")
    assert str(checker.module_name) == "omdlib.foo"


def test_module_name_for_packages() -> None:
    checker = _make_checker("packages/cmk-agent-based/cmk/base/foo.py")
    assert str(checker.module_name) == "cmk.base.foo"


def test_module_name_for_nonfree_packages() -> None:
    checker = _make_checker("non-free/packages/cmk-enterprise/cmk/gui/bar.py")
    assert str(checker.module_name) == "cmk.gui.bar"


def test_module_name_with_flycheck_prefix() -> None:
    checker = _make_checker("cmk/base/flycheck_config.py")
    assert str(checker.module_name) == "cmk.base.config"


def test_component_for_cmk_base_config() -> None:
    checker = _make_checker("cmk/base/config.py")
    assert checker.component == Component("cmk.base.config")


def test_component_for_cmk_gui() -> None:
    checker = _make_checker("cmk/gui/pages.py")
    assert checker.component == Component("cmk.gui")


def test_component_for_cmk_utils_paths() -> None:
    checker = _make_checker("cmk/utils/paths.py")
    assert checker.component == Component("cmk.utils.paths")


def test_component_for_cmk_ccc() -> None:
    checker = _make_checker("cmk/ccc/version.py")
    assert checker.component == Component("cmk.ccc")


def test_component_for_explicit_mapping_bin_check_mk() -> None:
    checker = _make_checker("bin/check_mk")
    assert checker.component == Component("cmk.base")


def test_component_for_explicit_mapping_bin_cmk_passwd() -> None:
    checker = _make_checker("bin/cmk-passwd")
    assert checker.component == Component("cmk.cmkpasswd")


def test_component_for_file_without_component() -> None:
    checker = _make_checker("some_random_script.py")
    assert checker.component is None


def test_allowed_import_same_component_gui() -> None:
    source_code = "from cmk.gui.pages import Page"
    checker = _make_checker("cmk/gui/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_allowed_import_gui_from_ccc() -> None:
    source_code = "from cmk.ccc.version import Version"
    checker = _make_checker("cmk/gui/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_allowed_import_gui_from_utils() -> None:
    source_code = "from cmk.utils.paths import omd_root"
    checker = _make_checker("cmk/gui/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_allowed_import_gui_from_livestatus_client() -> None:
    source_code = "from cmk.livestatus_client import Query"
    checker = _make_checker("cmk/gui/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_disallowed_import_ccc_from_gui() -> None:
    source_code = "from cmk.gui.pages import Page"
    checker = _make_checker("cmk/ccc/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 1
    assert "cmk.gui.pages" in errors[0].message


def test_disallowed_import_ccc_from_base() -> None:
    source_code = "from cmk.base.config import load_config"
    checker = _make_checker("cmk/ccc/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 1
    assert "cmk.base.config" in errors[0].message


def test_clean_plugin_allowed_imports() -> None:
    source_code = """from cmk.agent_based.v2 import AgentSection
from cmk.rulesets.v1 import form_specs
"""
    checker = _make_checker("cmk/plugins/aws/agent_based/test_check.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_clean_plugin_disallowed_import_from_utils() -> None:
    source_code = "from cmk.utils.paths import omd_root"
    checker = _make_checker("cmk/plugins/aws/agent_based/test_check.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 1
    assert "cmk.utils.paths" in errors[0].message


def test_gui_excludes_gui_plugins() -> None:
    source_code = "from cmk.gui.plugins.views import register"
    checker = _make_checker("cmk/gui/views.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 1
    assert "cmk.gui.plugins" in errors[0].message


def test_simple_import_statement() -> None:
    source_code = "import cmk.base.config"
    checker = _make_checker("cmk/ccc/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 1
    assert "cmk.base.config" in errors[0].message


def test_from_import_statement() -> None:
    source_code = "from cmk.gui.pages import Page"
    checker = _make_checker("cmk/ccc/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 1
    assert "cmk.gui.pages" in errors[0].message


def test_multiple_names_from_import() -> None:
    source_code = "from cmk.gui.pages import Page, register_page, make_header"
    checker = _make_checker("cmk/ccc/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 3
    for error in errors:
        assert "cmk.gui.pages" in error.message


def test_relative_import_level_one() -> None:
    source_code = "from . import local_module"
    checker = _make_checker("cmk/gui/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_relative_import_level_two() -> None:
    source_code = "from .. import parent_module"
    checker = _make_checker("cmk/gui/subdir/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_external_stdlib_imports() -> None:
    source_code = """import sys
import os
from pathlib import Path
"""
    checker = _make_checker("cmk/gui/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_external_third_party_imports() -> None:
    source_code = """import pytest
from typing import Any
import requests
"""
    checker = _make_checker("cmk/gui/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_package_tests_directory_excluded() -> None:
    source_code = """from cmk.base.config import load_config
from cmk.gui.pages import Page
"""
    checker = _make_checker("packages/cmk-agent-based/tests/test_something.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_package_cmk_code_checked() -> None:
    source_code = "from cmk.gui.pages import Page"
    checker = _make_checker("packages/cmk-ccc/cmk/ccc/module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 1
    assert "cmk.gui.pages" in errors[0].message


def test_nonfree_package_tests_excluded() -> None:
    source_code = "from cmk.base.config import load_config"
    checker = _make_checker("non-free/packages/cmk-bla/tests/test_something.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_file_without_component_rejects_cmk_imports() -> None:
    source_code = "from cmk.utils.paths import omd_root"
    checker = _make_checker("some_random_script.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 1
    assert "cmk.utils.paths" in errors[0].message


def test_checker_id_value() -> None:
    checker = _make_checker("cmk/test.py")
    assert checker.checker_id() == "cmk-module-layer-violation"


def test_is_package_detection_for_init_file() -> None:
    checker = _make_checker("cmk/gui/__init__.py")
    assert checker.is_package is True


def test_is_package_detection_for_regular_file() -> None:
    checker = _make_checker("cmk/gui/pages.py")
    assert checker.is_package is False
