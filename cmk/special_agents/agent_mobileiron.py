#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent for monitoring MobileIron devices with Checkmk. The data
is fetched from the MobileIron Cloud. Documentation:
https://help.ivanti.com/mi/help/en_us/cld/76/api/Content/MobileIronCloudCustomerIntegrationAPIGuide/Device%20API%20Calls.htm#_Toc507757059

api call url parameters: "https://" + $tenantURL + "/api/v1/device?q=&rows=" + $interval + "&start=" + $start + "&dmPartitionId=" + $spaceId + "&fq=" + $filterCriteria + ""
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from urllib.parse import quote, urljoin

import requests
import urllib3

from cmk.utils.regex import regex, REGEX_HOST_NAME_CHARS

from cmk.special_agents.utils.agent_common import (
    ConditionalPiggybackSection,
    SectionWriter,
    special_agent_main,
)
from cmk.special_agents.utils.argument_parsing import create_default_argument_parser

if TYPE_CHECKING:
    from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

    from cmk.special_agents.utils.argument_parsing import Args

LOGGER = logging.getLogger("agent_mobileiron")


def _get_partition_list(opt_string: str) -> List[str]:
    return opt_string.split(",")


def parse_arguments(argv: Optional[Sequence[str]]) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument("--username", "-u", type=str, help="username for connection")
    parser.add_argument("--password", "-p", type=str, help="password for connection")
    parser.add_argument("--port", type=int, help="port for connection")
    parser.add_argument("--no-cert-check", action="store_true")
    parser.add_argument(
        "--partition",
        nargs="+",
        type=_get_partition_list,
        help="Partition id for connection parameters (dmPartitionId)",
    )
    parser.add_argument("--hostname", help="Name of the Mobileiron instance to query.")
    parser.add_argument("--proxy-host", help="The address of the proxy server")
    parser.add_argument("--proxy-port", help="The port of the proxy server")
    parser.add_argument("--proxy-user", help="The username for authentication of the proxy server")
    parser.add_argument(
        "--proxy-password", help="The password for authentication of the proxy server"
    )
    return parser.parse_args(argv)


def _proxy_address(
    server_address: str,
    port: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> str:
    """Constructs a full proxy address string."""
    address = server_address
    authentication = ""
    if port:
        address += f":{port}"
    if username and password:
        user_quoted = quote(username)
        password_quoted = quote(password)
        authentication = f"{user_quoted}:{password_quoted}@"
    return f"{authentication}{address}"


def _sanitize_hostname(raw_hostname: str) -> str:
    """
    Remove the part with @..., so the "foo@bar" becomes "foo"
    Then apply the standard hostname allowed characters.
    """
    return regex(f"[^{REGEX_HOST_NAME_CHARS}]").sub("_", raw_hostname.partition("@")[0])


class MobileironAPI:
    def __init__(
        self,
        api_host: str,
        port: int,
        auth: Tuple[str, str],
        verify: bool,
        proxies: Optional[str] = None,
    ) -> None:
        self.api_host = api_host
        self._api_url = urljoin(f"https://{api_host}:{port}", "/api/v1/device")
        self._session = requests.Session()
        self._session.auth = auth
        self._session.verify = verify
        self._session.headers["Accept"] = "application/json"
        if self._session.verify is False:
            urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)
        self._all_devices: Dict[str, Any] = {}
        self._devices_per_request = 200
        if proxies:
            self._session.proxies.update({"https": proxies})

    def __enter__(self) -> "MobileironAPI":
        return self

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        if self._session:
            self._session.close()

    def _get_devices(self, data_raw: Sequence[Mapping]) -> None:
        """
        Updates an _all_devices dict with duplicated json objects removed
        choosing the one with the latest registration time
        """

        # TODO chunks of _devices_per_request could contain duplicates
        self._all_devices.update(
            {
                _sanitize_hostname(device_json["entityName"]): device_json
                for device_json in sorted(data_raw, key=lambda d: d["lastRegistrationTime"])
            }
        )

    def get_all_devices(
        self,
        partitions: List[str],
    ) -> Mapping[str, Any]:
        """Returns all devices in all partitions without duplicates."""

        params: Dict[str, Union[int, str]] = {}

        # TODO consider using a ThreadPoolExecutor which can create concurrent.futures for asyncio:
        # https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor
        for partition in partitions:
            # always get first devices
            params = {"rows": self._devices_per_request, "start": 0, "dmPartitionId": partition}
            try:
                response = self._session.get(self._api_url, params=params, timeout=50)
                response.raise_for_status()
                response_json = response.json()
            except requests.Timeout:
                LOGGER.exception("The request timed out: %s, %s", self._api_url, params)
                raise
            except requests.JSONDecodeError:
                LOGGER.exception(
                    "No json in reply to: %s, %s. Got this instead %s",
                    self._api_url,
                    params,
                    response.text,
                )
                raise
            except requests.exceptions.SSLError:
                LOGGER.exception(
                    "Certificate verify failed. Please add the ssl certificate to the Trusted certificate authorities for SSL storage. Or disable certificate check. %s, %s.",
                    self._api_url,
                    params,
                )
                raise

            self._get_devices(response_json["result"]["searchResults"])
            total_count = response_json["result"]["totalCount"]
            self._all_devices.update(
                {
                    self.api_host: {
                        "total_count": total_count,
                        "queryTime": response_json["result"]["queryTime"],
                    }
                }
            )

            # if the first get() was enough, continue, else get all devices in a cycle
            # until total_count is exhausted
            if total_count > self._devices_per_request:
                # start is 0 based range with _devices_per_request step
                for start in range(
                    self._devices_per_request, total_count, self._devices_per_request
                ):
                    params = {
                        "rows": self._devices_per_request,
                        "start": start,
                        "dmPartitionId": partition,
                    }
                    try:
                        response = self._session.get(self._api_url, params=params, timeout=50)
                        response.raise_for_status()
                        response_json = response.json()
                    except requests.Timeout:
                        LOGGER.exception("The request timed out: %s, %s", self._api_url, params)
                        raise
                    except requests.JSONDecodeError:
                        LOGGER.exception(
                            "No json in reply to: %s, %s. Got this instead %s",
                            self._api_url,
                            params,
                            response.text,
                        )
                        raise
                    except requests.exceptions.SSLError:
                        LOGGER.exception(
                            "Certificate verify failed. Please add the ssl certificate to the Trusted certificate authorities for SSL storage. Or disable certificate check. %s, %s.",
                            self._api_url,
                            params,
                        )
                        raise
                    self._get_devices(response_json["result"]["searchResults"])

        return self._all_devices


