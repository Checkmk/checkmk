#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from collections.abc import Mapping, Sequence

import pydantic
import requests

from cmk.special_agents.v0_unstable.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser


def agent_elasticsearch_main(args: Args) -> int:
    for host in args.hosts:
        url_base = "%s://%s:%d" % (args.proto, host, args.port)

        # Sections to query
        # Cluster health: https://www.elastic.co/guide/en/elasticsearch/reference/current/cluster-health.html
        # Node stats: https://www.elastic.co/guide/en/elasticsearch/reference/current/cluster-nodes-stats.html
        # Indices Stats: https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-stats.html
        section_urls_and_handlers = {
            "cluster_health": ("/_cluster/health", handle_cluster_health),
            "nodes": ("/_nodes/_all/stats", handle_nodes),
            "stats": ("/_stats/store,docs?ignore_unavailable=true", handle_stats),
        }

        sections_to_query = set()
        if args.cluster_health:
            sections_to_query.add("cluster_health")
        if args.nodes:
            sections_to_query.add("nodes")
        if args.stats:
            sections_to_query.add("stats")

        try:
            for section in sections_to_query:
                section_url, handler = section_urls_and_handlers[section]

                url = (
                    f"{url_base}/{','.join(args.stats)}{section_url}"
                    if section == "stats"
                    else f"{url_base}{section_url}"
                )

                auth = (args.user, args.password) if args.user and args.password else None
                certcheck = not args.no_cert_check
                try:
                    response = requests.get(url, auth=auth, verify=certcheck, timeout=900)
                except requests.exceptions.RequestException as e:
                    sys.stderr.write("Error: %s\n" % e)
                    if args.debug:
                        raise

                handler(response.json())

        except Exception:
            if args.debug:
                raise
            return 1

    return 0


def parse_arguments(argv: Sequence[str] | None) -> Args:
    parser = create_default_argument_parser(description=__doc__)

    parser.add_argument("-u", "--user", default=None, help="Username for elasticsearch login")
    parser.add_argument("-s", "--password", default=None, help="Password for easticsearch login")
    parser.add_argument(
        "-P",
        "--proto",
        default="https",
        help="Use 'http' or 'https' for connection to elasticsearch (default=https)",
    )
    parser.add_argument(
        "-p", "--port", default=9200, type=int, help="Use alternative port (default: 9200)"
    )
    parser.add_argument(
        "--no-cert-check", action="store_true", help="Disable certificate verification."
    )

    parser.add_argument("--cluster-health", action="store_true", help="Query cluster health data")
    parser.add_argument("--nodes", action="store_true", help="Query nodes data")

    parser.add_argument(
        "--stats",
        nargs="*",
        default=[],
        help="List of patterns for the statistics query",
    )

    parser.add_argument(
        "hosts",
        metavar="HOSTNAME",
        nargs="+",
        help="You can define one or more elasticsearch instances to query. First instance where data is queried wins.",
    )

    return parser.parse_args(argv)


def handle_cluster_health(response: Mapping[str, object]) -> None:
    with SectionWriter("elasticsearch_cluster_health", separator=" ") as writer:
        for item, value in response.items():
            writer.append(f"{item} {value}")


class _CPUResponse(pydantic.BaseModel, frozen=True):
    percent: int
    total_in_millis: int


class _MemResponse(pydantic.BaseModel, frozen=True):
    total_virtual_in_bytes: int


class _ProcessResponse(pydantic.BaseModel, frozen=True):
    open_file_descriptors: int
    max_file_descriptors: int
    cpu: _CPUResponse
    mem: _MemResponse


class _NodeReponse(pydantic.BaseModel, frozen=True):
    name: str
    process: _ProcessResponse


class _NodesReponse(pydantic.BaseModel, frozen=True):
    nodes: Mapping[str, _NodeReponse]


def handle_nodes(response: Mapping[str, object]) -> None:
    with SectionWriter("elasticsearch_nodes", separator=" ") as writer:
        for node_response in _NodesReponse.model_validate(response).nodes.values():
            writer.append(
                f"{node_response.name} open_file_descriptors {node_response.process.open_file_descriptors}"
            )
            writer.append(
                f"{node_response.name} max_file_descriptors {node_response.process.max_file_descriptors}"
            )
            writer.append(f"{node_response.name} cpu_percent {node_response.process.cpu.percent}")
            writer.append(
                f"{node_response.name} cpu_total_in_millis {node_response.process.cpu.total_in_millis}"
            )
            writer.append(
                f"{node_response.name} mem_total_virtual_in_bytes {node_response.process.mem.total_virtual_in_bytes}"
            )


def handle_stats(response: Mapping[str, object]) -> None:
    with SectionWriter("elasticsearch_indices") as writer:
        writer.append_json(response["indices"])


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(parse_arguments, agent_elasticsearch_main)
