#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The SNMP commands: --snmptranslate, --snmpwalk and --snmpget."""

import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

import cmk.ccc.cleanup
import cmk.ccc.debug
import cmk.utils.paths
from cmk.base import config
from cmk.base.modes.check_mk import (
    forced_ip_lookup,
    parse_snmp_backend,
    set_fake_dns,
    SNMP_BACKEND_OPTION,
)
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
    SNMPHostConfig,
    walk_for_export,
)
from cmk.cli.engine.modes import option_strings
from cmk.cli.internal import Args, CLICommand, CLIOption, GlobalOptions, Options
from cmk.utils import ip_lookup
from cmk.utils.log import console

# .
#   .--snmptranslate-------------------------------------------------------.
#   |                            _                       _       _         |
#   |  ___ _ __  _ __ ___  _ __ | |_ _ __ __ _ _ __  ___| | __ _| |_ ___   |
#   | / __| '_ \| '_ ` _ \| '_ \| __| '__/ _` | '_ \/ __| |/ _` | __/ _ \  |
#   | \__ \ | | | | | | | | |_) | |_| | | (_| | | | \__ \ | (_| | ||  __/  |
#   | |___/_| |_|_| |_| |_| .__/ \__|_|  \__,_|_| |_|___/_|\__,_|\__\___|  |
#   |                     |_|                                              |
#   '----------------------------------------------------------------------'


def _make_local_mibs_dir(omd_root: Path) -> Path:
    # This must be kept in sync with cmk.ec.create_paths(...).local_mibs_dir
    return omd_root / "local/share/snmp/mibs"


def _mode_snmptranslate(
    _omd_root: Path, _global_options: GlobalOptions, _options: Options, args: Args
) -> int:
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
        f"-M+{_make_local_mibs_dir(cmk.utils.paths.omd_root)}",
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
    return 0


cli_command_snmptranslate = CLICommand(
    long_option="snmptranslate",
    handler_function=_mode_snmptranslate,
    argument=True,
    argument_descr="HOST",
    short_help="Do snmptranslate on walk",
    long_help=[
        (
            "Does not contact the host again, but reuses the hosts walk from the directory "
            f"{cmk.utils.paths.snmpwalks_dir}. You can add further MIBs to the directory "
            f"{_make_local_mibs_dir(cmk.utils.paths.omd_root)}."
        )
    ],
)


# .
#   .--snmpwalk------------------------------------------------------------.
#   |                                                   _ _                |
#   |            ___ _ __  _ __ ___  _ ____      ____ _| | | __            |
#   |           / __| '_ \| '_ ` _ \| '_ \ \ /\ / / _` | | |/ /            |
#   |           \__ \ | | | | | | | | |_) \ V  V / (_| | |   <             |
#   |           |___/_| |_|_| |_| |_| .__/ \_/\_/ \__,_|_|_|\_\            |
#   |                               |_|                                    |
#   '----------------------------------------------------------------------'

_SNMPWalkOptions = dict[str, list[OID]]


def _execute_walks_for_dump(
    oids: list[OID], *, backend: SNMPBackend
) -> Iterable[list[tuple[OID, str]]]:
    context_config = backend.config.snmpv3_contexts_of(None)
    for oid in oids:
        try:
            console.verbose(f'Walk on "{oid}"...')
            added_oids: set[OID] = set()
            rows: list[tuple[OID, str]] = []
            for context in context_config.contexts:
                for row_oid, value in walk_for_export(backend.walk(oid, context=context)):
                    if row_oid not in added_oids:
                        added_oids.add(row_oid)
                        rows.append((row_oid, value))
            yield rows
        except Exception as e:
            console.error(f"Error: {e}", file=sys.stderr)
            if cmk.ccc.debug.enabled():
                raise


def _do_snmpwalk_on(options: _SNMPWalkOptions, filename: Path, *, backend: SNMPBackend) -> None:
    console.verbose(f"{backend.hostname}:")

    oids = oids_to_walk(options)

    with filename.open("w", encoding="utf-8") as file:
        for rows in _execute_walks_for_dump(oids, backend=backend):
            for oid, value in rows:
                file.write(f"{oid} {value}\n")
            console.verbose(f"{len(rows)} variables.")

    console.verbose(f"Wrote fetched data to {tty.bold}{filename}{tty.normal}.")


def _do_snmpwalk(options: _SNMPWalkOptions, *, backend: SNMPBackend) -> None:
    cmk.utils.paths.snmpwalks_dir.mkdir(parents=True, exist_ok=True)

    # TODO: What about SNMP management boards?
    try:
        _do_snmpwalk_on(
            options,
            cmk.utils.paths.snmpwalks_dir / backend.hostname,
            backend=backend,
        )
    except Exception as e:
        console.error(f"Error walking {backend.hostname}: {e}", file=sys.stderr)
        if cmk.ccc.debug.enabled():
            raise
    cmk.ccc.cleanup.cleanup_globals()


def _make_backend(snmp_config: SNMPHostConfig) -> SNMPBackend:
    """Create the configured backend, reporting an unavailable one as user error"""
    try:
        return make_backend(snmp_config)
    except BackendError as exc:
        raise MKGeneralException(str(exc)) from exc


