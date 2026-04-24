#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path
from typing import Protocol

import pytest

from cmk.astrein.checker_module_layers import ModuleLayersChecker
from cmk.astrein.module_layers_config import (
    Component,
    CONFIG_FILENAME,
    load_config,
    ModuleLayersConfig,
)


class _MakeChecker(Protocol):
    def __call__(self, file_path: str, source_code: str = "") -> ModuleLayersChecker: ...


def _find_repo_root() -> Path:
    """Find the repository root by walking up from this file."""
    p = Path(__file__).resolve()
    while p != p.parent:
        if (p / "module_layers.toml").exists():
            return p
        p = p.parent
    pytest.skip("module_layers.toml not found in parent directories")


@pytest.fixture(scope="module")
def repo_root() -> Path:
    return _find_repo_root()


@pytest.fixture(scope="module")
def module_config(repo_root: Path) -> ModuleLayersConfig:
    return load_config(repo_root / CONFIG_FILENAME)


@pytest.fixture(scope="module")
def make_checker(repo_root: Path, module_config: ModuleLayersConfig) -> _MakeChecker:
    def _make(file_path: str, source_code: str = "") -> ModuleLayersChecker:
        full_path = repo_root / file_path
        return ModuleLayersChecker(full_path, repo_root, source_code, config=module_config)

    return _make


def test_no_component_masked_by_more_general_component(
    module_config: ModuleLayersConfig,
) -> None:
    """Ensure no component shadows another in the COMPONENTS mapping.

    This test verifies that component hierarchies are properly ordered so that
    more specific components aren't masked by more general ones.
    """
    seen: set[Component] = set()
    for component in module_config.components:
        shadowed = {c for c in seen if component.is_below(c)}
        assert not shadowed, f"Component {component} is shadowed by {shadowed}"
        seen.add(component)


def test_inline_suppression_support(repo_root: Path, module_config: ModuleLayersConfig) -> None:
    """Test that inline suppressions are respected by the checker."""
    # Test code with suppressed and unsuppressed violations
    source_code = """from cmk.base.config import something  # astrein: disable=cmk-module-layer-violation

# astrein: disable=cmk-module-layer-violation
from cmk.gui.something import other

from cmk.checkengine.plugins import Plugin
"""

    # Parse and check
    tree = ast.parse(source_code)
    test_file_path = repo_root / "cmk" / "test_suppression.py"

    checker = ModuleLayersChecker(test_file_path, repo_root, source_code, config=module_config)
    errors = checker.check(tree)

    # Only the last import (line 6) should produce an error
    assert len(errors) == 1
    assert errors[0].line == 6


def test_module_name_for_cmk_base(make_checker: _MakeChecker) -> None:
    checker = make_checker("cmk/base/config.py")
    assert str(checker.module_name) == "cmk.base.config"


def test_module_name_for_cmk_gui_init(make_checker: _MakeChecker) -> None:
    checker = make_checker("cmk/gui/__init__.py")
    assert str(checker.module_name) == "cmk.gui.__init__"


def test_module_name_for_omdlib(make_checker: _MakeChecker) -> None:
    checker = make_checker("omd/packages/omd/omdlib/foo.py")
    assert str(checker.module_name) == "omdlib.foo"


def test_module_name_for_packages(make_checker: _MakeChecker) -> None:
    checker = make_checker("packages/cmk-agent-based/cmk/base/foo.py")
    assert str(checker.module_name) == "cmk.base.foo"


def test_module_name_for_nonfree_packages(make_checker: _MakeChecker) -> None:
    checker = make_checker("non-free/packages/cmk-enterprise/cmk/gui/bar.py")
    assert str(checker.module_name) == "cmk.gui.bar"


def test_module_name_with_flycheck_prefix(make_checker: _MakeChecker) -> None:
    checker = make_checker("cmk/base/flycheck_config.py")
    assert str(checker.module_name) == "cmk.base.config"


def test_component_for_cmk_base_config(make_checker: _MakeChecker) -> None:
    checker = make_checker("cmk/base/config.py")
    assert checker.component == Component("cmk.base.config")


def test_component_for_cmk_gui(make_checker: _MakeChecker) -> None:
    checker = make_checker("cmk/gui/pages.py")
    assert checker.component == Component("cmk.gui")


def test_component_for_cmk_utils_paths(make_checker: _MakeChecker) -> None:
    checker = make_checker("cmk/utils/paths.py")
    assert checker.component == Component("cmk.utils.paths")


def test_component_for_cmk_ccc(make_checker: _MakeChecker) -> None:
    checker = make_checker("cmk/ccc/version.py")
    assert checker.component == Component("cmk.ccc")


def test_component_for_explicit_mapping_bin_check_mk(make_checker: _MakeChecker) -> None:
    checker = make_checker("bin/check_mk")
    assert checker.component == Component("cmk.base")


def test_component_for_explicit_mapping_bin_cmk_passwd(make_checker: _MakeChecker) -> None:
    checker = make_checker("bin/cmk-passwd")
    assert checker.component == Component("cmk.cmkpasswd")


def test_component_for_file_without_component(make_checker: _MakeChecker) -> None:
    checker = make_checker("some_random_script.py")
    assert checker.component is None


