#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from typing import Iterable, List, Optional

import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException, MKSNMPError, MKTimeout
from cmk.utils.log import console
from cmk.utils.type_defs import SectionName

from cmk.snmplib.type_defs import OID, SNMPBackend, SNMPContextName, SNMPRawValue, SNMPRowInfo

from ._utils import strip_snmp_value

__all__ = ["ClassicSNMPBackend"]


class ClassicSNMPBackend(SNMPBackend):
    def get(
        self, oid: OID, context_name: Optional[SNMPContextName] = None
    ) -> Optional[SNMPRawValue]:
        if oid.endswith(".*"):
            oid_prefix = oid[:-2]
            commandtype = "getnext"
        else:
            oid_prefix = oid
            commandtype = "get"

        protospec = self._snmp_proto_spec()
        ipaddress = self.config.ipaddress or "0.0.0.0"
        if self.config.is_ipv6_primary:
            ipaddress = "[" + ipaddress + "]"
        portspec = self._snmp_port_spec()
        command = self._snmp_base_command(commandtype, context_name) + [
            "-On",
            "-OQ",
            "-Oe",
            "-Ot",
            "%s%s%s" % (protospec, ipaddress, portspec),
            oid_prefix,
        ]

        console.vverbose("Running '%s'\n" % subprocess.list2cmdline(command))

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
            console.verbose(tty.red + tty.bold + "ERROR: " + tty.normal + "SNMP error\n")
            console.verbose(error + "\n")
            return None

        if not line:
            console.verbose("Error in response to snmpget.\n")
            return None

        parts = line.split("=", 1)
        if len(parts) != 2:
            return None
        item = parts[0]
        value = parts[1].strip()
        console.vverbose("SNMP answer: ==> [%s]\n" % value)
        if (
            value.startswith("No more variables")
            or value.startswith("End of MIB")
            or value.startswith("No Such Object available")
            or value.startswith("No Such Instance currently exists")
        ):
            return None

        # In case of .*, check if prefix is the one we are looking for
        if commandtype == "getnext" and not item.startswith(oid_prefix + "."):
            return None

        return strip_snmp_value(value)

    def walk(
        self,
        oid: str,
        section_name: Optional[SectionName] = None,
        table_base_oid: Optional[str] = None,
        context_name: Optional[str] = None,
    ) -> SNMPRowInfo:
        protospec = self._snmp_proto_spec()

        ipaddress = self.config.ipaddress or "0.0.0.0"
        if self.config.is_ipv6_primary:
            ipaddress = "[" + ipaddress + "]"

        portspec = self._snmp_port_spec()
        command = self._snmp_walk_command(context_name)
        command += ["-OQ", "-OU", "-On", "-Ot", "%s%s%s" % (protospec, ipaddress, portspec), oid]
        console.vverbose("Running '%s'\n" % subprocess.list2cmdline(command))

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
            console.verbose(
                tty.red + tty.bold + "ERROR: " + tty.normal + "SNMP error: %s\n" % error.strip()
            )
            raise MKSNMPError(
                "SNMP Error on %s: %s (Exit-Code: %d)"
                % (
                    ipaddress,
                    error.strip(),
                    snmp_process.returncode,
                )
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
        if self.config.port == 161:
            return ""
        return ":%d" % self.config.port

    def _snmp_walk_command(self, context_name: Optional[SNMPContextName]) -> List[str]:
        """Returns command lines for snmpwalk and snmpget

        Including options for authentication. This handles communities and
        authentication for SNMP V3. Also bulkwalk hosts"""
        return self._snmp_base_command("walk", context_name) + ["-Cc"]

    # if the credentials are a string, we use that as community,
    # if it is a four-tuple, we use it as V3 auth parameters:
    # (1) security level (-l)
    # (2) auth protocol (-a, e.g. 'md5')
    # (3) security name (-u)
    # (4) auth password (-A)
    # And if it is a six-tuple, it has the following additional arguments:
    # (5) privacy protocol (DES|AES) (-x)
    # (6) privacy protocol pass phrase (-X)
    def _snmp_base_command(self, what: str, context_name: Optional[SNMPContextName]) -> List[str]:
        options = []

        if what == "get":
            command = ["snmpget"]
        elif what == "getnext":
            command = ["snmpgetnext", "-Cf"]
        elif self.config.is_bulkwalk_host:
            command = ["snmpbulkwalk"]

            options.append("-Cr%d" % self.config.bulk_walk_size_of)
        else:
            command = ["snmpwalk"]

        if not self.config.is_snmpv3_host:
            # Handle V1 and V2C
            if self.config.is_bulkwalk_host:
                options.append("-v2c")
            else:
                if what == "walk":
                    command = ["snmpwalk"]
                if self.config.is_snmpv2or3_without_bulkwalk_host:
                    options.append("-v2c")
                else:
                    options.append("-v1")

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
                    "Invalid SNMP credentials '%r' for host %s: must be "
                    "string, 2-tuple, 4-tuple or 6-tuple"
                    % (self.config.credentials, self.config.hostname)
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
                    "-v3",
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
                    "-v3",
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
                options += ["-v3", "-l", sec_level, "-u", sec_name]

        # Do not load *any* MIB files. This save lot's of CPU.
        options += ["-m", "", "-M", ""]

        # Configuration of timing and retries
        settings = self.config.timing
        if "timeout" in settings:
            options += ["-t", "%0.2f" % settings["timeout"]]
        if "retries" in settings:
            options += ["-r", "%d" % settings["retries"]]

        if context_name is not None:
            options += ["-n", context_name]

        return command + options


def _auth_proto_for(proto_name: str) -> str:
    if proto_name == "md5":
        return "md5"
    if proto_name == "sha":
        return "sha"
    if proto_name == "SHA-224":
        return "SHA-224"
    if proto_name == "SHA-256":
        return "SHA-256"
    if proto_name == "SHA-384":
        return "SHA-384"
    if proto_name == "SHA-512":
        return "SHA-512"
    raise MKGeneralException("Invalid SNMP auth protocol: %s" % proto_name)


def _priv_proto_for(proto_name: str) -> str:
    if proto_name == "DES":
        return "DES"
    if proto_name == "AES":
        return "AES"
    raise MKGeneralException("Invalid SNMP priv protocol: %s" % proto_name)
