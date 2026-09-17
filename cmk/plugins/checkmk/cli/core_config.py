#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The core configuration commands: --nagios-config, --update, --restart and --reload."""

import itertools
import sys
from collections.abc import Callable
from dataclasses import fields

import cmk.ccc.debug
import cmk.ccc.site
import cmk.utils.password_store
import cmk.utils.paths
from cmk.base import config
from cmk.base.base_app import CheckmkBaseApp
from cmk.base.configlib.servicename import make_final_service_name_config
from cmk.base.core import interface as core_interface
from cmk.base.modes.check_mk import forced_ip_lookup, host_addresses, load_checks, set_fake_dns
from cmk.ccc import tty
from cmk.ccc.store import activation_lock
from cmk.checkengine.checker_helper_config import make_packed_config_writer
from cmk.checkengine.plugins import make_plugin_store
from cmk.cli.internal import Args, CLICommand, GlobalOptions, Options
from cmk.ruleset_matcher.matcher import BundledHostRulesetMatcher
from cmk.server_side_calls_backend import load_secrets_file
from cmk.utils import config_warnings, ip_lookup, timeperiod
from cmk.utils.log import console

# .
#   .--nagios-config-------------------------------------------------------.
#   |                     _                                  __ _          |
#   |   _ __   __ _  __ _(_) ___  ___        ___ ___  _ __  / _(_) __ _    |
#   |  | '_ \ / _` |/ _` | |/ _ \/ __|_____ / __/ _ \| '_ \| |_| |/ _` |   |
#   |  | | | | (_| | (_| | | (_) \__ \_____| (_| (_) | | | |  _| | (_| |   |
#   |  |_| |_|\__,_|\__, |_|\___/|___/      \___\___/|_| |_|_| |_|\__, |   |
#   |               |___/                                         |___/    |
#   '----------------------------------------------------------------------'


def _mode_dump_nagios_config(
    app: CheckmkBaseApp, global_options: GlobalOptions, _options: Options, raw_host_names: Args
) -> int:
    set_fake_dns(global_options.fake_dns)
    args = host_addresses(raw_host_names)

    from cmk.base.core.nagios import create_config
    from cmk.base.core.nagios._create_config import NagiosCoreConfig

    plugins = load_checks()
    loading_result = config.load()
    loaded_config = loading_result.loaded_config
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    label_manager = loading_result.config_cache.label_manager
    config_cache = loading_result.config_cache
    core_objects_config = config.CoreObjectsConfig(loaded_config, ruleset_matcher, label_manager)
    hosts_config = loading_result.hosts_config

    ip_lookup_config = config_cache.ip_lookup_config()

    hostnames = args if args else None

    if loaded_config.host_notification_periods:
        config_warnings.warn(
            "host_notification_periods is not longer supported. Please use extra_host_conf['notification_period'] instead."
        )

    if loaded_config.service_notification_periods:
        config_warnings.warn(
            "service_notification_periods is not longer supported. Please use extra_service_conf['notification_period'] instead."
        )

    if hostnames is None:
        hostnames = sorted(
            {
                hn
                for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
                if config_cache.is_active(hn) and config_cache.is_online(hn)
            }
        )
    else:
        hostnames = sorted(hostnames)

    final_service_name_config = make_final_service_name_config(loaded_config, ruleset_matcher)
    service_name_config = config_cache.make_passive_service_name_config(final_service_name_config)
    _notify_host_files = create_config(
        outfile=sys.stdout,
        hosts_config=hosts_config,
        host_tags=loading_result.host_tags,
        config_cache=config_cache,
        core_objects_config=core_objects_config,
        nagios_core_config=NagiosCoreConfig(
            delay_precompile=loaded_config.delay_precompile,
            host_template=loaded_config.host_template,
            cluster_template=loaded_config.cluster_template,
            pingonly_template=loaded_config.pingonly_template,
            active_service_template=loaded_config.active_service_template,
            passive_service_template_perf=loaded_config.passive_service_template_perf,
            inventory_check_template=loaded_config.inventory_check_template,
            service_dependency_template=loaded_config.service_dependency_template,
            generate_hostconf=loaded_config.generate_hostconf,
            generate_dummy_commands=loaded_config.generate_dummy_commands,
            dummy_check_commandline=loaded_config.dummy_check_commandline,
            default_host_group=loaded_config.default_host_group,
            extra_nagios_conf=loaded_config.extra_nagios_conf,
            contacts=loaded_config.contacts,
            define_contactgroups=loaded_config.define_contactgroups,
            define_hostgroups=loaded_config.define_hostgroups,
            define_servicegroups=loaded_config.define_servicegroups,
            contactgroup_members=loaded_config.contactgroup_members,
            simulation_mode=loaded_config.simulation_mode,
        ),
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
        licensing_handler=app.licensing_handler_factory(),
        passwords=load_secrets_file(cmk.utils.password_store.pending_secrets_path_site()),
        get_ip_stack_config=ip_lookup_config.ip_stack_config,
        default_address_family=ip_lookup_config.default_address_family,
        ip_address_of=ip_lookup.ConfiguredIPLookup(
            forced_ip_lookup() or ip_lookup.make_lookup_ip_address(ip_lookup_config),
            allow_empty=hosts_config.clusters,
            error_handler=config.handle_ip_lookup_failure,
        ),
        service_depends_on=config.ServiceDependsOn(
            tag_list=loading_result.host_tags.tag_list,
            service_dependencies=loading_result.loaded_config.service_dependencies,
        ),
        timeperiods=timeperiod.get_all_timeperiods(loaded_config.timeperiods),
        get_relay_id=lambda host_name: config.get_relay_id(label_manager.labels_of_host(host_name)),
    )
    return 0


