#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checker to prevent disallowed imports of modules"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final, Protocol

from astroid.nodes import Import, ImportFrom  # type: ignore[import-untyped]
from pylint.checkers import BaseChecker
from pylint.checkers.utils import only_required_for_messages
from pylint.lint.pylinter import PyLinter

from tests.testlib.common.repo import repo_path


class ModulePath(Path):
    def is_below(self, path: str) -> bool:
        return is_prefix_of(Path(path).parts, self.parts)


class Component:
    def __init__(self, name: str):
        self.name: Final = name
        self.parts: Final = tuple(name.split("."))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r})"

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Component):
            return NotImplemented
        return self.parts == other.parts

    def __hash__(self) -> int:
        return hash(self.parts)

    def is_below(self, component: str | Component) -> bool:
        component = component if isinstance(component, Component) else Component(component)
        return is_prefix_of(component.parts, self.parts)


class ModuleName:
    def __init__(self, name: str):
        self.name: Final = name
        self.parts: Final = tuple(name.split("."))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r})"

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ModuleName):
            return NotImplemented
        return self.parts == other.parts

    def in_component(self, component: Component) -> bool:
        return is_prefix_of(component.parts, self.parts)


class ImportCheckerProtocol(Protocol):
    def __call__(
        self,
        *,
        imported: ModuleName,
        component: Component | None,
    ) -> bool: ...


def is_prefix_of[T](x: Sequence[T], y: Sequence[T]) -> bool:
    return x == y[: len(x)]


def register(linter: PyLinter) -> None:
    linter.register_checker(CMKModuleLayerChecker(linter))


def get_absolute_importee(
    *,
    root_name: str,
    modname: str,
    level: int,
    is_package: bool,
) -> ModuleName:
    parent = root_name.rsplit(".", level - is_package)[0]
    return ModuleName(f"{parent}.{modname}")


def _is_package(node: ImportFrom) -> bool:
    parent = node.parent
    try:
        return bool(parent.package)
    except AttributeError:  # could be a try/except block, for instance.
        return _is_package(parent)


def _allow(
    *modules: str,
    exclude: tuple[str, ...] = (),
) -> ImportCheckerProtocol:
    # I don't like having to support excludes, but the current rule for
    # `gui` is everything from "self" but not "cmk.gui.plugins"
    allowed = {Component(m) for m in modules}
    forbidden = {Component(m) for m in exclude}

    def _is_allowed(
        *,
        imported: ModuleName,
        component: Component | None,
    ) -> bool:
        if any(imported.in_component(m) for m in forbidden):
            return False
        return (component is not None and imported.in_component(component)) or any(
            imported.in_component(m) for m in allowed
        )

    return _is_allowed


