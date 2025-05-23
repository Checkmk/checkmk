#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import json
import sys
import time
from typing import NamedTuple

import requests
import urllib3

import cmk.utils.password_store

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
cmk.utils.password_store.replace_passwords()


class GraylogSection(NamedTuple):
    name: str
    uri: str


def _probe_api(args: argparse.Namespace) -> None:
    url = f"{args.proto}://{args.hostname}:{args.port}/api/system"
    response = requests.get(url, auth=(args.user, args.password), timeout=900)
    response.raise_for_status()


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = parse_arguments(argv)

    try:
        _probe_api(args)
    except requests.exceptions.RequestException as e:
        sys.stderr.write(f"Error: Request to Graylog API failed: '{e}'\n")
        return 2

    # calculate time difference from now and args.since in ISO8601 Format
    since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - args.since))

    # Add new queries here
    sections = [
        GraylogSection(name="alerts", uri="/streams/alerts?limit=300"),
        GraylogSection(name="cluster_health", uri="/system/indexer/cluster/health"),
        GraylogSection(name="cluster_inputstates", uri="/cluster/inputstates"),
        GraylogSection(name="cluster_stats", uri="/system/cluster/stats"),
        GraylogSection(name="cluster_traffic", uri="/system/cluster/traffic?days=1&daily=false"),
        GraylogSection(name="failures", uri="/system/indexer/failures/count/?since=%s" % since),
        GraylogSection(name="jvm", uri="/system/metrics/namespace/jvm.memory.heap"),
        GraylogSection(name="license", uri="/plugins/org.graylog.plugins.license/licenses/status"),
        GraylogSection(name="messages", uri="/count/total"),
        GraylogSection(name="nodes", uri="/cluster"),
        GraylogSection(name="sidecars", uri="/sidecars/all"),
        GraylogSection(name="sources", uri="/sources"),
        GraylogSection(name="streams", uri="/streams"),
        GraylogSection(name="events", uri="/events/search"),
    ]

    try:
        handle_request(args, sections)
    except Exception:
        if args.debug:
            return 1

    return 0


def handle_request(args, sections):  # pylint: disable=too-many-branches
    url_base = f"{args.proto}://{args.hostname}:{args.port}/api"

    for section in sections:
        if section.name not in args.sections:
            continue

        url = url_base + section.uri

        if section.name == "events":
            value = handle_response(url, args, "POST").json()
        else:
            value = handle_response(url, args).json()

        # add failure details
        if section.name == "failures":
            url_failures = url_base + "/system/indexer/failures?limit=30"

            value.update(handle_response(url_failures, args).json())

            # add param from datasource for use in check output
            value.update({"ds_param_since": args.since})

        if section.name == "nodes":
            url_nodes = url_base + "/cluster/inputstates"
            node_inputstates = handle_response(url_nodes, args).json()

            node_list = []
            for node in node_inputstates:
                if node in value:
                    value[node].update({"inputstates": node_inputstates[node]})
                    new_value = {node: value[node]}
                    if args.display_node_details == "node":
                        handle_piggyback(new_value, args, new_value[node]["hostname"], section.name)
                        continue
                    node_list.append(new_value)

            if node_list:
                handle_output(node_list, section.name, args)

        if section.name == "jvm":
            metric_data = value.get("metrics")
            if metric_data is None:
                continue

            new_value = {}
            for metric in value["metrics"]:
                metric_value = metric.get("metric", {}).get("value")
                metric_name = metric.get("full_name")
                if metric_value is None or metric_name is None:
                    continue

                new_value.update({metric_name: metric_value})

            value = new_value

        if section.name == "sidecars":
            sidecars = value.get("sidecars")
            if sidecars is not None:
                sidecar_list = []
                for sidecar in sidecars:
                    if args.display_sidecar_details == "sidecar":
                        handle_piggyback(sidecar, args, sidecar["node_name"], section.name)
                        continue
                    sidecar_list.append(sidecar)

                if sidecar_list:
                    handle_output(sidecar_list, section.name, args)

        if section.name == "events":
            num_of_events = value.get("total_events", 0)
            num_of_events_in_range = 0
            events_since_argument = args.events_since

            if events_since_argument:
                num_of_events_in_range = (
                    handle_response(
                        url=url,
                        args=args,
                        method="POST",
                        events_since=args.events_since,
                    )
                    .json()
                    .get("total_events", 0)
                )

            events = {
                "events": {
                    "num_of_events": num_of_events,
                    "has_since_argument": bool(events_since_argument),
                    "events_since": events_since_argument if events_since_argument else None,
                    "num_of_events_in_range": num_of_events_in_range,
                }
            }
            handle_output([events], section.name, args)

        if section.name == "alerts":
            num_of_alerts = value.get("total", 0)
            num_of_alerts_in_range = 0
            alerts_since_argument = args.alerts_since

            if alerts_since_argument:
                url_alerts_in_range = f"{url}%since={str(alerts_since_argument)}"
                num_of_alerts_in_range = (
                    handle_response(url_alerts_in_range, args).json().get("total", 0)
                )

            alerts = {
                "alerts": {
                    "num_of_alerts": num_of_alerts,
                    "has_since_argument": bool(alerts_since_argument),
                    "alerts_since": alerts_since_argument if alerts_since_argument else None,
                    "num_of_alerts_in_range": num_of_alerts_in_range,
                }
            }
            handle_output([alerts], section.name, args)

        if section.name == "sources":
            sources_in_range = {}
            source_since_argument = args.source_since

            if source_since_argument:
                url_sources_in_range = f"{url_base}/sources?range={str(source_since_argument)}"
                sources_in_range = (
                    handle_response(url_sources_in_range, args).json().get("sources", {})
                )

            if (sources := value.get("sources")) is None:
                continue

            value = {"sources": {}}
            for source, messages in sources.items():
                value["sources"].setdefault(
                    source,
                    {
                        "messages": messages,
                        "has_since_argument": bool(source_since_argument),
                        "source_since": source_since_argument if source_since_argument else None,
                    },
                )

                if source in sources_in_range:
                    value["sources"][source].update(
                        {
                            "messages_since": sources_in_range[source],
                        }
                    )

                if args.display_source_details == "source":
                    handle_piggyback(value, args, source, section.name)
                    value = {"sources": {}}

            if args.display_source_details == "host":
                handle_output([value], section.name, args)

        if section.name not in ["nodes", "sidecars", "sources", "alerts", "events"]:
            handle_output(value, section.name, args)


