#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from typing import Optional, Sequence

import requests

from cmk.special_agents.utils.agent_common import special_agent_main
from cmk.special_agents.utils.argument_parsing import Args, create_default_argument_parser


def agent_elasticsearch_main(args: Args) -> None:
    for host in args.hosts:
        url_base = "%s://%s:%d" % (args.proto, host, args.port)

        # Sections to query
        # Cluster health: https://www.elastic.co/guide/en/elasticsearch/reference/current/cluster-health.html
        # Node stats: https://www.elastic.co/guide/en/elasticsearch/reference/current/cluster-nodes-stats.html
        # Indices Stats: https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-stats.html
        sections = {
            "cluster_health": "/_cluster/health",
            "nodes": "/_nodes/_all/stats",
            "stats": "/*-*/_stats/store,docs",
        }

        try:
            for section in args.modules:
                url = url_base + sections[section]

                auth = (args.user, args.password) if args.user and args.password else None
                certcheck = not args.no_cert_check
                try:
                    response = requests.get(url, auth=auth, verify=certcheck)
                except requests.exceptions.RequestException as e:
                    sys.stderr.write("Error: %s\n" % e)
                    if args.debug:
                        raise
                else:
                    sys.stdout.write("<<<elasticsearch_%s>>>\n" % section)

                json_response = response.json()
                if section == "cluster_health":
                    handle_cluster_health(json_response)
                elif section == "nodes":
                    handle_nodes(json_response)
                elif section == "stats":
                    handle_stats(json_response)
            sys.exit(0)
        except Exception:
            if args.debug:
                raise


def parse_arguments(argv: Optional[Sequence[str]]) -> Args:

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
        "-m",
        "--modules",
        type=lambda x: x.split(" "),
        default="cluster_health nodes stats",
        help="Space-separated list of modules to query. Possible values: cluster_health, nodes, stats (default: all)",
    )
    parser.add_argument(
        "--no-cert-check", action="store_true", help="Disable certificate verification"
    )
    parser.add_argument(
        "hosts",
        metavar="HOSTNAME",
        nargs="+",
        help="You can define one or more elasticsearch instances to query. First instance where data is queried wins.",
    )

    return parser.parse_args(argv)


def handle_cluster_health(response):
    for item, value in response.items():
        sys.stdout.write("%s %s\n" % (item, value))


def handle_nodes(response):
    nodes_data = response.get("nodes")
    if nodes_data is not None:
        for node in nodes_data:
            node = nodes_data[node]
            proc = node["process"]
            cpu = proc["cpu"]
            mem = proc["mem"]

            sys.stdout.write(
                "%s open_file_descriptors %s\n" % (node["name"], proc["open_file_descriptors"])
            )
            sys.stdout.write(
                "%s max_file_descriptors %s\n" % (node["name"], proc["max_file_descriptors"])
            )
            sys.stdout.write("%s cpu_percent %s\n" % (node["name"], cpu["percent"]))
            sys.stdout.write("%s cpu_total_in_millis %s\n" % (node["name"], cpu["total_in_millis"]))
            sys.stdout.write(
                "%s mem_total_virtual_in_bytes %s\n" % (node["name"], mem["total_virtual_in_bytes"])
            )


def handle_stats(response):
    shards = response.get("_shards")
    if shards is not None:
        sys.stdout.write("<<<elasticsearch_shards>>>\n")

        sys.stdout.write(
            "%s %s %s\n" % (shards.get("total"), shards.get("successful"), shards.get("failed"))
        )

    docs = response.get("_all", {}).get("total")
    if docs is not None:
        sys.stdout.write("<<<elasticsearch_cluster>>>\n")
        count = docs.get("docs", {}).get("count")
        size = docs.get("store", {}).get("size_in_bytes")

        sys.stdout.write("%s %s\n" % (count, size))

    indices_data = response.get("indices")
    if indices_data is not None:
        indices = set()

        sys.stdout.write("<<<elasticsearch_indices>>>\n")
        for index in indices_data:
            indices.add(index.split("-")[0])
        for indice in list(indices):
            all_counts = []
            all_sizes = []
            for index in indices_data:
                if index.split("-")[0] == indice:
                    all_counts.append(
                        indices_data.get(index, {})
                        .get("primaries", {})
                        .get("docs", {})
                        .get("count")
                    )
                    all_sizes.append(
                        indices_data.get(index, {})
                        .get("total", {})
                        .get("store", {})
                        .get("size_in_bytes")
                    )
            sys.stdout.write(
                "%s %s %s\n"
                % (indice, sum(all_counts) / len(all_counts), sum(all_sizes) / len(all_sizes))
            )  # fixed: true-division


def main():
    """Main entry point to be used"""
    special_agent_main(parse_arguments, agent_elasticsearch_main)