_PLUGIN_FAMILIES_WITH_KNOWN_API_VIOLATIONS = {
    "aws": (
        "cmk.agent_based.v1",  # FIXME
        "cmk.ccc.version",  # edition detection
        "cmk.ccc.store",
        "cmk.plugins.lib",  # ?
        "cmk.utils.paths",  # edition detection
    ),
    "azure_deprecated": (
        "cmk.agent_based.v1",  # FIXME
        "cmk.ccc.version",  # edition detection
        "cmk.ccc.hostaddress",  # FormSpec validation
        "cmk.plugins.lib",  # ?
        "cmk.plugins.lib.azure_app_gateway",  # FIXME
        "cmk.plugins.lib.azure",  # FIXME
        "cmk.utils.http_proxy_config",
        "cmk.utils.paths",  # edition detection
    ),
    "azure_v2": (
        "cmk.agent_based.v1",  # FIXME
        "cmk.ccc.version",  # edition detection
        "cmk.ccc.hostaddress",  # FormSpec validation
        "cmk.plugins.lib",  # ?
        "cmk.plugins.lib.azure_app_gateway",  # FIXME
        "cmk.plugins.lib.azure",  # FIXME
        "cmk.utils.http_proxy_config",
        "cmk.utils.paths",  # edition detection
    ),
    "bazel": (
        "cmk.utils.semantic_version",
        "cmk.utils.paths",
    ),
    "checkmk": (
        "cmk.agent_based.v1",  # FIXME
        # These plugins are tightly coupled to Checkmk.
        # We cannot expect them to not depend on the core
        # product.
        "cmk.base",
        "cmk.fetchers",
        "cmk.gui",  # bi
        "cmk.checkengine",
        "cmk.utils",
        "cmk.ccc",
    ),
    "cisco_meraki": (
        "cmk.agent_based.v1",  # FIXME
        "cmk.utils.paths",
        "cmk.plugins.lib.cisco_meraki",  # FIXME
        "cmk.plugins.lib.humidity",
        "cmk.plugins.lib.temperature",
    ),
    "datadog": (
        "cmk.ccc.store",
        "cmk.ccc.version",  # edition detection
        "cmk.ec.export",
        "cmk.gui.form_specs.unstable",
        "cmk.gui.mkeventd",
        "cmk.utils.http_proxy_config",
        "cmk.utils.paths",  # edition detection
    ),
    "emailchecks": (
        "cmk.ccc.version",  # edition detection
        "cmk.utils.paths",  # edition detection
        "cmk.utils.render",  # FIXME
        "cmk.gui.mkeventd",
    ),
    "gcp": (
        "cmk.agent_based.v1",  # FIXME
        "cmk.ccc.version",  # edition detection
        "cmk.utils.paths",  # edition detection
        "cmk.plugins.lib",  # diskstat + X
    ),
    "gerrit": (
        "cmk.utils.semantic_version",
        "cmk.utils.paths",
    ),
    "jolokia": ("cmk.utils.paths",),
    "kube": (
        "cmk.ccc.hostaddress",
        "cmk.ccc.profile",
        "cmk.ccc.version",  # edition detection
        "cmk.gui.form_specs.unstable",
        "cmk.plugins.lib",
        "cmk.plugins.lib.node_exporter",
        "cmk.utils.http_proxy_config",
        "cmk.utils.paths",  # persisting stuff
    ),
    "logwatch": (
        "cmk.base.config",
        "cmk.base.configlib.servicename",
        "cmk.ccc.hostaddress",
        "cmk.ccc.debug",
        "cmk.checkengine.plugins",
        "cmk.ec.event",
        "cmk.ec.export",
        "cmk.gui.mkeventd",
        "cmk.plugins.lib",
        "cmk.utils.paths",
    ),
    "mobileiron": (
        "cmk.utils.http_proxy_config",
        "cmk.utils.regex",
    ),
    "mqtt": ("cmk.ccc.hostaddress",),
    "prometheus": (
        "cmk.ccc.hostaddress",
        "cmk.plugins.lib.prometheus_form_elements",  # FIXME
        "cmk.plugins.lib.prometheus",  # FIXME
        "cmk.plugins.lib.node_exporter",
    ),
    "proxmox_ve": (
        "cmk.agent_based.v1",  # FIXME
        "cmk.plugins.lib.memory",
        "cmk.plugins.lib.cpu_util",
        "cmk.plugins.lib.uptime",
        "cmk.plugins.lib.df",
        "cmk.utils.paths",
    ),
    "otel": (
        "cmk.gui.form_specs.unstable",
        "cmk.otel_collector",
        "cmk.shared_typing.vue_formspec_components",
    ),
    "redfish": (
        "cmk.plugins.lib.elphase",
        "cmk.plugins.lib.humidity",
        "cmk.plugins.lib.temperature",
        "cmk.utils.paths",
    ),
    "robotmk": ("cmk.cee.robotmk",),
    "sftp": ("cmk.utils.ssh_client",),
    "smb": ("cmk.ccc.hostaddress",),
    "storeonce4x": ("cmk.utils.paths",),
    "vnx_quotas": ("cmk.utils.ssh_client",),
    "vsphere": (
        "cmk.agent_based.v1",  # FIXME
        "cmk.utils.paths",
        "cmk.plugins.lib",
    ),
}

PACKAGE_PLUGIN_APIS = (
    "cmk.agent_based.prediction_backend",
    "cmk.agent_based.legacy",
    "cmk.agent_based.v1",
    "cmk.agent_based.v2",
    "cmk.bakery.v2_alpha",
    "cmk.graphing.v1",
    "cmk.inventory_ui.v1_alpha",
    "cmk.rulesets.v1",
    "cmk.server_side_calls.v1",
)

PACKAGE_CCC = ("cmk.ccc",)

PACKAGE_MESSAGING = ("cmk.messaging",)

PACKAGE_MKP_TOOL = ("cmk.mkp_tool",)

PACKAGE_WERKS = ("cmk.werks",)

PACKAGE_CRYPTO = ("cmk.crypto",)

PACKAGE_TRACE = ("cmk.trace",)

CLEAN_UTILS_MODULES = (
    "agent_registration",
    "auto_queue",
    "check_utils",
    "crypto",
    "datastructures",
    "deprecation_warnings",
    "encoding",
    "everythingtype",
    "experimental_config",
    "html",
    "http_proxy_config",
    "images",
    "livestatus_helpers",
    "macros",
    "man_pages",
    "metrics",
    "mrpe_config",
    "ms_teams_constants",
    "object_diff",
    "parameters",
    "plugin_loader",
    "schedule",
    "sectionname",
    "semantic_version",
    "statename",
    "timeout",
    "typing_helpers",
)

# we consider these ""Components"", but we allow them
# to import each other. Would be nice to narrow this down,
# but there's a lot going on.
CROSS_DEPENDING_UTILS_MODULES = (
    "backup",
    "caching",
    "caching_redis",
    "cce",
    "cee",
    "cme",
    "config_path",
    "config_warnings",
    "cse",
    "dateutils",
    "diagnostics",
    "encryption",
    "escaping",
    "global_ident_type",
    "ip_lookup",
    "jsontype",
    "labels",
    "licensing",
    "local_secrets",
    "log",
    "mail",
    "misc",
    "msi_engine",
    "msi_patch",
    "observer",
    "password_store",
    "paths",
    "redis",
    "render",
    "regex",
    "setup_search_index",
    "ssh_client",
    "tags",
    "timeperiod",
    "translations",
    "servicename",
    "urls",
    "visuals",
)

