#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import namedtuple
import argparse
import sys
import requests
import urllib3  # type: ignore[import]
import cmk.utils.password_store

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
cmk.utils.password_store.replace_passwords()

Section = namedtuple('Section', ['name', 'uri', 'handler'])


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    # Sections to query
    # https://docs.splunk.com/Documentation/Splunk/7.2.6/RESTREF/RESTlicense#licenser.2Fpools
    sections = [
        Section(
            name="license_state",
            uri="/services/licenser/licenses",
            handler=handle_license_state,
        ),
        Section(
            name="license_usage",
            uri="/services/licenser/usage",
            handler=handle_license_usage,
        ),
        Section(
            name="system_msg",
            uri="/services/messages",
            handler=handle_system_msg,
        ),
        Section(
            name="jobs",
            uri="/services/search/jobs",
            handler=handle_jobs,
        ),
        Section(
            name="health",
            uri="/services/server/health/splunkd/details",
            handler=handle_health,
        ),
        Section(
            name="alerts",
            uri="/services/alerts/fired_alerts",
            handler=handle_alerts,
        ),
    ]

    args = parse_arguments(argv)

    sys.stdout.write("<<<check_mk>>>\n")

    try:
        handle_request(args, sections)
    except Exception as e:
        sys.stderr.write("Unhandled exception: %s\n" % e)
        if args.debug:
            return 1


def handle_request(args, sections):
    url_base = "%s://%s:%d" % (args.proto, args.hostname, args.port)

    for section in sections:
        if section.name in args.modules:
            try:
                url = url_base + section.uri

                response = requests.get(
                    url,
                    auth=(args.user, args.password),
                    data={"output_mode": "json"},
                )

                response.raise_for_status()

            except requests.exceptions.RequestException as e:
                sys.stderr.write("Error: %s\n" % e)
                if args.debug:
                    raise
                return 1

            value = response.json().get('entry')
            if value is None:
                continue

            sys.stdout.write("<<<splunk_%s>>>\n" % section.name)
            section.handler(value)


def parse_arguments(argv):

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

    return parser.parse_args(argv)


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
            # Application of the search, may be empty for internal searches
            entries.get("content", {}).get("request", {}).get("ui_dispatch_app", "Unknown"),
            entries["content"]["dispatchState"],  # state of the search
            entries["content"]["isZombie"],  # zombie state (false/true)
        ))


def handle_health(value):
    sys.stdout.write("Overall_state %s\n" % value[0].get("content", {}).get("health"))

    for func, state in value[0]["content"]["features"].items():
        func_name = "%s%s" % (func[0].upper(), func[1:].lower())
        sys.stdout.write("%s %s\n" % (func_name.replace(" ", "_"), state.get("health", {})))

        if state.get("disabled", False):
            # Some functions may have set '"disabled": True' and it seems
            # that "features" are missing in this case
            continue

        for feature, status in state["features"].items():
            feature_name = "%s%s" % (feature[0].upper(), feature[1:].lower())
            sys.stdout.write(
                "%s %s %s\n" %
                (func_name.replace(" ", "_"), feature_name.replace(" ", "_"), status["health"]))


def handle_alerts(value):
    sys.stdout.write("%s\n" % value[0]["content"]["triggered_alert_count"])


if __name__ == "__main__":
    sys.exit(main())
