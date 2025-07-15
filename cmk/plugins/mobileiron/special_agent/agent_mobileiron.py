#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent for monitoring MobileIron devices with Checkmk. The data
is fetched from the MobileIron Cloud. Documentation:
https://help.ivanti.com/mi/help/en_us/cld/76/api/Content/MobileIronCloudCustomerIntegrationAPIGuide/Device%20API%20Calls.htm#_Toc507757059

api call url parameters: "https://" + $tenantURL + "/api/v1/device?q=&rows=" + $interval + "&start=" + $start + "&dmPartitionId=" + $spaceId + "&fq=" + $filterCriteria + ""
"""

from __future__ import annotations

import enum
import itertools
import logging
import re
import sys
from collections import defaultdict, UserDict
from collections.abc import Collection, Iterator, Mapping, Sequence
from typing import Any, Final
from urllib.parse import urljoin

import requests

from cmk.utils.http_proxy_config import deserialize_http_proxy_config
from cmk.utils.regex import regex, REGEX_HOST_NAME_CHARS

from cmk.special_agents.v0_unstable.agent_common import (
    ConditionalPiggybackSection,
    SectionWriter,
    special_agent_main,
)
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser

LOGGER = logging.getLogger("agent_mobileiron")


class PlatformType(enum.Enum):
    """Platform (os) types returned by mobileiron API."""

    ANDROID = "ANDROID"
    IOS = "IOS"
    OTHER = "OTHER"


class Regexes:
    """Regex patterns for hostnames."""

    def __init__(
        self,
        android_regexes: Collection[str],
        ios_regexes: Collection[str],
        others_regexes: Collection[str],
    ) -> None:
        self._regexes: Final = {
            PlatformType.ANDROID: android_regexes,
            PlatformType.IOS: ios_regexes,
            PlatformType.OTHER: others_regexes,
        }

    def validate_hostname(self, key: str, platform_type: PlatformType) -> bool:
        """Check if hostname matches the platform specific regex."""

        platform_specific_regex_patterns = self._regexes[platform_type]

        return any(re.search(pattern, key) for pattern in platform_specific_regex_patterns)


class HostnameDict(UserDict):
    """Keeps track of seen keys and replaces the invalid characters before adding.
    Adds successive _count(2) if key is already in the dictionary.
    E.g. key_exists, key_exists_2, key_exists_3, ...
    """

    def __init__(self) -> None:
        self._keys_seen: dict[str, itertools.count] = defaultdict(itertools.count)
        super().__init__()

    def __setitem__(self, key: str, value: Mapping) -> None:
        key = _sanitize_hostname(key)
        if (current_count := next(self._keys_seen[key])) >= 1:
            key = f"{key}_{current_count + 1}"
        super().__setitem__(key, value)


def _get_partition_list(opt_string: str) -> list[str]:
    return opt_string.split(",")


def parse_arguments(argv: Sequence[str] | None) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument("--username", "-u", type=str, help="username for connection")
    parser.add_argument("--password", "-p", type=str, help="password for connection")
    parser.add_argument("--key-fields", action="append", help="field for host name generation")
    parser.add_argument(
        "--partition",
        default=[],
        type=_get_partition_list,
        help="Partition id for connection parameters (dmPartitionId)",
    )
    parser.add_argument("--hostname", help="Name of the Mobileiron instance to query.")
    parser.add_argument(
        "--android-regex", action="append", default=[], help="Regex for Android hosts."
    )
    parser.add_argument("--ios-regex", action="append", default=[], help="Regex for iOS hosts.")
    parser.add_argument(
        "--other-regex", action="append", default=[], help="Regex for other platform hosts."
    )
    parser.add_argument(
        "--proxy",
        type=str,
        default=None,
        metavar="PROXY",
        help="HTTP proxy used to connect to the Mobileiron API. If not set, the environment settings will be used.",
    )
    return parser.parse_args(argv)


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
        key_fields: Sequence[str],
        auth: tuple[str, str],
        regex_patterns: Regexes,
        proxy: str | None = None,
    ) -> None:
        self.api_host = api_host
        self._key_fields = key_fields
        self._api_url = urljoin(f"https://{api_host}", "/api/v1/device")
        self._session = requests.Session()
        self._session.auth = auth
        self._session.verify = True
        self._session.headers["Accept"] = "application/json"
        self._all_devices: HostnameDict = HostnameDict()
        self._devices_per_request = 200
        self.regex_patterns = regex_patterns
        self._proxy = deserialize_http_proxy_config(proxy)
        if _requests_proxy := self._proxy.to_requests_proxies():
            self._session.proxies = _requests_proxy

    def __enter__(self) -> MobileironAPI:
        return self

    def __exit__(self, *exc_info: tuple) -> None:
        self._session.close()

    def _get_devices(self, data_raw: Sequence[Mapping]) -> None:
        """
        Updates an _all_devices dict with devices if they match the platform specific regex.
        """

        for device_json in data_raw:
            compound_key = "-".join(
                _sanitize_hostname(device_json[key_field]) for key_field in self._key_fields
            )
            if self.regex_patterns.validate_hostname(
                compound_key, PlatformType(device_json["platformType"])
            ):
                self._all_devices[compound_key] = device_json

    def _get_one_page(self, params: dict[str, int | str]) -> Mapping[str, Any]:
        """Yield one page from the API with params."""

        try:
            response = self._session.get(self._api_url, params=params, timeout=50)
        except requests.Timeout:
            LOGGER.exception("The request timed out: %s, %s", self._api_url, params)
            raise
        except requests.exceptions.SSLError:
            LOGGER.exception(
                "Certificate verify failed. Please add the ssl certificate to the Trusted certificate authorities for SSL storage. Or disable certificate check. %s, %s.",
                self._api_url,
                params,
            )
            raise

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            LOGGER.exception(
                "HTTPError %s occurred: %s, %s.",
                e,
                self._api_url,
                params,
            )
            raise

        try:
            response_json = response.json()
        except requests.exceptions.JSONDecodeError:
            LOGGER.exception(
                "No json in reply to: %s, %s. Got this instead %s",
                self._api_url,
                params,
                response.text,
            )
            raise

        return response_json

    def _get_all_pages(self, partition: str) -> Iterator[Mapping[str, Any]]:
        """Yield one or more pages of json depending on the total_count and _devices_per_request"""

        first_page_json = self._get_one_page(
            params={
                "rows": self._devices_per_request,
                "start": 0,
                "dmPartitionId": partition,
            }
        )
        total_count = first_page_json["result"]["totalCount"]
        non_compliant = first_page_json["result"]["facetedResults"]["COMPLIANCESTATE"]["false"]
        self._all_devices.update(
            {
                self.api_host: {
                    "total_count": total_count,
                    "non_compliant": non_compliant,
                }
            }
        )
        yield first_page_json

        if total_count > self._devices_per_request:
            # start is 0 based range with _devices_per_request step
            for start in range(self._devices_per_request, total_count, self._devices_per_request):
                yield self._get_one_page(
                    params={
                        "rows": self._devices_per_request,
                        "start": start,
                        "dmPartitionId": partition,
                    }
                )

    def get_all_devices(
        self,
        partitions: list[str],
    ) -> Mapping[str, Any]:
        """Returns all devices in all partitions without duplicates."""

        for partition in partitions:
            for page in self._get_all_pages(partition=partition):
                self._get_devices(page["result"]["searchResults"])

        return self._all_devices


def agent_mobileiron_main(args: Args) -> int:
    """Fetches and writes selected information formatted as agent output to stdout.
    Standard out with sections and piggyback example:
    <<<mobileiron_statistics>>>
    {"...": ...}
    <<<<entityName>>>>
    <<<mobileiron_section>>>
    {"...": ...}
    <<<<entityName>>>>
    <<<mobileiron_df>>>
    {"...": ...}
    <<<<>>>>
    """
    try:
        LOGGER.info("Fetch general device information...")

        if args.debug:
            LOGGER.debug("Initialize Mobileiron API")

        with MobileironAPI(
            api_host=args.hostname,
            key_fields=args.key_fields,
            regex_patterns=Regexes(args.android_regex, args.ios_regex, args.other_regex),
            auth=(args.username, args.password),
            proxy=args.proxy,
        ) as mobileiron_api:
            all_devices = mobileiron_api.get_all_devices(partitions=args.partition)

        if args.debug:
            LOGGER.debug("Received the following devices: %s", all_devices)

        LOGGER.info("Write agent output..")
        for device in all_devices:
            if "total_count" in all_devices[device]:
                with SectionWriter("mobileiron_statistics") as writer:
                    writer.append_json(all_devices[device])
            else:
                with (
                    ConditionalPiggybackSection(device),
                    SectionWriter("mobileiron_section") as writer,
                ):
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
    except (
        requests.Timeout,
        requests.exceptions.SSLError,
        requests.exceptions.HTTPError,
        requests.exceptions.JSONDecodeError,
    ) as exc:
        sys.stderr.write(f"{type(exc).__name__}: {exc}")
        return 1
    return 0


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(parse_arguments, agent_mobileiron_main)


if __name__ == "__main__":
    sys.exit(main())
