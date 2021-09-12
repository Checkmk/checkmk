#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import json
import logging
import sys
from typing import NamedTuple

import requests
import urllib3  # type: ignore[import]
from requests.exceptions import ConnectionError as RequestsConnectionError

import cmk.utils.password_store

urllib3.disable_warnings(urllib3.exceptions.SubjectAltNameWarning)
cmk.utils.password_store.replace_passwords()


class Section(NamedTuple):
    name: str
    uri: str


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = parse_arguments(argv)
    setup_logging(args.verbose)

    # possible sections to query
    sections = [
        Section(
            name="cluster",
            uri="overview?columns="
            "cluster_name,"
            "object_totals.connections,"
            "object_totals.channels,"
            "object_totals.queues,"
            "object_totals.consumers,"
            "queue_totals.messages,"
            "queue_totals.messages_ready,"
            "queue_totals.messages_unacknowledged,"
            "message_stats.publish,"
            "message_stats.publish_details.rate,"
            "message_stats.deliver_get,"
            "message_stats.deliver_get.rate,"
            "rabbitmq_version,"
            "erlang_version,",
        ),
        Section(
            name="nodes",
            uri="nodes?columns="
            "mem_used,"
            "mem_limit,"
            "mem_alarm,"
            "disk_free_limit,"
            "disk_free_alarm,"
            "fd_total,"
            "fd_used,"
            "io_file_handle_open_attempt_count,"
            "io_file_handle_open_attempt_count_details,"
            "sockets_total,"
            "sockets_used,"
            "message_stats.disk_reads,"
            "message_stats.disk_writes,"
            "gc_num,"
            "gc_num_details,"
            "gc_bytes_reclaimed,"
            "gc_bytes_reclaimed_details,"
            "proc_total,"
            "proc_used,"
            "run_queue,"
            "name,"
            "type,"
            "running,"
            "uptime",
        ),
        Section(
            name="vhosts",
            uri="vhosts?columns="
            "memory,"
            "messages,"
            "messages_ready,"
            "messages_unacknowledged,"
            "message_stats.publish,"
            "message_stats.publish_details.rate,"
            "message_stats.deliver_get,"
            "message_stats.deliver_get.rate,"
            "name,"
            "description",
        ),
        Section(
            name="queues",
            uri="queues?columns="
            "memory,"
            "messages,"
            "messages_ready,"
            "messages_unacknowledged,"
            "message_stats.publish,"
            "message_stats.publish_details.rate,"
            "message_stats.deliver_get,"
            "message_stats.deliver_get.rate,"
            "name,"
            "node,"
            "type,"
            "state",
        ),
    ]

    try:
        _handle_rabbitmq_connection(args, sections)
    except RequestsConnectionError as connection_error:
        sys.stderr.write("Error connecting to RabbitMQ server: %s\n" % connection_error)
        if args.debug:
            raise
        return 1
    except Exception as unknown_error:
        sys.stderr.write("Unhandled exception: %s\n" % unknown_error)
        if args.debug:
            raise
        return 1

    return 0


def _handle_rabbitmq_connection(args, sections):
    url_base = "%s://%s:%s/api" % (
        args.proto,
        args.hostname,
        args.port,
    )

    for section in sections:
        if section.name not in args.sections:
            logging.warning('Ignoring unknown section "%s"', section.name)
            continue

        section_data = _handle_request("%s/%s" % (url_base, section.uri), args)
        _handle_output(section.name, section_data)


def _handle_output(section, section_data):
    # some sections have multiple entries
    multi_sections = ["nodes", "vhosts", "queues"]

    sys.stdout.write("<<<rabbitmq_%s:sep(0)>>>\n" % section)
    if section in multi_sections:
        for section_value in section_data:
            sys.stdout.write("%s\n" % json.dumps(section_value))
    else:
        sys.stdout.write("%s\n" % json.dumps(section_data))


def _handle_request(url, args):
    response = requests.get(
        url,
        auth=(args.user, args.password),
    )

    response.raise_for_status()

    return response.json()


def setup_logging(verbosity: int) -> None:
    if verbosity >= 3:
        lvl = logging.DEBUG
    elif verbosity == 2:
        lvl = logging.INFO
    elif verbosity == 1:
        lvl = logging.WARN
    else:
        logging.disable(logging.CRITICAL)
        lvl = logging.CRITICAL
    logging.basicConfig(level=lvl, format="%(asctime)s %(levelname)s %(message)s")


def parse_arguments(argv):
    sections = [
        "cluster",
        "nodes",
        "vhosts",
        "queues",
    ]

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--debug",
        action="store_true",
        help="""Debug mode: raise Python exceptions""",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbose mode (for even more output use -vvv)",
    )
    parser.add_argument(
        "-P",
        "--proto",
        default="https",
        required=True,
        help="Use 'http' or 'https' for connection to RabbitMQ (default=https)",
    )
    parser.add_argument(
        "-p",
        "--port",
        default=15672,
        type=int,
        help="Port to use",
    )
    parser.add_argument(
        "-u",
        "--user",
        default=None,
        required=True,
        help="Username for RabbitMQ login",
    )
    parser.add_argument(
        "-s",
        "--password",
        default=None,
        required=True,
        help="Password for RabbitMQ login",
    )
    parser.add_argument(
        "-m",
        "--sections",
        default=sections,
        help="Comma separated list of data to query. Possible values: %s (default: all)"
        % ",".join(sections),
    )
    parser.add_argument(
        "--hostname",
        required=True,
        help="RabbitMQ server to use",
    )

    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