COMPONENTS: Mapping[Component, ImportCheckerProtocol] = {
    Component("cmk.automations"): _allow(
        *PACKAGE_CCC,
        "cmk.checkengine",
        "cmk.helper_interface",
        "cmk.utils.check_utils",
        "cmk.utils.config_warnings",
        "cmk.utils.ip_lookup",
        "cmk.utils.labels",
        "cmk.utils.notify_types",
        "cmk.utils.rulesets.ruleset_matcher",
        "cmk.utils.servicename",
    ),
    Component("cmk.bakery"): _allow(),  # only allow itself, this is the future :-)
    Component("cmk.base.api.bakery"): _allow(
        "cmk.bakery",
        "cmk.ccc",
        "cmk.utils",
    ),
    Component("cmk.base.cee.bakery"): _allow(
        "cmk.bakery",
        "cmk.base.api.bakery",
        "cmk.base.plugins.bakery.bakery_api",
        "cmk.base.cee.cap",
        "cmk.base.cee.plugins.bakery.bakery_api",
        "cmk.crypto.certificate",
        "cmk.cee.robotmk.bakery",
        "cmk.ccc",
        "cmk.cee.bakery",
        "cmk.discover_plugins",
        "cmk.utils",
    ),
    Component("cmk.base.cee"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        "cmk.base",
        "cmk.fetcher_encoder",
        "cmk.fetcher_helper",
        "cmk.check_helper_protocol",
        "cmk.checkengine",
        "cmk.events",
        "cmk.fetchers",
        "cmk.helper_interface",
        "cmk.utils",
    ),
    Component("cmk.base.core.cee"): _allow(
        *PACKAGE_CCC,
        "cmk.base.cee",
        "cmk.base.config",
        "cmk.base.core",
        "cmk.fetcher_encoder",
        "cmk.fetcher_helper",
        "cmk.cee.robotmk",
        "cmk.checkengine",
        "cmk.fetchers",
        "cmk.inventory",
        "cmk.rrd",
        "cmk.utils",
    ),
    Component("cmk.base.check_legacy_includes"): _allow(
        *PACKAGE_PLUGIN_APIS,
        "cmk.plugins",
    ),
    Component("cmk.base.legacy_checks"): _allow(
        *PACKAGE_PLUGIN_APIS,
        "cmk.plugins",
        "cmk.base.check_legacy_includes",
    ),
    Component("cmk.base.plugins.bakery.bakery_api"): _allow(
        "cmk.bakery",
        "cmk.base.api.bakery",
        "cmk.utils",
    ),
    Component("cmk.base"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_TRACE,
        "cmk.automations",
        "cmk.cee.bakery",
        "cmk.fetcher_helper",
        "cmk.checkengine",
        "cmk.discover_plugins",
        "cmk.ec",
        "cmk.events",
        "cmk.fetchers",
        "cmk.helper_interface",
        "cmk.inventory",
        "cmk.piggyback",
        "cmk.relay_fetcher_trigger",
        "cmk.rrd",
        "cmk.server_side_calls_backend",
        "cmk.snmplib",
        "cmk.utils",
    ),
    Component("cmk.bi"): _allow(
        *PACKAGE_CCC,
        "cmk.fields",
        "cmk.utils",
    ),
    Component("cmk.checkengine.value_store"): _allow(
        *PACKAGE_CCC,
        "cmk.utils",
    ),
    Component("cmk.checkengine"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        "cmk.discover_plugins",
        "cmk.inventory",
        "cmk.piggyback.backend",
        "cmk.snmplib",
        "cmk.trace",
        "cmk.helper_interface",
        "cmk.utils.auto_queue",
        "cmk.utils.check_utils",
        "cmk.utils.encoding",
        "cmk.utils.everythingtype",
        "cmk.utils.labels",
        "cmk.utils.log",
        "cmk.utils.metrics",
        "cmk.utils.parameters",
        "cmk.utils.paths",
        "cmk.utils.regex",
        "cmk.utils.rulesets",
        "cmk.utils.servicename",
        "cmk.utils.timeperiod",
        "cmk.utils.translations",
    ),
    Component("cmk.fetcher_helper"): _allow(
        *PACKAGE_CCC,
        "cmk.fetchers",
        "cmk.helper_interface",
        "cmk.snmplib",
        "cmk.utils.caching",
        "cmk.utils.paths",
    ),
    Component("cmk.cmkcert"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_MESSAGING,
        "cmk.utils",
    ),
    Component("cmk.cmkpasswd"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_CRYPTO,
        "cmk.gui",
        "cmk.utils",
    ),
    Component("cmk.ec"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_MKP_TOOL,
        "cmk.events",
        "cmk.utils",
    ),
    Component("cmk.fetchers"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_CRYPTO,
        "cmk.helper_interface",
        "cmk.relay_protocols",
        "cmk.snmplib",
    ),
    Component("cmk.fields"): _allow(*PACKAGE_CCC),
    Component("cmk.gui.plugins"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        "cmk.bi",
        "cmk.checkengine",
        "cmk.gui",
        "cmk.inventory",
        "cmk.utils.dateutils",
        "cmk.utils.paths",
        "cmk.utils.rulesets",
        "cmk.utils.tags",
    ),
    Component("cmk.gui.cee.plugins"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        "cmk.gui",
        "cmk.utils.cee",
        "cmk.utils.mrpe_config",
        "cmk.utils.paths",
        "cmk.utils.render",
        "cmk.utils.rulesets",
    ),
    Component("cmk.gui.cce.plugins"): _allow(
        "cmk.gui",
    ),
    Component("cmk.gui.cee"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_CRYPTO,
        *PACKAGE_MKP_TOOL,
        "cmk.cee.bakery",
        "cmk.cee.robotmk.gui",
        "cmk.discover_plugins",
        "cmk.fields",
        "cmk.gui",
        "cmk.shared_typing",
        "cmk.utils.caching",
        "cmk.utils.cee",
        "cmk.utils.certs",
        "cmk.utils.config_warnings",
        "cmk.utils.dateutils",
        "cmk.utils.global_ident_type",
        "cmk.utils.images",
        "cmk.utils.licensing",
        "cmk.utils.local_secrets",
        "cmk.utils.log",
        "cmk.utils.macros",
        "cmk.utils.mail",
        "cmk.utils.metrics",
        "cmk.utils.misc",
        "cmk.utils.password_store",
        "cmk.utils.paths",
        "cmk.utils.redis",
        "cmk.utils.render",
        "cmk.utils.rulesets",
        "cmk.utils.schedule",
        "cmk.utils.servicename",
        "cmk.utils.setup_search_index",
        "cmk.utils.statename",
        "cmk.utils.tags",
        "cmk.utils.timeperiod",
        "cmk.utils.typing_helpers",
        "cmk.utils.urls",
        "cmk.utils.visuals",
        exclude=("cmk.gui.plugins", "cmk.gui.cee.plugins"),
    ),
    Component("cmk.gui.cce"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        "cmk.cce.metric_backend.gui",
        "cmk.checkengine",
        "cmk.cee.robotmk.gui",
        "cmk.fields",
        "cmk.gui",
        "cmk.otel_collector",
        "cmk.shared_typing",
        "cmk.utils.agent_registration",
        "cmk.utils.cee",
        "cmk.utils.config_warnings",
        "cmk.utils.labels",
        "cmk.utils.macros",
        "cmk.utils.password_store",
        "cmk.utils.paths",
        "cmk.utils.regex",
        "cmk.utils.render",
        "cmk.utils.rulesets",
        "cmk.utils.translations",
        exclude=("cmk.gui.plugins", "cmk.gui.cee.plugins"),
    ),
    Component("cmk.gui.cme"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_CRYPTO,
        *PACKAGE_MESSAGING,
        "cmk.bi",
        "cmk.cce.metric_backend.gui.register",
        "cmk.cee.robotmk.gui",
        "cmk.gui",
        "cmk.inventory",
        "cmk.piggyback",
        "cmk.utils.cee",
        "cmk.utils.certs",
        "cmk.utils.cme",
        "cmk.utils.images",
        "cmk.utils.password_store",
        "cmk.utils.paths",
        "cmk.utils.redis",
        exclude=("cmk.gui.plugins", "cmk.gui.cee.plugins"),
    ),
    Component("cmk.gui.cse"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_CRYPTO,
        *PACKAGE_TRACE,
        "cmk.cce.metric_backend.gui.register",
        "cmk.fields",
        "cmk.gui",
        "cmk.utils.agent_registration",
        "cmk.utils.cee",
        "cmk.utils.cse",
        "cmk.utils.licensing",
        "cmk.utils.local_secrets",
        "cmk.utils.log",
        "cmk.utils.paths",
        "cmk.utils.redis",
        "cmk.utils.urls",
        exclude=("cmk.gui.plugins", "cmk.gui.cee.plugins"),
    ),
    Component("cmk.gui"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_CRYPTO,
        *PACKAGE_MESSAGING,
        *PACKAGE_MKP_TOOL,
        *PACKAGE_TRACE,
        *PACKAGE_WERKS,
        "cmk.automations",
        "cmk.bi",
        "cmk.checkengine",
        "cmk.discover_plugins",
        "cmk.diskspace",
        "cmk.fields",
        "cmk.inventory",
        "cmk.inventory_ui",
        "cmk.livestatus_client",
        "cmk.piggyback",
        "cmk.server_side_calls_backend",
        "cmk.shared_typing",
        "cmk.utils.agent_registration",
        "cmk.utils.auto_queue",
        "cmk.utils.backup",
        "cmk.utils.certs",
        "cmk.utils.check_utils",
        "cmk.utils.config_warnings",
        "cmk.utils.datastructures",
        "cmk.utils.dateutils",
        "cmk.utils.diagnostics",
        "cmk.utils.encoding",
        "cmk.utils.encryption",
        "cmk.utils.escaping",
        "cmk.utils.everythingtype",
        "cmk.utils.experimental_config",
        "cmk.utils.global_ident_type",
        "cmk.utils.host_storage",
        "cmk.utils.html",
        "cmk.utils.images",
        "cmk.utils.jsontype",
        "cmk.utils.labels",
        "cmk.utils.licensing",
        "cmk.utils.livestatus_helpers",
        "cmk.utils.local_secrets",
        "cmk.utils.log",
        "cmk.utils.macros",
        "cmk.utils.mail",
        "cmk.utils.man_pages",
        "cmk.utils.metrics",
        "cmk.utils.misc",
        "cmk.utils.ms_teams_constants",
        "cmk.utils.notify",
        "cmk.utils.notify_types",
        "cmk.utils.object_diff",
        "cmk.utils.password_store",
        "cmk.utils.paths",
        "cmk.utils.plugin_loader",
        "cmk.utils.prediction",
        "cmk.utils.redis",
        "cmk.utils.regex",
        "cmk.utils.render",
        "cmk.utils.rulesets",
        "cmk.utils.schedule",
        "cmk.utils.servicename",
        "cmk.utils.setup_search_index",
        "cmk.utils.statename",
        "cmk.utils.tags",
        "cmk.utils.timeperiod",
        "cmk.utils.translations",
        "cmk.utils.urls",
        "cmk.utils.visuals",
        "cmk.utils.werks",
        exclude=(
            "cmk.gui.plugins",
            "cmk.gui.cee.plugins",
            "cmk.gui.cee",
            "cmk.gui.cce",
            "cmk.gui.cme",
        ),
    ),
    Component("cmk.helper_interface"): _allow(*PACKAGE_CCC),  # should become a package
    Component("cmk.inventory"): _allow(
        *PACKAGE_CCC,
        "cmk.utils.regex",
    ),
    Component("cmk.notification_plugins"): _allow(
        *PACKAGE_CCC,
        "cmk.utils",
    ),
    Component("cmk.piggyback"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_MESSAGING,
        "cmk.utils.paths",
    ),
    **{  # some plugin families that refuse to play by the rules:
        Component(f"cmk.plugins.{family}"): _allow(
            *PACKAGE_PLUGIN_APIS,
            "cmk.special_agents.v0_unstable",
            "cmk.utils.password_store",
            *violations,
        )
        for family, violations in _PLUGIN_FAMILIES_WITH_KNOWN_API_VIOLATIONS.items()
    },
    Component("cmk.plugins"): _allow(
        *PACKAGE_PLUGIN_APIS,
        "cmk.bakery.v2_unstable",
        "cmk.special_agents.v0_unstable",
        "cmk.utils.password_store",
    ),
    Component("cmk.server_side_calls_backend"): _allow(
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_CCC,
        "cmk.discover_plugins",
        "cmk.utils",
    ),
    Component("cmk.special_agents"): _allow(
        *PACKAGE_CCC,
        "cmk.utils.password_store",
        "cmk.utils.paths",
    ),
    Component("cmk.snmplib"): _allow(*PACKAGE_CCC),
    Component("cmk.update_config"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_WERKS,
        "cmk.base",
        "cmk.cce.metric_backend",
        "cmk.checkengine",
        "cmk.cee.robotmk",
        "cmk.discover_plugins",
        "cmk.diskspace.config",
        "cmk.fetchers",
        "cmk.gui",
        "cmk.mkp_tool",
        "cmk.otel_collector",
        "cmk.utils",
        "cmk.validate_config",
    ),
    Component("cmk.validate_config"): _allow(
        *PACKAGE_CCC,
        "cmk.base",
        "cmk.checkengine",
        "cmk.gui",
        "cmk.utils",
    ),
    Component("cmk.validate_plugins"): _allow(
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_CCC,
        "cmk.discover_plugins",
        "cmk.utils.paths",
        "cmk.utils.rulesets",
    ),
    Component("cmk.cee.bakery"): _allow(
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_CCC,
        *PACKAGE_CRYPTO,
        "cmk.base.checkers",
        "cmk.base.config",
        "cmk.base.configlib.loaded_config",
        "cmk.base.core.cee.cmc",
        "cmk.base.errorhandling",
        "cmk.base.plugins.bakery.bakery_api.v1",
        "cmk.base.sources",
        "cmk.base.utils",
        "cmk.utils.paths",
    ),
    Component("cmk.cee.dcd"): _allow(
        *PACKAGE_CCC,
        "cmk.cce.metric_backend.dcd.register",
        "cmk.otel_collector",
        "cmk.piggyback",
        "cmk.utils",
    ),
    Component("cmk.cee.mknotifyd"): _allow(),
    Component("cmk.cee.snmp_backend"): _allow(),
    Component("cmk.cee.liveproxy"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_TRACE,
        "cmk.inventory",
        "cmk.utils",
    ),
    Component("cmk.cee.notification_plugins"): _allow("cmk.utils"),
    Component("cmk.cee.robotmk"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        # I don't think we have any idea of how to fix this.
        "cmk.base.cee.bakery",
        "cmk.base.plugins.bakery",
        "cmk.cee.bakery",
        "cmk.checkengine",
        "cmk.gui",
        "cmk.shared_typing",
        "cmk.utils",
    ),
    Component("cmk.diskspace"): _allow(*PACKAGE_CCC),
    Component("cmk.rrd"): _allow(
        *PACKAGE_CCC,
        "cmk.utils",
    ),
    Component("cmk.post_rename_site"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_MESSAGING,
        "cmk.gui",
        "cmk.utils",
    ),
    Component("cmk.utils.certs"): _allow(
        *PACKAGE_CRYPTO,
        *PACKAGE_CCC,
        "cmk.utils.log",
    ),
    Component("cmk.utils.prediction"): _allow(
        *PACKAGE_CCC,
        "cmk.agent_based.prediction_backend",
        "cmk.utils.servicename",
        "cmk.utils.log",
    ),
    Component("cmk.utils.rulesets"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_TRACE,
        "cmk.utils.global_ident_type",
        "cmk.utils.labels",
        "cmk.utils.parameters",
        "cmk.utils.paths",
        "cmk.utils.regex",
        "cmk.utils.servicename",
        "cmk.utils.tags",
    ),
    Component("cmk.utils.werks"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_WERKS,
        "cmk.utils.mail",
        "cmk.utils.paths",
    ),
    Component("cmk.utils.notify_types"): _allow(
        "cmk.events",
        "cmk.utils.rulesets",
        "cmk.utils.tags",
        "cmk.utils.timeperiod",
    ),
    Component("cmk.utils.notify"): _allow(
        *PACKAGE_CCC,
        "cmk.utils.notify_types",
        "cmk.utils.config_path",
        "cmk.utils.labels",
        "cmk.utils.paths",
        "cmk.utils.servicename",
        "cmk.utils.tags",
    ),
    Component("cmk.utils.host_storage"): _allow(
        *PACKAGE_CCC,
        "cmk.utils.labels",
        "cmk.utils.rulesets",
        "cmk.utils.tags",
    ),
    **{
        Component(f"cmk.utils.{module}"): _allow(
            *PACKAGE_CCC,
            *PACKAGE_CRYPTO,
            *(f"cmk.utils.{m}" for m in CROSS_DEPENDING_UTILS_MODULES),
        )
        for module in CROSS_DEPENDING_UTILS_MODULES
    },
    **{Component(f"cmk.utils.{module}"): _allow(*PACKAGE_CCC) for module in CLEAN_UTILS_MODULES},
    Component("cmk.utils"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_CRYPTO,
        "cmk.events",
        "cmk.otel_collector",
    ),
    Component("cmk.cce.metric_backend.dcd"): _allow(
        "cmk.ccc",
        "cmk.cee.dcd",
        "cmk.utils",
    ),
    Component("cmk.cce.metric_backend.gui"): _allow(
        *PACKAGE_PLUGIN_APIS,
        "cmk.ccc",
        "cmk.fields",
        "cmk.gui",
    ),
    Component("omdlib"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_CRYPTO,
        "cmk.utils",
    ),
    Component("tests.code_quality"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_WERKS,
        "cmk.utils.werks",
    ),
    Component("tests.composition"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_CRYPTO,
        "cmk.piggyback.backend",
        "cmk.utils.agent_registration",
        "cmk.utils.rulesets",
    ),
    Component("tests.extension_compatibility"): _allow(
        *PACKAGE_CCC,
        "cmk.base.config",
        "cmk.gui.main_modules",
        "cmk.gui.utils",
        "cmk.utils.paths",
    ),
    Component("tests.gui_e2e"): _allow(
        *PACKAGE_CRYPTO,
        "cmk.utils.cee.licensing",
        "cmk.utils.paths",
    ),
    Component("tests.integration.cmk.base"): _allow(
        *PACKAGE_CCC,
        "cmk.automations",
        "cmk.base",
        "cmk.cee.bakery",
        "cmk.checkengine",
        "cmk.discover_plugins",
        "cmk.utils",
    ),
    Component("tests.integration.cmk.cee.liveproxy"): _allow(
        *PACKAGE_CCC,
        "cmk.cee.liveproxy",
    ),
    Component("tests.integration.cmk.cee.robotmk"): _allow(
        *PACKAGE_CCC,
        "cmk.cee.robotmk",
        "cmk.utils.rulesets",
        "cmk.utils.servicename",
    ),
    Component("tests.integration.cmk.gui"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_CRYPTO,
        "cmk.bi",
        "cmk.gui",
        "cmk.utils",
    ),
    Component("tests.integration.cmk.post_rename_site"): _allow(
        "cmk.post_rename_site",
    ),
    Component("tests.integration.cmk.snmplib"): _allow(
        *PACKAGE_CCC,
        "cmk.snmplib",
        "cmk.utils",
    ),
    Component("tests.integration.otel"): _allow(
        *PACKAGE_CCC,
        "cmk.otel_collector.constants",
    ),
    Component("tests.integration"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_MKP_TOOL,
        "cmk.utils",
    ),
    Component("tests.integration_redfish"): _allow(
        *PACKAGE_CCC,
    ),
    Component("tests.pylint"): _allow("cmk.utils.escaping"),
    # Tests are allowed to import everything for now. Should be cleaned up soon (TM)
    Component("tests.testlib"): lambda *_a, **_kw: True,
    Component("tests.unit.cmk.base.legacy_checks"): _allow(
        *PACKAGE_PLUGIN_APIS,
        "cmk.base.check_legacy_includes",
        "cmk.base.legacy_checks",
        "cmk.checkengine.plugins",
        "cmk.discover_plugins",
        "cmk.plugins",
        "cmk.utils.paths",
    ),
    Component("tests.unit.cmk.fetchers"): _allow(
        *PACKAGE_CCC,
        "cmk.agent_based",
        "cmk.checkengine",
        "cmk.fetchers",
        "cmk.inline_snmp",
        "cmk.helper_interface",
        "cmk.relay_protocols",
        "cmk.relay_fetcher_trigger",
        "cmk.snmplib",
        "cmk.utils",
    ),
    Component("tests.unit.cmk"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_CRYPTO,
        *PACKAGE_MESSAGING,
        *PACKAGE_MKP_TOOL,
        *PACKAGE_TRACE,
        *PACKAGE_WERKS,
        "cmk.automations",
        "cmk.bakery",
        "cmk.base",
        "cmk.bi",
        "cmk.cce.metric_backend",
        "cmk.cee.bakery",
        "cmk.cee.dcd",
        "cmk.fetcher_encoder",
        "cmk.fetcher_helper",
        "cmk.cee.liveproxy",
        "cmk.cee.robotmk",
        "cmk.checkengine",
        "cmk.cmkcert",
        "cmk.cmkpasswd",
        "cmk.discover_plugins",
        "cmk.diskspace",
        "cmk.ec",
        "cmk.events",
        "cmk.fetchers",
        "cmk.fields",
        "cmk.gui",
        "cmk.helper_interface",
        "cmk.inventory",
        "cmk.livestatus_client",
        "cmk.notification_plugins",
        "cmk.otel_collector",
        "cmk.piggyback",
        "cmk.plugins",
        "cmk.post_rename_site",
        "cmk.rrd",
        "cmk.server_side_calls_backend",
        "cmk.shared_typing",
        "cmk.snmplib",
        "cmk.special_agents",
        "cmk.trace",
        "cmk.update_config",
        "cmk.utils",
        "cmk.validate_config",
    ),
    Component("tests.update"): _allow(
        *PACKAGE_CCC,
        "cmk.utils.licensing",
    ),
    Component("tests.unit"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_WERKS,
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_CRYPTO,
        "cmk.piggyback",
        "cmk.utils",
    ),
}

