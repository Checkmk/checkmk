#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
import sys
from collections.abc import Iterable
from functools import partial
from pathlib import Path

import cmk.ccc.cleanup
import cmk.utils.paths
from cmk.base import config
from cmk.ccc import tty
from cmk.ccc.exceptions import MKBailOut, MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.helper_interface import SourceType
from cmk.checkengine.snmp_backend_builder import BackendError, make_backend
from cmk.checkengine.snmplib import (
    get_single_oid,
    OID,
    oids_to_walk,
    SNMPBackend,
    SNMPContext,
    SNMPHostConfig,
    walk_all_contexts_for_export,
)
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Handler as CLIHandler
from cmk.plugins.checkmk.cli.snmp import (
    cli_command_snmpget,
    cli_command_snmptranslate,
    cli_command_snmpwalk,
    GetRequest,
    make_local_mibs_dir,
    WalkRequest,
)
from cmk.utils import ip_lookup
from cmk.utils.log import console


def _mode_snmptranslate(
    _omd_root: Path, _global_options: CLIGlobalOptions, args: CLIArgs
) -> CLIExitCode:
    walk_filename = args[0]
    if not walk_filename:
        raise MKGeneralException("Please provide the name of a SNMP walk file")

    walk_path = cmk.utils.paths.snmpwalks_dir / walk_filename
    if not walk_path.exists():
        raise MKGeneralException("The walk '%s' does not exist" % walk_path)

    command = [
        "snmptranslate",
        "-m",
        "ALL",
        f"-M+{make_local_mibs_dir(cmk.utils.paths.omd_root)}",
        "-",
    ]
    with walk_path.open("rb") as walk_file:
        walk = walk_file.read().split(b"\n")
    while walk[-1] == b"":
        del walk[-1]

    # to be compatible to previous version of this script, we do not feed
    # to original walk to snmptranslate (which would be possible) but a
    # version without values. The output should look like:
    # "[full oid] [value] --> [translated oid]"
    walk_without_values = b"\n".join(line.split(b" ", 1)[0] for line in walk)

    completed_process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        check=False,
        input=walk_without_values,
    )

    data_translated = completed_process.stdout.split(b"\n")
    # remove last empty line (some tools add a '\n' at the end of the file, others not)
    if data_translated[-1] == b"":
        del data_translated[-1]

    if len(walk) != len(data_translated):
        raise MKGeneralException("call to snmptranslate returned a ambiguous result")

    for element_input, element_translated in zip(walk, data_translated):
        sys.stdout.buffer.write(element_input.strip())
        sys.stdout.buffer.write(b" --> ")
        sys.stdout.buffer.write(element_translated.strip())
        sys.stdout.buffer.write(b"\n")
    return CLIExitCode.SUCCESS


def _run_snmptranslate(context: CLIContext, _request: None, args: CLIArgs) -> CLIExitCode:
    try:
        return _mode_snmptranslate(context.omd_root, context.global_options, args)
    except MKGeneralException as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return CLIExitCode.UNKNOWN


_SNMPWalkOptions = dict[str, list[OID]]


def _execute_walks_for_dump(
    oids: list[OID], *, backend: SNMPBackend, debug: bool
) -> Iterable[list[tuple[OID, str]]]:
    for oid in oids:
        console.verbose(f'Walk on "{oid}"...')
        yield walk_all_contexts_for_export(
            oid, backend=backend, on_error=partial(_report_walk_error, debug=debug)
        )


def _report_walk_error(oid: OID, context: SNMPContext, e: Exception, *, debug: bool) -> None:
    where = f"context '{context}'" if context else "default context"
    console.error(f"Error walking OID '{oid}', {where}: {e}", file=sys.stderr)
    if debug:
        raise e


def _do_snmpwalk_on(
    options: _SNMPWalkOptions, filename: Path, *, backend: SNMPBackend, debug: bool
) -> None:
    console.verbose(f"{backend.hostname}:")

    oids = oids_to_walk(options)

    with filename.open("w", encoding="utf-8") as file:
        for rows in _execute_walks_for_dump(oids, backend=backend, debug=debug):
            for oid, value in rows:
                file.write(f"{oid} {value}\n")
            console.verbose(f"{len(rows)} variables.")

    console.verbose(f"Wrote fetched data to {tty.bold}{filename}{tty.normal}.")


def _do_snmpwalk(options: _SNMPWalkOptions, *, backend: SNMPBackend, debug: bool) -> None:
    cmk.utils.paths.snmpwalks_dir.mkdir(parents=True, exist_ok=True)

    # TODO: What about SNMP management boards?
    try:
        _do_snmpwalk_on(
            options,
            cmk.utils.paths.snmpwalks_dir / backend.hostname,
            backend=backend,
            debug=debug,
        )
    except Exception as e:
        console.error(f"Error walking {backend.hostname}: {e}", file=sys.stderr)
        if debug:
            raise
    cmk.ccc.cleanup.cleanup_globals()


