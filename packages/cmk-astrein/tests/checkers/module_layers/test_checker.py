#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from functools import partial
from pathlib import Path
from typing import Protocol

import pytest

from cmk.astrein.checkers.module_layers.checker import ModuleLayersChecker
from cmk.astrein.checkers.module_layers.config import (
    Component,
    CONFIG_FILENAME,
    load_config,
    ModuleLayersConfig,
)
from cmk.astrein.engine import run_checkers
from cmk.astrein.framework import CheckerError


class _MakeChecker(Protocol):
    def __call__(self, file_path: str) -> ModuleLayersChecker: ...


class _CheckImports(Protocol):
    def __call__(self, file_path: str, source_code: str) -> list[CheckerError]: ...


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
    def _make(file_path: str) -> ModuleLayersChecker:
        full_path = repo_root / file_path
        return ModuleLayersChecker(full_path, repo_root, "", config=module_config)

    return _make


@pytest.fixture(scope="module")
def check_imports(repo_root: Path, module_config: ModuleLayersConfig) -> _CheckImports:
    def _check(file_path: str, source_code: str) -> list[CheckerError]:
        return run_checkers(
            repo_root / file_path,
            repo_root,
            [partial(ModuleLayersChecker, config=module_config)],
            source_code=source_code,
        )

    return _check


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


def test_inline_suppression_support(check_imports: _CheckImports) -> None:
    """Test that inline suppressions are respected by the checker."""
    # Test code with suppressed and unsuppressed violations
    source_code = """from cmk.base.config import something  # astrein: disable=module-layers

# astrein: disable=module-layers
from cmk.gui.something import other

from cmk.checkengine.plugins import Plugin
"""

    errors = check_imports("cmk/test_suppression.py", source_code)

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


def test_component_for_explicit_mapping_diskspace(make_checker: _MakeChecker) -> None:
    checker = make_checker("omd/packages/maintenance/diskspace.py")
    assert checker.component == Component("cmk.diskspace")


def test_component_for_file_without_component(make_checker: _MakeChecker) -> None:
    checker = make_checker("some_random_script.py")
    assert checker.component is None


def test_allowed_import_same_component_gui(check_imports: _CheckImports) -> None:
    source_code = "from cmk.gui.pages import Page"
    errors = check_imports("cmk/gui/test_module.py", source_code)

    assert len(errors) == 0


def test_allowed_import_gui_from_ccc(check_imports: _CheckImports) -> None:
    source_code = "from cmk.ccc.version import Version"
    errors = check_imports("cmk/gui/test_module.py", source_code)

    assert len(errors) == 0


def test_allowed_import_gui_from_utils(check_imports: _CheckImports) -> None:
    source_code = "from cmk.utils.paths import omd_root"
    errors = check_imports("cmk/gui/test_module.py", source_code)

    assert len(errors) == 0


def test_allowed_import_gui_from_livestatus_client(check_imports: _CheckImports) -> None:
    source_code = "from cmk.livestatus_client import Query"
    errors = check_imports("cmk/gui/test_module.py", source_code)

    assert len(errors) == 0


def test_disallowed_import_gui_from_legacy_livestatus(check_imports: _CheckImports) -> None:
    """The legacy alias is fully migrated; even components that may use
    cmk.livestatus_client must not import it."""
    source_code = "from livestatus import SiteConfiguration"
    errors = check_imports("cmk/gui/test_module.py", source_code)

    assert len(errors) == 1
    assert "livestatus" in errors[0].message


def test_disallowed_import_ccc_from_legacy_livestatus(check_imports: _CheckImports) -> None:
    source_code = "import livestatus"
    errors = check_imports("cmk/ccc/test_module.py", source_code)

    assert len(errors) == 1
    assert "livestatus" in errors[0].message


def test_disallowed_import_ccc_from_gui(check_imports: _CheckImports) -> None:
    source_code = "from cmk.gui.pages import Page"
    errors = check_imports("cmk/ccc/test_module.py", source_code)

    assert len(errors) == 1
    assert "cmk.gui.pages" in errors[0].message


def test_disallowed_import_ccc_from_base(check_imports: _CheckImports) -> None:
    source_code = "from cmk.base.config import load_config"
    errors = check_imports("cmk/ccc/test_module.py", source_code)

    assert len(errors) == 1
    assert "cmk.base.config" in errors[0].message


def test_clean_plugin_allowed_imports(check_imports: _CheckImports) -> None:
    source_code = """from cmk.agent_based.v2 import AgentSection
from cmk.rulesets.v1 import form_specs
"""
    errors = check_imports("cmk/plugins/aws_deprecated/agent_based/test_check.py", source_code)

    assert len(errors) == 0


