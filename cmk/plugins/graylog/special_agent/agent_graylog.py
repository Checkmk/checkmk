#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import json
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from typing import TypeAlias

import requests
import urllib3

import cmk.utils.password_store

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
cmk.utils.password_store.replace_passwords()

JsonSerializable: TypeAlias = (
    Mapping[str, "JsonSerializable"]
    | Sequence["JsonSerializable"]
    | str
    | int
    | float
    | bool
    | None
)
DEFAULT_HTTP_TIMEOUT = 60


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    args = parse_arguments(argv)
    with requests.Session() as session:
        session.auth = (args.user, args.password)
        try:
            _probe_api(args, session)
        except requests.exceptions.RequestException as e:
            sys.stderr.write(f"Error: Request to Graylog API failed: '{e}'\n")
            return 2

        # calculate time difference from now and args.since in ISO8601 Format
        since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - args.since))

        handle_section(args, session, "alerts", "/streams/alerts?limit=300", section_alerts)
        handle_section(
            args,
            session,
            "cluster_health",
            "/system/indexer/cluster/health",
            section_cluster_health,
        )
        handle_section(
            args,
            session,
            "cluster_inputstates",
            "/cluster/inputstates",
            section_cluster_inputstates,
        )
        handle_section(
            args, session, "cluster_stats", "/system/cluster/stats", section_cluster_stats
        )
        handle_section(
            args,
            session,
            "cluster_traffic",
            "/system/cluster/traffic?days=1&daily=false",
            section_cluster_traffic,
        )
        handle_section(
            args,
            session,
            "failures",
            "/system/indexer/failures/count/?since=%s" % since,
            section_failures,
        )
        handle_section(
            args, session, "jvm", "/system/metrics/namespace/jvm.memory.heap", section_jvm
        )
        handle_section(
            args,
            session,
            "license",
            "/plugins/org.graylog.plugins.license/licenses/status",
            section_license,
        )
        handle_section(args, session, "messages", "/system/indexer/overview", section_messages)
        handle_section(args, session, "nodes", "/cluster", section_nodes)
        handle_section(args, session, "sidecars", "/sidecars/all", section_sidecars)
        handle_section(args, session, "sources", "/sources", section_sources)
        handle_section(args, session, "streams", "/streams", section_streams)
        handle_section(args, session, "events", "/events/search", section_events)
        return 0
    return 2


def handle_section(
    args: argparse.Namespace,
    session: requests.Session,
    section_name: str,
    section_uri: str,
    handle_function: Callable[[argparse.Namespace, str, requests.Session], JsonSerializable],
) -> None:
    if section_name not in args.sections:
        return
    try:
        section_output = handle_function(args, _get_section_url(args, section_uri), session)
        if section_output:
            handle_output(section_output, section_name, args)
    except (requests.RequestException, RuntimeError) as e:
        sys.stderr.write("Error: %s\n" % e)
        if args.debug:
            raise


def section_alerts(
    args: argparse.Namespace, url: str, session: requests.Session
) -> JsonSerializable:
    section_response = _do_get(url, args, session).json()
    num_of_alerts = section_response.get("total", 0)
    num_of_alerts_in_range = 0
    alerts_since_argument = args.alerts_since
    if alerts_since_argument:
        url_alerts_in_range = f"{url}%since={str(alerts_since_argument)}"
        num_of_alerts_in_range = _do_get(url_alerts_in_range, args, session).json().get("total", 0)

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
    args: argparse.Namespace, url: str, session: requests.Session
) -> JsonSerializable:
    return _do_get(url, args, session).json()


def section_cluster_inputstates(
    args: argparse.Namespace, url: str, session: requests.Session
) -> JsonSerializable:
    return _do_get(url, args, session).json()


def section_cluster_stats(
    args: argparse.Namespace, url: str, session: requests.Session
) -> JsonSerializable:
    return _do_get(url, args, session).json()


def section_cluster_traffic(
    args: argparse.Namespace, url: str, session: requests.Session
) -> JsonSerializable:
    return _do_get(url, args, session).json()


def section_failures(
    args: argparse.Namespace, url: str, session: requests.Session
) -> JsonSerializable:
    section_response = _do_get(url, args, session).json()
    failures_url = _get_base_url(args) + "/system/indexer/failures?limit=30"
    additional_response = _do_get(failures_url, args, session).json()
    return {
        "count": section_response.get("count", 0),
        "ds_param_since": args.since,
    } | additional_response


def section_jvm(args: argparse.Namespace, url: str, session: requests.Session) -> JsonSerializable:
    value = _do_get(url, args, session).json()
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


