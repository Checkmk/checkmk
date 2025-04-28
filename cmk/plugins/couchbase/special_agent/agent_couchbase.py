#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent for monitoring Couchbase servers with Checkmk
"""

import logging
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from typing import Any, TypeVar

import requests

from cmk.special_agents.v0_unstable.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser

LOGGER = logging.getLogger(__name__)

SECTION_KEYS_INFO = (
    "clusterCompatibility",
    "clusterMembership",
    "status",
    "otpNode",
    "recoveryType",
    "version",
)

SECTION_KEYS_STATS = (
    "cpu_utilization_rate",
    "mem_total",
    "mem_free",
    "swap_total",
    "swap_used",
)

SECTION_KEYS_CACHE = (
    "ep_bg_fetched",
    "get_hits",
)

SECTION_KEYS_ITEMS = (
    "curr_items",
    "curr_items_tot",
    "vb_active_num_non_resident",
)

SECTION_KEYS_SERVICES = ("services",)

SECTION_KEYS_PORTS = ("ports",)

SECTION_KEYS_SIZE = (
    "couch_docs_actual_disk_size",
    "couch_docs_data_size",
    "couch_spatial_data_size",
    "couch_spatial_disk_size",
    "couch_views_actual_disk_size",
    "couch_views_data_size",
)

SECTION_KEYS_B_MEM = (
    "mem_total",
    "mem_free",
    "ep_mem_high_wat",
    "ep_mem_low_wat",
)

SECTION_KEYS_B_OPERATIONS = (
    "ops",
    "cmd_get",
    "cmd_set",
    "ep_num_ops_del_meta",
    "ep_ops_create",
    "ep_ops_update",
)

SECTION_KEYS_B_ITEMS = (
    "curr_items_tot",
    "ep_bg_fetched",
    "ep_diskqueue_drain",
    "ep_diskqueue_fill",
    "disk_write_queue",
)

SECTION_KEYS_B_VBUCKET = (
    "vb_active_resident_items_ratio",
    "vb_active_eject",
    "vb_active_itm_memory",
    "vb_active_ops_create",
    "vb_pending_num",
    "vb_replica_num",
    "vb_replica_itm_memory",
)

SECTION_KEYS_B_FRAGMENTATION = (
    "couch_docs_fragmentation",
    "couch_views_fragmentation",
)

SECTION_KEYS_B_CACHE = ("ep_cache_miss_rate",)

#
# These bucket related keys are not (yet) in use.
#
#    "ep_ops_create",
#    "ep_diskqueue_drain",
#    "ep_diskqueue_fill",
#    "ep_bg_fetched",
#    "ep_ops_update",
#    "disk_write_queue",
#    "couch_docs_fragmentation",
#    "couch_views_fragmentation",
#    "ep_mem_high_wat",
#    "ep_mem_low_wat",
#    "vb_active_resident_items_ratio",
#    "vb_active_eject",
#    "vb_active_itm_memory",
#    "vb_active_ops_create",
#    "vb_pending_num",
#    "vb_replica_num",
#    "vb_replica_itm_memory",
#    "curr_items_tot",
#


def parse_arguments(argv: Sequence[str] | None) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=10,
        help="Timeout for API-calls in seconds. Default: 10",
    )
    parser.add_argument(
        "-b",
        "--buckets",
        default=[],
        action="append",
        help="Gives a bucket to monitor. Can be used multiple times.",
    )
    parser.add_argument(
        "-P", "--port", type=int, default=8091, help="Gives the port for API-calls. Default: 8091"
    )
    parser.add_argument(
        "-u", "--username", default=None, help="The username for authentication at the API."
    )
    parser.add_argument(
        "-p", "--password", default=None, help="The password for authentication at the API."
    )
    parser.add_argument("hostname", help="Host or ip address to contact.")

    return parser.parse_args(argv)


def set_up_logging(verbosity: int) -> None:
    fmt = "%(levelname)s: %(message)s"
    if verbosity >= 2:
        fmt = "%(levelname)s: %(name)s: %(filename)s: %(lineno)s %(message)s"
        lvl = logging.DEBUG
    else:
        lvl = logging.INFO if verbosity else logging.WARNING

    logging.basicConfig(level=lvl, format=fmt)


class CouchbaseClient:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        timeout: int,
        credentials: tuple[str, str] | None,
    ) -> None:
        self._session = requests.Session()
        self._timeout = timeout
        if credentials:
            self._session.auth = credentials
        self._base = f"http://{host}:{port}/pools/default"

    def _get_suburi(self, suburi: str) -> Any:
        uri = self._base + suburi
        LOGGER.debug("request GET %r", uri)

        try:
            response = self._session.get(uri, timeout=self._timeout)
            response.raise_for_status()
        except (requests.ConnectionError, requests.HTTPError):
            LOGGER.warning("%r could not be reached", uri)
            raise

        try:
            return response.json()
        except ValueError:
            LOGGER.warning("Invalid response: %r", response)
            raise

    def get_pool(self) -> Mapping[str, Any]:
        """Gets the pools response"""
        # https://docs.couchbase.com/server/current/rest-api/rest-cluster-details.html#response
        return self._get_suburi("")

    def get_bucket(self, bucket: str) -> Mapping[str, Any]:
        # See https://docs.couchbase.com/server/current/rest-api/rest-bucket-stats.html#response-2
        return self._get_suburi("/buckets/%s/stats" % bucket)


_TRawData = TypeVar("_TRawData")


def _get_dump(
    node_name: str,
    raw_data: Mapping[str, _TRawData],
    filter_keys: Iterable[str],
    process: Callable[[_TRawData], object] = lambda x: x,
) -> dict[str, object]:
    data: dict[str, object] = {"name": node_name}
    for key in filter_keys:
        if key in raw_data:
            data[key] = process(raw_data[key])
    return data


def sections_node(client: CouchbaseClient) -> None:
    node_list = [
        (
            node["hostname"].split(":")[0],
            node,
        )
        for node in client.get_pool().get("nodes", ())
    ]

    for section_name, section_generator_str in [
        (
            "couchbase_nodes_uptime",
            ("{} {}".format(node["uptime"], name) for name, node in node_list),
        ),
        (
            "couchbase_nodes_operations",
            (
                "{} {}".format(node.get("interestingStats", {}).get("ops"), name)
                for name, node in node_list
            ),
        ),
    ]:
        with SectionWriter(section_name, separator=None) as section_writer:
            section_writer.append(section_generator_str)

    for section_name, section_generator_dict in [
        (
            "couchbase_nodes_info",
            (_get_dump(name, node, SECTION_KEYS_INFO) for name, node in node_list),
        ),
        (
            "couchbase_nodes_services",
            (_get_dump(name, node, SECTION_KEYS_SERVICES) for name, node in node_list),
        ),
        (
            "couchbase_nodes_ports",
            (_get_dump(name, node, SECTION_KEYS_PORTS) for name, node in node_list),
        ),
        (
            "couchbase_nodes_stats",
            (
                _get_dump(name, node.get("systemStats", {}), SECTION_KEYS_STATS)
                for name, node in node_list
            ),
        ),
        (
            "couchbase_nodes_cache",
            (
                _get_dump(name, node.get("interestingStats", {}), SECTION_KEYS_CACHE)
                for name, node in node_list
            ),
        ),
        (
            "couchbase_nodes_items",
            (
                _get_dump(name, node.get("interestingStats", {}), SECTION_KEYS_ITEMS)
                for name, node in node_list
            ),
        ),
        (
            "couchbase_nodes_size",
            (
                _get_dump(name, node.get("interestingStats", {}), SECTION_KEYS_SIZE)
                for name, node in node_list
            ),
        ),
    ]:
        with SectionWriter(section_name) as section_writer:
            section_writer.append_json(section_generator_dict)


def fetch_bucket_data(
    client: CouchbaseClient,
    buckets: Iterable[str],
    debug: bool,
) -> Iterator[tuple[str, Mapping[str, Sequence[float]]]]:
    for bucket in buckets:
        try:
            response = client.get_bucket(bucket)
        except (ValueError, KeyError, requests.ConnectionError, requests.HTTPError):
            if debug:
                raise
            continue
        yield bucket, response.get("op", {}).get("samples", {})


def _average(value_list: Sequence[float]) -> float | None:
    if value_list:
        return sum(value_list) / float(len(value_list))
    return None


def sections_buckets(bucket_list: Sequence[tuple[str, Mapping[str, Sequence[float]]]]) -> None:
    for section_name, filter_keys in [
        (
            "couchbase_buckets_mem",
            SECTION_KEYS_B_MEM,
        ),
        (
            "couchbase_buckets_operations",
            SECTION_KEYS_B_OPERATIONS,
        ),
        (
            "couchbase_buckets_cache",
            SECTION_KEYS_B_CACHE,
        ),
        (
            "couchbase_buckets_vbuckets",
            SECTION_KEYS_B_VBUCKET,
        ),
        (
            "couchbase_buckets_fragmentation",
            SECTION_KEYS_B_FRAGMENTATION,
        ),
        (
            "couchbase_buckets_items",
            SECTION_KEYS_B_ITEMS,
        ),
    ]:
        with SectionWriter(section_name) as section_writer:
            for name, data in bucket_list:
                section_writer.append_json(_get_dump(name, data, filter_keys, _average))


def couchbase_main(args: Args) -> int:
    set_up_logging(args.verbose)

    client = CouchbaseClient(
        host=args.hostname,
        port=args.port,
        timeout=args.timeout,
        credentials=(
            (
                args.username,
                args.password,
            )
            if args.username and args.password
            else None
        ),
    )

    try:
        sections_node(client)
    except (ValueError, requests.ConnectionError, requests.HTTPError):
        if args.debug:
            raise
        return 1

    sections_buckets(list(fetch_bucket_data(client, args.buckets, args.debug)))

    return 0


def main() -> int:
    return special_agent_main(parse_arguments, couchbase_main)