def test_clean_plugin_disallowed_import_from_utils(check_imports: _CheckImports) -> None:
    source_code = "from cmk.utils.paths import omd_root"
    errors = check_imports("cmk/plugins/aws_deprecated/agent_based/test_check.py", source_code)

    assert len(errors) == 1
    assert "cmk.utils.paths" in errors[0].message


def test_gui_excludes_gui_plugins(check_imports: _CheckImports) -> None:
    source_code = "from cmk.gui.plugins.views import register"
    errors = check_imports("cmk/gui/views.py", source_code)

    assert len(errors) == 1
    assert "cmk.gui.plugins" in errors[0].message


def test_simple_import_statement(check_imports: _CheckImports) -> None:
    source_code = "import cmk.base.config"
    errors = check_imports("cmk/ccc/test_module.py", source_code)

    assert len(errors) == 1
    assert "cmk.base.config" in errors[0].message


def test_from_import_statement(check_imports: _CheckImports) -> None:
    source_code = "from cmk.gui.pages import Page"
    errors = check_imports("cmk/ccc/test_module.py", source_code)

    assert len(errors) == 1
    assert "cmk.gui.pages" in errors[0].message


def test_multiple_names_from_import(check_imports: _CheckImports) -> None:
    source_code = "from cmk.gui.pages import Page, register_page, make_header"
    errors = check_imports("cmk/ccc/test_module.py", source_code)

    assert len(errors) == 3
    for error in errors:
        assert "cmk.gui.pages" in error.message


def test_relative_import_level_one(check_imports: _CheckImports) -> None:
    source_code = "from . import local_module"
    errors = check_imports("cmk/gui/test_module.py", source_code)

    assert len(errors) == 0


def test_relative_import_level_two(check_imports: _CheckImports) -> None:
    source_code = "from .. import parent_module"
    errors = check_imports("cmk/gui/subdir/test_module.py", source_code)

    assert len(errors) == 0


def test_external_stdlib_imports(check_imports: _CheckImports) -> None:
    source_code = """import sys
import os
from pathlib import Path
"""
    errors = check_imports("cmk/gui/test_module.py", source_code)

    assert len(errors) == 0


def test_external_third_party_imports(check_imports: _CheckImports) -> None:
    source_code = """import pytest
from typing import Any
import requests
"""
    errors = check_imports("cmk/gui/test_module.py", source_code)

    assert len(errors) == 0


def test_package_tests_directory_excluded(check_imports: _CheckImports) -> None:
    source_code = """from cmk.base.config import load_config
from cmk.gui.pages import Page
"""
    errors = check_imports("packages/cmk-agent-based/tests/test_something.py", source_code)

    assert len(errors) == 0


def test_package_cmk_code_checked(check_imports: _CheckImports) -> None:
    source_code = "from cmk.gui.pages import Page"
    errors = check_imports("packages/cmk-ccc/cmk/ccc/module.py", source_code)

    assert len(errors) == 1
    assert "cmk.gui.pages" in errors[0].message


def test_nonfree_package_tests_excluded(check_imports: _CheckImports) -> None:
    source_code = "from cmk.base.config import load_config"
    errors = check_imports("non-free/packages/cmk-bla/tests/test_something.py", source_code)

    assert len(errors) == 0


def test_top_level_tests_excluded(check_imports: _CheckImports) -> None:
    source_code = """from cmk.base.config import load_config
from cmk.gui.pages import Page
"""
    errors = check_imports("tests/unit/cmk/gui/test_foo.py", source_code)

    assert len(errors) == 0


def test_top_level_tests_non_cmk_subdir_excluded(check_imports: _CheckImports) -> None:
    source_code = "from cmk.gui.watolib.rulespecs import Rulespec"
    errors = check_imports(
        "tests/integration/plugin_consistency/nonfree/pro/test_bar.py", source_code
    )

    assert len(errors) == 0


def test_non_free_top_level_tests_excluded(check_imports: _CheckImports) -> None:
    source_code = """from cmk.data_backend.config import Foo
from cmk.testlib.data_backend.telemetry_metrics.data import bar
"""
    errors = check_imports("non-free/tests/system/data_backend/test_ttl.py", source_code)

    assert len(errors) == 0


def test_file_without_component_rejects_cmk_imports(check_imports: _CheckImports) -> None:
    source_code = "from cmk.utils.paths import omd_root"
    errors = check_imports("some_random_script.py", source_code)

    assert len(errors) == 1
    assert "cmk.utils.paths" in errors[0].message


def test_checker_id_value(make_checker: _MakeChecker) -> None:
    checker = make_checker("cmk/test.py")
    assert checker.checker_id == "module-layers"


def test_is_package_detection_for_init_file(make_checker: _MakeChecker) -> None:
    checker = make_checker("cmk/gui/__init__.py")
    assert checker.is_package is True


def test_is_package_detection_for_regular_file(make_checker: _MakeChecker) -> None:
    checker = make_checker("cmk/gui/pages.py")
    assert checker.is_package is False