cli_command_nagios_config = CLICommand(
    long_option="nagios-config",
    short_option="N",
    handler_function=_mode_dump_nagios_config,
    argument=True,
    argument_descr="HOST1 HOST2...",
    argument_optional=True,
    short_help="Output Nagios configuration",
    long_help=[
        (
            "Outputs the Nagios configuration. You may optionally add a list "
            "of hosts. In that case the configuration is generated only for "
            "that hosts (useful for debugging)."
        ),
    ],
)


# .
#   .--update--------------------------------------------------------------.
#   |                                   _       _                          |
#   |                   _   _ _ __   __| | __ _| |_ ___                    |
#   |                  | | | | '_ \ / _` |/ _` | __/ _ \                   |
#   |                  | |_| | |_) | (_| | (_| | ||  __/                   |
#   |                   \__,_| .__/ \__,_|\__,_|\__\___|                   |
#   |                        |_|                                           |
#   '----------------------------------------------------------------------'


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


def _mode_update(
    app: CheckmkBaseApp, global_options: GlobalOptions, _options: Options, _args: Args
) -> int:
    set_fake_dns(global_options.fake_dns)
    plugins = load_checks()
    loading_result = config.load()
    loaded_config = loading_result.loaded_config
    raw_config = {f.name: getattr(loaded_config, f.name) for f in fields(loaded_config)}
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    label_manager = loading_result.config_cache.label_manager
    core_objects_config = config.CoreObjectsConfig(loaded_config, ruleset_matcher, label_manager)
    hosts_config = loading_result.hosts_config

    ip_lookup_config = loading_result.config_cache.ip_lookup_config()
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        forced_ip_lookup() or ip_lookup.make_lookup_ip_address(ip_lookup_config),
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
        with activation_lock(
            main_mk_file=cmk.utils.paths.default_config_dir / "main.mk",
            mode=loaded_config.restart_locking,
        ):
            core_interface.do_create_config(
                core=app.create_core(
                    app.edition,
                    ruleset_matcher,
                    label_manager,
                    loaded_config,
                    make_plugin_store(plugins),
                    loading_result.config_cache,
                    plugins,
                ),
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
                ip_address_of_mgmt=forced_ip_lookup()
                or ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config),
                hosts_to_update=None,
                service_depends_on=config.ServiceDependsOn(
                    tag_list=loading_result.host_tags.tag_list,
                    service_dependencies=loading_result.loaded_config.service_dependencies,
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
                checker_config_writer=make_packed_config_writer(
                    raw_config,
                    hosts_config,
                    is_online=loading_result.config_cache.is_online,
                    is_active=loading_result.config_cache.is_active,
                ),
                licensing_handler_factory=app.licensing_handler_factory,
            )
    except Exception as e:
        console.error(f"Configuration Error: {e}", file=sys.stderr)
        if cmk.ccc.debug.enabled():
            raise
        sys.exit(1)

    for warning in ip_address_of.error_handler.format_errors():
        console.warning(tty.format_warning(f"\n{warning}"))
    return 0


