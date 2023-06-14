#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sys
from collections.abc import Sequence

from cmk.special_agents.utils.agent_common import (
    ConditionalPiggybackSection,
    SectionWriter,
    special_agent_main,
)
from cmk.special_agents.utils.argument_parsing import Args, create_default_argument_parser
from cmk.special_agents.utils.request_helper import HTTPSAuthRequester, Requester

LOGGING = logging.getLogger("agent_prism")


def parse_arguments(argv: Sequence[str] | None) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout in seconds for network connects (default=10)",
    )
    parser.add_argument(
        "--server", type=str, required=True, metavar="ADDRESS", help="host to connect to"
    )
    parser.add_argument("--port", type=int, metavar="PORT", default=9440)
    parser.add_argument(
        "--username", type=str, required=True, metavar="USER", help="user account on prism"
    )
    parser.add_argument(
        "--password", type=str, required=True, metavar="PASSWORD", help="password for that account"
    )

    return parser.parse_args(argv)


def output_containers(requester: Requester) -> None:
    LOGGING.debug("do request..")
    obj = requester.get("containers")
    LOGGING.debug("got %d containers", len(obj["entities"]))
    with SectionWriter("prism_containers") as w:
        w.append_json(obj)


def output_alerts(requester: Requester) -> None:
    LOGGING.debug("do request..")
    obj = requester.get(
        "alerts",
        parameters={"resolved": "false", "acknowledged": "false"},
    )
    LOGGING.debug("got %d alerts", len(obj["entities"]))
    with SectionWriter("prism_alerts") as w:
        w.append_json(obj)


def output_cluster(requester: Requester) -> None:
    LOGGING.debug("do request..")
    obj = requester.get("cluster")
    LOGGING.debug("got %d keys", len(obj.keys()))
    with SectionWriter("prism_info") as w:
        w.append_json(obj)


def output_storage_pools(requester: Requester) -> None:
    LOGGING.debug("do request..")
    obj = requester.get("storage_pools")
    LOGGING.debug("got %d entities", len(obj["entities"]))
    with SectionWriter("prism_storage_pools") as w:
        w.append_json(obj)


def output_vms(requester: Requester) -> None:
    obj = requester.get("vms")
    with SectionWriter("prism_vms") as w:
        w.append_json(obj)
    for element in obj.get("entities"):
        with ConditionalPiggybackSection(element.get("vmName")):
            with SectionWriter("prism_vm") as w:
                w.append_json(element)


def output_hosts(requester: Requester) -> None:
    obj = requester.get("hosts")
    with SectionWriter("prism_hosts") as w:
        w.append_json(obj)
    for element in obj.get("entities"):
        with ConditionalPiggybackSection(element.get("name")):
            with SectionWriter("prism_host") as w:
                w.append_json(element)


def output_protection(requester: Requester) -> None:
    obj = requester.get("protection_domains")
    with SectionWriter("prism_protection_domains") as w:
        w.append_json(obj)


def output_support(requester: Requester) -> None:
    obj = requester.get("cluster/remote_support")
    with SectionWriter("prism_remote_support") as w:
        w.append_json(obj)


def output_ha(requester: Requester) -> None:
    obj = requester.get("ha")
    with SectionWriter("prism_ha") as w:
        w.append_json(obj)


def agent_prism_main(args: Args) -> int:
    """Establish a connection to a Prism server and process containers, alerts, clusters and
    storage_pools"""
    LOGGING.info("setup HTTPS connection..")
    requester_v1 = HTTPSAuthRequester(
        args.server,
        args.port,
        "PrismGateway/services/rest/v1",
        args.username,
        args.password,
    )
    requester_v2 = HTTPSAuthRequester(
        args.server,
        args.port,
        "PrismGateway/services/rest/v2.0",
        args.username,
        args.password,
    )

    LOGGING.info("fetch and write container info..")
    output_containers(requester_v1)

    LOGGING.info("fetch and write alerts..")
    output_alerts(requester_v2)

    LOGGING.info("fetch and write cluster info..")
    output_cluster(requester_v2)

    LOGGING.info("fetch and write storage_pools..")
    output_storage_pools(requester_v1)

    LOGGING.info("fetch and write vm info..")
    output_vms(requester_v1)

    LOGGING.info("fetch and write hosts info..")
    output_hosts(requester_v2)

    LOGGING.info("fetch and write protection domain info..")
    output_protection(requester_v2)

    LOGGING.info("fetch and write support info..")
    output_support(requester_v2)

    LOGGING.info("fetch and write ha state..")
    output_ha(requester_v2)

    LOGGING.info("all done. bye.")

    return 0


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(parse_arguments, agent_prism_main)


if __name__ == "__main__":
    sys.exit(main())
