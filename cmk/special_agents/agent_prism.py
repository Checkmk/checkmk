#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import logging
import sys
from collections.abc import Sequence

import requests

from cmk.special_agents.v0_unstable.agent_common import (
    ConditionalPiggybackSection,
    SectionWriter,
    special_agent_main,
)
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser

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


def output_containers(session: requests.Session, url: str) -> None:
    obj = session.get(url + "/containers", verify=False, timeout=5)
    with SectionWriter("prism_containers") as w:
        w.append_json(obj.json())


def output_alerts(session: requests.Session, url: str) -> None:
    obj = session.get(
        url + "/alerts",
        params={"resolved": "false", "acknowledged": "false"},
        verify=False,
        timeout=5,
    )
    with SectionWriter("prism_alerts") as w:
        w.append_json(obj.json())


def output_cluster(session: requests.Session, url: str) -> None:
    obj = session.get(url + "/cluster", verify=False, timeout=5)
    with SectionWriter("prism_info") as w:
        w.append_json(obj.json())


def output_storage_pools(session: requests.Session, url: str) -> None:
    obj = session.get(url + "/storage_pools", verify=False, timeout=5)
    with SectionWriter("prism_storage_pools") as w:
        w.append_json(obj.json())


def output_vms(session: requests.Session, url: str) -> None:
    obj = session.get(url + "/vms", verify=False, timeout=5)
    with SectionWriter("prism_vms") as w:
        w.append_json(obj.json())
    for element in obj.json().get("entities"):
        with ConditionalPiggybackSection(element.get("vmName")):
            with SectionWriter("prism_vm") as w:
                w.append_json(element)


def output_hosts(session: requests.Session, url: str) -> None:
    obj = session.get(url + "/hosts", verify=False, timeout=5)
    with SectionWriter("prism_hosts") as w:
        w.append_json(obj.json())
    for element in obj.json().get("entities"):
        with ConditionalPiggybackSection(element.get("name")):
            with SectionWriter("prism_host") as w:
                w.append_json(element)
            networks = session.get(
                url + f"/hosts/{element.get("uuid")}/host_nics", verify=False, timeout=5
            )
            with SectionWriter("prism_host_networks") as w:
                w.append_json(networks.json())


def output_protection(session: requests.Session, url: str) -> None:
    obj = session.get(url + "/protection_domains", verify=False, timeout=5)
    with SectionWriter("prism_protection_domains") as w:
        w.append_json(obj.json())


def output_support(session: requests.Session, url: str) -> None:
    obj = session.get(url + "/cluster/remote_support", verify=False, timeout=5)
    with SectionWriter("prism_remote_support") as w:
        w.append_json(obj.json())


def output_ha(session: requests.Session, url: str) -> None:
    obj = session.get(url + "/ha", verify=False, timeout=5)
    with SectionWriter("prism_ha") as w:
        w.append_json(obj.json())


def agent_prism_main(args: Args) -> int:
    """Establish a connection to a Prism server and process containers, alerts, clusters and
    storage_pools"""
    LOGGING.info("setup HTTPS connection..")
    headers = {
        "Authorization": "Basic "
        + base64.encodebytes((f"{args.username}:{args.password}").encode())
        .strip()
        .decode()
        .replace("\n", "")
    }
    base_url_v1 = f"https://{args.server}:{args.port}/PrismGateway/services/rest/v1"
    base_url_v2 = f"https://{args.server}:{args.port}/PrismGateway/services/rest/v2.0"
    s = requests.session()
    s.headers.update(headers)

    LOGGING.info("fetch and write container info..")
    output_containers(s, base_url_v1)

    LOGGING.info("fetch and write alerts..")
    output_alerts(s, base_url_v2)

    LOGGING.info("fetch and write cluster info..")
    output_cluster(s, base_url_v2)

    LOGGING.info("fetch and write storage_pools..")
    output_storage_pools(s, base_url_v1)

    LOGGING.info("fetch and write vm info..")
    output_vms(s, base_url_v1)

    LOGGING.info("fetch and write hosts info..")
    output_hosts(s, base_url_v2)

    LOGGING.info("fetch and write protection domain info..")
    output_protection(s, base_url_v2)

    LOGGING.info("fetch and write support info..")
    output_support(s, base_url_v2)

    LOGGING.info("fetch and write ha state..")
    output_ha(s, base_url_v2)

    LOGGING.info("all done. bye.")

    return 0


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(parse_arguments, agent_prism_main)


if __name__ == "__main__":
    sys.exit(main())
