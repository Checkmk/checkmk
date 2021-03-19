#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import getopt
import os
import subprocess
import sys
from typing import Dict, List, Tuple


def agent_ipmi_sensors_usage():
    sys.stderr.write("""Check_MK IPMI Sensors

USAGE: agent_ipmi_sensors [OPTIONS] HOST
       agent_ipmi_sensors --help

ARGUMENTS:
  HOST                              Host name or IP address

OPTIONS:
  --help                            Show this help message and exit.
  --debug                           Debug output
  --ipmi-command IPMI-CMD           Possible values are 'freeipmi' or 'ipmitool'.
                                    If no command is specified 'freeipmi' is used.
  -u USER                           Username
  -p PASSWORD                       Password
  -l LEVEL                          Privilege level
                                    Possible are 'user', 'operator', 'admin'

FreeIPMI OPTIONS:
  -D DRIVER                         Specify IPMI driver.
  --quiet-cache                     Do not output information about cache creation/deletion.
  --sdr-cache-recreate              Automatically recreate the sensor data repository (SDR) cache.
  --interpret-oem-data              Attempt to interpret OEM data.
  --output-sensor-state             Output sensor state in output.
  --ignore-not-available-sensors    Ignore not-available (i.e. N/A) sensors in output.
  --driver-type DRIVER-TYPE         Specify the driver type to use instead of doing an auto selection.
  --output-sensor-thresholds        Output sensor thresholds in output.
  -k KEY                            Specify the K_g BMC key to use when authenticating
                                    with the remote host for IPMI 2.0.
""")


def parse_data(data, excludes):
    for line in data:
        if line.startswith("ID"):
            continue
        if excludes:
            has_excludes = False
            for exclude in excludes:
                if exclude in line:
                    has_excludes = True
                    break
            if not has_excludes:
                sys.stdout.write("%s\n" % line)
        else:
            sys.stdout.write("%s\n" % line)


def main(sys_argv=None):
    if sys_argv is None:
        sys_argv = sys.argv[1:]

    short_options = 'u:p:l:D:k:'
    long_options = [
        'help', 'debug', 'ipmi-command=', 'quiet-cache', 'sdr-cache-recreate', 'interpret-oem-data',
        'output-sensor-state', 'ignore-not-available-sensors', 'driver-type=',
        'output-sensor-thresholds'
    ]

    opt_debug = False
    hostname = None
    username = None
    password = None
    privilege_lvl = None
    ipmi_cmd_type = None

    try:
        opts, args = getopt.getopt(sys_argv, short_options, long_options)
    except getopt.GetoptError as err:
        sys.stderr.write("%s\n" % err)
        return 1

    additional_opts = []
    for o, a in opts:
        if o in ['--help']:
            agent_ipmi_sensors_usage()
            return 1
        if o in ['--debug']:
            opt_debug = True

        # Common options
        elif o in ['--ipmi-command']:
            ipmi_cmd_type = a
        elif o in ['-u']:
            username = a
        elif o in ['-p']:
            password = a
        elif o in ['-l']:
            privilege_lvl = a

        # FreeIPMI options
        elif o in ['-D']:
            additional_opts += ["%s" % o, "%s" % a]
        elif o in ['--driver-type']:
            additional_opts += ["%s=%s" % (o, a)]
        elif o in ['-k']:
            additional_opts += ["%s" % o, "%s" % a]
        elif o in ['--quiet-cache']:
            additional_opts.append(o)
        elif o in ['--sdr-cache-recreate']:
            additional_opts.append(o)
        elif o in ['--interpret-oem-data']:
            additional_opts.append(o)
        elif o in ['--output-sensor-state']:
            additional_opts.append(o)
        elif o in ['--ignore-not-available-sensors']:
            additional_opts.append(o)
        elif o in ['--output-sensor-thresholds']:
            additional_opts.append(o)

    if len(args) == 1:
        hostname = args[0]
    else:
        sys.stderr.write("ERROR: Please specify exactly one host.\n")
        return 1

    if not (username and password and privilege_lvl):
        sys.stderr.write("ERROR: Credentials are missing.\n")
        return 1

    os.environ["PATH"] = "/usr/local/sbin:/usr/sbin:/sbin:" + os.environ["PATH"]

    if ipmi_cmd_type in [None, 'freeipmi']:
        ipmi_cmd = [ "ipmi-sensors",
                     "-h", hostname, "-u", username,
                     "-p", password, "-l", privilege_lvl ] + \
                     additional_opts
        queries: Dict[str, Tuple[List[str], List[str]]] = {"_sensors": ([], [])}
    elif ipmi_cmd_type == 'ipmitool':
        ipmi_cmd = ["ipmitool", "-H", hostname, "-U", username, "-P", password, "-L", privilege_lvl]
        # As in check_mk_agent
        queries = {
            "": (["sensor", "list"], ['command failed', 'discrete']),
            "_discrete": (["sdr", "elist", "compact"], [])
        }

    else:
        sys.stderr.write("ERROR: Unknown IPMI command '%s'.\n" % ipmi_cmd_type)
        return 1

    ipmi_cmd_str = subprocess.list2cmdline(ipmi_cmd)

    if opt_debug:
        sys.stderr.write("Executing: '%s'\n" % ipmi_cmd_str)

    errors = []
    for section, (types, excludes) in queries.items():
        sys.stdout.write("<<<ipmi%s:sep(124)>>>\n" % section)
        try:
            try:
                p = subprocess.Popen(
                    ipmi_cmd + types,
                    close_fds=True,
                    stdin=open(os.devnull),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding="utf-8",
                )
            except OSError as e:
                if e.errno == errno.ENOENT:  # No such file or directory
                    raise Exception("Could not find '%s' command (PATH: %s)" %
                                    (ipmi_cmd_type, os.environ.get("PATH")))
                raise

            stdout, stderr = p.communicate()
            if stderr:
                errors.append(stderr)
            parse_data(stdout.splitlines(), excludes)
        except Exception as e:
            errors.append(str(e))

    if errors:
        sys.stderr.write("ERROR: '%s'.\n" % ", ".join(errors))
        return 1
    return 0