def handle_response(url, args, method="GET", events_since=86400):
    if method == "POST":
        try:
            response = requests.post(  # nosec B113
                url,
                auth=(args.user, args.password),
                headers={
                    "Content-Type": "application/json",
                    "X-Requested-By": args.user,
                },
                json={"timerange": {"type": "relative", "range": events_since}},
            )
        except requests.exceptions.RequestException as e:
            sys.stderr.write("Error: %s\n" % e)
            if args.debug:
                raise

    else:
        try:
            response = requests.get(url, auth=(args.user, args.password))  # nosec B113
        except requests.exceptions.RequestException as e:
            sys.stderr.write("Error: %s\n" % e)
            if args.debug:
                raise

    return response


def handle_output(value, section, args):
    sys.stdout.write("<<<graylog_%s:sep(0)>>>\n" % section)
    if isinstance(value, list):
        for entry in value:
            sys.stdout.write("%s\n" % json.dumps(entry))
        return

    sys.stdout.write("%s\n" % json.dumps(value))

    for name, param_piggyback, value_piggyback in [
        ("nodes", args.display_node_details, "node"),
        ("sidecars", args.display_sidecar_details, "sidecar"),
        ("sources", args.display_source_details, "source"),
    ]:
        if section == name and param_piggyback == value_piggyback:
            sys.stdout.write("<<<<>>>>\n")

    return


def handle_piggyback(value, args, piggyback_name, section):
    sys.stdout.write("<<<<%s>>>>\n" % piggyback_name)
    handle_output(value, section, args)


def parse_arguments(argv):
    sections = [
        "alerts",
        "cluster_stats",
        "cluster_traffic",
        "failures",
        "jvm",
        "license",
        "messages",
        "nodes",
        "sidecars",
        "sources",
        "streams",
        "events",
    ]

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("-u", "--user", default=None, help="Username for graylog login")
    parser.add_argument("-s", "--password", default=None, help="Password for graylog login")
    parser.add_argument(
        "-P",
        "--proto",
        default="https",
        help="Use 'http' or 'https' for connection to graylog (default=https)",
    )
    parser.add_argument(
        "-p",
        "--port",
        default=443,
        type=int,
        help="Use alternative port (default: 443)",
    )
    parser.add_argument(
        "-t",
        "--since",
        default=1800,
        type=int,
        help="The time in seconds, since when failures should be covered",
    )
    parser.add_argument(
        "--source_since",
        default=None,
        type=int,
        help="The time in seconds, since when source messages should be covered",
    )
    parser.add_argument(
        "--alerts_since",
        default=None,
        type=int,
        help="The time in seconds, since when alerts should be covered",
    )
    parser.add_argument(
        "--events_since",
        default=None,
        type=int,
        help="The time in seconds, since when events should be covered",
    )
    parser.add_argument(
        "-m",
        "--sections",
        default=sections,
        help="""Comma separated list of data to query. Possible values: %s (default: all)"""
        % ", ".join(sections),
    )
    parser.add_argument(
        "--display_node_details",
        default=None,
        choices=("host", "node"),
        help="""You can optionally choose, where the node details are shown.
        Default is the queried graylog host. Possible values: host, node (default: host)""",
    )
    parser.add_argument(
        "--display_sidecar_details",
        default="host",
        choices=("host", "sidecar"),
        help="""You can optionally choose, where the sidecar details are shown.
        Default is the queried graylog host. Possible values: host, sidecar (default: host)""",
    )
    parser.add_argument(
        "--display_source_details",
        default="host",
        choices=("host", "source"),
        help="""You can optionally choose, where the source details are shown.
        Default is the queried graylog host. Possible values: host, source (default: host)""",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug mode: let Python exceptions come through",
    )

    parser.add_argument(
        "hostname", metavar="HOSTNAME", help="Name of the graylog instance to query."
    )

    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
