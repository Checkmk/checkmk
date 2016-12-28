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

import cmk.debug
import cmk.tty as tty
from cmk.exceptions import MKGeneralException

import cmk_base.console as console
import cmk_base.config as config
from cmk_base.exceptions import MKSNMPError


#.
#   .--SNMP interface------------------------------------------------------.
#   | ____  _   _ __  __ ____    _       _             __                  |
#   |/ ___|| \ | |  \/  |  _ \  (_)_ __ | |_ ___ _ __ / _| __ _  ___ ___   |
#   |\___ \|  \| | |\/| | |_) | | | '_ \| __/ _ \ '__| |_ / _` |/ __/ _ \  |
#   | ___) | |\  | |  | |  __/  | | | | | ||  __/ |  |  _| (_| | (_|  __/  |
#   ||____/|_| \_|_|  |_|_|     |_|_| |_|\__\___|_|  |_|  \__,_|\___\___|  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Implements the neccessary function for Check_MK                      |
#   '----------------------------------------------------------------------'

def walk(hostname, ip, oid, hex_plain = False, context_name = None):
    import cmk_base.snmp as snmp
    protospec = _snmp_proto_spec(hostname)
    portspec = _snmp_port_spec(hostname)
    command = _snmp_walk_command(hostname)
    if context_name != None:
        command += [ "-n", context_name ]
    command += [ "-OQ", "-OU", "-On", "-Ot", "%s%s%s" % (protospec, ip, portspec), oid ]

    debug_cmd = [ "''" if a == "" else a for a in command ]
    console.vverbose("Running '%s'\n" % " ".join(debug_cmd))

    snmp_process = subprocess.Popen(command, close_fds=True, stdin=open(os.devnull),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Ugly(1): in some cases snmpwalk inserts line feed within one
    # dataset. This happens for example on hexdump outputs longer
    # than a few bytes. Those dumps are enclosed in double quotes.
    # So if the value begins with a double quote, but the line
    # does not end with a double quote, we take the next line(s) as
    # a continuation line.
    rowinfo = []
    try:
        line_iter = snmp_process.stdout.xreadlines()
        while True:
            line = line_iter.next().strip()
            parts = line.split('=', 1)
            if len(parts) < 2:
                continue # broken line, must contain =
            oid = parts[0].strip()
            value = parts[1].strip()
            # Filter out silly error messages from snmpwalk >:-P
            if value.startswith('No more variables') or value.startswith('End of MIB') \
               or value.startswith('No Such Object available') or value.startswith('No Such Instance currently exists'):
                continue

            if value == '"' or (len(value) > 1 and value[0] == '"' and (value[-1] != '"')): # to be continued
                while True: # scan for end of this dataset
                    nextline = line_iter.next().strip()
                    value += " " + nextline
                    if value[-1] == '"':
                        break
            rowinfo.append((oid, snmp.strip_snmp_value(value, hex_plain)))

    except StopIteration:
        pass

    error = snmp_process.stderr.read()
    exitstatus = snmp_process.wait()
    if exitstatus:
        console.verbose(tty.red + tty.bold + "ERROR: " + tty.normal + "SNMP error: %s\n" % error.strip())
        raise MKSNMPError("SNMP Error on %s: %s (Exit-Code: %d)" % (ip, error.strip(), exitstatus))
    return rowinfo


def get(hostname, ipaddress, oid):
    if oid.endswith(".*"):
        oid_prefix = oid[:-2]
        commandtype = "getnext"
    else:
        oid_prefix = oid
        commandtype = "get"

    protospec = _snmp_proto_spec(hostname)
    portspec = _snmp_port_spec(hostname)
    command = _snmp_base_command(commandtype, hostname) + \
               [ "-On", "-OQ", "-Oe", "-Ot",
                 "%s%s%s" % (protospec, ipaddress, portspec),
                 oid_prefix ]

    debug_cmd = [ "''" if a == "" else a for a in command ]
    console.vverbose("Running '%s'\n" % " ".join(debug_cmd))

    snmp_process = subprocess.Popen(command, close_fds=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    exitstatus = snmp_process.wait()
    if exitstatus:
        console.verbose(tty.red + tty.bold + "ERROR: " + tty.normal + "SNMP error\n")
        console.verbose(snmp_process.stderr.read()+"\n")
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


def _snmp_port_spec(hostname):
    port = config.snmp_port_of(hostname)
    if port == None:
        return ""
    else:
        return ":%d" % port


def _snmp_proto_spec(hostname):
    if config.is_ipv6_primary(hostname):
        return "udp6:"
    else:
        return ""


# Returns command lines for snmpwalk and snmpget including
# options for authentication. This handles communities and
# authentication for SNMP V3. Also bulkwalk hosts
def _snmp_walk_command(hostname):
    return _snmp_base_command('walk', hostname) + [ "-Cc" ]


# if the credentials are a string, we use that as community,
# if it is a four-tuple, we use it as V3 auth parameters:
# (1) security level (-l)
# (2) auth protocol (-a, e.g. 'md5')
# (3) security name (-u)
# (4) auth password (-A)
# And if it is a six-tuple, it has the following additional arguments:
# (5) privacy protocol (DES|AES) (-x)
# (6) privacy protocol pass phrase (-X)
def _snmp_base_command(what, hostname):
    if what == 'get':
        command = [ 'snmpget' ]
    elif what == 'getnext':
        command = [ 'snmpgetnext', '-Cf' ]
    elif config.is_bulkwalk_host(hostname):
        command = [ 'snmpbulkwalk' ]
    else:
        command = [ 'snmpwalk' ]

    options = []
    credentials = config.snmp_credentials_of(hostname)

    if type(credentials) in [ str, unicode ]:
        # Handle V1 and V2C
        if config.is_bulkwalk_host(hostname):
            options.append('-v2c')
        else:
            if what == 'walk':
                command = [ 'snmpwalk' ]
            if config.is_snmpv2c_host(hostname):
                options.append('-v2c')
            else:
                options.append('-v1')

        options += [ "-c", credentials ]

    else:
        # Handle V3
        if len(credentials) == 6:
            options += [
                "-v3", "-l", credentials[0], "-a", credentials[1],
                "-u", credentials[2], "-A", credentials[3],
                "-x", credentials[4], "-X", credentials[5],
            ]
        elif len(credentials) == 4:
            options += [
                "-v3", "-l", credentials[0], "-a", credentials[1],
                "-u", credentials[2], "-A", credentials[3],
            ]
        elif len(credentials) == 2:
            options += [
                "-v3", "-l", credentials[0], "-u", credentials[1],
            ]
        else:
            raise MKGeneralException("Invalid SNMP credentials '%r' for host %s: must be "
                                     "string, 2-tuple, 4-tuple or 6-tuple" % (credentials, hostname))

    # Do not load *any* MIB files. This save lot's of CPU.
    options += [ "-m", "", "-M", "" ]

    # Configuration of timing and retries
    settings = config.snmp_timing_of(hostname)
    if "timeout" in settings:
        options += [ "-t", "%0.2f" % settings["timeout"] ]
    if "retries" in settings:
        options += [ "-r", "%d" % settings["retries"] ]

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

