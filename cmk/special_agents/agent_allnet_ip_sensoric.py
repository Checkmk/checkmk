#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This agent uses UPNP API calls to the Fritz!Box to gather information
# about connection configuration and status.

import getopt
import pprint
import re
import socket
import sys
import traceback
import urllib.request

from cmk.utils.exceptions import MKException


def usage():
    sys.stderr.write(
        """Check_MK ALLNET IP-Sensoric Agent

USAGE: agent_allnet_ip_sensoric [OPTIONS] HOST
       agent_allnet_ip_sensoric -h

ARGUMENTS:
  HOST                          Host name or IP address of your ALLNET IP-Sensoric

OPTIONS:
  -h, --help                    Show this help message and exit
  -t, --timeout SEC             Set the network timeout to <SEC> seconds.
                                Default is 10 seconds. Note: the timeout is not
                                applied to the whole check, instead it is used for
                                the http query only.
  --debug                       Debug mode: let Python exceptions come through
"""
    )


class RequestError(MKException):
    pass


def get_allnet_ip_sensoric_info(host_address, opt_debug):
    url = "http://%s/xml/sensordata.xml" % host_address

    headers = {
        "User-agent": "Check_MK agent_allnet_ip_sensoric",
    }

    if opt_debug:
        sys.stdout.write("============================\n")
        sys.stdout.write("URL: %s\n" % url)

    try:
        req = urllib.request.Request(url, None, headers)
        with urllib.request.urlopen(req) as handle:
            infos = handle.info()
            contents = handle.read().decode("utf-8")
    except Exception:
        if opt_debug:
            sys.stdout.write("----------------------------\n")
            sys.stdout.write(traceback.format_exc())
            sys.stdout.write("============================\n")
        raise RequestError("Error during http call")

    if opt_debug:
        sys.stdout.write("----------------------------\n")
        sys.stdout.write("Server: %s\n" % infos["SERVER"])
        sys.stdout.write("----------------------------\n")
        sys.stdout.write(contents + "\n")
        sys.stdout.write("============================\n")

    attrs = {}

    context = None
    for line in contents.splitlines():

        match = re.search("<(sensor[0-9]+|system)>", line)
        if match:
            context = match.group(1)
            continue

        match = re.search("</(sensor[0-9]+|system)>", line)
        if match:
            context = None
            continue

        match = re.search(r"<(\w+)>(.+)</\w+>", line)
        if match and context:
            attrs["%s.%s" % (context, match.group(1))] = match.group(2)

    if opt_debug:
        sys.stdout.write("Parsed: %s\n" % pprint.pformat(attrs))

    return attrs


def main(sys_argv=None):
    if sys_argv is None:
        sys_argv = sys.argv[1:]

    short_options = "h:t:d"
    long_options = ["help", "timeout=", "debug"]

    host_address = None
    opt_debug = False
    opt_timeout = 10

    try:
        opts, args = getopt.getopt(sys_argv, short_options, long_options)
    except getopt.GetoptError as err:
        sys.stderr.write("%s\n" % err)
        return 1

    for o, a in opts:
        if o in ["--debug"]:
            opt_debug = True
        elif o in ["-t", "--timeout"]:
            opt_timeout = int(a)
        elif o in ["-h", "--help"]:
            usage()
            sys.exit(0)

    if len(args) == 1:
        host_address = args[0]
    elif not args:
        sys.stderr.write("ERROR: No host given.\n")
        return 1
    else:
        sys.stderr.write("ERROR: Please specify exactly one host.\n")
        return 1

    socket.setdefaulttimeout(opt_timeout)

    try:
        status = {}
        try:
            status.update(get_allnet_ip_sensoric_info(host_address, opt_debug))
        except Exception:
            if opt_debug:
                raise

        sys.stdout.write("<<<allnet_ip_sensoric:sep(59)>>>\n")
        for key, value in sorted(status.items()):
            sys.stdout.write("%s;%s\n" % (key, value))

    except Exception:
        if opt_debug:
            raise
        sys.stderr.write("Unhandled error: %s" % traceback.format_exc())
    return None