def test_allowed_import_same_component_gui(make_checker: _MakeChecker) -> None:
    source_code = "from cmk.gui.pages import Page"
    checker = make_checker("cmk/gui/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_allowed_import_gui_from_ccc(make_checker: _MakeChecker) -> None:
    source_code = "from cmk.ccc.version import Version"
    checker = make_checker("cmk/gui/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_allowed_import_gui_from_utils(make_checker: _MakeChecker) -> None:
    source_code = "from cmk.utils.paths import omd_root"
    checker = make_checker("cmk/gui/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_allowed_import_gui_from_livestatus_client(make_checker: _MakeChecker) -> None:
    source_code = "from cmk.livestatus_client import Query"
    checker = make_checker("cmk/gui/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_disallowed_import_ccc_from_gui(make_checker: _MakeChecker) -> None:
    source_code = "from cmk.gui.pages import Page"
    checker = make_checker("cmk/ccc/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 1
    assert "cmk.gui.pages" in errors[0].message


def test_disallowed_import_ccc_from_base(make_checker: _MakeChecker) -> None:
    source_code = "from cmk.base.config import load_config"
    checker = make_checker("cmk/ccc/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 1
    assert "cmk.base.config" in errors[0].message


def test_clean_plugin_allowed_imports(make_checker: _MakeChecker) -> None:
    source_code = """from cmk.agent_based.v2 import AgentSection
from cmk.rulesets.v1 import form_specs
"""
    checker = make_checker("cmk/plugins/aws/agent_based/test_check.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_clean_plugin_disallowed_import_from_utils(make_checker: _MakeChecker) -> None:
    source_code = "from cmk.utils.paths import omd_root"
    checker = make_checker("cmk/plugins/aws/agent_based/test_check.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 1
    assert "cmk.utils.paths" in errors[0].message


def test_gui_excludes_gui_plugins(make_checker: _MakeChecker) -> None:
    source_code = "from cmk.gui.plugins.views import register"
    checker = make_checker("cmk/gui/views.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 1
    assert "cmk.gui.plugins" in errors[0].message


def test_simple_import_statement(make_checker: _MakeChecker) -> None:
    source_code = "import cmk.base.config"
    checker = make_checker("cmk/ccc/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 1
    assert "cmk.base.config" in errors[0].message


def test_from_import_statement(make_checker: _MakeChecker) -> None:
    source_code = "from cmk.gui.pages import Page"
    checker = make_checker("cmk/ccc/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 1
    assert "cmk.gui.pages" in errors[0].message


def test_multiple_names_from_import(make_checker: _MakeChecker) -> None:
    source_code = "from cmk.gui.pages import Page, register_page, make_header"
    checker = make_checker("cmk/ccc/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 3
    for error in errors:
        assert "cmk.gui.pages" in error.message


def test_relative_import_level_one(make_checker: _MakeChecker) -> None:
    source_code = "from . import local_module"
    checker = make_checker("cmk/gui/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_relative_import_level_two(make_checker: _MakeChecker) -> None:
    source_code = "from .. import parent_module"
    checker = make_checker("cmk/gui/subdir/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_external_stdlib_imports(make_checker: _MakeChecker) -> None:
    source_code = """import sys
import os
from pathlib import Path
"""
    checker = make_checker("cmk/gui/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_external_third_party_imports(make_checker: _MakeChecker) -> None:
    source_code = """import pytest
from typing import Any
import requests
"""
    checker = make_checker("cmk/gui/test_module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_package_tests_directory_excluded(make_checker: _MakeChecker) -> None:
    source_code = """from cmk.base.config import load_config
from cmk.gui.pages import Page
"""
    checker = make_checker("packages/cmk-agent-based/tests/test_something.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_package_cmk_code_checked(make_checker: _MakeChecker) -> None:
    source_code = "from cmk.gui.pages import Page"
    checker = make_checker("packages/cmk-ccc/cmk/ccc/module.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 1
    assert "cmk.gui.pages" in errors[0].message


def test_nonfree_package_tests_excluded(make_checker: _MakeChecker) -> None:
    source_code = "from cmk.base.config import load_config"
    checker = make_checker("non-free/packages/cmk-bla/tests/test_something.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_top_level_tests_excluded(make_checker: _MakeChecker) -> None:
    source_code = """from cmk.base.config import load_config
from cmk.gui.pages import Page
"""
    checker = make_checker("tests/unit/cmk/gui/test_foo.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_top_level_tests_non_cmk_subdir_excluded(make_checker: _MakeChecker) -> None:
    source_code = "from cmk.gui.watolib.rulespecs import Rulespec"
    checker = make_checker("tests/plugins_consistency/nonfree/pro/test_bar.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_non_free_top_level_tests_excluded(make_checker: _MakeChecker) -> None:
    source_code = """from cmk.metric_backend.config import Foo
from cmk.testlib.metric_backend.data import bar
"""
    checker = make_checker("non-free/tests/system/metric_backend/test_ttl.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_file_without_component_rejects_cmk_imports(make_checker: _MakeChecker) -> None:
    source_code = "from cmk.utils.paths import omd_root"
    checker = make_checker("some_random_script.py", source_code)
    tree = ast.parse(source_code)
    errors = checker.check(tree)

    assert len(errors) == 1
    assert "cmk.utils.paths" in errors[0].message


def test_checker_id_value(make_checker: _MakeChecker) -> None:
    checker = make_checker("cmk/test.py")
    assert checker.checker_id() == "cmk-module-layer-violation"


def test_is_package_detection_for_init_file(make_checker: _MakeChecker) -> None:
    checker = make_checker("cmk/gui/__init__.py")
    assert checker.is_package is True


def test_is_package_detection_for_regular_file(make_checker: _MakeChecker) -> None:
    checker = make_checker("cmk/gui/pages.py")
    assert checker.is_package is False
