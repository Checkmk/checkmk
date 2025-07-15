#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from collections.abc import Iterable
from typing import assert_never, Literal, TypeAlias

from cmk.ccc import tty
from cmk.ccc.exceptions import MKGeneralException, MKSNMPError, MKTimeout

from cmk.utils.sectionname import SectionName

from cmk.snmplib import OID, SNMPBackend, SNMPContext, SNMPRawValue, SNMPRowInfo, SNMPVersion

from ._utils import strip_snmp_value

__all__ = ["ClassicSNMPBackend"]

CommandType: TypeAlias = Literal["snmpget", "snmpgetnext", "snmpwalk"]


def _sanitize_tuple(tuple_: object) -> str:
    """For the snmp credentials, we don't want to print secrets...

    >>> _sanitize_tuple((1, 2, 3))
    "('***', '***', '***')"
    >>> _sanitize_tuple("foo")
    "<class 'str'>"
    >>> _sanitize_tuple(object())
    "<class 'object'>"
    """
    return (
        str(type(tuple_)) if not isinstance(tuple_, tuple) else repr(tuple("***" for _ in tuple_))
    )


class ClassicSNMPBackend(SNMPBackend):
    def get(self, /, oid: OID, *, context: SNMPContext) -> SNMPRawValue | None:
        if oid.endswith(".*"):
            oid_prefix = oid[:-2]
            commandtype: CommandType = "snmpgetnext"
        else:
            oid_prefix = oid
            commandtype = "snmpget"

        protospec = self._snmp_proto_spec()
        ipaddress = self.config.ipaddress or "0.0.0.0"
        if self.config.is_ipv6_primary:
            ipaddress = "[" + ipaddress + "]"
        portspec = self._snmp_port_spec()
        command = self._snmp_base_command(commandtype, context) + [
            "-On",
            "-OQ",
            "-Oe",
            "-Ot",
            f"{protospec}{ipaddress}{portspec}",
            oid_prefix,
        ]

        self._logger.debug(f"Running '{subprocess.list2cmdline(command)}'")

        with subprocess.Popen(
            command,
            close_fds=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        ) as snmp_process:
            assert snmp_process.stdout
            assert snmp_process.stderr
            line = snmp_process.stdout.readline().strip()
            error = snmp_process.stderr.read()

        if snmp_process.returncode:
            self._logger.debug(f"{tty.red}{tty.bold}ERROR: {tty.normal}SNMP error: {error.strip()}")
            return None

        if not line:
            self._logger.debug("Error in response to snmpget.")
            return None

        parts = line.split("=", 1)
        if len(parts) != 2:
            return None
        item = parts[0]
        value = parts[1].strip()
        self._logger.debug(f"SNMP answer: ==> [{value}]")
        if (
            value.startswith("No more variables")
            or value.startswith("End of MIB")
            or value.startswith("No Such Object available")
            or value.startswith("No Such Instance currently exists")
        ):
            return None

        # In case of .*, check if prefix is the one we are looking for
        if commandtype == "snmpgetnext" and not item.startswith(oid_prefix + "."):
            return None

        return strip_snmp_value(value)

    def walk(
        self,
        /,
        oid: str,
        *,
        context: SNMPContext,
        section_name: SectionName | None = None,
        table_base_oid: str | None = None,
    ) -> SNMPRowInfo:
        protospec = self._snmp_proto_spec()

        ipaddress = self.config.ipaddress or "0.0.0.0"
        if self.config.is_ipv6_primary:
            ipaddress = "[" + ipaddress + "]"

        portspec = self._snmp_port_spec()
        command = self._snmp_base_command("snmpwalk", context) + ["-Cc"]
        command += ["-OQ", "-OU", "-On", "-Ot", f"{protospec}{ipaddress}{portspec}", oid]
        self._logger.debug(f"Running '{subprocess.list2cmdline(command)}'")

        rowinfo: SNMPRowInfo = []
        with subprocess.Popen(
            command,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        ) as snmp_process:
            assert snmp_process.stdout
            assert snmp_process.stderr
            try:
                rowinfo = self._get_rowinfo_from_walk_output(snmp_process.stdout)
                error = snmp_process.stderr.read()
            except MKTimeout:
                snmp_process.kill()
                raise

        if snmp_process.returncode:
            self._logger.debug(f"{tty.red}{tty.bold}ERROR: {tty.normal}SNMP error: {error.strip()}")
            raise MKSNMPError(
                f"SNMP Error on {ipaddress}: {error.strip()} (Exit-Code: {snmp_process.returncode})"
            )
        return rowinfo

    def _get_rowinfo_from_walk_output(self, lines: Iterable[str]) -> SNMPRowInfo:
        # Ugly(1): in some cases snmpwalk inserts line feed within one
        # dataset. This happens for example on hexdump outputs longer
        # than a few bytes. Those dumps are enclosed in double quotes.
        # So if the value begins with a double quote, but the line
        # does not end with a double quote, we take the next line(s) as
        # a continuation line.
        rowinfo = []
        line_iter = iter(lines)
        while True:
            try:
                line = next(line_iter).strip()
            except StopIteration:
                break

            parts = line.split("=", 1)
            if len(parts) < 2:
                continue  # broken line, must contain =
            oid = parts[0].strip()
            value = parts[1].strip()
            # Filter out silly error messages from snmpwalk >:-P
            if (
                value.startswith("No more variables")
                or value.startswith("End of MIB")
                or value.startswith("No Such Object available")
                or value.startswith("No Such Instance currently exists")
            ):
                continue

            if value == '"' or (
                len(value) > 1 and value[0] == '"' and (value[-1] != '"')
            ):  # to be continued
                while True:  # scan for end of this dataset
                    nextline = next(line_iter).strip()
                    value += " " + nextline
                    if value[-1] == '"':
                        break
            rowinfo.append((oid, strip_snmp_value(value)))
        return rowinfo

    def _snmp_proto_spec(self) -> str:
        if self.config.is_ipv6_primary:
            return "udp6:"

        return ""

    def _snmp_port_spec(self) -> str:
        return "" if self.config.port == 161 else f":{self.config.port}"

    def _snmp_version_spec(self) -> Literal["-v1", "-v2c", "-v3"]:
        match self.config.snmp_version:
            case SNMPVersion.V1:
                return "-v1"
            case SNMPVersion.V2C:
                return "-v2c"
            case SNMPVersion.V3:
                return "-v3"

    # if the credentials are a string, we use that as community,
    # if it is a four-tuple, we use it as V3 auth parameters:
    # (1) security level (-l)
    # (2) auth protocol (-a, e.g. 'md5')
    # (3) security name (-u)
    # (4) auth password (-A)
    # And if it is a six-tuple, it has the following additional arguments:
    # (5) privacy protocol (DES|AES) (-x)
    # (6) privacy protocol pass phrase (-X)
    def _snmp_base_command(self, cmd: CommandType, context: SNMPContext) -> list[str]:
        options: list[str] = [self._snmp_version_spec()]

        match cmd:
            case "snmpget":
                command = ["snmpget"]
            case "snmpgetnext":
                command = ["snmpgetnext", "-Cf"]
            case "snmpwalk":
                command = (
                    ["snmpbulkwalk", f"-Cr{self.config.bulk_walk_size_of}"]
                    if self.config.use_bulkwalk
                    else ["snmpwalk"]
                )
            case other:
                assert_never(other)

        if self.config.snmp_version is not SNMPVersion.V3:
            # Handle V1 and V2C
            if not isinstance(self.config.credentials, str):
                raise TypeError()
            options += ["-c", self.config.credentials]

        else:
            # TODO: Fix the horrible credentials typing
            if not (
                isinstance(self.config.credentials, tuple)
                and len(self.config.credentials) in (2, 4, 6)
            ):
                raise MKGeneralException(
                    f"Invalid SNMP credentials '{_sanitize_tuple(self.config.credentials)}' for host {self.config.hostname}: "
                    "must be string, 2-tuple, 4-tuple or 6-tuple"
                )

            if len(self.config.credentials) == 6:
                (
                    sec_level,
                    auth_proto,
                    sec_name,
                    auth_pass,
                    priv_proto,
                    priv_pass,
                ) = self.config.credentials
                options += [
                    "-l",
                    sec_level,
                    "-a",
                    _auth_proto_for(auth_proto),
                    "-u",
                    sec_name,
                    "-A",
                    auth_pass,
                    "-x",
                    _priv_proto_for(priv_proto),
                    "-X",
                    priv_pass,
                ]

            elif len(self.config.credentials) == 4:
                sec_level, auth_proto, sec_name, auth_pass = self.config.credentials
                options += [
                    "-l",
                    sec_level,
                    "-a",
                    _auth_proto_for(auth_proto),
                    "-u",
                    sec_name,
                    "-A",
                    auth_pass,
                ]

            else:
                sec_level, sec_name = self.config.credentials
                options += ["-l", sec_level, "-u", sec_name]

        # Do not load *any* MIB files. This save lot's of CPU.
        options += ["-m", "", "-M", ""]

        # Configuration of timing and retries
        settings = self.config.timing
        if "timeout" in settings:
            options += ["-t", f"{settings['timeout']:.2f}"]
        if "retries" in settings:
            options += ["-r", f"{settings['retries']}"]

        if context:
            options += ["-n", context]

        return command + options


def _auth_proto_for(proto_name: str) -> str:
    if proto_name in {"md5", "sha", "SHA-224", "SHA-256", "SHA-384", "SHA-512"}:
        return proto_name
    raise MKGeneralException(f"Invalid SNMP auth protocol: {proto_name}")


def _priv_proto_for(proto_name: str) -> str:
    if proto_name in {"DES", "AES", "AES-256", "AES-192"}:
        return proto_name
    raise MKGeneralException(f"Invalid SNMP priv protocol: {proto_name}")
