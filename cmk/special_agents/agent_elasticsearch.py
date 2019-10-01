#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
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

from __future__ import division
import argparse
import sys
import requests


def main():

    args = parse_arguments()

    try:
        user = args.user
    except TypeError:
        user = None
    try:
        pwd = args.password
    except TypeError:
        pwd = None

    opt_port = args.port
    query_objects = args.modules
    opt_proto = args.proto
    opt_debug = args.debug
    elastic_host = args.HOSTNAME

    sys.stdout.write('<<<check_mk>>>\n')
    handle_request(user, pwd, opt_port, query_objects, opt_proto, opt_debug, elastic_host)


def handle_request(user, pwd, opt_port, query_objects, opt_proto, opt_debug, elastic_host):

    for host in elastic_host:
        url_base = "%s://%s:%d" % (opt_proto, host, int(opt_port))

        # Sections to query
        # Cluster health: https://www.elastic.co/guide/en/elasticsearch/reference/current/cluster-health.html
        # Node stats: https://www.elastic.co/guide/en/elasticsearch/reference/current/cluster-nodes-stats.html
        # Indices Stats: https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-stats.html
        sections = {
            'cluster_health': '/_cluster/health',
            'nodes': '/_nodes/_all/stats',
            'stats': '/*-*/_stats/store,docs',
        }

        try:
            for section in query_objects:
                url = url_base + sections[section]

                try:
                    if user and pwd:
                        response = requests.get(url, auth=(user, pwd))
                    else:
                        response = requests.get(url)
                except requests.exceptions.RequestException:
                    if opt_debug:
                        raise
                else:
                    sys.stdout.write("<<<elasticsearch_%s>>>\n" % section)

                if section == 'cluster_health' and 'cluster_health' in query_objects:
                    handle_cluster_health(response)
                elif section == 'nodes' and 'nodes' in query_objects:
                    handle_nodes(response)
                # checks for stats section follow soon
                elif section == 'stats' and 'stats' in query_objects:
                    handle_stats(response)
            sys.exit(0)
        except Exception:
            if opt_debug:
                raise


def parse_arguments(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("-u", "--user", default=None, help="Username for elasticsearch login")
    parser.add_argument("-s", "--password", default=None, help="Password for easticsearch login")
    parser.add_argument(
        "-P",
        "--proto",
        default="https",
        help="Use 'http' or 'https' for connection to elasticsearch (default=https)")
    parser.add_argument("-p", "--port", default=9200, help="Use alternative port (default: 9200)")
    parser.add_argument(
        "-m",
        "--modules",
        type=lambda x: x.split(' '),
        default="cluster_health nodes stats",
        help=
        "Space-separated list of modules to query. Possible values: cluster_health, nodes, stats (default: all)"
    )
    parser.add_argument("--debug",
                        action="store_true",
                        help="Debug mode: let Python exceptions come through")

    parser.add_argument(
        "HOSTNAME",
        nargs="*",
        help=
        "You can define one or more elasticsearch instances to query. First instance where data is queried wins."
    )

    return parser.parse_args()


def handle_cluster_health(response):
    for item, value in response.json().iteritems():
        sys.stdout.write("%s %s\n" % (item, value))


def handle_nodes(response):
    for node in response.json()["nodes"]:
        node = response.json()["nodes"][node]
        proc = node["process"]
        cpu = proc["cpu"]
        mem = proc["mem"]

        sys.stdout.write("%s open_file_descriptors %s\n" %
                         (node["name"], proc["open_file_descriptors"]))
        sys.stdout.write("%s max_file_descriptors %s\n" %
                         (node["name"], proc["max_file_descriptors"]))
        sys.stdout.write("%s cpu_percent %s\n" % (node["name"], cpu["percent"]))
        sys.stdout.write("%s cpu_total_in_millis %s\n" % (node["name"], cpu["total_in_millis"]))
        sys.stdout.write("%s mem_total_virtual_in_bytes %s\n" %
                         (node["name"], mem["total_virtual_in_bytes"]))


def handle_stats(response):
    sys.stdout.write("<<<elasticsearch_shards>>>\n")
    shards = response.json()["_shards"]
    sys.stdout.write("%s %s %s\n" % (shards["total"], shards["successful"], shards["failed"]))

    sys.stdout.write("<<<elasticsearch_cluster>>>\n")
    if "docs" in response.json()["_all"]["total"]:
        count = response.json()["_all"]["total"]["docs"]["count"]
        size = response.json()["_all"]["total"]["store"]["size_in_bytes"]
        sys.stdout.write("%s %s\n" % (count, size))

    sys.stdout.write("<<<elasticsearch_indices>>>\n")
    indices = set()
    for ind in response.json()["indices"]:
        indices.add(ind[:-11])
    for indice in list(indices):
        all_counts = []
        all_sizes = []
        for ind in response.json()["indices"]:
            if ind[:-11] == indice:
                all_counts.append(response.json()["indices"][ind]["total"]["docs"]["count"])
                all_sizes.append(response.json()["indices"][ind]["total"]["store"]["size_in_bytes"])
        sys.stdout.write("%s %s %s\n" % (indice, sum(all_counts) / len(all_counts),
                                         sum(all_sizes) / len(all_sizes)))  # fixed: true-division
