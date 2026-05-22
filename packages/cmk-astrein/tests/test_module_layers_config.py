#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import tomllib
from pathlib import Path
from textwrap import dedent

import pytest

from cmk.astrein.module_layers_config import (
    _build_checker,
    _build_plugin_components,
    _expand_allows,
    Component,
    load_config,
    ModuleLayersConfig,
    ModuleName,
    ModulePath,
)


def test_expand_allows_plain_modules() -> None:
    groups: dict[str, list[str]] = {}
    result = _expand_allows(["cmk.foo", "cmk.bar"], groups)
    assert result == ["cmk.foo", "cmk.bar"]


def test_expand_allows_group_reference() -> None:
    groups = {"ccc": ["cmk.ccc"]}
    result = _expand_allows(["@ccc", "cmk.other"], groups)
    assert result == ["cmk.ccc", "cmk.other"]


def test_expand_allows_multi_member_group() -> None:
    groups = {"apis": ["cmk.api.v1", "cmk.api.v2"]}
    result = _expand_allows(["@apis"], groups)
    assert result == ["cmk.api.v1", "cmk.api.v2"]


def test_expand_allows_multiple_groups() -> None:
    groups = {"a": ["cmk.a"], "b": ["cmk.b"]}
    result = _expand_allows(["@a", "@b"], groups)
    assert result == ["cmk.a", "cmk.b"]


def test_expand_allows_unknown_group_raises() -> None:
    with pytest.raises(ValueError, match="Unknown group reference.*@nonexistent"):
        _expand_allows(["@nonexistent"], {})


def test_expand_allows_empty_list() -> None:
    assert _expand_allows([], {}) == []


def test_build_checker_allow_all() -> None:
    checker = _build_checker({"allow_all": True}, {})
    assert checker(imported=ModuleName("cmk.anything"), component=Component("test"))


def test_build_checker_allows_simple() -> None:
    checker = _build_checker({"allows": ["cmk.foo"]}, {})
    assert checker(imported=ModuleName("cmk.foo.bar"), component=None)
    assert not checker(imported=ModuleName("cmk.other"), component=None)


def test_build_checker_allows_with_group() -> None:
    groups = {"mygroup": ["cmk.a", "cmk.b"]}
    checker = _build_checker({"allows": ["@mygroup"]}, groups)
    assert checker(imported=ModuleName("cmk.a.x"), component=None)
    assert checker(imported=ModuleName("cmk.b.y"), component=None)
    assert not checker(imported=ModuleName("cmk.c"), component=None)


def test_build_checker_excludes() -> None:
    checker = _build_checker(
        {"allows": ["cmk.gui"], "excludes": ["cmk.gui.plugins"]},
        {},
    )
    assert checker(imported=ModuleName("cmk.gui.views"), component=None)
    assert not checker(imported=ModuleName("cmk.gui.plugins.views"), component=None)


def test_build_checker_self_import_allowed() -> None:
    """The _allow function implicitly allows imports from the importing component."""
    checker = _build_checker({"allows": []}, {})
    comp = Component("cmk.mycomp")
    assert checker(imported=ModuleName("cmk.mycomp.internal"), component=comp)
    assert not checker(imported=ModuleName("cmk.other"), component=comp)


def test_build_checker_missing_allows_raises() -> None:
    with pytest.raises(ValueError, match="must have 'allows' or 'allow_all'"):
        _build_checker({}, {})


def test_build_checker_allows_wrong_type_raises() -> None:
    with pytest.raises(TypeError, match="'allows' must be a list"):
        _build_checker({"allows": "cmk.foo"}, {})


def test_build_checker_excludes_wrong_type_raises() -> None:
    with pytest.raises(TypeError, match="'excludes' must be a list"):
        _build_checker({"allows": [], "excludes": "cmk.foo"}, {})


def test_build_plugin_components_clean() -> None:
    groups = {"plugin_apis": ["cmk.api.v1"]}
    plugin_families: dict[str, object] = {"clean": ["aws", "azure"]}
    result = _build_plugin_components(plugin_families, groups)

    assert Component("cmk.plugins.aws") in result
    assert Component("cmk.plugins.azure") in result

    checker = result[Component("cmk.plugins.aws")]
    assert checker(imported=ModuleName("cmk.api.v1.section"), component=None)
    assert checker(imported=ModuleName("cmk.plugins.lib.utils"), component=None)
    assert not checker(imported=ModuleName("cmk.utils.paths"), component=None)


