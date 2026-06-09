#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Collection
from types import ModuleType

from cmk.dcd_connector_parameters.internal.connector_parameter_specs import (
    ConnectorParametersSpec,
)
from cmk.dcd_connectors.internal import (
    Connector,
    ConnectorContext,
    ConnectorSpec,
    NullObject,
)
from cmk.discover_plugins import Collector, discover_modules, PluginGroup, PluginLocation
from cmk.rulesets.v1 import form_specs


class _AssumeDirs:
    def __init__(self, *dirs: str) -> None:
        self._dirs = tuple(d.rstrip("/") for d in dirs)

    def __call__(self, path: str) -> Collection[str]:
        path_ = path.rstrip("/")
        return sorted(
            {
                s
                for d in self._dirs
                if (s := d.removeprefix(path_).strip("/").split("/")[0]) and d.startswith(path_)
            }
        )


def _dummy_factory(_ctx: ConnectorContext) -> Connector[str]:
    raise NotImplementedError


def _make_module(name: str, path: list[str], **kwargs: object) -> ModuleType:
    m = ModuleType(name)
    m.__path__ = path
    for attr, value in kwargs.items():
        setattr(m, attr, value)
    return m


def test_discover_connector_modules_from_plugin_family() -> None:
    modules = list(
        discover_modules(
            PluginGroup.DCD_CONNECTORS,
            raise_errors=True,
            modules=(_make_module("cmk.plugins", ["/lib/cmk/plugins"]),),
            ls=_AssumeDirs(
                "/lib/cmk/plugins/my_family/dcd_connectors/my_connector.py",
            ),
        )
    )
    assert modules == ["cmk.plugins.my_family.dcd_connectors.my_connector"]


def test_collect_connector_spec_by_prefix() -> None:
    collector = Collector(
        {ConnectorSpec: "connector_"},
        skip_wrong_types=False,
        raise_errors=True,
    )
    spec = ConnectorSpec(
        name="test", create_connector=_dummy_factory, connector_object_class=NullObject
    )
    module = _make_module("test_module", [], connector_test=spec)
    collector.add_from_module(
        "test_module",
        lambda *_args, **_kwargs: module,
    )
    assert not collector.errors
    assert collector.plugins == {
        PluginLocation("test_module", "connector_test"): spec,
    }


def test_collector_ignores_connector_spec_with_wrong_prefix() -> None:
    collector = Collector(
        {ConnectorSpec: "connector_"},
        skip_wrong_types=False,
        raise_errors=True,
    )
    spec = ConnectorSpec(
        name="test", create_connector=_dummy_factory, connector_object_class=NullObject
    )
    module = _make_module("test_module", [], wrong_prefix_test=spec)
    collector.add_from_module(
        "test_module",
        lambda *_args, **_kwargs: module,
    )
    assert not collector.errors
    assert not collector.plugins


def test_discover_connector_parameter_modules_from_plugin_family() -> None:
    modules = list(
        discover_modules(
            PluginGroup.DCD_CONNECTOR_PARAMETERS,
            raise_errors=True,
            modules=(_make_module("cmk.plugins", ["/lib/cmk/plugins"]),),
            ls=_AssumeDirs(
                "/lib/cmk/plugins/my_family/dcd_connector_parameters/my_connector.py",
            ),
        )
    )
    assert modules == ["cmk.plugins.my_family.dcd_connector_parameters.my_connector"]


def test_collect_connector_parameters_spec_by_prefix() -> None:
    collector = Collector(
        {ConnectorParametersSpec: "connector_params_"},
        skip_wrong_types=False,
        raise_errors=True,
    )
    spec = ConnectorParametersSpec(
        name="test",
        title="Test",
        description="desc",
        form_spec=lambda: form_specs.Dictionary(elements={}),
    )
    module = _make_module("test_module", [], connector_params_test=spec)
    collector.add_from_module(
        "test_module",
        lambda *_args, **_kwargs: module,
    )
    assert not collector.errors
    assert collector.plugins == {
        PluginLocation("test_module", "connector_params_test"): spec,
    }


def test_connector_and_parameter_groups_discover_from_separate_directories() -> None:
    ls = _AssumeDirs(
        "/lib/cmk/plugins/foo/dcd_connectors/bar.py",
        "/lib/cmk/plugins/foo/dcd_connector_parameters/bar.py",
    )
    plugins_module = (_make_module("cmk.plugins", ["/lib/cmk/plugins"]),)

    connector_modules = list(
        discover_modules(
            PluginGroup.DCD_CONNECTORS, raise_errors=True, modules=plugins_module, ls=ls
        )
    )
    parameter_modules = list(
        discover_modules(
            PluginGroup.DCD_CONNECTOR_PARAMETERS, raise_errors=True, modules=plugins_module, ls=ls
        )
    )
    assert connector_modules == ["cmk.plugins.foo.dcd_connectors.bar"]
    assert parameter_modules == ["cmk.plugins.foo.dcd_connector_parameters.bar"]