_EXPLICIT_FILE_TO_COMPONENT = {
    ModulePath("web/app/index.wsgi"): Component("cmk.gui"),
    ModulePath("bin/check_mk"): Component("cmk.base"),
    ModulePath("bin/cmk-automation-helper"): Component("cmk.base"),
    ModulePath("bin/cmk-cert"): Component("cmk.cmkcert"),
    ModulePath("bin/cmk-compute-api-spec"): Component("cmk.gui"),
    ModulePath("bin/cmk-passwd"): Component("cmk.cmkpasswd"),
    ModulePath("bin/cmk-ui-job-scheduler"): Component("cmk.gui"),
    ModulePath("bin/cmk-update-config"): Component("cmk.update_config"),
    ModulePath("bin/cmk-migrate-http"): Component("cmk.update_config"),
    ModulePath("bin/cmk-migrate-extension-rulesets"): Component("cmk.update_config"),
    ModulePath("bin/cmk-validate-config"): Component("cmk.validate_config"),
    ModulePath("bin/cmk-validate-plugins"): Component("cmk.validate_plugins"),
    ModulePath("bin/post-rename-site"): Component("cmk.post_rename_site"),
    ModulePath("bin/mkeventd"): Component("cmk.ec"),
    ModulePath("bin/cmk-convert-rrds"): Component("cmk.rrd"),
    ModulePath("bin/cmk-create-rrd"): Component("cmk.rrd"),
    ModulePath("cmk/active_checks/check_cmk_inv.py"): Component("cmk.base"),
    ModulePath("omd/packages/appliance/webconf_snapin.py"): Component("cmk.gui"),
    ModulePath("omd/packages/enterprise/bin/cmk-dcd"): Component("cmk.cee.dcd"),
    ModulePath("omd/packages/enterprise/bin/dcd"): Component("cmk.cee.dcd"),
    ModulePath("omd/packages/enterprise/bin/fetch-ad-hoc"): Component("cmk.fetcher_helper"),
    ModulePath("omd/packages/enterprise/bin/fetcher"): Component("cmk.fetcher_helper"),
    ModulePath("omd/packages/enterprise/bin/liveproxyd"): Component("cmk.cee.liveproxy"),
    ModulePath("omd/packages/enterprise/bin/mknotifyd"): Component("cmk.cee.mknotifyd"),
    ModulePath("omd/packages/maintenance/diskspace.py"): Component("cmk.diskspace"),
    # Notification plugins
    ModulePath("notifications/asciimail"): Component("cmk.notification_plugins"),
    ModulePath("notifications/cisco_webex_teams"): Component("cmk.notification_plugins"),
    ModulePath("notifications/ilert"): Component("cmk.notification_plugins"),
    ModulePath("notifications/mail"): Component("cmk.notification_plugins"),
    ModulePath("notifications/msteams"): Component("cmk.notification_plugins"),
    ModulePath("notifications/opsgenie_issues"): Component("cmk.notification_plugins"),
    ModulePath("notifications/pagerduty"): Component("cmk.notification_plugins"),
    ModulePath("notifications/pushover"): Component("cmk.notification_plugins"),
    ModulePath("notifications/signl4"): Component("cmk.notification_plugins"),
    ModulePath("notifications/slack"): Component("cmk.notification_plugins"),
    ModulePath("notifications/sms_api"): Component("cmk.notification_plugins"),
    ModulePath("notifications/sms"): Component("cmk.notification_plugins"),
    ModulePath("notifications/spectrum"): Component("cmk.notification_plugins"),
    ModulePath("notifications/victorops"): Component("cmk.notification_plugins"),
    # CEE specific notification plugins
    ModulePath("notifications/servicenow"): Component("cmk.cee.notification_plugins"),
    ModulePath("notifications/jira_issues"): Component("cmk.cee.notification_plugins"),
}

