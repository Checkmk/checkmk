#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | "_ \ / _ \/ __| |/ /   | |\/| | " /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
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

from typing import NamedTuple, Text
import argparse
import json
import sys
import requests

GraylogSection = NamedTuple("GraylogSection", [
    ("name", Text),
    ("uri", Text),
])


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = parse_arguments(argv)

    # Add new queries here
    sections = [
        GraylogSection(name="alerts", uri="/streams/alerts?limit=300"),
        GraylogSection(name="collectors", uri="/plugins/org.graylog.plugins.collector/collectors"),
        GraylogSection(name="cluster_health", uri="/system/indexer/cluster/health"),
        GraylogSection(name="cluster_inputstates", uri="/cluster/inputstates"),
        GraylogSection(name="cluster_stats", uri="/system/cluster/stats"),
        GraylogSection(name="cluster_traffic", uri="/system/cluster/traffic"),
        GraylogSection(name="failures", uri="/system/indexer/failures?limit=300"),
        GraylogSection(name="jvm", uri="/system/stats/jvm"),
        GraylogSection(name="messages", uri="/count/total"),
        GraylogSection(name="nodes", uri="/cluster"),
        GraylogSection(name="sidecars", uri="/sidecars"),
    ]

    try:
        handle_request(args, sections)
    except Exception:
        if args.debug:
            return 1

    return 0


def handle_request(args, sections):
    url_base = "%s://%s:%s/api" % (args.proto, args.hostname, args.port)

    for section in sections:
        if section.name not in args.sections:
            continue

        sys.stdout.write("<<<graylog_%s:sep(0)>>>\n" % section.name)
        url = url_base + section.uri

        try:
            response = requests.get(url, auth=(args.user, args.password))
        except requests.exceptions.RequestException as e:
            sys.stderr.write("Error: %s\n" % e)
            if args.debug:
                raise

        if section.name == "lbstatus":
            # no json output
            value = {"lb_state": response.text}
        else:
            value = response.json()

        sys.stdout.write("%s\n" % json.dumps(value))


def parse_arguments(argv):
    sections = [
        "alerts", "cluster_health", "cluster_inputstates", "cluster_stats", "cluster_traffic",
        "collectors", "failures", "jvm", "messages", "nodes", "sidecars"
    ]

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("-u", "--user", default=None, help="Username for graylog login")
    parser.add_argument("-s", "--password", default=None, help="Password for graylog login")
    parser.add_argument("-P",
                        "--proto",
                        default="https",
                        help="Use 'http' or 'https' for connection to graylog (default=https)")
    parser.add_argument("-p",
                        "--port",
                        default=443,
                        type=int,
                        help="Use alternative port (default: 443)")
    parser.add_argument(
        "-m",
        "--sections",
        default=sections,
        help="Comma seperated list of data to query. Possible values: %s (default: all)" %
        ", ".join(sections))
    parser.add_argument("--debug",
                        action="store_true",
                        help="Debug mode: let Python exceptions come through")

    parser.add_argument("hostname",
                        metavar="HOSTNAME",
                        help="Name of the graylog instance to query.")

    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
