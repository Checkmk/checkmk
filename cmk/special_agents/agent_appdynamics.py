#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import getopt
import json
import socket
import sys
from base64 import b64encode
from http.client import HTTPConnection
from pathlib import Path
from typing import Any, Dict


def usage():
    sys.stderr.write(
        """Check_MK AppDynamics special agent

USAGE: agent_appdynamics [OPTIONS] HOST APPLICATION

ARGUMENTS:
  HOST                          The AppDynamics host
  APPLICATION                   The application to query

OPTIONS:
  -u, --user USERNAME           Login username
  -p, --password PASSWORD       Login password
  -P, --port PORT               TCP port to connect to (default: 8090)
  -t, --timeout SECONDS         Connection timeout (default: 30 seconds)
  -f FILENAME                   Read JSON from file FILENAME instead of socket
  -v, --verbose                 Be more verbose
  --debug                       Debug mode: let Python exceptions come through
  -h, --help                    Show this help message and exit
"""
    )


def main(sys_argv=None):  # pylint: disable=too-many-branches
    if sys_argv is None:
        sys_argv = sys.argv[1:]

    short_options = "u:p:P:t:f:hv"
    long_options = [
        "username=",
        "password=",
        "port=",
        "timeout=",
        "filename=",
        "help",
        "verbose",
        "debug",
    ]

    opt_username = None
    opt_password = None
    opt_port = 8090
    opt_timeout = 30
    opt_verbose = False
    opt_debug = False
    opt_filename = None

    try:
        opts, args = getopt.getopt(sys_argv, short_options, long_options)
    except getopt.GetoptError as err:
        sys.stderr.write("%s\n" % err)
        return 1

    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
            sys.exit(0)
        elif o in ["-u", "--username"]:
            opt_username = a
        elif o in ["-p", "--password"]:
            opt_password = a
        elif o in ["-f", "--filename"]:
            opt_filename = a
        elif o in ["-P", "--port"]:
            try:
                opt_port = int(a)
                if opt_port < 1 or opt_port > 65534:
                    raise ValueError
            except ValueError:
                sys.stderr.write("Port is not a valid integer in range 1-65534\n")
                return 1
        elif o in ["-t", "--timeout"]:
            try:
                opt_timeout = int(a)
            except ValueError:
                sys.stderr.write("Timeout is not a valid integer\n")
                return 1
        elif o in ["-v", "--verbose"]:
            opt_verbose = True
        elif o in ["--debug"]:
            opt_debug = True

    if len(args) < 2:
        sys.stderr.write("Too few arguments\n")
        usage()
        return 1

    arg_host, arg_application = args[0:2]

    if opt_filename:
        try:
            data = json.loads(Path(opt_filename).read_text())
        except Exception as e:
            sys.stderr.write("Cannot read JSON data from file %s: %s\n" % (opt_filename, e))
            if opt_debug:
                raise
            return 1

    else:
        url = (
            "/controller/rest/applications/%(application)s/metric-data"
            "?metric-path=Application%%20Infrastructure%%20Performance|*|Individual%%20Nodes|*|%(object)s|*|*"
            "&time-range-type=BEFORE_NOW&duration-in-mins=1&output=json"
        )

        socket.setdefaulttimeout(opt_timeout)

        data = []

        # Initialize server connection
        try:
            connection = HTTPConnection(arg_host, opt_port)

            if opt_verbose:
                sys.stdout.write("Connecting to %s:%s...\n" % (arg_host, opt_port))
            connection.connect()

            auth = b64encode(("%s:%s" % (opt_username, opt_password)).encode())
            headers = {"Authorization": "Basic " + auth.decode()}
            for obj in ["Agent", "*|*"]:
                connection.request(
                    "GET", url % {"application": arg_application, "object": obj}, headers=headers
                )
                response = connection.getresponse()

                if response.status != 200:
                    sys.stderr.write(
                        "Could not fetch data from AppDynamics server. "
                        "HTTP %s: %s\n" % (response.status, response.reason)
                    )
                    return 1

                data += json.loads(response.read())

        except Exception as e:
            sys.stderr.write("Cannot connect to AppDynamics server. %s\n" % e)
            if opt_debug:
                raise
            return 1

    grouped_data: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for metric in data:
        path_parts = metric["metricPath"].split("|")
        if len(path_parts) == 7:  # Unit missing
            path_parts.append("")

        _base, application, _section, node, provider, typename, item, unit = path_parts

        try:
            value = metric["metricValues"][0]["current"]
        except IndexError:
            continue  # Skip empty values

        if provider not in ("Agent", "JMX", "JVM"):
            continue  # Skip unwanted values

        grouped_data.setdefault(node, {}).setdefault(application, {}).setdefault(
            typename, {}
        ).setdefault(item, {})[unit] = value

    for node, applications in grouped_data.items():
        sys.stdout.write("<<<<%s>>>>\n" % node)
        for application, types in applications.items():
            for typename, items in types.items():
                typename = typename.lower().replace(" ", "_")
                if typename in ["app", "memory", "sessions", "web_container_runtime"]:
                    sys.stdout.write(
                        "<<<appdynamics_%s:sep(124)>>>\n" % (typename.replace("_runtime", ""))
                    )
                    for item, values in items.items():
                        if values:
                            output_items = [application, item]
                            for name, value in values.items():
                                if not name:
                                    output_items.append("%s" % value)
                                else:
                                    output_items.append("%s:%s" % (name, value))
                            sys.stdout.write("|".join(output_items) + "\n")
    sys.stdout.write("<<<<>>>>\n")
