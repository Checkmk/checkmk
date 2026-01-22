#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Configuration for module layer architecture checker"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final, Protocol


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


def get_absolute_importee(
    *,
    root_name: str,
    modname: str,
    level: int,
    is_package: bool,
) -> ModuleName:
    parent = root_name.rsplit(".", level - is_package)[0]
    return ModuleName(f"{parent}.{modname}")


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


CLEAN_PLUGIN_FAMILIES = {
    "acme",
    "activemq",
    "alertmanager",
    "allnet_ip_sensoric",
    "appdynamics",
    "aws",
    "azure_status",
    "azure",
    # "azure_v2",  # :Edition, HostAddress
    "bazel",
    "cisco_meraki",
    "cisco",
    "couchbase",
    # "datadog", This cannot be fixed easily. It bypasses APIs to talk to the EC
    "ddn_s2a",
    "fritzbox",
    # "gcp",  # : Edition
    "gerrit",
    "graylog",
    "hivemanager_ng",
    "hivemanager",
    "hp_msa",
    "hpe_3par",
    "ibmsvc",
    "innovaphone",
    "jenkins",
    "jira",
    # "jolokia",  # : import hack. resolve by migrating the bakery plugin
    # "metric_backend",  # :cmk.metric_backend, cmk.utils.paths
    "mobileiron",
    "mqtt",
    # "otel", # :
    "prometheus",
    "ruckus_spot",
    "salesforce",
    "siemens_plc",
    "smb",
    "storeonce4x",
    "storeonce",
    "tinkerforge",
    # "vnx_quotas", TODO. make the authorized keys configurable?
    "zerto",
}


_PLUGIN_FAMILIES_WITH_KNOWN_API_VIOLATIONS = {
    "azure_deprecated": (
        "cmk.agent_based.v1",  # FIXME
        "cmk.ccc.version",  # edition detection
        "cmk.ccc.hostaddress",  # FormSpec validation
        "cmk.plugins.azure.lib",  # FIXME
        "cmk.utils.http_proxy_config",
        "cmk.utils.paths",  # edition detection
    ),
    "azure_v2": (
        "cmk.agent_based.v1",  # FIXME
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
        "cmk.server_side_calls_backend",
        "cmk.utils",
        "cmk.ccc",
    ),
    "custom_query_metric_backend": (
        "cmk.metric_backend",
        "cmk.utils.macros",
        "cmk.utils.paths",
        "cmk.gui.form_specs.nonfree.ultimate.unstable.metric_backend_custom_query",
    ),
    "datadog": (
        "cmk.ccc.store",
        "cmk.ccc.version",  # edition detection
        "cmk.ec.export",
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
    ),
    "jolokia": ("cmk.utils.paths",),
    "logwatch": (
        "cmk.base.config",
        "cmk.base.configlib.servicename",
        "cmk.ccc.hostaddress",
        "cmk.ccc.debug",
        "cmk.checkengine.plugins",
        "cmk.ec.event",
        "cmk.ec.export",
        "cmk.gui.mkeventd",
        "cmk.utils.paths",
    ),
    "metric_backend_omd": ("cmk.metric_backend",),
    "otel": (
        "cmk.gui.form_specs.unstable",
        "cmk.otel_collector",
        "cmk.shared_typing.vue_formspec_components",
        "cmk.metric_backend",
        "cmk.utils.paths",
        "cmk.discover_plugins",
    ),
    "robotmk": ("cmk.nonfree.pro.robotmk",),
    "sftp": ("cmk.utils.paths",),
    "vnx_quotas": ("cmk.utils.paths",),
}

PACKAGE_PLUGIN_APIS = (
    "cmk.agent_based.prediction_backend",
    "cmk.agent_based.legacy",
    "cmk.agent_based.v1",
    "cmk.agent_based.v2",
    "cmk.bakery.v2_unstable",
    "cmk.graphing.v1",
    "cmk.inventory_ui.v1_unstable",
    "cmk.password_store.v1_unstable",
    "cmk.rulesets.v1",
    "cmk.rulesets.internal",
    "cmk.server_side_calls.internal",
    "cmk.server_side_calls.v1",
    "cmk.server_side_programs.v1_unstable",
)

PACKAGE_CCC = ("cmk.ccc",)

PACKAGE_MESSAGING = ("cmk.messaging",)

PACKAGE_MKP_TOOL = ("cmk.mkp_tool",)

PACKAGE_WERKS = ("cmk.werks",)

PACKAGE_CRYPTO = ("cmk.crypto",)

