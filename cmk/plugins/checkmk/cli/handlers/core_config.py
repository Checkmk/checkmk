#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cmk.ccc.site
import cmk.utils.password_store
import cmk.utils.paths
from cmk.base import config
from cmk.base.app import make_app
from cmk.base.configlib.servicename import make_final_service_name_config
from cmk.base.core import interface as core_interface
from cmk.base.core.nagios import create_config, NagiosCoreConfig
from cmk.ccc import tty
from cmk.ccc.exceptions import MKBailOut, MKGeneralException
from cmk.ccc.hostaddress import HostAddress
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Handler as CLIHandler
from cmk.plugins.checkmk.cli.core_config import (
    cli_command_nagios_config,
    cli_command_reload,
    cli_command_restart,
    cli_command_update,
    CoreConfigRequest,
)
from cmk.ruleset_matcher.matcher import BundledHostRulesetMatcher
from cmk.server_side_calls_backend import load_secrets_file
from cmk.utils import config_warnings, ip_lookup, timeperiod
from cmk.utils.log import console

from .agent_based import load_checks


class _ConfigureCore(Protocol):
    def __call__(self, request: CoreConfigRequest, *, omd_root: Path, debug: bool) -> None: ...


def _dump_nagios_config(request: CoreConfigRequest, *, omd_root: Path, debug: bool) -> None:
    app = make_app(omd_root)

    plugins = load_checks(debug=debug)
    loading_result = config.load(validate_hosts=True, debug=debug)
    loaded_config = loading_result.loaded_config
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    label_manager = loading_result.config_cache.label_manager
    config_cache = loading_result.config_cache
    core_objects_config = config.CoreObjectsConfig(loaded_config, ruleset_matcher, label_manager)
    hosts_config = loading_result.hosts_config

    ip_lookup_config = config_cache.ip_lookup_config(fake_dns=request.fake_dns)

    if loaded_config.host_notification_periods:
        config_warnings.warn(
            "host_notification_periods is not longer supported. Please use extra_host_conf['notification_period'] instead."
        )

    if loaded_config.service_notification_periods:
        config_warnings.warn(
            "service_notification_periods is not longer supported. Please use extra_service_conf['notification_period'] instead."
        )

    hostnames = sorted(
        request.hosts
        or {
            hn
            for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
            if config_cache.is_active(hn) and config_cache.is_online(hn)
        }
    )

    final_service_name_config = make_final_service_name_config(loaded_config, ruleset_matcher)
    service_name_config = config_cache.make_passive_service_name_config(final_service_name_config)
    _notify_host_files = create_config(
        outfile=sys.stdout,
        hosts_config=hosts_config,
        host_tags=loading_result.host_tags,
        config_cache=config_cache,
        core_objects_config=core_objects_config,
        nagios_core_config=NagiosCoreConfig.from_raw_config(loaded_config),
        final_service_name_config=final_service_name_config,
        passive_service_name_config=service_name_config,
        enforced_services_table=config.EnforcedServicesTable(
            BundledHostRulesetMatcher(
                loaded_config.static_checks,
                ruleset_matcher,
                label_manager.labels_of_host,
            ),
            service_name_config,
            plugins.check_plugins,
            label_manager.labels_of_service,
        ),
        plugins=plugins.check_plugins,
        hostnames=hostnames,
        # This only dumps the configuration; unlike an activation it deliberately
        # does not persist the licensed state.
        licensing_handler=app.licensing_handler_factory(debug=debug),
        passwords=load_secrets_file(cmk.utils.password_store.pending_secrets_path_site()),
        get_ip_stack_config=ip_lookup_config.ip_stack_config,
        default_address_family=ip_lookup_config.default_address_family,
        ip_address_of=ip_lookup.ConfiguredIPLookup(
            ip_lookup.make_lookup_ip_address(ip_lookup_config),
            allow_empty=hosts_config.clusters,
            error_handler=config.handle_ip_lookup_failure,
        ),
        service_depends_on=config.ServiceDependsOn(
            tag_list=loading_result.host_tags.tag_list,
            service_dependencies=loading_result.loaded_config.service_dependencies,
            debug=debug,
        ),
        timeperiods=timeperiod.get_all_timeperiods(loaded_config.timeperiods),
        get_relay_id=lambda host_name: config.get_relay_id(label_manager.labels_of_host(host_name)),
    )


