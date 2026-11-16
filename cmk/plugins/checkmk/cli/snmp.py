#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The SNMP commands: --snmptranslate, --snmpwalk and --snmpget."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import cmk.utils.paths
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.snmplib import (
    OID,
    SNMPBackendEnum,
)
from cmk.cli.internal import Argument as CLIArgument
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Values as CLIValues

from .options import FAKE_DNS_VALUE, SNMP_BACKEND_VALUE


def make_local_mibs_dir(omd_root: Path) -> Path:
    # This must be kept in sync with cmk.ec.create_paths(...).local_mibs_dir
    return omd_root / "local/share/snmp/mibs"


def _translate_request(options: CLIReader) -> str | None:
    return options.argument(CLIArgument(placeholder="WALK", parse=str))


cli_command_snmptranslate = CLICommand(
    name="snmptranslate",
    handler="cmk.plugins.checkmk.cli.handlers.snmp:cli_handler_snmptranslate",
    long="snmptranslate",
    request=_translate_request,
    help="Do snmptranslate on walk",
    description=[
        (
            "Does not contact the host again, but reuses the hosts walk from the directory "
            f"{cmk.utils.paths.snmpwalks_dir}. You can add further MIBs to the directory "
            f"{make_local_mibs_dir(cmk.utils.paths.omd_root)}."
        )
    ],
)


_EXTRA_OIDS_VALUES: Final = CLIValues(
    long="extraoid",
    placeholder="A",
    help="Walk also on this OID, in addition to mib-2 and "
    "enterprises. You can specify this option multiple "
    "times.",
    parse=OID,
)


_OIDS_VALUES: Final = CLIValues(
    long="oid",
    placeholder="A",
    help="Walk on this OID instead of mib-2 and enterprises. "
    "You can specify this option multiple times.",
    parse=OID,
)


@dataclass(frozen=True, kw_only=True)
class WalkRequest:
    backend: SNMPBackendEnum | None
    extra_oids: Sequence[OID]
    oids: Sequence[OID]
    fake_dns: HostAddress | None
    hosts: Sequence[HostName]


def _walk_request(options: CLIReader) -> WalkRequest:
    return WalkRequest(
        backend=options.value(SNMP_BACKEND_VALUE),
        extra_oids=options.values(_EXTRA_OIDS_VALUES),
        oids=options.values(_OIDS_VALUES),
        fake_dns=options.value(FAKE_DNS_VALUE),
        hosts=options.arguments(CLIArguments(placeholder="HOST1 HOST2...", parse=HostName)),
    )


cli_command_snmpwalk = CLICommand(
    name="snmpwalk",
    handler="cmk.plugins.checkmk.cli.handlers.snmp:cli_handler_snmpwalk",
    long="snmpwalk",
    request=_walk_request,
    help="Do snmpwalk on one or more hosts",
    description=[
        "Does a complete snmpwalk for the specified hosts both "
        "on the standard MIB and the enterprises MIB and stores the "
        "result in the directory '%s'. Use the option --oid one or several "
        "times in order to specify alternative OIDs to walk. You need to "
        "specify numeric OIDs. If you want to keep the two standard OIDS "
        ".1.3.6.1.2.1 and .1.3.6.1.4.1 then use --extraoid for just adding "
        "additional OIDs to walk." % cmk.utils.paths.snmpwalks_dir,
    ],
)


@dataclass(frozen=True, kw_only=True)
class GetRequest:
    backend: SNMPBackendEnum | None
    fake_dns: HostAddress | None
    oid: OID | None
    hosts: Sequence[HostName]


def _get_request(options: CLIReader) -> GetRequest:
    return GetRequest(
        backend=options.value(SNMP_BACKEND_VALUE),
        fake_dns=options.value(FAKE_DNS_VALUE),
        oid=options.argument(CLIArgument(placeholder="OID", parse=OID)),
        hosts=options.arguments(CLIArguments(placeholder="HOST1 HOST2...", parse=HostName)),
    )


cli_command_snmpget = CLICommand(
    name="snmpget",
    handler="cmk.plugins.checkmk.cli.handlers.snmp:cli_handler_snmpget",
    long="snmpget",
    request=_get_request,
    help="Fetch single OID from one or multiple hosts",
    description=[
        (
            "Does a snmpget on the given OID on one or multiple hosts. In case "
            "no host is given, all known SNMP hosts are queried."
        )
    ],
)