PACKAGE_TRACE = ("cmk.trace",)

PACKAGE_METRIC_BACKEND = ("cmk.metric_backend",)

PACKAGE_LIVESTATUS_CLIENT = ("cmk.livestatus_client",)

PACKAGE_RELAY_PROTOCOLS = ("cmk.relay_protocols",)

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
    "automation_config",
    "backup",
    "caching",
    "caching_redis",
    "config_path",
    "config_warnings",
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
    "nonfree.cloud",
    "nonfree.pro",
    "nonfree.ultimate",
    "nonfree.ultimatemt",
    "observer",
    "paths",
    "redis",
    "regex",
    "render",
    "servicename",
    "setup_search_index",
    "ssh_client",
    "tags",
    "timeperiod",
    "translations",
    "urls",
    "visuals",
)

COMPONENTS: Mapping[Component, ImportCheckerProtocol] = {
    Component("cmk.agent_based"): _allow(),
    Component("cmk.agent_receiver"): _allow(
        *PACKAGE_CCC,
        "cmk.relay_protocols",
    ),
    Component("cmk.automations"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_TRACE,
        *PACKAGE_PLUGIN_APIS,
        "cmk.checkengine",
        "cmk.helper_interface",
        "cmk.utils.check_utils",
        "cmk.utils.config_warnings",
        "cmk.utils.http_proxy_config",
        "cmk.utils.oauth2_connection",
        "cmk.utils.ip_lookup",
        "cmk.utils.labels",
        "cmk.utils.log",
        "cmk.utils.notify_types",
        "cmk.utils.paths",
        "cmk.utils.rulesets.ruleset_matcher",
        "cmk.utils.servicename",
        "cmk.utils.unixsocket_http",
    ),
    Component("cmk.astrein"): _allow(),
    # only allow itself, this is the future :-)
    Component("cmk.bakery"): _allow(),
    Component("cmk.base.api.bakery"): _allow(
        "cmk.bakery",
        "cmk.ccc",
        "cmk.utils",
    ),
    Component("cmk.base.nonfree.ultimate.metric_backend_fetcher"): _allow(
        "cmk.base.config",
        "cmk.ccc",
        "cmk.fetchers",
        "cmk.plugins.otel.special_agents.nonfree.ultimate.agent_otel",
    ),
    Component("cmk.base.nonfree.bakery"): _allow(
        "cmk.bakery",
        "cmk.base.api.bakery",
        "cmk.base.automations",
        "cmk.base.base_app",
        "cmk.base.config",
        "cmk.base.configlib",
        "cmk.base.plugins.bakery.bakery_api",
        "cmk.base.modes.modes",
        "cmk.base.nonfree.cap",
        "cmk.base.nonfree.plugins.bakery.bakery_api",
        "cmk.checkengine",
        "cmk.crypto.certificate",
        "cmk.nonfree.pro.robotmk.bakery",
        "cmk.ccc",
        "cmk.nonfree.pro.bakery",
        "cmk.discover_plugins",
        "cmk.utils",
        "cmk.automations",
    ),
    Component("cmk.base.nonfree.notify_automation"): _allow(
        "cmk.automations",
        "cmk.base.automations",
        "cmk.base.config",
        "cmk.base.notify",
        "cmk.ccc.version",
        "cmk.checkengine",
        "cmk.utils",
    ),
    Component("cmk.base.nonfree.cmc"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_RELAY_PROTOCOLS,
        "cmk.base.nonfree",
        "cmk.base.config",
        "cmk.base.configlib",
        "cmk.base.core",
        "cmk.core_client",
        "cmk.fetcher_encoder",
        "cmk.fetcher_helper",
        "cmk.nonfree.pro.robotmk",
        "cmk.checkengine",
        "cmk.fetchers",
        "cmk.inventory",
        "cmk.rrd",
        "cmk.utils",
    ),
    Component("cmk.base.nonfree.ultimate.relay"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_RELAY_PROTOCOLS,
        "cmk.base.nonfree",
        "cmk.base.config",
        "cmk.base.configlib",
        "cmk.base.core",
        "cmk.fetcher_encoder",
        "cmk.fetcher_helper",
        "cmk.checkengine.plugins",
        "cmk.relay_fetcher_trigger",
        "cmk.fetchers",
        "cmk.inventory",
        "cmk.rrd",
        "cmk.utils",
    ),
    Component("cmk.base.nonfree"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        "cmk.base",
        "cmk.checkengine",
        "cmk.check_helper_protocol",
        "cmk.events",
        "cmk.fetcher_encoder",
        "cmk.fetcher_helper",
        "cmk.fetchers",
        "cmk.helper_interface",
        "cmk.server_side_calls_backend",
        "cmk.utils",
    ),
    Component("cmk.base.config"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_TRACE,
        "cmk.automations",
        "cmk.base.default_config",
        "cmk.base.configlib",
        "cmk.base.parent_scan",
        "cmk.base.snmp_plugin_store",
        "cmk.base.sources",
        "cmk.fetcher_helper",
        "cmk.checkengine",
        "cmk.discover_plugins",
        "cmk.ec",
        "cmk.events",
        "cmk.fetchers",
        "cmk.helper_interface",
        "cmk.inventory",
        "cmk.piggyback",
        "cmk.rrd",
        "cmk.server_side_calls_backend",
        "cmk.snmplib",
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
        "cmk.fetcher_helper",
        "cmk.checkengine",
        "cmk.core_client",
        "cmk.discover_plugins",
        "cmk.ec",
        "cmk.events",
        "cmk.fetchers",
        "cmk.helper_interface",
        "cmk.inventory",
        "cmk.piggyback",
        "cmk.product_telemetry",
        "cmk.relay_fetcher_trigger",
        "cmk.relay_protocols",
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
    Component("cmk.ccc"): _allow(
        *PACKAGE_TRACE,
    ),
    Component("cmk.config_anonymizer"): _allow(
        *PACKAGE_CCC,
        "cmk.config_anonymizer",
        "cmk.checkengine",
        "cmk.utils.paths",
        "cmk.gui.log",
        "cmk.gui.utils.script_helpers",
        "cmk.gui.config",
        "cmk.utils.host_storage",
        "cmk.utils.redis.disable_redis",
        "cmk.utils.tags",
        "cmk.gui.form_specs",
        "cmk.gui.site_config",
        "cmk.gui.watolib.attributes",
        "cmk.gui.watolib.config_sync",
        "cmk.gui.watolib.host_attributes",
        "cmk.gui.watolib.hosts_and_folders",
        "cmk.gui.watolib.sites",
        "cmk.gui.watolib.tags",
        "cmk.gui.watolib.utils",
        "cmk.gui.main_modules",
        "cmk.gui.session",
        "cmk.livestatus_client",
    ),
    Component("cmk.check_helper_protocol"): _allow(
        *PACKAGE_CCC,
        "cmk.snmplib",
        "cmk.helper_interface",
        "cmk.fetchers",
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
        "cmk.utils.rulesets",
        "cmk.utils.servicename",
        "cmk.utils.timeperiod",
    ),
    Component("cmk.core_client"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_TRACE,
    ),
    Component("cmk.crypto"): _allow(
        *PACKAGE_CCC,
    ),
    Component("cmk.diskspace"): _allow(*PACKAGE_CCC),
    Component("cmk.events"): _allow(
        *PACKAGE_CCC,
        "cmk.livestatus_client",
    ),
    Component("cmk.fetcher_encoder"): _allow(
        "cmk.fetchers",
    ),
    Component("cmk.fetcher_helper"): _allow(
        *PACKAGE_CCC,
        "cmk.fetchers",
        "cmk.helper_interface",
        "cmk.snmplib",
        "cmk.utils.caching",
        "cmk.utils.paths",
        "cmk.check_helper",
        "cmk.relay_protocols",
        "cmk.check_helper_protocol",
        "cmk.relay_fetcher_trigger",
    ),
    Component("cmk.gui.cmkcert"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_MESSAGING,
        "cmk.gui",
        "cmk.utils",
        "cmk.crypto.certificate",
    ),
    Component("cmk.messaging"): _allow(
        *PACKAGE_CCC,
    ),
    Component("cmk.message_broker_certs"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_MESSAGING,
        "cmk.utils",
    ),
    Component("cmk.metric_backend"): _allow(
        *PACKAGE_CCC,
    ),
    Component("cmk.mkp_tool"): _allow(),
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
        "cmk.livestatus_client",
        "cmk.utils",
    ),
    Component("cmk.fetchers"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_CRYPTO,
        *PACKAGE_RELAY_PROTOCOLS,
        "cmk.helper_interface",
        "cmk.snmplib",
        "cmk.password_store.v1_unstable",
        "cmk.agent_based.v1",
        "cmk.inline_snmp",
    ),
    Component("cmk.fields"): _allow(*PACKAGE_CCC),
    Component("cmk.graphing"): _allow(),
    Component("cmk.gui.main_modules"): _allow(
        *PACKAGE_CCC,
        "cmk.utils.paths",
        "cmk.gui.utils",
        "cmk.gui.nonfree",
        "cmk.gui.community_registration",
    ),
    Component("cmk.gui.plugins"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        "cmk.bi",
        "cmk.checkengine",
        "cmk.gui",
        "cmk.inventory",
        "cmk.shared_typing.vue_formspec_components",
        "cmk.utils.dateutils",
        "cmk.utils.paths",
        "cmk.utils.rulesets",
        "cmk.utils.tags",
    ),
    Component("cmk.gui.nonfree.pro.plugins"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        "cmk.gui",
        "cmk.shared_typing.vue_formspec_components",
        "cmk.utils.nonfree.pro",
        "cmk.utils.mrpe_config",
        "cmk.utils.paths",
        "cmk.utils.render",
        "cmk.utils.rulesets",
    ),
    Component("cmk.gui.nonfree.ultimate.plugins"): _allow(
        *PACKAGE_PLUGIN_APIS,
        "cmk.gui",
        "cmk.shared_typing.vue_formspec_components",
    ),
    Component("cmk.gui.nonfree.pro"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_CRYPTO,
        *PACKAGE_MKP_TOOL,
        "cmk.nonfree.pro.bakery",
        "cmk.nonfree.pro.robotmk.gui",
        "cmk.discover_plugins",
        "cmk.fields",
        "cmk.gui",
        "cmk.shared_typing",
        "cmk.livestatus_client",
        "cmk.product_telemetry",
        "cmk.utils.agent_registration",
        "cmk.utils.automation_config",
        "cmk.utils.caching",
        "cmk.utils.nonfree.pro",
        "cmk.utils.certs",
        "cmk.utils.config_warnings",
        "cmk.utils.dateutils",
        "cmk.utils.global_ident_type",
        "cmk.utils.http_proxy_config",
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
        exclude=("cmk.gui.plugins", "cmk.gui.nonfree.pro.plugins"),
    ),
    Component("cmk.gui.nonfree.ultimate"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_METRIC_BACKEND,
        "cmk.nonfree.ultimate.metric_backend.gui",
        "cmk.nonfree.ultimate.otel.gui.register",
        "cmk.checkengine",
        "cmk.nonfree.pro.robotmk.gui",
        "cmk.fields",
        "cmk.gui",
        "cmk.otel_collector",
        "cmk.shared_typing",
        "cmk.utils.automation_config",
        "cmk.utils.certs",
        "cmk.utils.licensing",
        "cmk.utils.agent_registration",
        "cmk.utils.nonfree.pro",
        "cmk.utils.config_warnings",
        "cmk.utils.labels",
        "cmk.utils.macros",
        "cmk.utils.password_store",
        "cmk.utils.paths",
        "cmk.utils.render",
        "cmk.utils.rulesets",
        exclude=("cmk.gui.plugins", "cmk.gui.nonfree.pro.plugins"),
    ),
    Component("cmk.gui.nonfree.ultimatemt"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_CRYPTO,
        *PACKAGE_MESSAGING,
        "cmk.bi",
        "cmk.nonfree.ultimate.metric_backend.gui.register",
        "cmk.nonfree.ultimate.otel.gui.register",
        "cmk.nonfree.pro.robotmk.gui",
        "cmk.gui",
        "cmk.inventory",
        "cmk.piggyback",
        "cmk.utils.nonfree.pro",
        "cmk.utils.automation_config",
        "cmk.utils.certs",
        "cmk.utils.licensing",
        "cmk.utils.nonfree.ultimatemt",
        "cmk.utils.images",
        "cmk.utils.password_store",
        "cmk.utils.paths",
        "cmk.utils.redis",
        exclude=("cmk.gui.plugins", "cmk.gui.nonfree.pro.plugins"),
    ),
    Component("cmk.gui.nonfree.cloud"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_CRYPTO,
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_TRACE,
        "cmk.nonfree.ultimate.metric_backend.gui.register",
        "cmk.nonfree.ultimate.otel.gui.register",
        "cmk.fields",
        "cmk.gui",
        "cmk.utils.agent_registration",
        "cmk.utils.config_warnings",
        "cmk.utils.nonfree.pro",
        "cmk.utils.nonfree.cloud",
        "cmk.utils.licensing",
        "cmk.utils.local_secrets",
        "cmk.utils.log",
        "cmk.utils.paths",
        "cmk.utils.redis",
        "cmk.utils.urls",
        "cmk.rulesets.v1",
        "cmk.shared_typing",
        exclude=("cmk.gui.plugins", "cmk.gui.nonfree.pro.plugins"),
    ),
    Component("cmk.gui.graphing.nonfree.ultimate"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_METRIC_BACKEND,
        "cmk.gui",
        "cmk.nonfree.ultimate.metric_backend.gui",
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
        "cmk.product_telemetry",
        "cmk.server_side_calls_backend",
        "cmk.shared_typing",
        "cmk.utils.agent_registration",
        "cmk.utils.auto_queue",
        "cmk.utils.automation_config",
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
        "cmk.utils.ip_lookup",
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
        "cmk.utils.render",
        "cmk.utils.rulesets",
        "cmk.utils.schedule",
        "cmk.utils.servicename",
        "cmk.utils.setup_search_index",
        "cmk.utils.statename",
        "cmk.utils.tags",
        "cmk.utils.timeperiod",
        "cmk.utils.translations",
        "cmk.utils.unixsocket_http",
        "cmk.utils.urls",
        "cmk.utils.http_proxy_config",
        "cmk.utils.oauth2_connection",
        "cmk.utils.visuals",
        "cmk.utils.werks",
        exclude=(
            "cmk.gui.plugins",
            "cmk.gui.nonfree.pro.plugins",
            "cmk.gui.nonfree.pro",
            "cmk.gui.nonfree.ultimate",
            "cmk.gui.nonfree.ultimatemt",
        ),
    ),
    # should become a package
    Component("cmk.helper_interface"): _allow(*PACKAGE_CCC),
    Component("cmk.inline_snmp"): _allow(
        *PACKAGE_CCC,
        "cmk.helper_interface",
        "cmk.snmplib",
    ),
    Component("cmk.inventory"): _allow(
        *PACKAGE_CCC,
    ),
    Component("cmk.inventory_ui"): _allow(),
    Component("cmk.notification_plugins"): _allow(
        *PACKAGE_CCC,
        "cmk.utils",
    ),
    Component("cmk.piggyback"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_MESSAGING,
        "cmk.utils.paths",
        "cmk.utils.log.security_event",
    ),
    **{  # some plugin families that refuse to play by the rules:
        Component(f"cmk.plugins.{family}"): _allow(
            *PACKAGE_PLUGIN_APIS,
            "cmk.plugins.lib",
            *violations,
        )
        for family, violations in _PLUGIN_FAMILIES_WITH_KNOWN_API_VIOLATIONS.items()
    },
    # These are ready to be moved to a package.
    # PLEASE DO NOT INTRODUCE NEW DEPENDENCIES!
    **{
        Component(f"cmk.plugins.{family}"): _allow(
            *PACKAGE_PLUGIN_APIS,
            "cmk.plugins.lib",
        )
        for family in CLEAN_PLUGIN_FAMILIES
    },
    Component("cmk.password_store"): _allow(),
    Component("cmk.plugins"): _allow(
        *PACKAGE_PLUGIN_APIS,
    ),
    Component("cmk.product_telemetry"): _allow(
        "cmk.ccc.version",
        "cmk.base.app.make_app",
        "cmk.base.config.load",
        "cmk.livestatus_client",
        "cmk.utils.http_proxy_config",
        "cmk.utils.livestatus_helpers",
        "cmk.utils.paths",
    ),
    Component("cmk.rulesets"): _allow(),
    Component("cmk.server_side_calls"): _allow(),
    Component("cmk.server_side_calls_backend"): _allow(
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_CCC,
        "cmk.discover_plugins",
        "cmk.utils",
    ),
    Component("cmk.server_side_programs"): _allow(),
    Component("cmk.special_agents"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        "cmk.utils.password_store",
        "cmk.utils.paths",
    ),
    Component("cmk.snmplib"): _allow(
        *PACKAGE_CCC,
        "cmk.agent_based.v1",
    ),
    Component("cmk.update_config"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_TRACE,
        *PACKAGE_WERKS,
        "cmk.base",
        "cmk.nonfree.ultimate.metric_backend",
        "cmk.checkengine",
        "cmk.nonfree.pro.robotmk",
        "cmk.discover_plugins",
        "cmk.diskspace.config",
        "cmk.fetchers",
        "cmk.gui",
        "cmk.messaging",
        "cmk.message_broker_certs",
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
    Component("cmk.livestatus_client"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_TRACE,
    ),
    Component("cmk.mknotifyd"): _allow(
        *PACKAGE_CCC,
        "cmk.events",
    ),
    Component("cmk.nonfree.ultimate.metric_backend.dcd"): _allow(
        *PACKAGE_METRIC_BACKEND,
        "cmk.ccc",
        "cmk.nonfree.pro.dcd",
        "cmk.utils",
    ),
    Component("cmk.nonfree.ultimate.metric_backend.gui"): _allow(
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_METRIC_BACKEND,
        "cmk.ccc",
        "cmk.fields",
        "cmk.gui",
        "cmk.utils",
    ),
    Component("cmk.nonfree.pro.bakery"): _allow(
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_CCC,
        *PACKAGE_CRYPTO,
        "cmk.base.checkers",
        "cmk.base.config",
        "cmk.base.configlib.loaded_config",
        "cmk.base.nonfree.cmc",
        "cmk.base.errorhandling",
        "cmk.base.plugins.bakery.bakery_api.v1",
        "cmk.base.sources",
        "cmk.base.utils",
        "cmk.utils.paths",
    ),
    Component("cmk.nonfree.pro.dcd"): _allow(
        *PACKAGE_CCC,
        "cmk.nonfree.ultimate.otel.dcd.register",
        "cmk.otel_collector",
        "cmk.piggyback",
        "cmk.utils",
    ),
    Component("cmk.nonfree.pro.snmp_backend"): _allow(),
    Component("cmk.nonfree.pro.liveproxy"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_TRACE,
        "cmk.inventory",
        "cmk.utils",
    ),
    Component("cmk.nonfree.pro.notification_plugins"): _allow("cmk.utils"),
    Component("cmk.nonfree.pro.robotmk"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        # I don't think we have any idea of how to fix this.
        "cmk.base.nonfree.bakery",
        "cmk.base.plugins.bakery",
        "cmk.nonfree.pro.bakery",
        "cmk.checkengine",
        "cmk.gui",
        "cmk.shared_typing",
        "cmk.utils",
    ),
    Component("cmk.otel_collector"): _allow(
        *PACKAGE_CCC,
    ),
    Component("cmk.relay"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_CRYPTO,
        *PACKAGE_RELAY_PROTOCOLS,
        "cmk.check_helper_protocol",
    ),
    Component("cmk.relay_engine"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_CRYPTO,
        "cmk.check_helper_protocol",
        "cmk.relay",
        "cmk.relay_protocols",
        "cmk.testlib.relay",
    ),
    Component("cmk.relay_protocols"): _allow(),
    Component("cmk.relay_fetcher_trigger"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_RELAY_PROTOCOLS,
        "cmk.check_helper_protocol",
        "cmk.fetchers",
        "cmk.fetcher_encoder",
        "cmk.helper_interface",
        "cmk.snmplib",
    ),
    Component("cmk.testlib.agent_receiver"): _allow(
        "cmk.agent_receiver",
        "cmk.relay_protocols",
    ),
    Component("cmk.testlib.relay"): _allow(
        *PACKAGE_CCC,
        "cmk.check_helper_protocol",
        "cmk.relay",
        "cmk.relay_protocols",
    ),
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
    Component("cmk.trace"): _allow(),
    Component("cmk.utils.certs"): _allow(
        *PACKAGE_CRYPTO,
        *PACKAGE_CCC,
        "cmk.utils.log",
    ),
    Component("cmk.utils.password_store"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        "cmk.utils.paths",
        "cmk.utils.global_ident_type",
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
            "cmk.utils.password_store",
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
    Component("cmk.nonfree.ultimate.metric_backend.gui"): _allow(
        *PACKAGE_METRIC_BACKEND,
        "cmk.ccc",
        "cmk.gui",
        "cmk.utils",
    ),
    Component("cmk.nonfree.ultimate.otel.dcd"): _allow(
        *PACKAGE_METRIC_BACKEND,
        "cmk.ccc",
        "cmk.nonfree.pro.dcd",
        "cmk.utils",
    ),
    Component("cmk.nonfree.ultimate.otel.gui"): _allow(
        *PACKAGE_PLUGIN_APIS,
        "cmk.fields",
        "cmk.gui",
    ),
    Component("cmk.werks"): _allow(
        *PACKAGE_CCC,
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
        "cmk.utils.nonfree.pro.licensing",
        "cmk.utils.paths",
        "cmk.utils.rulesets",
    ),
    Component("tests.plugins_siteless"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        "cmk.plugins",
        "cmk.base.app.make_app",
        "cmk.base.config",
        "cmk.base.checkers",
        "cmk.base.sources",
        "cmk.checkengine",
        "cmk.discover_plugins",
        "cmk.fetchers",
        "cmk.gui",
        "cmk.helper_interface",
        "cmk.piggyback",
        "cmk.server_side_calls_backend",
        "cmk.utils",
    ),
    Component("tests.integration.cmk.base.nonfree.pro.helper_bake_and_sign"): (
        lambda *_a, **_kw: True
    ),
    Component("tests.integration.cmk.base.nonfree.pro.helper_bake_without_sign"): (
        lambda *_a, **_kw: True
    ),
    Component("tests.integration.cmk.base"): _allow(
        *PACKAGE_CCC,
        "cmk.automations",
        "cmk.base",
        "cmk.nonfree.pro.bakery",
        "cmk.checkengine",
        "cmk.crypto",
        "cmk.discover_plugins",
        "cmk.utils",
    ),
    Component("tests.integration.cmk.nonfree.pro.liveproxy"): _allow(
        *PACKAGE_CCC,
        "cmk.nonfree.pro.liveproxy",
    ),
    Component("tests.integration.cmk.nonfree.pro.robotmk"): _allow(
        *PACKAGE_CCC,
        "cmk.nonfree.pro.robotmk",
        "cmk.utils.rulesets",
        "cmk.utils.servicename",
    ),
    Component("tests.integration.cmk.gui"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_CRYPTO,
        "cmk.bi",
        "cmk.gui",
        "cmk.shared_typing",
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
    Component("tests.integration.nonfree.ultimate.metric_backend"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_METRIC_BACKEND,
        "cmk.gui",
        "cmk.plugins",
        "cmk.utils",
    ),
    Component("tests.integration.nonfree.ultimate.otel"): _allow(
        *PACKAGE_CCC,
        "cmk.otel_collector.constants",
    ),
    Component("tests.integration.nonfree.ultimate.relay"): _allow(
        *PACKAGE_RELAY_PROTOCOLS,
        "cmk.agent_receiver.lib.certs",
        "cmk.crypto.certificate",
        "cmk.crypto.keys",
        "cmk.crypto.x509",
    ),
    Component("tests.integration"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_MKP_TOOL,
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_CRYPTO,
        "cmk.base.config",
        "cmk.checkengine",
        "cmk.discover_plugins",
        "cmk.plugins",
        "cmk.server_side_calls_backend",
        "cmk.utils",
    ),
    Component("tests.integration_redfish"): _allow(
        *PACKAGE_CCC,
    ),
    Component("tests.plugins_integration"): _allow(
        *PACKAGE_CRYPTO,
    ),
    # Tests are allowed to import everything for now. Should be cleaned up soon (TM)
    Component("tests.testlib"): lambda *_a, **_kw: True,
    Component("tests.unit.cmk.nonfree.ultimate.otel.dcd"): _allow(
        *PACKAGE_CCC,
        "cmk.nonfree.ultimate.otel.dcd",
        "cmk.nonfree.pro.dcd",
        "cmk.utils.paths",
    ),
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
        *PACKAGE_RELAY_PROTOCOLS,
        "cmk.agent_based",
        "cmk.checkengine",
        "cmk.fetchers",
        "cmk.inline_snmp",
        "cmk.helper_interface",
        "cmk.relay_fetcher_trigger",
        "cmk.snmplib",
        "cmk.utils",
    ),
    Component("tests.unit.cmk"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_CRYPTO,
        *PACKAGE_MESSAGING,
        *PACKAGE_MKP_TOOL,
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_RELAY_PROTOCOLS,
        *PACKAGE_TRACE,
        *PACKAGE_WERKS,
        "cmk.automations",
        "cmk.bakery",
        "cmk.base",
        "cmk.bi",
        "cmk.checkengine",
        "cmk.cmkpasswd",
        "cmk.core_client",
        "cmk.discover_plugins",
        "cmk.diskspace",
        "cmk.ec",
        "cmk.events",
        "cmk.fetcher_encoder",
        "cmk.fetcher_helper",
        "cmk.fetchers",
        "cmk.fields",
        "cmk.gui",
        "cmk.helper_interface",
        "cmk.inventory",
        "cmk.livestatus_client",
        "cmk.message_broker_certs",
        "cmk.metric_backend",
        "cmk.nonfree.pro.bakery",
        "cmk.nonfree.pro.dcd",
        "cmk.nonfree.pro.liveproxy",
        "cmk.nonfree.pro.robotmk",
        "cmk.nonfree.ultimate.metric_backend",
        "cmk.notification_plugins",
        "cmk.otel_collector",
        "cmk.piggyback",
        "cmk.plugins",
        "cmk.post_rename_site",
        "cmk.product_telemetry",
        "cmk.rrd",
        "cmk.server_side_calls_backend",
        "cmk.shared_typing",
        "cmk.snmplib",
        "cmk.special_agents",
        "cmk.update_config",
        "cmk.utils",
        "cmk.validate_config",
    ),
    Component("tests.update"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_CRYPTO,
        "cmk.utils.licensing",
    ),
    Component("tests.unit"): _allow(
        *PACKAGE_CCC,
        *PACKAGE_WERKS,
        *PACKAGE_PLUGIN_APIS,
        *PACKAGE_CRYPTO,
        *PACKAGE_LIVESTATUS_CLIENT,
        "cmk.piggyback",
        "cmk.utils",
    ),
}

_EXPLICIT_FILE_TO_COMPONENT = {
    ModulePath("bin/check_mk"): Component("cmk.base"),
    ModulePath("bin/cmk-automation-helper"): Component("cmk.base"),
    ModulePath("bin/cmk-cert"): Component("cmk.gui.cmkcert"),
    ModulePath("bin/message-broker-certs"): Component("cmk.message_broker_certs"),
    ModulePath("bin/cmk-config-anonymizer.py"): Component("cmk.config_anonymizer"),
    ModulePath("bin/cmk-convert-rrds"): Component("cmk.rrd"),
    ModulePath("bin/cmk-create-rrd"): Component("cmk.rrd"),
    ModulePath("bin/cmk-migrate-extension-rulesets"): Component("cmk.update_config"),
    ModulePath("bin/cmk-migrate-http"): Component("cmk.update_config"),
    ModulePath("bin/cmk-passwd"): Component("cmk.cmkpasswd"),
    ModulePath("bin/cmk-ui-job-scheduler"): Component("cmk.gui"),
    ModulePath("bin/cmk-update-config"): Component("cmk.update_config"),
    ModulePath("bin/cmk-validate-config"): Component("cmk.validate_config"),
    ModulePath("bin/cmk-validate-plugins"): Component("cmk.validate_plugins"),
    ModulePath("bin/mkeventd"): Component("cmk.ec"),
    ModulePath("bin/post-rename-site"): Component("cmk.post_rename_site"),
    ModulePath("cmk/active_checks/check_cmk_inv.py"): Component("cmk.base"),
    ModulePath("omd/packages/appliance/webconf_snapin.py"): Component("cmk.gui"),
    ModulePath("omd/non-free/packages/cmk-dcd/cmk-dcd.py"): Component("cmk.nonfree.pro.dcd"),
    ModulePath("omd/non-free/packages/cmk-dcd/dcd.py"): Component("cmk.nonfree.pro.dcd"),
    ModulePath("omd/non-free/packages/cmk-liveproxyd/liveproxyd.py"): Component(
        "cmk.nonfree.pro.liveproxy"
    ),
    ModulePath("omd/packages/maintenance/diskspace.py"): Component("cmk.diskspace"),
    ModulePath("web/app/index.wsgi"): Component("cmk.gui"),
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
    ModulePath("notifications/servicenow"): Component("cmk.nonfree.pro.notification_plugins"),
    ModulePath("notifications/jira_issues"): Component("cmk.nonfree.pro.notification_plugins"),
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
        *PACKAGE_LIVESTATUS_CLIENT,
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
    ModulePath("buildscripts/scripts/build-cmk-container.py"): _allow(*PACKAGE_CCC),
    ModulePath("buildscripts/scripts/assert_build_artifacts.py"): _allow(*PACKAGE_CCC),
    ModulePath("buildscripts/scripts/publish_cloud_images.py"): _allow(*PACKAGE_CCC),
    ModulePath("buildscripts/scripts/unpublish-container-image.py"): _allow(*PACKAGE_CCC),
    ModulePath("buildscripts/scripts/lib/registry.py"): _allow(*PACKAGE_CCC),
    ModulePath("omd/packages/check_mk/post-create/01_create-sample-config.py"): _allow(),
    ModulePath("omd/non-free/packages/licensing/cmk-license-email-notification.py"): _allow(
        "cmk.utils.nonfree.pro.licensing"
    ),
}