def test_build_plugin_components_violations() -> None:
    groups = {"plugin_apis": ["cmk.api.v1"]}
    plugin_families: dict[str, object] = {
        "clean": [],
        "violations": {
            "myfamily": {"allows": ["cmk.utils.paths"]},
        },
    }
    result = _build_plugin_components(plugin_families, groups)

    checker = result[Component("cmk.plugins.myfamily")]
    assert checker(imported=ModuleName("cmk.api.v1.x"), component=None)
    assert checker(imported=ModuleName("cmk.plugins.lib.y"), component=None)
    assert checker(imported=ModuleName("cmk.utils.paths"), component=None)
    assert not checker(imported=ModuleName("cmk.gui.pages"), component=None)


def test_build_plugin_components_violations_with_group() -> None:
    groups = {"plugin_apis": ["cmk.api.v1"], "ccc": ["cmk.ccc"]}
    plugin_families: dict[str, object] = {
        "clean": [],
        "violations": {
            "myfamily": {"allows": ["@ccc"]},
        },
    }
    result = _build_plugin_components(plugin_families, groups)
    checker = result[Component("cmk.plugins.myfamily")]
    assert checker(imported=ModuleName("cmk.ccc.version"), component=None)


def test_build_plugin_components_empty() -> None:
    result = _build_plugin_components({}, {"plugin_apis": ["cmk.api.v1"]})
    assert result == {}


def _write_toml(tmp_path: Path, content: str) -> Path:
    config_path = tmp_path / "module_layers.toml"
    config_path.write_text(dedent(content))
    return config_path


def test_load_config_minimal(tmp_path: Path) -> None:
    config_path = _write_toml(
        tmp_path,
        """\
        [groups]

        [components."cmk.foo"]
        allows = []
        """,
    )
    config = load_config(config_path)
    assert isinstance(config, ModuleLayersConfig)
    assert Component("cmk.foo") in config.components


def test_load_config_with_groups(tmp_path: Path) -> None:
    config_path = _write_toml(
        tmp_path,
        """\
        [groups]
        ccc = ["cmk.ccc"]

        [components."cmk.gui"]
        allows = ["@ccc", "cmk.utils"]
        """,
    )
    config = load_config(config_path)
    checker = config.components[Component("cmk.gui")]
    assert checker(imported=ModuleName("cmk.ccc.store"), component=None)
    assert checker(imported=ModuleName("cmk.utils.paths"), component=None)
    assert not checker(imported=ModuleName("cmk.base"), component=None)


def test_load_config_with_excludes(tmp_path: Path) -> None:
    config_path = _write_toml(
        tmp_path,
        """\
        [groups]

        [components."cmk.gui"]
        allows = ["cmk.gui"]
        excludes = ["cmk.gui.plugins"]
        """,
    )
    config = load_config(config_path)
    checker = config.components[Component("cmk.gui")]
    assert checker(imported=ModuleName("cmk.gui.views"), component=None)
    assert not checker(imported=ModuleName("cmk.gui.plugins.views"), component=None)


def test_load_config_allow_all(tmp_path: Path) -> None:
    config_path = _write_toml(
        tmp_path,
        """\
        [groups]

        [components."tests.testlib"]
        allow_all = true
        """,
    )
    config = load_config(config_path)
    checker = config.components[Component("tests.testlib")]
    assert checker(imported=ModuleName("cmk.anything.at.all"), component=None)


def test_load_config_plugin_families(tmp_path: Path) -> None:
    config_path = _write_toml(
        tmp_path,
        """\
        [groups]
        plugin_apis = ["cmk.agent_based.v2"]

        [plugin_families]
        clean = ["aws"]

        [plugin_families.violations.azure_v2]
        allows = ["cmk.agent_based.v1"]
        """,
    )
    config = load_config(config_path)

    # Clean family
    aws_checker = config.components[Component("cmk.plugins.aws")]
    assert aws_checker(imported=ModuleName("cmk.agent_based.v2.x"), component=None)
    assert aws_checker(imported=ModuleName("cmk.plugins.lib.y"), component=None)
    assert not aws_checker(imported=ModuleName("cmk.utils.paths"), component=None)

    # Violation family
    azure_checker = config.components[Component("cmk.plugins.azure_v2")]
    assert azure_checker(imported=ModuleName("cmk.agent_based.v2.x"), component=None)
    assert azure_checker(imported=ModuleName("cmk.agent_based.v1.x"), component=None)
    assert not azure_checker(imported=ModuleName("cmk.utils.paths"), component=None)


