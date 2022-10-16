#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sys
from typing import Optional, Sequence

from cmk.special_agents.utils.agent_common import special_agent_main
from cmk.special_agents.utils.argument_parsing import Args, create_default_argument_parser
from cmk.special_agents.utils.request_helper import HTTPSAuthRequester, Requester

LOGGING = logging.getLogger("agent_prism")


def write_title(section: str) -> None:
    sys.stdout.write("<<<prism_%s:sep(0)>>>\n" % (section))


def parse_arguments(argv: Optional[Sequence[str]]) -> Args:
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
    write_title("containers")
    print(obj)


def output_alerts(requester: Requester) -> None:
    LOGGING.debug("do request..")
    obj = requester.get(
        "alerts",
        parameters={"resolved": "false", "acknowledged": "false"},
    )
    LOGGING.debug("got %d alerts", len(obj["entities"]))
    write_title("alerts")
    print(obj)


def output_cluster(requester: Requester) -> None:
    LOGGING.debug("do request..")
    obj = requester.get("cluster")
    LOGGING.debug("got %d keys", len(obj.keys()))
    write_title("info")
    print(obj)


def output_storage_pools(requester: Requester) -> None:
    LOGGING.debug("do request..")
    obj = requester.get("storage_pools")
    LOGGING.debug("got %d entities", len(obj["entities"]))
    write_title("storage_pools")
    print(obj)


def output_vms(requester: Requester) -> None:
    write_title("vms")
    obj = requester.get("vms")
    print(obj)
    for element in obj.get("entities"):
        print("<<<<%s>>>>" % element.get("vmName"))
        write_title("vm")
        print(element)
        print("<<<<>>>>")


def output_hosts(requester: Requester) -> None:
    write_title("hosts")
    obj = requester.get("hosts")
    print(obj)
    for element in obj.get("entities"):
        print("<<<<%s>>>>" % element.get("name"))
        write_title("host")
        print(element)
        print("<<<<>>>>")


def output_protection(requester: Requester) -> None:
    write_title("protection_domains")
    obj = requester.get("protection_domains")
    print(obj)


def output_support(requester: Requester) -> None:
    write_title("remote_support")
    obj = requester.get("cluster/remote_support")
    print(obj)


def agent_prism_main(args: Args) -> None:
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

    LOGGING.info("all done. bye.")


def main() -> None:
    """Main entry point to be used"""
    special_agent_main(parse_arguments, agent_prism_main)


if __name__ == "__main__":
    main()
