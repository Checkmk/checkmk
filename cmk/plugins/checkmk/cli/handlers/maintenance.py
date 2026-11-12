#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
import os
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cmk.utils.paths
from cmk.base import config
from cmk.base.configlib.servicename import make_final_service_name_config
from cmk.ccc import tty
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress
from cmk.checkengine.discovery import remove_autochecks_of_host
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Handler as CLIHandler
from cmk.inventory.paths import InventoryPaths
from cmk.piggyback import backend as piggyback_backend
from cmk.plugins.checkmk.cli.maintenance import (
    cli_command_cleanup_piggyback,
    cli_command_flush,
    cli_command_update_dns_cache,
)
from cmk.plugins.checkmk.cli.output import write_stdout
from cmk.utils import ip_lookup

from .agent_based import load_checks


class _UpdateDNSCache(Protocol):
    def __call__(self, fake_dns: HostAddress | None, *, debug: bool) -> None: ...


def _update_dns_cache(fake_dns: HostAddress | None, *, debug: bool) -> None:
    loading_result = config.load(validate_hosts=True, debug=debug)
    config_cache = loading_result.config_cache
    hosts_config = loading_result.hosts_config
    ip_lookup_config = config_cache.ip_lookup_config(fake_dns=fake_dns)
    ip_lookup.update_dns_cache(
        hosts=(
            hn
            for hn in set(hosts_config.hosts).union(hosts_config.clusters)
            if config_cache.is_active(hn) and config_cache.is_online(hn)
        ),
        get_ip_stack_config=ip_lookup_config.ip_stack_config,
        lookup_ip_address=(ip_lookup.make_lookup_ip_address(ip_lookup_config)),
        debug=debug,
    )


@dataclass(frozen=True, kw_only=True)
class _UpdateDNSCacheCommand:
    update_dns_cache: _UpdateDNSCache

    def run(self, context: CLIContext, fake_dns: HostAddress | None) -> CLIExitCode:
        try:
            self.update_dns_cache(fake_dns, debug=context.global_options.debug)
        except MKGeneralException as e:
            context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
            if context.global_options.debug:
                raise
            return CLIExitCode.UNKNOWN
        return CLIExitCode.SUCCESS


class _CleanupPiggyback(Protocol):
    def __call__(self, omd_root: Path, *, debug: bool) -> None: ...


def _cleanup_piggyback(omd_root: Path, *, debug: bool) -> None:
    loaded_config = config.load(validate_hosts=True, debug=debug).loaded_config
    piggyback_backend.cleanup_piggyback_files(
        now=time.time(),
        max_cache_file_age=loaded_config.piggyback_max_cachefile_age,
        all_configured_rule_values=(r["value"] for r in loaded_config.piggybacked_host_files),
        omd_root=omd_root,
    )


@dataclass(frozen=True, kw_only=True)
class _CleanupPiggybackCommand:
    cleanup_piggyback: _CleanupPiggyback

    def run(self, context: CLIContext, _request: None) -> CLIExitCode:
        try:
            self.cleanup_piggyback(context.omd_root, debug=context.global_options.debug)
        except MKGeneralException as e:
            context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
            if context.global_options.debug:
                raise
            return CLIExitCode.UNKNOWN
        return CLIExitCode.SUCCESS


class _Flush(Protocol):
    def __call__(self, hosts: Sequence[HostAddress], *, debug: bool) -> None: ...


def _flush(hosts: Sequence[HostAddress], *, debug: bool) -> None:
    plugins = load_checks(debug=debug)
    loading_result = config.load(validate_hosts=True, debug=debug)
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

    hosts = hosts or sorted(
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
                node,
                host,
                effective_host_callback,
                cmk.utils.paths.autochecks_dir,
                debug=debug,
            )
            for node in (hosts_config.clusters.get(host) or [host])
        )
        # config_cache.remove_autochecks(host)
        if count:
            flushed = True
            write_stdout(tty.bold + tty.cyan + " autochecks(%d)" % count)

        # inventory
        tree_path = InventoryPaths(cmk.utils.paths.omd_root).inventory_tree(host)
        if tree_path.exists():
            tree_path.unlink(missing_ok=True)
            write_stdout(tty.bold + tty.yellow + " inventory")

        if not flushed:
            write_stdout("(nothing)")

        write_stdout(tty.normal + "\n")


@dataclass(frozen=True, kw_only=True)
class _FlushCommand:
    flush: _Flush

    def run(self, context: CLIContext, hosts: Sequence[HostAddress]) -> CLIExitCode:
        try:
            self.flush(hosts, debug=context.global_options.debug)
        except MKGeneralException as e:
            context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
            if context.global_options.debug:
                raise
            return CLIExitCode.UNKNOWN
        return CLIExitCode.SUCCESS


cli_handler_update_dns_cache = CLIHandler(
    command=cli_command_update_dns_cache,
    run=_UpdateDNSCacheCommand(update_dns_cache=_update_dns_cache).run,
)

cli_handler_cleanup_piggyback = CLIHandler(
    command=cli_command_cleanup_piggyback,
    run=_CleanupPiggybackCommand(cleanup_piggyback=_cleanup_piggyback).run,
)

cli_handler_flush = CLIHandler(command=cli_command_flush, run=_FlushCommand(flush=_flush).run)