def _make_configured_notify_relay(
    relays_present: bool,
) -> Callable[[Callable[[str], object]], None]:
    noop = lambda *a, **kw: None  # noqa: ARG005

    if not relays_present:
        return noop

    try:
        from cmk.relay_fetcher_trigger.relay_client import (  # type: ignore[import-not-found, unused-ignore]
            Client,
            ClientConfig,
        )
    except ImportError:
        return noop

    config = cmk.ccc.site.get_omd_config(cmk.utils.paths.omd_root)
    return Client(  # type: ignore[no-any-return, unused-ignore]
        ClientConfig(
            agent_receiver_port=int(config["CONFIG_AGENT_RECEIVER_PORT"]),
            site_name=cmk.ccc.site.omd_site(),
            omd_root=cmk.utils.paths.omd_root,
        )
    ).publish_new_config


class _Update(Protocol):
    def __call__(self, fake_dns: HostAddress | None, *, omd_root: Path, debug: bool) -> bool: ...


def _update(fake_dns: HostAddress | None, *, omd_root: Path, debug: bool) -> bool:
    app = make_app(omd_root)
    plugins = load_checks(debug=debug)
    loading_result = config.load(validate_hosts=True, debug=debug)
    loaded_config = loading_result.loaded_config
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    label_manager = loading_result.config_cache.label_manager
    core_objects_config = config.CoreObjectsConfig(loaded_config, ruleset_matcher, label_manager)
    hosts_config = loading_result.hosts_config

    ip_lookup_config = loading_result.config_cache.ip_lookup_config(fake_dns=fake_dns)
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=hosts_config.clusters,
        error_handler=ip_lookup.CollectFailedHosts(),
    )
    final_service_name_config = make_final_service_name_config(loaded_config, ruleset_matcher)
    service_name_config = loading_result.config_cache.make_passive_service_name_config(
        final_service_name_config
    )
    enfored_services_table = config.EnforcedServicesTable(
        BundledHostRulesetMatcher(
            loaded_config.static_checks,
            ruleset_matcher,
            label_manager.labels_of_host,
        ),
        service_name_config,
        plugins.check_plugins,
        label_manager.labels_of_service,
    )

    try:
        with core_interface.activation_lock(mode=loaded_config.restart_locking):
            core, core_client = app.create_core(loaded_config)

            core_interface.do_create_config(
                core_client=core_client,
                config_builders=core_interface.config_builders(core),
                hosts_config=hosts_config,
                host_tags=loading_result.host_tags,
                config_cache=loading_result.config_cache,
                core_objects_config=core_objects_config,
                final_service_name_config=final_service_name_config,
                passive_service_name_config=service_name_config,
                enforced_services_table=enfored_services_table,
                plugins=plugins,
                get_ip_stack_config=ip_lookup_config.ip_stack_config,
                default_address_family=ip_lookup_config.default_address_family,
                ip_address_of=ip_address_of,
                ip_address_of_mgmt=ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config),
                hosts_to_update=None,
                service_depends_on=config.ServiceDependsOn(
                    tag_list=loading_result.host_tags.tag_list,
                    service_dependencies=loading_result.loaded_config.service_dependencies,
                    debug=debug,
                ),
                duplicates=sorted(
                    hosts_config.duplicates(
                        lambda hn: (
                            loading_result.config_cache.is_active(hn)
                            and loading_result.config_cache.is_online(hn)
                        )
                    )
                ),
                notify_relay=_make_configured_notify_relay(bool(loaded_config.relays)),
                licensing_handler_factory=app.licensing_handler_factory,
                edition=app.edition,
                loaded_config=loaded_config,
                make_fetcher_trigger=app.make_fetcher_trigger,
                debug=debug,
            )
    except Exception as e:
        console.error(f"Configuration Error: {e}", file=sys.stderr)
        if debug:
            raise
        return False

    for warning in ip_address_of.error_handler.format_errors():
        console.warning(tty.format_warning(f"\n{warning}"))
    return True


@dataclass(frozen=True, kw_only=True)
class _UpdateCommand:
    update: _Update

    def run(self, context: CLIContext, fake_dns: HostAddress | None) -> CLIExitCode:
        try:
            updated = self.update(
                fake_dns, omd_root=context.omd_root, debug=context.global_options.debug
            )
        except (MKBailOut, MKGeneralException) as e:
            context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
            if context.global_options.debug:
                raise
            return CLIExitCode.UNKNOWN
        return CLIExitCode.SUCCESS if updated else CLIExitCode.FAILURE


