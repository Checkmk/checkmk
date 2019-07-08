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

from collections import namedtuple
import argparse
import sys
import requests

Section = namedtuple('Section', ['name', 'uri', 'handler'])


def main():
    # Sections to query
    # https://docs.splunk.com/Documentation/Splunk/7.2.6/RESTREF/RESTlicense#licenser.2Fpools
    sections = [
        Section(name="license_state",
                uri="/services/licenser/licenses",
                handler=handle_license_state),
        Section(name="license_usage", uri="/services/licenser/usage", handler=handle_license_usage),
        Section(name="system_msg", uri="/services/messages", handler=handle_system_msg),
        Section(name="jobs", uri="/services/search/jobs", handler=handle_jobs),
        Section(name="health", uri="/services/server/health/splunkd/details",
                handler=handle_health),
        Section(name="alerts", uri="/services/alerts/fired_alerts", handler=handle_alerts),
    ]

    args = parse_arguments()

    sys.stdout.write("<<<check_mk>>>\n")

    try:
        handle_request(args, sections)
    except Exception:
        if args.debug:
            return 1


def handle_request(args, sections):
    url_base = "%s://%s:%d" % (args.proto, args.hostname, args.port)

    for section in sections:
        try:
            url = url_base + section.uri
            response = requests.get(url,
                                    auth=(args.user, args.password),
                                    data={"output_mode": "json"})

        except requests.exceptions.RequestException:
            if args.debug:
                raise
        else:
            sys.stdout.write("<<<splunk_%s>>>\n" % section.name)

        if section.name in args.modules:
            value = response.json()['entry']
            section.handler(value)


def parse_arguments(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("-u", "--user", default=None, help="Username for splunk login")
    parser.add_argument("-s", "--password", default=None, help="Password for splunk login")
    parser.add_argument("-P",
                        "--proto",
                        default="https",
                        help="Use 'http' or 'https' for connection to splunk (default=https)")
    parser.add_argument("-p",
                        "--port",
                        default=8089,
                        type=int,
                        help="Use alternative port (default: 8089)")
    parser.add_argument(
        "-m",
        "--modules",
        default="license_state license_usage system_msg jobs health alerts",
        type=lambda x: x.split(' '),
        help=
        "Space-separated list of data to query. Possible values: 'license_state license_usage system_msg jobs health alerts' (default: all)"
    )
    parser.add_argument("--debug",
                        action="store_true",
                        help="Debug mode: let Python exceptions come through")

    parser.add_argument("hostname",
                        metavar="HOSTNAME",
                        help="Name of the splunk instance to query.")

    return parser.parse_args()


def handle_license_state(value):
    for entries in value:
        sys.stdout.write("%s %s %s %s %s %s\n" % (
            "_".join(entries["content"]["label"].split()),  # Plain text description of this license
            entries["content"]
            ["max_violations"],  # max number of violations allowed during window period
            entries["content"]
            ["window_period"],  # rolling period, in days, in which violations are aggregated
            entries["content"]["quota"],  # Daily indexing quota, in bytes, for this license
            entries["content"]["expiration_time"],  # time this license expires (UTC)
            entries["content"]["status"],  # status of a license can be either VALID or EXPIRED
        ))


def handle_license_usage(value):
    for entries in value:
        sys.stdout.write("%s %s\n" % (
            entries["content"]["quota"],  # The byte quota of this license stack (sum)
            entries["content"]
            ["slaves_usage_bytes"],  # Slave usage b across all pools within active license group.
        ))


def handle_system_msg(value):
    for entries in value:
        sys.stdout.write("%s %s %s %s %s\n" % (
            entries["name"],  # This field might contain the same text as the message field.
            entries["content"]
            ["severity"],  # One of the following message severity values: info/warn/error
            entries["content"]["server"],  # Name of the server that generated the error
            entries["content"]["timeCreated_iso"],  # ISO formatted timestamp
            entries["content"]["message"],  # message field
        ))


def handle_jobs(value):
    for entries in value:
        sys.stdout.write("%s %s %s %s %s\n" % (
            entries["published"],  # creation time
            entries["author"],  # author of the search
            entries.get("content", "Unknown").get("request", "Unkown").get(
                "ui_dispatch_app"),  # Application of the search, may be empty for internal searches
            entries["content"]["dispatchState"],  # state of the search
            entries["content"]["isZombie"],  # zombie state (false/true)
        ))


def handle_health(value):
    sys.stdout.write("Overall_state %s\n" % value[0].get("content", {}).get("health"))

    for func, state in value[0]["content"]["features"].iteritems():
        func_name = "%s%s" % (func[0].upper(), func[1:].lower())
        sys.stdout.write("%s %s\n" % (func_name.replace(" ", "_"), state.get("health", {})))

        for feature, status in state["features"].iteritems():
            feature_name = "%s%s" % (feature[0].upper(), feature[1:].lower())
            sys.stdout.write(
                "%s %s %s\n" %
                (func_name.replace(" ", "_"), feature_name.replace(" ", "_"), status["health"]))


def handle_alerts(value):
    sys.stdout.write("%s\n" % value[0]["content"]["triggered_alert_count"])


if __name__ == "__main__":
    sys.exit(main())
