#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The site maintenance commands: --flush, --update-dns-cache and --cleanup-piggyback."""

import itertools
import os
from pathlib import Path

import cmk.utils.paths
from cmk.base import config
from cmk.base.configlib.servicename import make_final_service_name_config
from cmk.base.modes.check_mk import forced_ip_lookup, host_addresses, load_checks, set_fake_dns
from cmk.ccc import tty
from cmk.checkengine.discovery import remove_autochecks_of_host
from cmk.cli.engine.modes import write_stdout
from cmk.cli.internal import Args, CLICommand, GlobalOptions, Options
from cmk.inventory.paths import Paths as InventoryPaths
from cmk.piggyback import backend as piggyback_backend
from cmk.utils import ip_lookup

# .
#   .--update-dns-cache----------------------------------------------------.
#   |                        _            _                                |
#   |        _   _ _ __   __| |        __| |_ __  ___        ___           |
#   |       | | | | '_ \ / _` | _____ / _` | '_ \/ __|_____ / __|          |
#   |       | |_| | |_) | (_| ||_____| (_| | | | \__ \_____| (__ _         |
#   |        \__,_| .__/ \__,_(_)     \__,_|_| |_|___/      \___(_)        |
#   |             |_|                                                      |
#   '----------------------------------------------------------------------'


def _mode_update_dns_cache(
    _omd_root: Path, global_options: GlobalOptions, _options: Options, _args: Args
) -> int:
    set_fake_dns(global_options.fake_dns)
    loading_result = config.load()
    config_cache = loading_result.config_cache
    hosts_config = loading_result.hosts_config
    ip_lookup_config = config_cache.ip_lookup_config()
    ip_lookup.update_dns_cache(
        hosts=(
            hn
            for hn in set(hosts_config.hosts).union(hosts_config.clusters)
            if config_cache.is_active(hn) and config_cache.is_online(hn)
        ),
        get_ip_stack_config=ip_lookup_config.ip_stack_config,
        lookup_ip_address=(
            forced_ip_lookup()  # this makes little sense.
            or ip_lookup.make_lookup_ip_address(ip_lookup_config)
        ),
    )
    return 0


cli_command_update_dns_cache = CLICommand(
    long_option="update-dns-cache",
    handler_function=_mode_update_dns_cache,
    short_help="Update IP address lookup cache",
)


# .
#   .--clean.-piggyb.------------------------------------------------------.
#   |        _                               _                   _         |
#   |    ___| | ___  __ _ _ __         _ __ (_) __ _  __ _ _   _| |__      |
#   |   / __| |/ _ \/ _` | '_ \  _____| '_ \| |/ _` |/ _` | | | | '_ \     |
#   |  | (__| |  __/ (_| | | | ||_____| |_) | | (_| | (_| | |_| | |_) |    |
#   |   \___|_|\___|\__,_|_| |_(_)    | .__/|_|\__, |\__, |\__, |_.__(_)   |
#   |                                 |_|      |___/ |___/ |___/           |
#   '----------------------------------------------------------------------'


def _mode_cleanup_piggyback(
    _omd_root: Path, _global_options: GlobalOptions, _options: Options, _args: Args
) -> int:
    loaded_config = config.load().loaded_config
    piggyback_backend.cleanup_piggyback_files(
        loaded_config.piggyback_max_cachefile_age,
        (r["value"] for r in loaded_config.piggybacked_host_files),
        cmk.utils.paths.omd_root,
    )
    return 0


cli_command_cleanup_piggyback = CLICommand(
    long_option="cleanup-piggyback",
    handler_function=_mode_cleanup_piggyback,
    short_help="Cleanup outdated piggyback files",
)


# .
#   .--flush---------------------------------------------------------------.
#   |                         __ _           _                             |
#   |                        / _| |_   _ ___| |__                          |
#   |                       | |_| | | | / __| '_ \                         |
#   |                       |  _| | |_| \__ \ | | |                        |
#   |                       |_| |_|\__,_|___/_| |_|                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _mode_flush(
    _omd_root: Path, _global_options: GlobalOptions, _options: Options, args: Args
) -> int:
    hosts = host_addresses(args)
    plugins = load_checks()
    loading_result = config.load()
    loaded_config = loading_result.loaded_config
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    hosts_config = loading_result.hosts_config
    config_cache = loading_result.config_cache

    service_name_config = config_cache.make_passive_service_name_config(
        make_final_service_name_config(loaded_config, ruleset_matcher)
    )

    effective_host_callback = config.AutochecksConfigurer(
        config_cache, plugins.check_plugins, service_name_config
    ).effective_host

    if not hosts:
        hosts = sorted(
            {
                hn
                for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
                if config_cache.is_active(hn) and config_cache.is_online(hn)
            }
        )

    for host in hosts:
        write_stdout("%-20s: " % host)
        flushed = False

        # counters
        try:
            (cmk.utils.paths.counters_dir / host).unlink()
            write_stdout(tty.bold + tty.blue + " counters")
            flushed = True
        except OSError:
            pass

        # cache files
        d = 0
        cache_dir = cmk.utils.paths.tcp_cache_dir
        if os.path.exists(cache_dir):
            for f in os.listdir(cache_dir):
                if f == host or f.startswith(host + "."):
                    try:
                        (cache_dir / f).unlink()
                        d += 1
                        flushed = True
                    except OSError:
                        pass
            if d == 1:
                write_stdout(tty.bold + tty.green + " cache")
            elif d > 1:
                write_stdout(tty.bold + tty.green + " cache(%d)" % d)

        # piggy files from this as source host
        d = piggyback_backend.remove_source_status_file(host, cmk.utils.paths.omd_root)
        if d:
            write_stdout(tty.bold + tty.magenta + " piggyback(1)")

        # logfiles
        log_dir = cmk.utils.paths.logwatch_dir / host
        if log_dir.exists():
            d = 0
            for f in os.listdir(str(log_dir)):
                if f not in [".", ".."]:
                    try:
                        (log_dir / f).unlink()
                        d += 1
                        flushed = True
                    except OSError:
                        pass
            if d > 0:
                write_stdout(tty.bold + tty.magenta + " logfiles(%d)" % d)

        # autochecks
        count = sum(
            remove_autochecks_of_host(
                node, host, effective_host_callback, cmk.utils.paths.autochecks_dir
            )
            for node in (hosts_config.clusters.get(host) or [host])
        )
        # config_cache.remove_autochecks(host)
        if count:
            flushed = True
            write_stdout(tty.bold + tty.cyan + " autochecks(%d)" % count)

        # inventory
        tree_path = InventoryPaths(cmk.utils.paths.omd_root).inventory_tree(host)
        if tree_path.path.exists() or tree_path.legacy.exists():
            tree_path.path.unlink(missing_ok=True)
            tree_path.legacy.unlink(missing_ok=True)
            write_stdout(tty.bold + tty.yellow + " inventory")

        if not flushed:
            write_stdout("(nothing)")

        write_stdout(tty.normal + "\n")
    return 0


cli_command_flush = CLICommand(
    long_option="flush",
    handler_function=_mode_flush,
    argument=True,
    argument_descr="HOST1 HOST2...",
    argument_optional=True,
    short_help="Flush all data of some or all hosts",
    long_help=[
        (
            "Deletes all runtime data belonging to a host. This includes "
            "the inventorized checks, the state of performance counters, "
            "cached agent output, and logfiles. Precompiled host checks "
            "are not deleted."
        ),
    ],
)
