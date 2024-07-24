#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import csv
import logging
import sys
from collections.abc import Generator, Sequence
from typing import Any

import requests
from requests.adapters import HTTPAdapter

from cmk.special_agents.utils.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.utils.argument_parsing import Args, create_default_argument_parser

SectionLine = tuple[Any, ...]

LOGGING = logging.getLogger("agent_prism")


class HostNameValidationAdapter(HTTPAdapter):
    def __init__(self, host_name: str) -> None:
        super().__init__()
        self._reference_host_name = host_name

    def cert_verify(self, conn, url, verify, cert):
        conn.assert_hostname = self._reference_host_name
        return super().cert_verify(conn, url, verify, cert)


class SessionManager:
    def __init__(
        self,
        username: str,
        password: str,
        timeout: int,
        cert_check: bool,
        check_hostname: str | None,
        base_url: str,
    ) -> None:
        self._session = requests.Session()
        auth_encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
        self._session.headers.update({"Authorization": f"Basic {auth_encoded}"})
        self._verify = cert_check
        self._timeout = timeout
        if cert_check and check_hostname:
            self._session.mount(base_url, HostNameValidationAdapter(check_hostname))

    def get(self, url: str, params: dict[str, str] | None = None) -> Any:
        try:
            resp = self._session.get(url, params=params, verify=self._verify, timeout=self._timeout)
        except requests.exceptions.ConnectionError as e:
            LOGGING.error("Connection failed: %s", e)
            raise e

        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            LOGGING.error("HTTP error: %s", e)
            raise e

        return resp.json()


# TODO: get rid of all this..
# >>>>
FIELD_SEPARATOR = "|"


def gen_csv_writer() -> Any:
    return csv.writer(sys.stdout, delimiter=FIELD_SEPARATOR)


def write_title(section: str) -> None:
    sys.stdout.write("<<<prism_%s:sep(%d)>>>\n" % (section, ord(FIELD_SEPARATOR)))


# <<<<


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


# TODO: get rid of CSV and write JSON
def output_containers(session_manager: SessionManager, url: str) -> None:
    LOGGING.debug("do request..")
    obj = session_manager.get(url + "/containers")
    LOGGING.debug("got %d containers", len(obj["entities"]))

    write_title("containers")
    writer = gen_csv_writer()
    writer.writerow(["name", "usage", "capacity"])
    for entity in obj["entities"]:
        writer.writerow(
            [
                entity["name"],
                entity["usageStats"]["storage.user_usage_bytes"],
                entity["usageStats"]["storage.user_capacity_bytes"],
            ]
        )


def output_alerts(session_manager: SessionManager, url: str) -> Generator[SectionLine, None, None]:
    needed_context_keys = {"vm_type"}

    LOGGING.debug("do request..")
    obj = session_manager.get(
        url + "/alerts",
        params={"resolved": "false", "acknowledged": "false"},
    )
    LOGGING.debug("got %d alerts", len(obj["entities"]))

    yield ("timestamp", "severity", "message", "context")

    for entity in obj["entities"]:
        # The message is stored as a pattern with placeholders, the
        # actual values are stored in context_values, the keys in
        # context_types
        full_context = dict(zip(entity["contextTypes"], entity["contextValues"]))

        # create a thinned out context we can provide together with the alert data in order to
        # provide more sophisticated checks in the future (this could be made a cli option, too)
        thin_context = {k: v for k, v in full_context.items() if k in needed_context_keys}

        # We have seen informational messages in format:
        # {dev_type} drive {dev_name} on host {ip_address} has the following problems: {err_msg}
        # In this case the keys have no values so we can not assign it to the message
        # To handle this, we output a message without assigning the keys
        try:
            message = entity["message"].format(**full_context)
        except KeyError:
            message = entity["message"]

        # message can contain line breaks which confuses the parser.
        message = message.replace("\n", r"\n")
        yield (entity["createdTimeStampInUsecs"], entity["severity"], message, thin_context)


# TODO: get rid of CSV and write JSON
def output_cluster(session_manager: SessionManager, url: str) -> None:
    LOGGING.debug("do request..")
    obj = session_manager.get(url + "/cluster")
    LOGGING.debug("got %d keys", len(obj.keys()))

    write_title("info")
    writer = gen_csv_writer()
    writer.writerow(["name", "version"])
    writer.writerow([obj["name"], obj["version"]])


# TODO: get rid of CSV and write JSON
def output_storage_pools(session_manager: SessionManager, url: str) -> None:
    LOGGING.debug("do request..")
    obj = session_manager.get(url + "/storage_pools")
    LOGGING.debug("got %d entities", len(obj["entities"]))

    write_title("storage_pools")
    writer = gen_csv_writer()
    writer.writerow(["name", "usage", "capacity"])

    for entity in obj["entities"]:
        writer.writerow(
            [
                entity["name"],
                entity["usageStats"]["storage.usage_bytes"],
                entity["usageStats"]["storage.capacity_bytes"],
            ]
        )


def agent_prism_main(args: Args) -> int:
    """Establish a connection to a Prism server and process containers, alerts, clusters and
    storage_pools"""
    LOGGING.info("setup HTTPS connection..")

    base_url = f"https://{args.server}:{args.port}"
    session_manager = SessionManager(
        username=args.username,
        password=args.password,
        timeout=args.timeout,
        cert_check=not args.no_cert_check,
        check_hostname=args.cert_server_name,
        base_url=base_url,
    )
    base_url_v1 = f"{base_url}/PrismGateway/services/rest/v1"

    LOGGING.info("fetch and write container info..")
    output_containers(session_manager, base_url_v1)

    LOGGING.info("fetch and write alerts..")
    with SectionWriter("prism_alerts") as writer:
        writer.append_json(output_alerts(session_manager, base_url_v1))

    LOGGING.info("fetch and write cluster info..")
    output_cluster(session_manager, base_url_v1)

    LOGGING.info("fetch and write storage_pools..")
    output_storage_pools(session_manager, base_url_v1)

    LOGGING.info("all done. bye.")

    return 0


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(parse_arguments, agent_prism_main)


if __name__ == "__main__":
    sys.exit(main())
