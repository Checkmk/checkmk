#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import json
import sys
import time
from collections.abc import Callable
from typing import Any, NamedTuple

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
        GraylogSection(name="sidecars", uri="/sidecars/all"),
        GraylogSection(name="sources", uri="/sources"),
        GraylogSection(name="streams", uri="/streams"),
        GraylogSection(name="events", uri="/events/search"),
    ]

    handle_section(args, "alerts", "/streams/alerts?limit=300", section_alerts)
    handle_section(args, "cluster_health", "/system/indexer/cluster/health", section_cluster_health)
    handle_section(args, "cluster_inputstates", "/cluster/inputstates", section_cluster_inputstates)
    handle_section(args, "cluster_stats", "/system/cluster/stats", section_cluster_stats)
    handle_section(
        args,
        "cluster_traffic",
        "/system/cluster/traffic?days=1&daily=false",
        section_cluster_traffic,
    )
    handle_section(
        args, "failures", "/system/indexer/failures/count/?since=%s" % since, section_failures
    )
    handle_section(args, "jvm", "/system/metrics/namespace/jvm.memory.heap", section_jvm)
    handle_section(
        args, "license", "/plugins/org.graylog.plugins.license/licenses/status", section_license
    )
    handle_section(args, "messages", "/system/indexer/overview", section_messages)
    handle_section(args, "nodes", "/cluster", section_nodes)

    try:
        handle_request(args, sections)
    except Exception:
        if args.debug:
            raise

    return 0


def handle_section(
    args: argparse.Namespace,
    section_name: str,
    section_uri: str,
    handle_function: Callable[[argparse.Namespace, str], list[dict[str, Any]] | dict[str, Any]],
) -> None:
    if section_name not in args.sections:
        return
    try:
        section_output = handle_function(args, section_uri)
        handle_output(section_output, section_name, args)
    except Exception:
        if args.debug:
            raise


def section_alerts(args: argparse.Namespace, uri: str) -> list[dict[str, Any]] | dict[str, Any]:
    url = _get_section_url(args, uri)
    section_response = handle_response(url, args).json()
    num_of_alerts = section_response.get("total", 0)
    num_of_alerts_in_range = 0
    alerts_since_argument = args.alerts_since
    if alerts_since_argument:
        url_alerts_in_range = f"{url}%since={str(alerts_since_argument)}"
        num_of_alerts_in_range = handle_response(url_alerts_in_range, args).json().get("total", 0)

    alerts = {
        "alerts": {
            "num_of_alerts": num_of_alerts,
            "has_since_argument": bool(alerts_since_argument),
            "alerts_since": alerts_since_argument if alerts_since_argument else None,
            "num_of_alerts_in_range": num_of_alerts_in_range,
        }
    }
    return [alerts]


def section_cluster_health(
    args: argparse.Namespace, uri: str
) -> list[dict[str, Any]] | dict[str, Any]:
    return handle_response(_get_section_url(args, uri), args).json()


def section_cluster_inputstates(
    args: argparse.Namespace, uri: str
) -> list[dict[str, Any]] | dict[str, Any]:
    return handle_response(_get_section_url(args, uri), args).json()


def section_cluster_stats(
    args: argparse.Namespace, uri: str
) -> list[dict[str, Any]] | dict[str, Any]:
    return handle_response(_get_section_url(args, uri), args).json()


def section_cluster_traffic(
    args: argparse.Namespace, uri: str
) -> list[dict[str, Any]] | dict[str, Any]:
    return handle_response(_get_section_url(args, uri), args).json()


def section_failures(args: argparse.Namespace, uri: str) -> list[dict[str, Any]] | dict[str, Any]:
    section_response = handle_response(_get_section_url(args, uri), args).json()
    failures_url = _get_base_url(args) + "/system/indexer/failures?limit=30"
    additional_response = handle_response(failures_url, args).json()
    return {
        "count": section_response.get("count", 0),
        "ds_param_since": args.since,
    } | additional_response


