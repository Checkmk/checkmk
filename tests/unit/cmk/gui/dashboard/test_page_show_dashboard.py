#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import override

from cmk.gui.dashboard import page_show_dashboard
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    ConfigDomainName,
    ConfigDomainRegistry,
    SerializedSettings,
)
from cmk.utils.config_warnings import ConfigurationWarnings


class _FakeNetworkFlowDomain(ABCConfigDomain):
    def __init__(self, value: object) -> None:
        self._value = value

    @classmethod
    @override
    def ident(cls) -> ConfigDomainName:
        return ConfigDomainName("network_flow")

    @override
    def config_dir(self) -> Path:
        return Path("network_flow.d")

    @override
    def default_globals(self) -> GlobalSettings:
        return {"network_flow": ("disabled", None)}

    @override
    def load(
        self, site_specific: bool = False, custom_site_path: str | None = None
    ) -> GlobalSettings:
        return {} if site_specific else {"network_flow": self._value}

    @override
    def create_artifacts(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        return []

    @override
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        return []


def _registry_with(domain: ABCConfigDomain | None) -> ConfigDomainRegistry:
    registry = ConfigDomainRegistry()
    if domain is not None:
        registry.register(domain)
    return registry


def test_network_flow_active_no_domain() -> None:
    assert page_show_dashboard._network_flow_active(_registry_with(None)) is False


def test_network_flow_active_enabled() -> None:
    registry = _registry_with(_FakeNetworkFlowDomain(("enabled", {})))
    assert page_show_dashboard._network_flow_active(registry) is True


def test_network_flow_active_disabled() -> None:
    registry = _registry_with(_FakeNetworkFlowDomain(("disabled", None)))
    assert page_show_dashboard._network_flow_active(registry) is False