def _make_backend(snmp_config: SNMPHostConfig) -> SNMPBackend:
    """Create the configured backend, reporting an unavailable one as user error"""
    try:
        return make_backend(snmp_config)
    except BackendError as exc:
        raise MKGeneralException(str(exc)) from exc


def _mode_snmpwalk(
    _omd_root: Path, global_options: CLIGlobalOptions, request: WalkRequest, hostnames: CLIArgs
) -> CLIExitCode:
    if request.oids and request.extra_oids:
        raise MKGeneralException("You cannot specify --oid and --extraoid at the same time.")

    walk_options: _SNMPWalkOptions = {}
    if request.oids:
        walk_options["oids"] = list(request.oids)
    if request.extra_oids:
        walk_options["extraoids"] = list(request.extra_oids)

    if not hostnames:
        raise MKBailOut("Please specify host names to walk on.")

    config_cache = config.load(validate_hosts=True, debug=global_options.debug).config_cache
    ip_lookup_config = config_cache.ip_lookup_config(fake_dns=request.fake_dns)
    ip_address_of = ip_lookup.make_lookup_ip_address(ip_lookup_config)

    for hostname in (HostName(hn) for hn in hostnames):
        if ip_lookup_config.ip_stack_config(hostname) is ip_lookup.IPStackConfig.NO_IP:
            raise MKGeneralException(f"Host is configured as No-IP host: {hostname}")

        ip_family = ip_lookup_config.default_address_family(hostname)
        ipaddress = ip_address_of(hostname, ip_family)
        if not ipaddress:
            raise MKGeneralException("Failed to gather IP address of %s" % hostname)

        snmp_config = config_cache.make_snmp_config(
            hostname, ip_family, ipaddress, SourceType.HOST, backend_override=request.backend
        )
        _do_snmpwalk(
            walk_options,
            backend=_make_backend(snmp_config),
            debug=global_options.debug,
        )
    return CLIExitCode.SUCCESS


def _run_snmpwalk(context: CLIContext, request: WalkRequest, args: CLIArgs) -> CLIExitCode:
    try:
        return _mode_snmpwalk(context.omd_root, context.global_options, request, args)
    except (MKBailOut, MKGeneralException) as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return CLIExitCode.UNKNOWN


def _mode_snmpget(
    _omd_root: Path, global_options: CLIGlobalOptions, request: GetRequest, args: CLIArgs
) -> CLIExitCode:
    if not args:
        raise MKBailOut("You need to specify an OID.")

    loading_result = config.load(validate_hosts=True, debug=global_options.debug)
    config_cache = loading_result.config_cache
    hosts_config = loading_result.hosts_config

    ip_lookup_config = config_cache.ip_lookup_config(fake_dns=request.fake_dns)
    ip_address_of = ip_lookup.make_lookup_ip_address(ip_lookup_config)
    oid, *hostnames = args

    if not hostnames:
        hostnames.extend(
            host
            for host in frozenset(hosts_config.hosts)
            if config_cache.is_active(host)
            and config_cache.is_online(host)
            and config_cache.computed_datasources(host).is_snmp
        )

    assert hostnames
    for hostname in (HostName(hn) for hn in hostnames):
        if ip_lookup_config.ip_stack_config(hostname) is ip_lookup.IPStackConfig.NO_IP:
            raise MKGeneralException(f"Host is configured as No-IP host: {hostname}")

        ip_family = ip_lookup_config.default_address_family(hostname)
        ipaddress = ip_address_of(hostname, ip_family)
        if not ipaddress:
            raise MKGeneralException("Failed to gather IP address of %s" % hostname)

        snmp_config = config_cache.make_snmp_config(
            hostname,
            ip_family,
            ipaddress,
            SourceType.HOST,
            backend_override=request.backend,
        )
        backend = _make_backend(snmp_config)
        value = get_single_oid(
            oid, single_oid_cache={}, backend=backend, debug=global_options.debug
        )
        sys.stdout.write(f"{backend.hostname} ({backend.address}): {value!r}\n")
    return CLIExitCode.SUCCESS


def _run_snmpget(context: CLIContext, request: GetRequest, args: CLIArgs) -> CLIExitCode:
    try:
        return _mode_snmpget(context.omd_root, context.global_options, request, args)
    except (MKBailOut, MKGeneralException) as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return CLIExitCode.UNKNOWN


cli_handler_snmptranslate = CLIHandler(command=cli_command_snmptranslate, run=_run_snmptranslate)

cli_handler_snmpwalk = CLIHandler(command=cli_command_snmpwalk, run=_run_snmpwalk)

cli_handler_snmpget = CLIHandler(command=cli_command_snmpget, run=_run_snmpget)
