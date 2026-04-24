#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared bootstrap for automation handlers.

:class:`AutomationEnvironment` bundles the ``(ctx, plugins, loading_result)``
triple and exposes the derived objects every handler needs
(service name configs, service configurer, enforced services table, IP
lookup, …) as property accessors.

Where different handlers need different variants, the choice is surfaced as
an explicit keyword argument on a small builder method:

* :class:`ConfigSource` drives the trusted-CA path and the fetcher trigger.
* :class:`IPLookupFailureMode` drives the ``error_handler`` on
  :class:`~cmk.utils.ip_lookup.ConfiguredIPLookup`.

Both enums are required at every call site so handler intent stays visible.
"""

from __future__ import annotations

import enum
from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Literal, overload

import cmk.utils.paths
from cmk.base import config
from cmk.base.automations.automations import (
    AutomationContext,
    load_config,
    load_plugins,
)
from cmk.base.config import ConfigCache
from cmk.base.configlib.checkengine import DiscoveryConfig
from cmk.base.configlib.loaded_config import LoadedConfigFragment
from cmk.base.configlib.servicename import (
    FinalServiceNameConfig,
    make_final_service_name_config,
    PassiveServiceNameConfig,
)
from cmk.base.core.active_config_layout import RELATIVE_PATH_TRUSTED_CAS
from cmk.ccc.config_path import VersionedConfigPath
from cmk.ccc.hostaddress import HostName, Hosts
from cmk.checkengine.checking import ServiceConfigurer
from cmk.checkengine.plugin_backend import extract_known_discovery_rulesets
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.fetchers import FetcherTrigger
from cmk.utils import ip_lookup
from cmk.utils.labels import LabelManager
from cmk.utils.rulesets.ruleset_matcher import (
    BundledHostRulesetMatcher,
    RulesetMatcher,
)


class ConfigSource(enum.Enum):
    """Which configuration a handler is operating against.

    ``PENDING`` is the WATO-editable state
    (``cmk.utils.paths.trusted_ca_file``, ``pending_secrets_path_*``).

    ``ACTIVATED`` is the versioned config actually running in the monitoring
    core, read through the unresolved ``helper_config/latest`` symlink.
    """

    PENDING = "pending"
    ACTIVATED = "activated"


class IPLookupFailureMode(enum.Enum):
    """How :class:`ConfiguredIPLookup` should react to lookup failures.

    ``COLLECT`` accumulates failures into a
    :class:`~cmk.utils.ip_lookup.CollectFailedHosts` instance that the caller
    drains later via ``.format_errors()``. ``HANDLE`` logs a warning via
    :func:`cmk.base.config.handle_ip_lookup_failure` and continues.
    """

    COLLECT = "collect"
    HANDLE = "handle"


# Non-frozen so @cached_property can populate the instance __dict__. The env
# is semantically immutable: handlers should treat it as a value.
@dataclass
class AutomationEnvironment:
    """Bootstrap state for an automation handler.

    Build via :meth:`create`, which lazy-loads plugins and the pending config
    if the caller passed ``None``. Variant-dependent factories are methods
    taking a required enum so the choice is always explicit at the call site.
    """

    ctx: AutomationContext
    plugins: AgentBasedPlugins
    loading_result: config.LoadingResult

    @classmethod
    def create(
        cls,
        ctx: AutomationContext,
        plugins: AgentBasedPlugins | None,
        loading_result: config.LoadingResult | None,
    ) -> AutomationEnvironment:
        """Lazy-loads plugins and the pending config if the caller passed ``None``."""
        if plugins is None:
            plugins = load_plugins()
        if loading_result is None:
            loading_result = load_config(
                discovery_rulesets=extract_known_discovery_rulesets(plugins),
                get_builtin_host_labels=ctx.get_builtin_host_labels,
                edition=ctx.edition,
            )
        return cls(ctx=ctx, plugins=plugins, loading_result=loading_result)

    # --- Pass-through accessors (no caching — just re-expose what's already there).

    @property
    def loaded_config(self) -> LoadedConfigFragment:
        return self.loading_result.loaded_config

    @property
    def config_cache(self) -> ConfigCache:
        return self.loading_result.config_cache

    @property
    def ruleset_matcher(self) -> RulesetMatcher:
        return self.config_cache.ruleset_matcher

    @property
    def label_manager(self) -> LabelManager:
        return self.config_cache.label_manager

    @property
    def hosts_config(self) -> Hosts:
        return self.config_cache.hosts_config

    @property
    def latest_config_path(self) -> Path:
        # Do not resolve: the core may prune a resolved serial directory at
        # any time.
        return VersionedConfigPath.make_latest_path(cmk.utils.paths.omd_root)

    # --- Cached derivations (non-trivial construction, called from multiple sites).

    @cached_property
    def ip_lookup_config(self) -> ip_lookup.IPLookupConfig:
        return self.config_cache.ip_lookup_config()

    @cached_property
    def final_service_name_config(self) -> FinalServiceNameConfig:
        return make_final_service_name_config(self.loaded_config, self.ruleset_matcher)

    @cached_property
    def passive_service_name_config(self) -> PassiveServiceNameConfig:
        return self.config_cache.make_passive_service_name_config(self.final_service_name_config)

    @cached_property
    def service_configurer(self) -> ServiceConfigurer:
        return self.config_cache.make_service_configurer(
            self.plugins.check_plugins,
            self.passive_service_name_config,
        )

    @cached_property
    def enforced_services_table(self) -> config.EnforcedServicesTable:
        return config.EnforcedServicesTable(
            BundledHostRulesetMatcher(
                self.loaded_config.static_checks,
                self.ruleset_matcher,
                self.label_manager.labels_of_host,
            ),
            self.passive_service_name_config,
            self.plugins.check_plugins,
        )

    @cached_property
    def autochecks_config(self) -> config.AutochecksConfigurer:
        return config.AutochecksConfigurer(
            self.config_cache,
            self.plugins.check_plugins,
            self.passive_service_name_config,
        )

    @cached_property
    def discovery_config(self) -> DiscoveryConfig:
        return DiscoveryConfig(
            self.ruleset_matcher,
            self.label_manager.labels_of_host,
            self.loaded_config.discovery_rules,
        )

    # --- Variant builders --------------------------------------------------

    @overload
    def ip_address_of(
        self,
        *,
        on_failure: Literal[IPLookupFailureMode.COLLECT],
    ) -> ip_lookup.ConfiguredIPLookup[ip_lookup.CollectFailedHosts]: ...

    @overload
    def ip_address_of(
        self,
        *,
        on_failure: Literal[IPLookupFailureMode.HANDLE],
    ) -> ip_lookup.ConfiguredIPLookup[Callable[[HostName, Exception], None]]: ...

    def ip_address_of(
        self,
        *,
        on_failure: IPLookupFailureMode,
    ) -> ip_lookup.ConfiguredIPLookup[Callable[[HostName, Exception], None]]:
        # Returns a fresh instance on every call so that COLLECT-mode
        # failure buckets never get shared between unrelated consumers.
        error_handler: Callable[[HostName, Exception], None]
        match on_failure:
            case IPLookupFailureMode.COLLECT:
                error_handler = ip_lookup.CollectFailedHosts()
            case IPLookupFailureMode.HANDLE:
                error_handler = config.handle_ip_lookup_failure
        return ip_lookup.ConfiguredIPLookup(
            ip_lookup.make_lookup_ip_address(self.ip_lookup_config),
            allow_empty=self.config_cache.hosts_config.clusters,
            error_handler=error_handler,
        )

    def trusted_ca_path(self, *, config_source: ConfigSource) -> Path:
        match config_source:
            case ConfigSource.PENDING:
                return cmk.utils.paths.trusted_ca_file
            case ConfigSource.ACTIVATED:
                return self.latest_config_path / RELATIVE_PATH_TRUSTED_CAS

    def make_fetcher_trigger(
        self,
        relay_id: str | None,
        *,
        config_source: ConfigSource,
    ) -> FetcherTrigger:
        return self.ctx.make_fetcher_trigger(
            relay_id,
            self.trusted_ca_path(config_source=config_source),
        )
