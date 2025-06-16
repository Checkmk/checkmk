#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
import logging
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, NotRequired, TypedDict

import requests

from cmk.special_agents.v0_unstable.agent_common import (
    CannotRecover,
    ConditionalPiggybackSection,
    SectionWriter,
    special_agent_main,
)
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser
from cmk.special_agents.v0_unstable.request_helper import HostnameValidationAdapter

LOGGING = logging.getLogger("agent_prism")


class GatewayData(TypedDict):
    # TODO: typing should be improved when switching to newer Prism API V4
    containers: dict[str, Any]
    alerts: dict[str, Any]
    cluster: dict[str, Any]
    storage_pools: dict[str, Any]
    vms: dict[str, Any]
    hosts: dict[str, Any]
    # The following data is not query-able on prism central
    # The corresponding endpoints would return: 412 Client Error: PRECONDITION FAILED
    protection_domains: NotRequired[dict[str, Any]]
    remote_support: NotRequired[dict[str, Any]]
    ha: NotRequired[dict[str, Any]]
    hosts_networks: NotRequired[dict[str, Any]]


class SessionManager:
    def __init__(
        self, username: str, password: str, timeout: int, cert_check: bool | str, base_url: str
    ) -> None:
        self._session = requests.Session()
        auth_encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
        self._session.headers.update({"Authorization": f"Basic {auth_encoded}"})
        self._verify = False if cert_check is False else True
        self._timeout = timeout
        if isinstance(cert_check, str):
            self._session.mount(base_url, HostnameValidationAdapter(cert_check))

    def get(self, url: str, params: dict[str, str] | None = None) -> Any:
        try:
            resp = self._session.get(url, params=params, verify=self._verify, timeout=self._timeout)
        except requests.exceptions.ReadTimeout as e:
            LOGGING.error("Timeout: %s", e)
            raise CannotRecover(f"Connection timed out after {self._timeout} seconds.")
        except requests.exceptions.ConnectionError as e:
            LOGGING.error("Connection failed: %s", e)
            raise e

        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            LOGGING.error("HTTP error: %s", e)
            raise e

        return resp.json()


def _is_only_ovh(hosts_obj: Mapping[str, Iterable[Mapping[str, str]]]) -> bool:
    return all(
        [host.get("hypervisor_type", "") == "kAcropolis" for host in hosts_obj.get("entities", [])]
    )


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
    cert_args = parser.add_mutually_exclusive_group()
    cert_args.add_argument(
        "--no-cert-check", action="store_true", help="Do not verify TLS certificate"
    )
    cert_args.add_argument(
        "--cert-server-name",
        help="Expect this as the servers name in the ssl certificate. Overrides '--no-cert-check'.",
    )

    return parser.parse_args(argv)


def fetch_from_gateway(
    server: str, port: int, username: str, password: str, timeout: int, cert_check: bool | str
) -> GatewayData:
    LOGGING.info("setup HTTPS connection..")
    base_url = f"https://{server}:{port}"
    session_manager = SessionManager(
        username=username,
        password=password,
        timeout=timeout,
        cert_check=cert_check,
        base_url=base_url,
    )
    base_url_v1 = f"{base_url}/PrismGateway/services/rest/v1"
    base_url_v2 = f"{base_url}/PrismGateway/services/rest/v2.0"

    hosts_obj = session_manager.get(f"{base_url_v2}/hosts")
    hosts_networks = {}
    for element in hosts_obj.get("entities", []):
        networks = session_manager.get(f"{base_url_v2}/hosts/{element['uuid']}/host_nics")
        hosts_networks[element["uuid"]] = networks

    LOGGING.info("fetching data from gateway..")

    cluster = session_manager.get(f"{base_url_v2}/cluster")
    is_prism_central = cluster["multicluster"]
    prism_objects: GatewayData = {
        "containers": session_manager.get(f"{base_url_v1}/containers"),
        "cluster": cluster,
        "alerts": session_manager.get(
            f"{base_url_v2}/alerts", params={"resolved": "false", "acknowledged": "false"}
        ),
        "storage_pools": session_manager.get(f"{base_url_v1}/storage_pools"),
        "vms": session_manager.get(f"{base_url_v1}/vms"),
        "hosts": hosts_obj,
    }
    if not is_prism_central:
        prism_objects.update(
            {
                "protection_domains": session_manager.get(f"{base_url_v2}/protection_domains"),
                "remote_support": session_manager.get(f"{base_url_v2}/cluster/remote_support"),
                "ha": session_manager.get(f"{base_url_v2}/ha") if _is_only_ovh(hosts_obj) else {},
                "hosts_networks": hosts_networks,
            }
        )

    LOGGING.debug("got %d containers", len(prism_objects["containers"]["entities"]))
    LOGGING.debug("got %d alerts", len(prism_objects["alerts"]["entities"]))
    LOGGING.debug("got %d keys", len(prism_objects["cluster"].keys()))
    LOGGING.debug("got %d entities", len(prism_objects["storage_pools"]["entities"]))

    return prism_objects


def output_vms(vms: dict[str, Any]) -> None:
    output_entities(vms, "vms")

    for element in vms.get("entities", []):
        with ConditionalPiggybackSection(element.get("vmName")):
            output_entities(element, "vm")


def output_hosts(hosts: dict[str, Any], hosts_networks: dict[str, Any]) -> None:
    output_entities(hosts, "hosts")
    for element in hosts.get("entities", []):
        with ConditionalPiggybackSection(element["name"]):
            output_entities(element, "host")
            if networks := hosts_networks.get(element["uuid"]):
                output_entities(networks, "host_networks")


def output_entities(entities: dict[str, Any], target_name: str) -> None:
    with SectionWriter(f"prism_{target_name}") as w:
        w.append_json(entities)


def agent_prism_main(args: Args) -> int:
    """Establish a connection to a Prism server and process containers, alerts, clusters and
    storage_pools"""
    try:
        gateway_objs = fetch_from_gateway(
            server=args.server,
            port=args.port,
            username=args.username,
            password=args.password,
            timeout=args.timeout,
            cert_check=args.cert_server_name or not args.no_cert_check,
        )
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError):
        return 1

    output_entities(gateway_objs["containers"], "containers")
    output_entities(gateway_objs["alerts"], "alerts")
    output_entities(gateway_objs["cluster"], "info")
    output_entities(gateway_objs["storage_pools"], "storage_pools")
    output_hosts(gateway_objs["hosts"], gateway_objs.get("hosts_networks", {}))
    output_vms(gateway_objs["vms"])

    for key in ("protection_domains", "remote_support", "ha"):
        if key in gateway_objs and (value := gateway_objs[key]):
            output_entities(value, key)

    LOGGING.info("all done. bye.")
    return 0


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(parse_arguments, agent_prism_main)


if __name__ == "__main__":
    sys.exit(main())