def test_load_config_file_components(tmp_path: Path) -> None:
    config_path = _write_toml(
        tmp_path,
        """\
        [groups]

        [file_components]
        "bin/check_mk" = "cmk.base"
        "bin/mkeventd" = "cmk.ec"
        """,
    )
    config = load_config(config_path)
    assert config.file_components[ModulePath("bin/check_mk")] == Component("cmk.base")
    assert config.file_components[ModulePath("bin/mkeventd")] == Component("cmk.ec")


def test_load_config_file_dependencies(tmp_path: Path) -> None:
    config_path = _write_toml(
        tmp_path,
        """\
        [groups]
        ccc = ["cmk.ccc"]

        [file_dependencies."bin/my-tool"]
        allows = ["@ccc", "cmk.utils.paths"]
        """,
    )
    config = load_config(config_path)
    checker = config.file_dependencies[ModulePath("bin/my-tool")]
    assert checker(imported=ModuleName("cmk.ccc.store"), component=None)
    assert checker(imported=ModuleName("cmk.utils.paths"), component=None)
    assert not checker(imported=ModuleName("cmk.gui"), component=None)


def test_load_config_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nonexistent.toml")


def test_load_config_invalid_toml(tmp_path: Path) -> None:
    config_path = tmp_path / "bad.toml"
    config_path.write_text("[invalid toml\n")
    with pytest.raises(tomllib.TOMLDecodeError):
        load_config(config_path)


def test_load_config_empty_file_produces_empty_config(tmp_path: Path) -> None:
    config_path = _write_toml(tmp_path, "")
    config = load_config(config_path)
    assert len(config.components) == 0
    assert len(config.file_components) == 0
    assert len(config.file_dependencies) == 0


def _find_repo_root() -> Path:
    p = Path(__file__).resolve()
    while p != p.parent:
        if (p / "module_layers.toml").exists():
            return p
        p = p.parent
    pytest.skip("module_layers.toml not found in parent directories")
    raise AssertionError("unreachable")


@pytest.fixture(scope="module")
def real_config() -> ModuleLayersConfig:
    repo_root = _find_repo_root()
    return load_config(repo_root / "module_layers.toml")


def test_real_config_loads_without_error(real_config: ModuleLayersConfig) -> None:
    # Should have a substantial number of components
    assert len(real_config.components) > 100
    assert len(real_config.file_components) > 10
    assert len(real_config.file_dependencies) > 5


def test_real_config_has_expected_core_components_smoke_test(
    real_config: ModuleLayersConfig,
) -> None:
    expected = [
        "cmk.agent_based",
        "cmk.base",
        "cmk.base.config",
        "cmk.ccc",
        "cmk.gui",
        "cmk.utils.paths",
        "cmk.checkengine",
        "cmk.ec",
    ]
    comp_names = {str(c) for c in real_config.components}
    for name in expected:
        assert name in comp_names, f"Expected component {name} not found"


def test_real_config_has_plugin_families_smoke_test(real_config: ModuleLayersConfig) -> None:
    comp_names = {str(c) for c in real_config.components}
    # Some known clean families
    assert "cmk.plugins.aws" in comp_names
    assert "cmk.plugins.azure" in comp_names
    # Some known violation families
    assert "cmk.plugins.azure_deprecated" in comp_names
    assert "cmk.plugins.datadog" in comp_names


def test_real_config_file_components_present_smoke_test(real_config: ModuleLayersConfig) -> None:
    assert real_config.file_components[ModulePath("bin/check_mk.py")] == Component("cmk.base")
    assert real_config.file_components[ModulePath("bin/mkeventd.py")] == Component("cmk.ec")


def test_real_config_checker_behavior_smoke_test(real_config: ModuleLayersConfig) -> None:
    gui = Component("cmk.gui")
    ccc = Component("cmk.ccc")
    gui_checker = real_config.components[gui]
    ccc_checker = real_config.components[ccc]

    # GUI can import from ccc
    assert gui_checker(imported=ModuleName("cmk.ccc.version"), component=gui)
    # GUI cannot import from its own plugins
    assert not gui_checker(imported=ModuleName("cmk.gui.plugins.views"), component=gui)
    # ccc cannot import from gui
    assert not ccc_checker(imported=ModuleName("cmk.gui.pages"), component=ccc)
    # ccc can import from itself
    assert ccc_checker(imported=ModuleName("cmk.ccc.store"), component=ccc)
    # ccc can import trace
    assert ccc_checker(imported=ModuleName("cmk.trace.export"), component=ccc)
    # ccc cannot import base
    assert not ccc_checker(imported=ModuleName("cmk.base.config"), component=ccc)