@dataclass(frozen=True, kw_only=True)
class _Activation:
    action: core_interface.CoreAction

    def activate(self, request: CoreConfigRequest, *, omd_root: Path, debug: bool) -> None:
        app = make_app(omd_root)
        plugins = load_checks(debug=debug)
        loading_result = config.load(validate_hosts=True, debug=debug)
        loaded_config = loading_result.loaded_config
        ruleset_matcher = loading_result.config_cache.ruleset_matcher
        label_manager = loading_result.config_cache.label_manager
        core_objects_config = config.CoreObjectsConfig(
            loaded_config, ruleset_matcher, label_manager
        )
        hosts_config = loading_result.hosts_config

        ip_lookup_config = loading_result.config_cache.ip_lookup_config(fake_dns=request.fake_dns)

        ip_address_of = ip_lookup.ConfiguredIPLookup(
            ip_lookup.make_lookup_ip_address(ip_lookup_config),
            allow_empty=hosts_config.clusters,
            error_handler=ip_lookup.CollectFailedHosts(),
        )
        ip_address_of_mgmt = ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config)
        final_service_name_config = make_final_service_name_config(loaded_config, ruleset_matcher)
        passive_service_name_config = loading_result.config_cache.make_passive_service_name_config(
            final_service_name_config
        )

        core, core_client = app.create_core(loaded_config)

        core_interface.build_and_activate_monitoring_config(
            self.action,
            loading_result.config_cache,
            core_objects_config,
            hosts_config,
            loading_result.host_tags,
            final_service_name_config,
            passive_service_name_config,
            config.EnforcedServicesTable(
                BundledHostRulesetMatcher(
                    loaded_config.static_checks,
                    ruleset_matcher,
                    label_manager.labels_of_host,
                ),
                passive_service_name_config,
                plugins.check_plugins,
                label_manager.labels_of_service,
            ),
            ip_lookup_config.ip_stack_config,
            ip_lookup_config.default_address_family,
            ip_address_of,
            ip_address_of_mgmt,
            core_client,
            plugins,
            config_builders=core_interface.config_builders(core),
            hosts_to_update=set(request.hosts) if request.hosts else None,
            locking_mode=loaded_config.restart_locking,
            service_depends_on=config.ServiceDependsOn(
                tag_list=loading_result.host_tags.tag_list,
                service_dependencies=loaded_config.service_dependencies,
                debug=debug,
            ),
            duplicates=sorted(
                hosts_config.duplicates(
                    lambda hn: (
                        loading_result.config_cache.is_active(hn)
                        and loading_result.config_cache.is_online(hn)
                    )
                )
            ),
            notify_relay=_make_configured_notify_relay(bool(loaded_config.relays)),
            licensing_handler_factory=app.licensing_handler_factory,
            edition=app.edition,
            loaded_config=loaded_config,
            make_fetcher_trigger=app.make_fetcher_trigger,
            debug=debug,
        )
        for warning in ip_address_of.error_handler.format_errors():
            console.warning(tty.format_warning(f"\n{warning}"))


@dataclass(frozen=True, kw_only=True)
class _ConfigureCoreCommand:
    configure_core: _ConfigureCore

    def run(self, context: CLIContext, request: CoreConfigRequest) -> CLIExitCode:
        try:
            self.configure_core(
                request, omd_root=context.omd_root, debug=context.global_options.debug
            )
        except (MKBailOut, MKGeneralException) as e:
            context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
            if context.global_options.debug:
                raise
            return CLIExitCode.UNKNOWN
        return CLIExitCode.SUCCESS


cli_handler_nagios_config = CLIHandler(
    command=cli_command_nagios_config,
    run=_ConfigureCoreCommand(configure_core=_dump_nagios_config).run,
)

cli_handler_update = CLIHandler(command=cli_command_update, run=_UpdateCommand(update=_update).run)

cli_handler_restart = CLIHandler(
    command=cli_command_restart,
    run=_ConfigureCoreCommand(
        configure_core=_Activation(action=core_interface.CoreAction.RESTART).activate
    ).run,
)

cli_handler_reload = CLIHandler(
    command=cli_command_reload,
    run=_ConfigureCoreCommand(
        configure_core=_Activation(action=core_interface.CoreAction.RELOAD).activate
    ).run,
)
