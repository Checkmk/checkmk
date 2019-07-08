#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import os
import subprocess
import signal
from typing import Optional  # pylint: disable=unused-import

import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException, MKTimeout

import cmk_base.console as console
import cmk_base.snmp_utils as snmp_utils
from cmk_base.exceptions import MKSNMPError


class ClassicSNMPBackend(snmp_utils.ABCSNMPBackend):
    def get(self, snmp_config, oid, context_name=None):
        if oid.endswith(".*"):
            oid_prefix = oid[:-2]
            commandtype = "getnext"
        else:
            oid_prefix = oid
            commandtype = "get"

        protospec = self._snmp_proto_spec(snmp_config)
        ipaddress = snmp_config.ipaddress
        if snmp_config.is_ipv6_primary:
            ipaddress = "[" + ipaddress + "]"
        portspec = self._snmp_port_spec(snmp_config)
        command = self._snmp_base_command(commandtype, snmp_config, context_name) + \
                   [ "-On", "-OQ", "-Oe", "-Ot",
                     "%s%s%s" % (protospec, ipaddress, portspec),
                     oid_prefix ]

        console.vverbose("Running '%s'\n" % subprocess.list2cmdline(command))

        snmp_process = subprocess.Popen(command,
                                        close_fds=True,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
        exitstatus = snmp_process.wait()
        if exitstatus:
            console.verbose(tty.red + tty.bold + "ERROR: " + tty.normal + "SNMP error\n")
            console.verbose(snmp_process.stderr.read() + "\n")
            return None

        line = snmp_process.stdout.readline().strip()
        if not line:
            console.verbose("Error in response to snmpget.\n")
            return None

        item, value = line.split("=", 1)
        value = value.strip()
        console.vverbose("SNMP answer: ==> [%s]\n" % value)
        if value.startswith('No more variables') or value.startswith('End of MIB') \
           or value.startswith('No Such Object available') or value.startswith('No Such Instance currently exists'):
            value = None

        # In case of .*, check if prefix is the one we are looking for
        if commandtype == "getnext" and not item.startswith(oid_prefix + "."):
            value = None

        # Strip quotes
        if value and value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        return value

    def walk(self, snmp_config, oid, check_plugin_name=None, table_base_oid=None,
             context_name=None):
        # type: (snmp_utils.SNMPHostConfig, str, Optional[str], Optional[str], Optional[str]) -> snmp_utils.SNMPRowInfo
        protospec = self._snmp_proto_spec(snmp_config)

        ipaddress = snmp_config.ipaddress
        if snmp_config.is_ipv6_primary:
            ipaddress = "[" + ipaddress + "]"

        portspec = self._snmp_port_spec(snmp_config)
        command = self._snmp_walk_command(snmp_config, context_name)
        command += ["-OQ", "-OU", "-On", "-Ot", "%s%s%s" % (protospec, ipaddress, portspec), oid]

        # list2cmdline exists, but mypy complains
        console.vverbose("Running '%s'\n" % subprocess.list2cmdline(command))  # type: ignore

        snmp_process = None
        exitstatus = None
        rowinfo = []  # type: snmp_utils.SNMPRowInfo
        try:
            snmp_process = subprocess.Popen(command,
                                            close_fds=True,
                                            stdin=open(os.devnull),
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)

            rowinfo = self._get_rowinfo_from_snmp_process(snmp_process)

        except MKTimeout:
            # On timeout exception try to stop the process to prevent child process "leakage"
            if snmp_process:
                os.kill(snmp_process.pid, signal.SIGTERM)
                snmp_process.wait()
            raise

        finally:
            # The stdout and stderr pipe are not closed correctly on a MKTimeout
            # Normally these pipes getting closed after p.communicate finishes
            # Closing them a second time in a OK scenario won't hurt neither..
            if snmp_process:
                exitstatus = snmp_process.wait()
                if snmp_process.stderr:
                    error = snmp_process.stderr.read()
                    snmp_process.stderr.close()
                if snmp_process.stdout:
                    snmp_process.stdout.close()

        if exitstatus:
            console.verbose(tty.red + tty.bold + "ERROR: " + tty.normal +
                            "SNMP error: %s\n" % error.strip())
            raise MKSNMPError("SNMP Error on %s: %s (Exit-Code: %d)" %
                              (ipaddress, error.strip(), exitstatus))
        return rowinfo

    def _get_rowinfo_from_snmp_process(self, snmp_process):
        line_iter = snmp_process.stdout.xreadlines()
        # Ugly(1): in some cases snmpwalk inserts line feed within one
        # dataset. This happens for example on hexdump outputs longer
        # than a few bytes. Those dumps are enclosed in double quotes.
        # So if the value begins with a double quote, but the line
        # does not end with a double quote, we take the next line(s) as
        # a continuation line.
        rowinfo = []
        while True:
            try:
                line = line_iter.next().strip()
            except StopIteration:
                break

            parts = line.split('=', 1)
            if len(parts) < 2:
                continue  # broken line, must contain =
            oid = parts[0].strip()
            value = parts[1].strip()
            # Filter out silly error messages from snmpwalk >:-P
            if value.startswith('No more variables') or value.startswith('End of MIB') \
               or value.startswith('No Such Object available') \
               or value.startswith('No Such Instance currently exists'):
                continue

            if value == '"' or (len(value) > 1 and value[0] == '"' and
                                (value[-1] != '"')):  # to be continued
                while True:  # scan for end of this dataset
                    nextline = line_iter.next().strip()
                    value += " " + nextline
                    if value[-1] == '"':
                        break
            rowinfo.append((oid, strip_snmp_value(value)))
        return rowinfo

    def _snmp_proto_spec(self, snmp_config):
        # type: (snmp_utils.SNMPHostConfig) -> str
        if snmp_config.is_ipv6_primary:
            return "udp6:"

        return ""

    def _snmp_port_spec(self, snmp_config):
        # type: (snmp_utils.SNMPHostConfig) -> str
        if snmp_config.port == 161:
            return ""
        return ":%d" % snmp_config.port

    def _snmp_walk_command(self, snmp_config, context_name):
        """Returns command lines for snmpwalk and snmpget

        Including options for authentication. This handles communities and
        authentication for SNMP V3. Also bulkwalk hosts"""
        return self._snmp_base_command('walk', snmp_config, context_name) + ["-Cc"]

    # if the credentials are a string, we use that as community,
    # if it is a four-tuple, we use it as V3 auth parameters:
    # (1) security level (-l)
    # (2) auth protocol (-a, e.g. 'md5')
    # (3) security name (-u)
    # (4) auth password (-A)
    # And if it is a six-tuple, it has the following additional arguments:
    # (5) privacy protocol (DES|AES) (-x)
    # (6) privacy protocol pass phrase (-X)
    def _snmp_base_command(self, what, snmp_config, context_name):
        options = []

        if what == 'get':
            command = ['snmpget']
        elif what == 'getnext':
            command = ['snmpgetnext', '-Cf']
        elif snmp_config.is_bulkwalk_host:
            command = ['snmpbulkwalk']

            options.append("-Cr%d" % snmp_config.bulk_walk_size_of)
        else:
            command = ['snmpwalk']

        if not snmp_utils.is_snmpv3_host(snmp_config):
            # Handle V1 and V2C
            if snmp_config.is_bulkwalk_host:
                options.append('-v2c')
            else:
                if what == 'walk':
                    command = ['snmpwalk']
                if snmp_config.is_snmpv2or3_without_bulkwalk_host:
                    options.append('-v2c')
                else:
                    options.append('-v1')

            options += ["-c", snmp_config.credentials]

        else:
            # Handle V3
            if len(snmp_config.credentials) == 6:
                options += [
                    "-v3", "-l", snmp_config.credentials[0], "-a", snmp_config.credentials[1], "-u",
                    snmp_config.credentials[2], "-A", snmp_config.credentials[3], "-x",
                    snmp_config.credentials[4], "-X", snmp_config.credentials[5]
                ]
            elif len(snmp_config.credentials) == 4:
                options += [
                    "-v3", "-l", snmp_config.credentials[0], "-a", snmp_config.credentials[1], "-u",
                    snmp_config.credentials[2], "-A", snmp_config.credentials[3]
                ]
            elif len(snmp_config.credentials) == 2:
                options += [
                    "-v3", "-l", snmp_config.credentials[0], "-u", snmp_config.credentials[1]
                ]
            else:
                raise MKGeneralException("Invalid SNMP credentials '%r' for host %s: must be "
                                         "string, 2-tuple, 4-tuple or 6-tuple" %
                                         (snmp_config.credentials, snmp_config.hostname))

        # Do not load *any* MIB files. This save lot's of CPU.
        options += ["-m", "", "-M", ""]

        # Configuration of timing and retries
        settings = snmp_config.timing
        if "timeout" in settings:
            options += ["-t", "%0.2f" % settings["timeout"]]
        if "retries" in settings:
            options += ["-r", "%d" % settings["retries"]]

        if context_name is not None:
            options += ["-n", context_name]

        return command + options


#.
#   .--SNMP helpers--------------------------------------------------------.
#   |     ____  _   _ __  __ ____    _          _                          |
#   |    / ___|| \ | |  \/  |  _ \  | |__   ___| |_ __   ___ _ __ ___      |
#   |    \___ \|  \| | |\/| | |_) | | '_ \ / _ \ | '_ \ / _ \ '__/ __|     |
#   |     ___) | |\  | |  | |  __/  | | | |  __/ | |_) |  __/ |  \__ \     |
#   |    |____/|_| \_|_|  |_|_|     |_| |_|\___|_| .__/ \___|_|  |___/     |
#   |                                            |_|                       |
#   +----------------------------------------------------------------------+
#   | Internal helpers for processing SNMP things                          |
#   '----------------------------------------------------------------------'


def strip_snmp_value(value):
    v = value.strip()
    if v.startswith('"'):
        v = v[1:-1]
        if len(v) > 2 and _is_hex_string(v):
            return _convert_from_hex(v)
        # Fix for non hex encoded string which have been somehow encoded by the
        # netsnmp command line tools. An example:
        # Checking windows systems via SNMP with hr_fs: disk names like c:\
        # are reported as c:\\, fix this to single \
        return v.strip().replace('\\\\', '\\')
    return v


def _is_hex_string(value):
    # as far as I remember, snmpwalk puts a trailing space within
    # the quotes in case of hex strings. So we require that space
    # to be present in order make sure, we really deal with a hex string.
    if value[-1] != ' ':
        return False
    hexdigits = "0123456789abcdefABCDEF"
    n = 0
    for x in value:
        if n % 3 == 2:
            if x != ' ':
                return False
        else:
            if x not in hexdigits:
                return False
        n += 1
    return True


def _convert_from_hex(value):
    hexparts = value.split()
    r = ""
    for hx in hexparts:
        r += chr(int(hx, 16))
    return r