def section_jvm(args: argparse.Namespace, uri: str) -> dict[str, object]:
    value = handle_response(_get_section_url(args, uri), args).json()
    metric_data = value.get("metrics")
    if metric_data is None:
        return {}

    new_value = {}
    for metric in value["metrics"]:
        metric_value = metric.get("metric", {}).get("value")
        metric_name = metric.get("full_name")
        if metric_value is None or metric_name is None:
            continue

        new_value.update({metric_name: metric_value})

    return new_value


def section_license(args: argparse.Namespace, uri: str) -> list[dict[str, Any]] | dict[str, Any]:
    return handle_response(_get_section_url(args, uri), args).json()


def section_messages(args: argparse.Namespace, uri: str) -> list[dict[str, Any]] | dict[str, Any]:
    value = handle_response(_get_section_url(args, uri), args)
    if value.status_code != 200:
        return value.json()
    return {"events": value.json().get("counts", {}).get("events", 0)}


def section_nodes(args: argparse.Namespace, uri: str) -> list[dict[str, Any]] | dict[str, Any]:
    value = handle_response(_get_section_url(args, uri), args).json()
    # Add inputstate data
    url_nodes = _get_base_url(args) + "/cluster/inputstates"
    node_inputstates = handle_response(url_nodes, args).json()
    node_list = []

    for node_id, node_data in value.items():
        current_node_data = {node_id: node_data.copy()}
        node_journal_data_response = handle_response(
            _get_base_url(args) + f"/cluster/{node_id}/journal",
            args,
        )
        node_journal_data = node_journal_data_response.json()
        current_node_data[node_id].update({"journal": node_journal_data})

        # Assign inputstates to individual nodes present in cluster
        if node_id not in node_inputstates:
            continue

        current_node_data[node_id].update({"inputstates": node_inputstates[node_id]})

        if args.display_node_details == "node":
            # Hand over node data to piggyback (and only that)
            node_hostname = current_node_data[node_id]["hostname"]
            handle_piggyback(current_node_data, args, node_hostname, "nodes")
            continue

        node_list.append(current_node_data)
    return node_list


def _get_base_url(args: argparse.Namespace) -> str:
    return f"{args.proto}://{args.hostname}:{args.port}/api"


def _get_section_url(args: argparse.Namespace, section_uri: str) -> str:
    return f"{_get_base_url(args)}{section_uri}"


def handle_request(args, sections):
    url_base = f"{args.proto}://{args.hostname}:{args.port}/api"

    for section in sections:
        if section.name not in args.sections:
            continue

        url = url_base + section.uri

        # Fill the variable `value` with the response from the API.
        # If sections require special or additional handling, this will
        # be done afterwards.
        if section.name == "events":
            value = handle_response(url, args, "POST").json()
        else:
            value = handle_response(url, args).json()

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
            response = requests.post(
                url,
                auth=(args.user, args.password),
                headers={
                    "Content-Type": "application/json",
                    "X-Requested-By": args.user,
                },
                json={"timerange": {"type": "relative", "range": events_since}},
                timeout=900,
            )
        except requests.exceptions.RequestException as e:
            sys.stderr.write("Error: %s\n" % e)
            if args.debug:
                raise

    else:
        try:
            response = requests.get(url, auth=(args.user, args.password), timeout=900)
        except requests.exceptions.RequestException as e:
            sys.stderr.write("Error: %s\n" % e)
            if args.debug:
                raise

    return response


def handle_output(
    value: list[dict[str, Any]] | dict[str, Any], section: str, args: argparse.Namespace
) -> None:
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
        "-p", "--port", default=443, type=int, help="Use alternative port (default: 443)"
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
        "--debug", action="store_true", help="Debug mode: let Python exceptions come through"
    )

    parser.add_argument(
        "hostname", metavar="HOSTNAME", help="Name of the graylog instance to query."
    )

    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