def section_license(
    args: argparse.Namespace, url: str, session: requests.Session
) -> JsonSerializable:
    try:
        return _do_get(url, args, session).json()
    except ValueError as e:
        raise RuntimeError(f"Could not parse license response from API: '{e}'") from e


def section_messages(
    args: argparse.Namespace, url: str, session: requests.Session
) -> JsonSerializable:
    value = _do_get(url, args, session)
    if value.status_code != 200:
        return value.json()
    return {"events": value.json().get("counts", {}).get("events", 0)}


def section_nodes(
    args: argparse.Namespace, url: str, session: requests.Session
) -> JsonSerializable:
    value = _do_get(url, args, session).json()
    # Add inputstate data
    url_nodes = _get_base_url(args) + "/cluster/inputstates"
    node_inputstates = _do_get(url_nodes, args, session).json()
    node_list = []

    for node_id, node_data in value.items():
        current_node_data = {node_id: node_data.copy()}
        node_journal_data_response = _do_get(
            _get_base_url(args) + f"/cluster/{node_id}/journal", args, session
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


def section_sidecars(
    args: argparse.Namespace, url: str, session: requests.Session
) -> JsonSerializable:
    value = _do_get(url, args, session).json()
    sidecar_list = []
    if sidecars := value.get("sidecars"):
        for sidecar in sidecars:
            if args.display_sidecar_details == "sidecar":
                handle_piggyback(sidecar, args, sidecar["node_name"], "sidecars")
                continue
            sidecar_list.append(sidecar)
    return sidecar_list


def section_sources(
    args: argparse.Namespace, url: str, session: requests.Session
) -> JsonSerializable:
    try:
        sources_response = _do_get(url, args, session).json()
    except ValueError as e:
        raise RuntimeError(f"Could not parse sources response from API: '{e}'") from e

    sources_in_range = {}
    source_since_argument = args.source_since
    if source_since_argument:
        url_sources_in_range = f"{url}?range={str(source_since_argument)}"
        sources_in_range = _do_get(url_sources_in_range, args, session).json().get("sources", {})

    results = {}
    for source, messages in sources_response.get("sources", {}).items():
        source_section = {
            "messages": messages,
            "has_since_argument": bool(source_since_argument),
            "source_since": source_since_argument if source_since_argument else None,
        }
        if source in sources_in_range and sources_in_range[source] is not None:
            source_section["messages_since"] = sources_in_range[source]
        if args.display_source_details == "source":
            handle_piggyback({"sources": {source: source_section}}, args, source, "sources")
        else:
            results[source] = source_section

    return {"sources": results} if args.display_source_details == "host" else []


def section_streams(
    args: argparse.Namespace, url: str, session: requests.Session
) -> JsonSerializable:
    return _do_get(url, args, session).json()


def section_events(
    args: argparse.Namespace, url: str, session: requests.Session
) -> JsonSerializable:
    value = _do_post(url, args, session).json()
    num_of_events = value.get("total_events", 0)
    num_of_events_in_range = 0
    events_since_argument = args.events_since
    if events_since_argument:
        num_of_events_in_range = (
            _do_post(
                url=url,
                args=args,
                session=session,
                json={"timerange": {"type": "relative", "range": events_since_argument}},
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
    return [events]


def _get_base_url(args: argparse.Namespace) -> str:
    return f"{args.proto}://{args.hostname}:{args.port}/api"


def _get_section_url(args: argparse.Namespace, section_uri: str) -> str:
    return f"{_get_base_url(args)}{section_uri}"


def _probe_api(args: argparse.Namespace, session: requests.Session) -> None:
    url = f"{_get_base_url(args)}/system"
    _do_get(url, args, session)


def _do_post(
    url: str,
    args: argparse.Namespace,
    session: requests.Session,
    json: Mapping[str, object] | None = None,
) -> requests.Response:
    response = session.post(
        url,
        headers={
            "Content-Type": "application/json",
            "X-Requested-By": args.user,
        },
        json=json,
        timeout=DEFAULT_HTTP_TIMEOUT,
    )
    response.raise_for_status()
    return response


def _do_get(url: str, args: argparse.Namespace, session: requests.Session) -> requests.Response:
    response = session.get(url, timeout=DEFAULT_HTTP_TIMEOUT)
    response.raise_for_status()
    return response


def handle_output(value: JsonSerializable, section: str, args: argparse.Namespace) -> None:
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


def handle_piggyback(
    value: JsonSerializable,
    args: argparse.Namespace,
    piggyback_name: str,
    section: str,
) -> None:
    sys.stdout.write("<<<<%s>>>>\n" % piggyback_name)
    handle_output(value, section, args)


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
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