_EXPLICIT_FILE_TO_DEPENDENCIES = {
    # We have files that depend on more than one component, yet we do not want to
    # add all those dependencies to one of those components.
    ModulePath("bin/cmk-broker-test"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_MESSAGING,
        "cmk.utils.paths",
    ),
    ModulePath("bin/cmk-piggyback-hub"): _allow(
        *PACKAGE_CCC,
        "cmk.piggyback",
        "cmk.utils",
    ),
    ModulePath("bin/cmk-piggyback"): _allow(
        "cmk.piggyback",
        "cmk.utils",
    ),
    ModulePath("bin/cmk-update-license-usage"): _allow(
        *PACKAGE_CCC,
        "cmk.utils",
    ),
    ModulePath("bin/cmk-transform-inventory-trees"): _allow(
        "cmk.inventory",
        "cmk.utils.paths",
    ),
    ModulePath("bin/init-redis"): _allow("cmk.utils.setup_search_index"),
    ModulePath("bin/mkbackup"): _allow(*PACKAGE_CCC, "cmk.utils"),
    ModulePath("bin/mkp"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_MKP_TOOL,
        "cmk.utils",
        "cmk.discover_plugins",
    ),
    ModulePath("buildscripts/scripts/assert_build_artifacts.py"): _allow(*PACKAGE_CCC),
    ModulePath("buildscripts/scripts/publish_cloud_images.py"): _allow(*PACKAGE_CCC),
    ModulePath("buildscripts/scripts/unpublish-container-image.py"): _allow(*PACKAGE_CCC),
    ModulePath("buildscripts/scripts/lib/registry.py"): _allow(*PACKAGE_CCC),
    ModulePath("omd/packages/check_mk/post-create/01_create-sample-config.py"): _allow(),
    ModulePath("omd/packages/enterprise/bin/cmk-license-email-notification"): _allow(
        "cmk.utils.cee.licensing"
    ),
}


