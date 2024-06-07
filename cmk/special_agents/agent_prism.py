#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
import logging
import sys
from collections.abc import Sequence
from typing import Any

import requests

from cmk.special_agents.v0_unstable.agent_common import (
    ConditionalPiggybackSection,
    SectionWriter,
    special_agent_main,
)
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser

LOGGING = logging.getLogger("agent_prism")


class SessionManager:
    def __init__(
        self, username: str, password: str, timeout: int, no_cert_check: bool = False
    ) -> None:
        self._session = requests.Session()
        auth_encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
        self._session.headers.update({"Authorization": f"Basic {auth_encoded}"})
        self._verify = (
            False if no_cert_check else True  # pylint: disable=simplifiable-if-expression
        )
        self._timeout = timeout

    def get(self, url: str, params: dict[str, str] | None = None) -> Any:
        resp = self._session.get(url, params=params, verify=self._verify, timeout=self._timeout)
        resp.raise_for_status()
        return resp.json()


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
    parser.add_argument(
        "--no-cert-check", action="store_true", help="Do not verify TLS certificate"
    )

    return parser.parse_args(argv)


def output_containers(session_manager: SessionManager, url: str) -> None:
    LOGGING.debug("do request..")
    obj = session_manager.get(url + "/containers")
    LOGGING.debug("got %d containers", len(obj["entities"]))
    with SectionWriter("prism_containers") as w:
        w.append_json(obj)


def output_alerts(session_manager: SessionManager, url: str) -> None:
    LOGGING.debug("do request..")
    obj = session_manager.get(
        url + "/alerts",
        params={"resolved": "false", "acknowledged": "false"},
    )
    LOGGING.debug("got %d alerts", len(obj["entities"]))
    with SectionWriter("prism_alerts") as w:
        w.append_json(obj)


def output_cluster(session_manager: SessionManager, url: str) -> None:
    LOGGING.debug("do request..")
    obj = session_manager.get(url + "/cluster")
    LOGGING.debug("got %d keys", len(obj.keys()))
    with SectionWriter("prism_info") as w:
        w.append_json(obj)


def output_storage_pools(session_manager: SessionManager, url: str) -> None:
    LOGGING.debug("do request..")
    obj = session_manager.get(url + "/storage_pools")
    LOGGING.debug("got %d entities", len(obj["entities"]))
    with SectionWriter("prism_storage_pools") as w:
        w.append_json(obj)


def output_vms(session_manager: SessionManager, url: str) -> None:
    obj = session_manager.get(url + "/vms")
    with SectionWriter("prism_vms") as w:
        w.append_json(obj)
    for element in obj.get("entities", []):
        with ConditionalPiggybackSection(element.get("vmName")):
            with SectionWriter("prism_vm") as w:
                w.append_json(element)


def output_hosts(session_manager: SessionManager, url: str) -> None:
    obj = session_manager.get(url + "/hosts")
    with SectionWriter("prism_hosts") as w:
        w.append_json(obj)
    for element in obj.get("entities", []):
        with ConditionalPiggybackSection(element.get("name")):
            with SectionWriter("prism_host") as w:
                w.append_json(element)
            networks = session_manager.get(url + f"/hosts/{element.get("uuid")}/host_nics")
            with SectionWriter("prism_host_networks") as w:
                w.append_json(networks)


def output_protection(session_manager: SessionManager, url: str) -> None:
    obj = session_manager.get(url + "/protection_domains")
    with SectionWriter("prism_protection_domains") as w:
        w.append_json(obj)


def output_support(session_manager: SessionManager, url: str) -> None:
    obj = session_manager.get(url + "/cluster/remote_support")
    with SectionWriter("prism_remote_support") as w:
        w.append_json(obj)


def output_ha(session_manager: SessionManager, url: str) -> None:
    obj = session_manager.get(url + "/ha")
    with SectionWriter("prism_ha") as w:
        w.append_json(obj)


def agent_prism_main(args: Args) -> int:
    """Establish a connection to a Prism server and process containers, alerts, clusters and
    storage_pools"""
    LOGGING.info("setup HTTPS connection..")
    base_url_v1 = f"https://{args.server}:{args.port}/PrismGateway/services/rest/v1"
    base_url_v2 = f"https://{args.server}:{args.port}/PrismGateway/services/rest/v2.0"
    session_manager = SessionManager(
        username=args.username,
        password=args.password,
        timeout=args.timeout,
        no_cert_check=args.no_cert_check,
    )

    LOGGING.info("fetch and write container info..")
    output_containers(session_manager, base_url_v1)

    LOGGING.info("fetch and write alerts..")
    output_alerts(session_manager, base_url_v2)

    LOGGING.info("fetch and write cluster info..")
    output_cluster(session_manager, base_url_v2)

    LOGGING.info("fetch and write storage_pools..")
    output_storage_pools(session_manager, base_url_v1)

    LOGGING.info("fetch and write vm info..")
    output_vms(session_manager, base_url_v1)

    LOGGING.info("fetch and write hosts info..")
    output_hosts(session_manager, base_url_v2)

    LOGGING.info("fetch and write protection domain info..")
    output_protection(session_manager, base_url_v2)

    LOGGING.info("fetch and write support info..")
    output_support(session_manager, base_url_v2)

    LOGGING.info("fetch and write ha state..")
    output_ha(session_manager, base_url_v2)

    LOGGING.info("all done. bye.")

    return 0


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(parse_arguments, agent_prism_main)


if __name__ == "__main__":
    sys.exit(main())