def _mode_snmpwalk(
    _omd_root: Path, global_options: GlobalOptions, options: Options, hostnames: Args
) -> int:
    set_fake_dns(global_options.fake_dns)
    oids = option_strings(options, "oid")
    extra_oids = option_strings(options, "extraoid")
    if oids and extra_oids:
        raise MKGeneralException("You cannot specify --oid and --extraoid at the same time.")

    walk_options: _SNMPWalkOptions = {}
    if oids:
        walk_options["oids"] = list(oids)
    if extra_oids:
        walk_options["extraoids"] = list(extra_oids)

    try:
        snmp_backend_override = parse_snmp_backend(options.get("snmp-backend"))
    except ValueError as exc:
        raise MKBailOut("Unknown SNMP backend") from exc

    if not hostnames:
        raise MKBailOut("Please specify host names to walk on.")

    config_cache = config.load().config_cache
    ip_lookup_config = config_cache.ip_lookup_config()
    ip_address_of = forced_ip_lookup() or ip_lookup.make_lookup_ip_address(ip_lookup_config)

    for hostname in (HostName(hn) for hn in hostnames):
        if ip_lookup_config.ip_stack_config(hostname) is ip_lookup.IPStackConfig.NO_IP:
            raise MKGeneralException(f"Host is configured as No-IP host: {hostname}")

        ip_family = ip_lookup_config.default_address_family(hostname)
        ipaddress = ip_address_of(hostname, ip_family)
        if not ipaddress:
            raise MKGeneralException("Failed to gather IP address of %s" % hostname)

        snmp_config = config_cache.make_snmp_config(
            hostname, ip_family, ipaddress, SourceType.HOST, backend_override=snmp_backend_override
        )
        _do_snmpwalk(
            walk_options,
            backend=_make_backend(snmp_config),
        )
    return 0


cli_command_snmpwalk = CLICommand(
    long_option="snmpwalk",
    handler_function=_mode_snmpwalk,
    argument=True,
    argument_descr="HOST1 HOST2...",
    argument_optional=True,
    sub_options=[
        SNMP_BACKEND_OPTION,
        CLIOption(
            long_option="extraoid",
            argument=True,
            argument_descr="A",
            repeat=True,
            short_help="Walk also on this OID, in addition to mib-2 and "
            "enterprises. You can specify this option multiple "
            "times.",
        ),
        CLIOption(
            long_option="oid",
            argument=True,
            argument_descr="A",
            repeat=True,
            short_help="Walk on this OID instead of mib-2 and enterprises. "
            "You can specify this option multiple times.",
        ),
    ],
    short_help="Do snmpwalk on one or more hosts",
    long_help=[
        "Does a complete snmpwalk for the specified hosts both "
        "on the standard MIB and the enterprises MIB and stores the "
        "result in the directory '%s'. Use the option --oid one or several "
        "times in order to specify alternative OIDs to walk. You need to "
        "specify numeric OIDs. If you want to keep the two standard OIDS "
        ".1.3.6.1.2.1 and .1.3.6.1.4.1 then use --extraoid for just adding "
        "additional OIDs to walk." % cmk.utils.paths.snmpwalks_dir,
    ],
)


# .
#   .--snmpget-------------------------------------------------------------.
#   |                                                   _                  |
#   |              ___ _ __  _ __ ___  _ __   __ _  ___| |_                |
#   |             / __| '_ \| '_ ` _ \| '_ \ / _` |/ _ \ __|               |
#   |             \__ \ | | | | | | | | |_) | (_| |  __/ |_                |
#   |             |___/_| |_|_| |_| |_| .__/ \__, |\___|\__|               |
#   |                                 |_|    |___/                         |
#   '----------------------------------------------------------------------'


def _mode_snmpget(
    _omd_root: Path, global_options: GlobalOptions, options: Options, args: Args
) -> int:
    set_fake_dns(global_options.fake_dns)
    if not args:
        raise MKBailOut("You need to specify an OID.")
    try:
        snmp_backend_override = parse_snmp_backend(options.get("snmp-backend"))
    except ValueError as exc:
        raise MKBailOut("Unknown SNMP backend") from exc

    loading_result = config.load()
    config_cache = loading_result.config_cache
    hosts_config = loading_result.hosts_config

    ip_lookup_config = config_cache.ip_lookup_config()
    ip_address_of = forced_ip_lookup() or ip_lookup.make_lookup_ip_address(ip_lookup_config)
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
            backend_override=snmp_backend_override,
        )
        backend = _make_backend(snmp_config)
        value = get_single_oid(oid, single_oid_cache={}, backend=backend)
        sys.stdout.write(f"{backend.hostname} ({backend.address}): {value!r}\n")
    return 0


cli_command_snmpget = CLICommand(
    long_option="snmpget",
    handler_function=_mode_snmpget,
    argument=True,
    argument_descr="OID [HOST1 HOST2...]",
    argument_optional=True,
    sub_options=[SNMP_BACKEND_OPTION],
    short_help="Fetch single OID from one or multiple hosts",
    long_help=[
        (
            "Does a snmpget on the given OID on one or multiple hosts. In case "
            "no host is given, all known SNMP hosts are queried."
        )
    ],
)