class CMKModuleLayerChecker(BaseChecker):
    name = "cmk-module-layer-violation"
    msgs = {
        "C8410": ("Import of %s not allowed in %r", "cmk-module-layer-violation", "whoop?"),
    }

    # This doesn't change during a pylint run, so let's save a realpath() call per import.
    cmk_path_cached = repo_path()

    @only_required_for_messages("cmk-module-layer-violation")
    def visit_import(self, node: Import) -> None:
        for name, _ in node.names:
            self._check_import(node, ModuleName(name))

    @only_required_for_messages("cmk-module-layer-violation")
    def visit_importfrom(self, node: ImportFrom) -> None:
        if node.level in {1, 2}:
            # This is a relative import. Assume this is fine.
            return

        assert node.modname

        imported = [f"{node.modname}.{n}" for n, _ in node.names]
        for modname in imported:
            self._check_import(
                node,
                (
                    ModuleName(modname)
                    if node.level is None
                    else get_absolute_importee(
                        root_name=node.root().name,
                        modname=modname,
                        level=node.level,
                        is_package=_is_package(node),
                    )
                ),
            )

    def _check_import(self, node: Import | ImportFrom, imported: ModuleName) -> None:
        # We only care about imports of our own modules.
        # ... blissfully ignoring tests/.
        if not imported.in_component(Component("cmk")):
            return

        # We use paths relative to our project root, but not for our "pasting magic".
        importing_path = ModulePath(node.root().file).relative_to(self.cmk_path_cached)

        importing = self._get_module_name_of_files(importing_path)
        component = self._find_component(importing, importing_path)
        if not self._is_import_allowed(component, importing_path, imported):
            self.add_message(
                "cmk-module-layer-violation", node=node, args=(imported, component or importing)
            )

    @staticmethod
    def _get_module_name_of_files(path: ModulePath) -> ModuleName:
        # Due to our symlinks and pasting magic, astroid gets confused, so we need to compute the
        # real module name from the file path of the module.
        # Emacs' flycheck stores files to be checked in a temporary file with a prefix.
        p = path.with_name(path.name.removeprefix("flycheck_").removesuffix(".py"))

        if p.is_below("cmk") or p.is_below("tests"):
            return ModuleName(".".join(p.parts))

        if p.is_below("omd/packages/omd/omdlib"):
            return ModuleName(".".join(p.parts[3:]))

        # For all modules which don't live below cmk after mangling, just assume a toplevel module.
        return ModuleName(p.parts[-1])

    def _is_import_allowed(
        self, component: Component | None, importing_path: ModulePath, imported: ModuleName
    ) -> bool:
        if component:
            return COMPONENTS[component](imported=imported, component=component)

        try:
            file_specific_checker = _EXPLICIT_FILE_TO_DEPENDENCIES[importing_path]
        except KeyError:
            # This file does not belong to any component, and is not listed in
            # _EXPLICIT_FILE_TO_DEPENDENCIES. We don't allow any cmk imports.
            return False
        return file_specific_checker(imported=imported, component=component)

    @staticmethod
    def _find_component(importing: ModuleName, importing_path: ModulePath) -> Component | None:
        # Let's *not* check the explicit list first. We don't want to encourage to define exceptions.
        # What's below cmk/foobar, belongs to cmk.foobar, PERIOD.
        for component in COMPONENTS:
            if importing.in_component(component):
                return component
        try:
            return _EXPLICIT_FILE_TO_COMPONENT[importing_path]
        except KeyError:
            return None