cli_command_update = CLICommand(
    long_option="update",
    short_option="U",
    handler_function=_mode_update,
    short_help="Create core config",
    long_help=[
        (
            "Updates the core configuration based on the current Checkmk "
            "configuration. When using the Nagios core, the precompiled host "
            "checks are created and the nagios configuration is updated. "
            "When using the CheckMK Micro Core, the core configuration is created "
            "and the configuration for the Core helper processes is being created."
        ),
    ],
)


# .
#   .--restart-------------------------------------------------------------.
#   |                                 _             _                      |
#   |                   _ __ ___  ___| |_ __ _ _ __| |_                    |
#   |                  | '__/ _ \/ __| __/ _` | '__| __|                   |
#   |                  | | |  __/\__ \ || (_| | |  | |_                    |
#   |                  |_|  \___||___/\__\__,_|_|   \__|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _mode_restart(
    app: CheckmkBaseApp, global_options: GlobalOptions, _options: Options, raw_host_names: Args
) -> int:
    set_fake_dns(global_options.fake_dns)
    args = host_addresses(raw_host_names)
    plugins = load_checks()
    loading_result = config.load()
    loaded_config = loading_result.loaded_config
    raw_config = {f.name: getattr(loaded_config, f.name) for f in fields(loaded_config)}
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    label_manager = loading_result.config_cache.label_manager
    core_objects_config = config.CoreObjectsConfig(loaded_config, ruleset_matcher, label_manager)
    hosts_config = loading_result.hosts_config

    ip_lookup_config = loading_result.config_cache.ip_lookup_config()

    ip_address_of = ip_lookup.ConfiguredIPLookup(
        forced_ip_lookup() or ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=hosts_config.clusters,
        error_handler=ip_lookup.CollectFailedHosts(),
    )
    ip_address_of_mgmt = forced_ip_lookup() or ip_lookup.make_lookup_mgmt_board_ip_address(
        ip_lookup_config
    )
    final_service_name_config = make_final_service_name_config(loaded_config, ruleset_matcher)
    passive_service_name_config = loading_result.config_cache.make_passive_service_name_config(
        final_service_name_config
    )

    core_interface.do_restart(
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
        app.create_core(
            app.edition,
            ruleset_matcher,
            label_manager,
            loaded_config,
            make_plugin_store(plugins),
            loading_result.config_cache,
            plugins,
        ),
        plugins,
        hosts_to_update=set(args) if args else None,
        locking_mode=loaded_config.restart_locking,
        service_depends_on=config.ServiceDependsOn(
            tag_list=loading_result.host_tags.tag_list,
            service_dependencies=loaded_config.service_dependencies,
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
        checker_config_writer=make_packed_config_writer(
            raw_config,
            hosts_config,
            is_online=loading_result.config_cache.is_online,
            is_active=loading_result.config_cache.is_active,
        ),
        licensing_handler_factory=app.licensing_handler_factory,
    )
    for warning in ip_address_of.error_handler.format_errors():
        console.warning(tty.format_warning(f"\n{warning}"))
    return 0


cli_command_restart = CLICommand(
    long_option="restart",
    short_option="R",
    handler_function=_mode_restart,
    argument=True,
    argument_descr="[HostA, HostB]",
    argument_optional=True,
    short_help="Create core config + core restart",
    long_help=[
        (
            "You may add host names as additional arguments. This enables the incremental "
            "activate mechanism, only compiling these host names and using cached data for all "
            "other hosts. Only supported with Checkmk Micro Core."
        )
    ],
)


# .
#   .--reload--------------------------------------------------------------.
#   |                             _                 _                      |
#   |                    _ __ ___| | ___   __ _  __| |                     |
#   |                   | '__/ _ \ |/ _ \ / _` |/ _` |                     |
#   |                   | | |  __/ | (_) | (_| | (_| |                     |
#   |                   |_|  \___|_|\___/ \__,_|\__,_|                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _mode_reload(
    app: CheckmkBaseApp, global_options: GlobalOptions, _options: Options, raw_host_names: Args
) -> int:
    set_fake_dns(global_options.fake_dns)
    args = host_addresses(raw_host_names)
    plugins = load_checks()
    loading_result = config.load()
    loaded_config = loading_result.loaded_config
    raw_config = {f.name: getattr(loaded_config, f.name) for f in fields(loaded_config)}
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    label_manager = loading_result.config_cache.label_manager
    core_objects_config = config.CoreObjectsConfig(loaded_config, ruleset_matcher, label_manager)
    hosts_config = loading_result.hosts_config

    ip_lookup_config = loading_result.config_cache.ip_lookup_config()

    ip_address_of = ip_lookup.ConfiguredIPLookup(
        forced_ip_lookup() or ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=hosts_config.clusters,
        error_handler=ip_lookup.CollectFailedHosts(),
    )
    ip_address_of_mgmt = forced_ip_lookup() or ip_lookup.make_lookup_mgmt_board_ip_address(
        ip_lookup_config
    )
    final_service_name_config = make_final_service_name_config(loaded_config, ruleset_matcher)
    passive_service_name_config = loading_result.config_cache.make_passive_service_name_config(
        final_service_name_config
    )

    core_interface.do_reload(
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
        app.create_core(
            app.edition,
            ruleset_matcher,
            label_manager,
            loaded_config,
            make_plugin_store(plugins),
            loading_result.config_cache,
            plugins,
        ),
        plugins,
        hosts_to_update=set(args) if args else None,
        locking_mode=loaded_config.restart_locking,
        service_depends_on=config.ServiceDependsOn(
            tag_list=loading_result.host_tags.tag_list,
            service_dependencies=loaded_config.service_dependencies,
        ),
        duplicates=sorted(
            hosts_config.duplicates(
                lambda hn: (
                    loading_result.config_cache.is_active(hn)
                    and loading_result.config_cache.is_online(hn)
                )
            ),
        ),
        notify_relay=_make_configured_notify_relay(bool(loaded_config.relays)),
        checker_config_writer=make_packed_config_writer(
            raw_config,
            hosts_config,
            is_online=loading_result.config_cache.is_online,
            is_active=loading_result.config_cache.is_active,
        ),
        licensing_handler_factory=app.licensing_handler_factory,
    )
    for warning in ip_address_of.error_handler.format_errors():
        console.warning(tty.format_warning(f"\n{warning}"))
    return 0


cli_command_reload = CLICommand(
    long_option="reload",
    short_option="O",
    handler_function=_mode_reload,
    argument=True,
    argument_descr="[HostA, HostB]",
    argument_optional=True,
    short_help="Create core config + core reload",
    long_help=[
        (
            "You may add host names as additional arguments. This enables the incremental "
            "activate mechanism, only compiling these host names and using cached data for all "
            "other hosts. Only supported with Checkmk Micro Core."
        )
    ],
)