def agent_mobileiron_main(args: Args) -> None:
    """Fetches and writes selected information formatted as agent output to stdout.
    Standard out with sections and piggyback example:
    <<<<entityName>>>>
    <<<mobileiron_section>>>
    {"...": ...}
    <<<<entityName>>>>
    <<<mobileiron_source_host>>>
    {"...": ...}
    <<<<>>>>
    <<<<entityName>>>>
    <<<mobileiron_df>>>
    {"...": ...}
    <<<<>>>>
    """

    LOGGER.info("Fetch general device information...")

    if args.debug:
        LOGGER.debug("Initialize Mobileiron API")

    with MobileironAPI(
        args.hostname,
        args.port,
        auth=(args.username, args.password),
        verify=not args.no_cert_check,
        proxies=_proxy_address(
            args.proxy_host,
            args.proxy_port,
            args.proxy_user,
            args.proxy_password,
        )
        if args.proxy_host
        else None,
    ) as mobileiron_api:

        all_devices = mobileiron_api.get_all_devices(partitions=args.partition)

    if args.debug:
        LOGGER.debug("Received the following devices: %s", all_devices)

    LOGGER.info("Write agent output..")
    for device in all_devices:
        if "total_count" in all_devices[device]:
            with ConditionalPiggybackSection(device), SectionWriter(
                "mobileiron_source_host"
            ) as writer:
                writer.append_json(all_devices[device])
        else:
            with ConditionalPiggybackSection(device), SectionWriter("mobileiron_section") as writer:
                writer.append_json(all_devices[device])
            if uptime := all_devices[device]["uptime"]:
                with ConditionalPiggybackSection(device), SectionWriter("uptime") as writer:
                    writer.append_json(uptime)
            with ConditionalPiggybackSection(device), SectionWriter("mobileiron_df") as writer:
                writer.append_json(
                    {
                        "totalCapacity": all_devices[device].get("totalCapacity"),
                        "availableCapacity": all_devices[device].get("availableCapacity"),
                    }
                )


def main() -> None:
    """Main entry point to be used"""
    special_agent_main(parse_arguments, agent_mobileiron_main)


if __name__ == "__main__":
    main()
