#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent azure: Monitoring Azure cloud applications with Checkmk

Resources and resourcegroups are all treated lowercase because of:
https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/frequently-asked-questions#are-resource-group-names-case-sensitive
"""

from __future__ import annotations

import abc
import argparse
import asyncio
import datetime
import enum
import json
import logging
import re
import string
import sys
import time
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from enum import Enum
from multiprocessing import Lock
from pathlib import Path
from typing import Any, Literal, NamedTuple, Required, TypedDict, TypeVar

import aiohttp  # type: ignore[import-not-found]
import msal
import requests

from cmk.utils import password_store
from cmk.utils.http_proxy_config import deserialize_http_proxy_config, HTTPProxyConfig
from cmk.utils.paths import tmp_dir

from cmk.special_agents.v0_unstable.misc import DataCache, vcrtrace

T = TypeVar("T")
Args = argparse.Namespace
GroupLabels = Mapping[str, Mapping[str, str]]

LOGGER = logging.getLogger()  # root logger for now

AZURE_CACHE_FILE_PATH = tmp_dir / "agents" / "agent_azure"

NOW = datetime.datetime.now(tz=datetime.UTC)

SUPPORTED_FLEXIBLE_DATABASE_SERVER_RESOURCE_TYPES = frozenset(
    {
        "Microsoft.DBforMySQL/flexibleServers",
        "Microsoft.DBforPostgreSQL/flexibleServers",
    }
)

ALL_METRICS: dict[str, list[tuple[str, str, str]]] = {
    # to add a new metric, just add a made up name, run the
    # agent, and you'll get a error listing available metrics!
    # key: list of (name(s), interval, aggregation, filter)
    # NB: Azure API won't have requests with more than 20 metric names at once
    # Also remember to add the service to the WATO rule:
    # cmk/gui/plugins/wato/special_agents/azure.py
    "Microsoft.Network/virtualNetworkGateways": [
        ("AverageBandwidth,P2SBandwidth", "PT5M", "average"),
        ("TunnelIngressBytes", "PT5M", "count"),
        ("TunnelEgressBytes", "PT5M", "count"),
        ("TunnelIngressPacketDropCount", "PT5M", "count"),
        ("TunnelEgressPacketDropCount", "PT5M", "count"),
        ("P2SConnectionCount", "PT1M", "maximum"),
    ],
    "Microsoft.Sql/servers/databases": [
        (
            "storage_percent,deadlock,cpu_percent,dtu_consumption_percent,"
            "connection_successful,connection_failed",
            "PT1M",
            "average",
        ),
    ],
    "Microsoft.Storage/storageAccounts": [
        (
            "UsedCapacity,Ingress,Egress,Transactions",
            "PT1H",
            "total",
        ),
        (
            "SuccessServerLatency,SuccessE2ELatency,Availability",
            "PT1H",
            "average",
        ),
    ],
    "Microsoft.Web/sites": [
        ("CpuTime,AverageResponseTime,Http5xx", "PT1M", "total"),
    ],
    "Microsoft.DBforMySQL/servers": [
        (
            "cpu_percent,memory_percent,io_consumption_percent,serverlog_storage_percent,"
            "storage_percent,active_connections",
            "PT1M",
            "average",
        ),
        (
            "connections_failed,network_bytes_ingress,network_bytes_egress",
            "PT1M",
            "total",
        ),
        (
            "seconds_behind_master",
            "PT1M",
            "maximum",
        ),
    ],
    "Microsoft.DBforMySQL/flexibleServers": [
        (
            # NOTE: the "serverlog_storage_percent" metric may soon be phased out of the MySQL
            # flexible server as it is no longer mentioned in the documentation and is not present
            # in PostgreSQL flexible server documentation.
            "cpu_percent,memory_percent,io_consumption_percent,serverlog_storage_percent,"
            "storage_percent,active_connections",
            "PT1M",
            "average",
        ),
        (
            "aborted_connections,network_bytes_ingress,network_bytes_egress",
            "PT1M",
            "total",
        ),
        (
            "replication_lag",
            "PT1M",
            "maximum",
        ),
    ],
    "Microsoft.DBforPostgreSQL/servers": [
        (
            "cpu_percent,memory_percent,io_consumption_percent,serverlog_storage_percent,"
            "storage_percent,active_connections",
            "PT1M",
            "average",
        ),
        (
            "connections_failed,network_bytes_ingress,network_bytes_egress",
            "PT1M",
            "total",
        ),
        (
            "pg_replica_log_delay_in_seconds",
            "PT1M",
            "maximum",
        ),
    ],
    "Microsoft.DBforPostgreSQL/flexibleServers": [
        (
            "cpu_percent,memory_percent,disk_iops_consumed_percentage,storage_percent,active_connections",
            "PT1M",
            "average",
        ),
        (
            "connections_failed,network_bytes_ingress,network_bytes_egress",
            "PT1M",
            "total",
        ),
        (
            "physical_replication_delay_in_seconds",
            "PT1M",
            "maximum",
        ),
    ],
    "Microsoft.Network/trafficmanagerprofiles": [
        (
            "QpsByEndpoint",
            "PT1M",
            "total",
        ),
        (
            "ProbeAgentCurrentEndpointStateByProfileResourceId",
            "PT1M",
            "maximum",
        ),
    ],
    "Microsoft.Network/loadBalancers": [
        (
            "ByteCount",
            "PT1M",
            "total",
        ),
        (
            "AllocatedSnatPorts,UsedSnatPorts,VipAvailability,DipAvailability",
            "PT1M",
            "average",
        ),
    ],
    "Microsoft.Network/applicationGateways": [
        ("HealthyHostCount", "PT1M", "average"),
        ("FailedRequests", "PT1M", "count"),
    ],
    "Microsoft.Compute/virtualMachines": [
        (
            "Percentage CPU,CPU Credits Consumed,CPU Credits Remaining,Available Memory Bytes,Disk Read Operations/Sec,Disk Write Operations/Sec",
            "PT1M",
            "average",
        ),
        (
            "Network In Total,Network Out Total,Disk Read Bytes,Disk Write Bytes",
            "PT1M",
            "total",
        ),
    ],
}

OPTIONAL_METRICS: Mapping[str, Sequence[str]] = {
    "Microsoft.Sql/servers/databases": [
        "storage_percent",
        "deadlock",
        "dtu_consumption_percent",
    ],
    "Microsoft.DBforMySQL/servers": ["seconds_behind_master"],
    "Microsoft.DBforMySQL/flexibleServers": ["replication_lag"],
    "Microsoft.DBforPostgreSQL/servers": ["pg_replica_log_delay_in_seconds"],
    "Microsoft.DBforPostgreSQL/flexibleServers": ["physical_replication_delay_in_seconds"],
    "Microsoft.Network/loadBalancers": ["AllocatedSnatPorts", "UsedSnatPorts"],
    "Microsoft.Compute/virtualMachines": [
        "CPU Credits Consumed",
        "CPU Credits Remaining",
    ],
}


class FetchedResource(Enum):
    """Available Azure resources, with section name, for API fetching"""

    virtual_machines = ("Microsoft.Compute/virtualMachines", "virtualmachines")
    vaults = ("Microsoft.RecoveryServices/vaults", "vaults")

    def __init__(self, resource_type, section_name):
        self.resource_type = resource_type
        self.section_name = section_name

    @property
    def section(self):
        return self.section_name

    @property
    def type(self):
        return self.resource_type


BULK_QUERIED_RESOURCES = {
    FetchedResource.virtual_machines.type,
}


class TagsImportPatternOption(enum.Enum):
    ignore_all = "IGNORE_ALL"
    import_all = "IMPORT_ALL"


TagsOption = str | Literal[TagsImportPatternOption.ignore_all, TagsImportPatternOption.import_all]


def _chunks(list_: Sequence[T], length: int = 50) -> Sequence[Sequence[T]]:
    return [list_[i : i + length] for i in range(0, len(list_), length)]


def parse_arguments(argv: Sequence[str]) -> Args:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--debug", action="store_true", help="""Debug mode: raise Python exceptions"""
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="""Verbose mode (for even more output use -vvv)""",
    )
    parser.add_argument(
        "--vcrtrace",
        action=vcrtrace(filter_post_data_parameters=[("client_secret", "****")]),
    )
    parser.add_argument(
        "--dump-config",
        action="store_true",
        help="""Dump parsed configuration and exit""",
    )
    parser.add_argument(
        "--timeout",
        default=10,
        type=int,
        help="""Timeout for individual processes in seconds (default 10)""",
    )
    parser.add_argument(
        "--piggyback_vms",
        default="grouphost",
        choices=["grouphost", "self"],
        help="""Send VM piggyback data to group host (default) or the VM iteself""",
    )

    group_subscription = parser.add_mutually_exclusive_group(required=False)
    group_subscription.add_argument(
        "--subscription",
        dest="subscriptions",
        action="append",
        default=[],
        help="Azure subscription IDs",
    )
    group_subscription.add_argument(
        "--all-subscriptions",
        action="store_true",
        help="Monitor all available Azure subscriptions",
    )

    # REQUIRED
    parser.add_argument("--client", required=True, help="Azure client ID")
    parser.add_argument("--tenant", required=True, help="Azure tenant ID")
    parser.add_argument("--secret", required=True, help="Azure authentication secret")
    parser.add_argument(
        "--cache-id",
        required="--connection-test" not in sys.argv,
        help="Unique id for this special agent configuration",
    )

    parser.add_argument(
        "--proxy",
        type=str,
        default=None,
        metavar="PROXY",
        help=(
            "HTTP proxy used to connect to the Azure API. If not set, the environment settings "
            "will be used."
        ),
    )

    # CONSTRAIN DATA TO REQUEST
    parser.add_argument(
        "--require-tag",
        default=[],
        metavar="TAG",
        action="append",
        help="""Only monitor resources that have the specified TAG.
              To require multiple tags, provide the option more than once.""",
    )
    parser.add_argument(
        "--require-tag-value",
        default=[],
        metavar=("TAG", "VALUE"),
        nargs=2,
        action="append",
        help="""Only monitor resources that have the specified TAG set to VALUE.
             To require multiple tags, provide the option more than once.""",
    )
    parser.add_argument(
        "--explicit-config",
        default=[],
        nargs="*",
        help="""list of arguments providing the configuration in <key>=<value> format.
             If omitted, all groups and all resources of the services specified in --services are
             fetched.
             If specified, every 'group=<name>' argument starts a new group configuration,
             and every 'resource=<name>' arguments specifies a resource.""",
    )
    parser.add_argument(
        "--services",
        default=[],
        nargs="*",
        help="List of services to monitor",
    )
    parser.add_argument(
        "--authority",
        default="global",
        choices=["global", "china"],
        required=True,
        help="Authority to be used",
    )

    group_import_tags = parser.add_mutually_exclusive_group()
    group_import_tags.add_argument(
        "--ignore-all-tags",
        action="store_const",
        const=TagsImportPatternOption.ignore_all,
        dest="tag_key_pattern",
        help="By default, all Azure tags are written to the agent output, validated to meet the "
        "Checkmk label requirements and added as host labels to their respective piggyback host "
        "and/or as service labels to the respective service using the syntax "
        "'cmk/azure/tag/{key}:{value}'. With this option you can disable the import of Azure "
        "tags.",
    )
    group_import_tags.add_argument(
        "--import-matching-tags-as-labels",
        dest="tag_key_pattern",
        help="You can restrict the imported tags by specifying a pattern which the agent searches "
        "for in the key of the tag.",
    )
    group_import_tags.set_defaults(tag_key_pattern=TagsImportPatternOption.import_all)

    parser.add_argument(
        "--connection-test",
        action="store_true",
        help="Run a connection test through the Management API only. No further agent code is "
        "executed.",
    )

    args = parser.parse_args(argv)

    # LOGGING
    if args.verbose and args.verbose >= 3:
        # this will show third party log messages as well
        fmt = "%(levelname)s: %(name)s: %(filename)s: %(lineno)s: %(message)s"
        lvl = logging.DEBUG
    elif args.verbose and args.verbose == 2:
        # be verbose, but silence msrest, urllib3 and requests_oauthlib
        fmt = "%(levelname)s: %(funcName)s: %(lineno)s: %(message)s"
        lvl = logging.DEBUG
        logging.getLogger("msrest").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests_oauthlib").setLevel(logging.WARNING)
    elif args.verbose:
        fmt = "%(levelname)s: %(funcName)s: %(message)s"
        lvl = logging.INFO
    else:
        fmt = "%(levelname)s: %(message)s"
        lvl = logging.WARNING
    logging.basicConfig(level=lvl, format=fmt)

    # V-VERBOSE INFO
    for key, value in vars(args).items():
        if key == "secret":
            value = "****"
        LOGGER.debug("argparse: %s = %r", key, value)

    return args


class ApiError(RuntimeError):
    pass


class ApiLoginFailed(ApiError):
    pass


class ApiErrorMissingData(ApiError):
    pass


class NoConsumptionAPIError(ApiError):
    pass


class ApiErrorAuthorizationRequestDenied(ApiError):
    pass


def _make_exception(error_data: object) -> ApiError:
    match error_data:
        case {"code": "Authorization_RequestDenied", **rest}:
            message = rest.get("message", error_data)
            assert isinstance(message, Mapping)
            return ApiErrorAuthorizationRequestDenied(**message)
        case {"code": _, "message": message}:
            return ApiError(message)
        case other:
            return ApiError(other)


class _AuthorityURLs(NamedTuple):
    login: str
    resource: str
    base: str
    regional: Callable[[str], str] | None = None


def _get_graph_authority_urls(authority: Literal["global", "china"]) -> _AuthorityURLs:
    if authority == "global":
        return _AuthorityURLs(
            "https://login.microsoftonline.com",
            "https://graph.microsoft.com",
            "https://graph.microsoft.com/v1.0/",
        )
    if authority == "china":
        return _AuthorityURLs(
            "https://login.partner.microsoftonline.cn",
            "https://microsoftgraph.chinacloudapi.cn",
            "https://microsoftgraph.chinacloudapi.cn/v1.0/",
        )
    raise ValueError("Unknown authority %r" % authority)


def _get_regional_url_func(subscription: str) -> Callable[[str], str]:
    def get_regional_url(region: str) -> str:
        return f"https://{region}.metrics.monitor.azure.com/subscriptions/{subscription}"

    return get_regional_url


def _get_mgmt_authority_urls(
    authority: Literal["global", "china"], subscription: str
) -> _AuthorityURLs:
    if authority == "global":
        return _AuthorityURLs(
            "https://login.microsoftonline.com",
            "https://management.azure.com",
            f"https://management.azure.com/subscriptions/{subscription}/",
            _get_regional_url_func(subscription),
        )
    if authority == "china":
        return _AuthorityURLs(
            "https://login.partner.microsoftonline.cn",
            "https://management.chinacloudapi.cn",
            f"https://management.chinacloudapi.cn/subscriptions/{subscription}/",
            lambda r: f"https://metrics.monitor.azure.cn/subscriptions/{subscription}/",
        )
    raise ValueError("Unknown authority %r" % authority)


class BaseApiClient(abc.ABC):
    def __init__(
        self,
        authority_urls: _AuthorityURLs,
        http_proxy_config: HTTPProxyConfig,
    ) -> None:
        self._ratelimit = float("Inf")
        self._headers: dict = {}
        self._login_url = authority_urls.login
        self._resource_url = authority_urls.resource
        self._base_url = authority_urls.base
        self._regional_url = authority_urls.regional
        self._http_proxy_config = http_proxy_config

    def login(self, tenant: str, client: str, secret: str) -> None:
        client_app = msal.ConfidentialClientApplication(
            client,
            secret,
            f"{self._login_url}/{tenant}",
            proxies=self._http_proxy_config.to_requests_proxies(),
        )
        token = client_app.acquire_token_for_client([self._resource_url + "/.default"])

        if error := token.get("error"):
            if error_description := token.get("error_description"):
                error = f"{error}. {error_description}"
            raise ApiLoginFailed(error)

        self._headers.update(
            {
                "Authorization": "Bearer %s" % token["access_token"],
                "Content-Type": "application/json",
                "ClientType": "monitoring-custom-client-type",
            }
        )

    @property
    def ratelimit(self):
        if isinstance(self._ratelimit, int):
            return self._ratelimit
        return None

    def _update_ratelimit(self, response: requests.Response) -> None:
        try:
            new_value = int(response.headers["x-ms-ratelimit-remaining-subscription-reads"])
        except (KeyError, ValueError, TypeError):
            return
        self._ratelimit = min(self._ratelimit, new_value)

    def _handle_ratelimit(self, get_response: Callable[[], requests.Response]) -> requests.Response:
        response = get_response()
        self._update_ratelimit(response)

        for cool_off_interval in (5, 10):
            if response.status_code != 429:
                break

            LOGGER.debug("Rate limit exceeded, waiting %s seconds", cool_off_interval)
            time.sleep(cool_off_interval)
            response = get_response()
            self._update_ratelimit(response)

        return response

    def _get(
        self,
        uri_end,
        key=None,
        params=None,
        next_page_key="nextLink",
    ):
        return self._request(
            method="GET",
            uri_end=uri_end,
            key=key,
            params=params,
            next_page_key=next_page_key,
        )

    # TODO: delete this in the future, substitute with _query_async
    def _query(self, uri_end, body, params=None):
        json_data = self._request_json_from_url(
            "POST", self._base_url + uri_end, body=body, params=params
        )

        data = self._lookup(json_data, "properties")
        columns = self._lookup(data, "columns")
        rows = self._lookup(data, "rows")

        next_link = data.get("nextLink")
        while next_link:
            new_json_data = self._request_json_from_url("POST", next_link, body=body)
            data = self._lookup(new_json_data, "properties")
            rows += self._lookup(data, "rows")
            next_link = data.get("nextLink")

        common_metadata = {k: v for k, v in json_data.items() if k != "properties"}
        processed_query = self._process_query(columns, rows, common_metadata)
        return processed_query

    def _process_query(self, columns, rows, common_metadata):
        processed_query = []
        column_names = [c["name"] for c in columns]
        for index, row in enumerate(rows):
            processed_row = common_metadata.copy()
            # each entry should have a different name because the agent expects this value to be
            # different for each resource but in case of a query the "name" is the id of the
            # query so we replace it with a different name for each query result
            processed_row["name"] = f"{processed_row['name']}-{index}"
            processed_row["properties"] = dict(zip(column_names, row))
            processed_query.append(processed_row)
        return processed_query

    def _get_paginated_data(
        self,
        next_link,
        next_page_key,
        method,
        body,
        key,
    ):
        data = []
        while next_link:
            new_json_data = self._request_json_from_url(method, next_link, body=body)
            data += self._lookup(new_json_data, key)
            next_link = new_json_data.get(next_page_key)

        return data

    def request(
        self,
        method,
        uri_end=None,
        full_uri=None,
        body=None,
        key=None,
        params=None,
        next_page_key="nextLink",
    ):
        return self._request(
            method=method,
            uri_end=uri_end,
            full_uri=full_uri,
            body=body,
            key=key,
            params=params,
            next_page_key=next_page_key,
        )

    def _request(
        self,
        method,
        uri_end=None,
        full_uri=None,
        body=None,
        key=None,
        params=None,
        next_page_key="nextLink",
    ):
        uri = full_uri or self._base_url + uri_end
        if not uri:
            raise ValueError("No URI provided")

        json_data = self._request_json_from_url(method, uri, body=body, params=params)

        if (error := json_data.get("error")) is not None:
            raise _make_exception(error)

        if key is None:
            return json_data

        data = self._lookup(json_data, key)

        # The API will not send more than 1000 recources at once.
        # See if we must fetch another page:
        if next_link := json_data.get(next_page_key):
            return data + self._get_paginated_data(
                next_link=next_link,
                next_page_key=next_page_key,
                method=method,
                body=body,
                key=key,
            )

        return data

    def _request_json_from_url(self, method, url, *, body=None, params=None):
        def get_response():
            return requests.request(
                method,
                url,
                json=body,
                params=params,
                headers=self._headers,
                proxies=self._http_proxy_config.to_requests_proxies(),
            )

        response = self._handle_ratelimit(get_response)
        json_data = response.json()
        LOGGER.debug("response: %r", json_data)
        return json_data

    @staticmethod
    def _lookup(json_data, key):
        try:
            return json_data[key]
        except KeyError:
            raise _make_exception(json_data)


class BaseAsyncApiClient(BaseApiClient):
    async def _query_async(self, uri_end, body, params=None):
        async with aiohttp.ClientSession(headers=self._headers) as session:
            async with session.request(
                "POST",
                self._base_url + uri_end,
                json=body,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
                proxy=self._http_proxy_config.to_requests_proxies(),
            ) as response:
                json_data = await response.json()
                data = self._lookup(json_data, "properties")
                columns = self._lookup(data, "columns")
                rows = self._lookup(data, "rows")

                next_link = data.get("nextLink")
                while next_link:
                    async with session.post(next_link, json=body) as new_response:
                        new_json_data = await new_response.json()
                        data = self._lookup(new_json_data, "properties")
                        rows += self._lookup(data, "rows")
                        next_link = data.get("nextLink")

                common_metadata = {k: v for k, v in json_data.items() if k != "properties"}
                processed_query = self._process_query(columns, rows, common_metadata)
                return processed_query

    async def _handle_ratelimit_async(self, session, method, url, **kwargs):
        async def get_response():
            async with session.request(method, url, **kwargs) as response:
                await response.json()
                return response

        response = await get_response()
        self._update_ratelimit(response)

        for cool_off_interval in (5, 10):
            if response.status != 429:
                break

            LOGGER.debug("Rate limit exceeded, waiting %s seconds", cool_off_interval)
            await asyncio.sleep(cool_off_interval)
            response = await get_response()
            self._update_ratelimit(response)

        return response

    async def request_async(
        self,
        method,
        uri_end=None,
        full_uri=None,
        body=None,
        key=None,
        params=None,
        next_page_key="nextLink",
        headers_expansion={},
    ):
        uri = full_uri or self._base_url + uri_end
        if not uri:
            raise ValueError("No URI provided")

        # TODO: share session between requests!
        async with aiohttp.ClientSession(headers={**self._headers, **headers_expansion}) as session:
            response = await self._handle_ratelimit_async(
                session,
                method,
                uri,
                json=body,
                params=params,
                timeout=30,
                proxy=self._http_proxy_config.to_requests_proxies(),
            )
            json_data = await response.json()
            LOGGER.debug("response: %r", json_data)

            if (error := json_data.get("error")) is not None:
                raise _make_exception(error)

            if key is None:
                return json_data

            data = self._lookup(json_data, key)

            if next_link := json_data.get(next_page_key):
                return data + await self._get_paginated_data_async(
                    next_link=next_link,
                    next_page_key=next_page_key,
                    method=method,
                    body=body,
                    key=key,
                )

            return data

    async def _get_paginated_data_async(
        self,
        next_link: str,
        next_page_key: str,
        method: str,
        body: dict,
        key: str,
    ) -> list:
        data = []
        while next_link:
            new_json_data = await self.request_async(method, full_uri=next_link, body=body)
            data += self._lookup(new_json_data, key)
            next_link = new_json_data.get(next_page_key)

        return data

    async def get_async(
        self,
        uri_end,
        key=None,
        params=None,
        next_page_key="nextLink",
    ):
        return await self.request_async(
            method="GET",
            uri_end=uri_end,
            key=key,
            params=params,
            next_page_key=next_page_key,
        )


class MgmtApiClient(BaseAsyncApiClient):
    def __init__(
        self,
        authority_urls: _AuthorityURLs,
        http_proxy_config: HTTPProxyConfig,
        subscription: str,
    ):
        self.subscription = subscription
        super().__init__(authority_urls, http_proxy_config)

    @staticmethod
    def _get_available_metrics_from_exception(
        desired_names: str, api_error: ApiError, resource_type: str
    ) -> str | None:
        error_message = api_error.args[0]
        match = re.match(
            r"Failed to find metric configuration for provider.*Valid metrics: ([\w,]*)",
            error_message,
        )
        if not match:
            raise api_error

        available_names = match.groups()[0]
        retry_names = set(desired_names.split(",")) & set(available_names.split(","))
        if not retry_names:
            LOGGER.debug("None of the expected metrics are available for %s", resource_type)
            return None

        return ",".join(sorted(retry_names))

    async def app_gateway_view(self, group, name):
        url = "resourceGroups/{}/providers/Microsoft.Network/applicationGateways/{}"
        return await self.get_async(url.format(group, name), params={"api-version": "2022-01-01"})

    async def load_balancer_view(self, group, name):
        url = "resourceGroups/{}/providers/Microsoft.Network/loadBalancers/{}"
        return self.get_async(url.format(group, name), params={"api-version": "2022-01-01"})

    def nic_ip_conf_view(self, group, nic_name, ip_conf_name):
        url = (
            "resourceGroups/{}/providers/Microsoft.Network/networkInterfaces/{}/ipConfigurations/{}"
        )
        return self._get(
            url.format(group, nic_name, ip_conf_name),
            params={"api-version": "2022-01-01"},
        )

    def nic_vmss_ip_conf_view(self, group, vmss, virtual_machine_index, nic_name, ip_conf_name):
        return self._get(
            f"resourceGroups/{group}/providers/microsoft.Compute/virtualMachineScaleSets/"
            f"{vmss}/virtualMachines/{virtual_machine_index}/networkInterfaces/{nic_name}/ipConfigurations/{ip_conf_name}",
            params={"api-version": "2024-07-01"},
        )

    async def public_ip_view(self, group, name):
        url = "resourceGroups/{}/providers/Microsoft.Network/publicIPAddresses/{}"
        return await self.get_async(url.format(group, name), params={"api-version": "2022-01-01"})

    async def vnet_gateway_view(self, group, name):
        url = "resourceGroups/{}/providers/Microsoft.Network/virtualNetworkGateways/{}"
        return await self.get_async(url.format(group, name), params={"api-version": "2022-01-01"})

    async def vnet_peering_view(self, group, providers, vnet_id, vnet_peering_id):
        url = "resourceGroups/{}/providers/{}/virtualNetworks/{}/virtualNetworkPeerings/{}"
        return await self.get_async(
            url.format(group, providers, vnet_id, vnet_peering_id),
            params={"api-version": "2022-01-01"},
        )

    async def vnet_gateway_health(self, group, providers, vnet_gw):
        url = (
            "resourceGroups/{}/providers/{}/virtualNetworkGateways/{}/providers/"
            "Microsoft.ResourceHealth/availabilityStatuses/current"
        )
        return await self.get_async(
            url.format(group, providers, vnet_gw), params={"api-version": "2015-01-01"}
        )

    async def usagedetails(self):
        yesterday = (NOW - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        body = {
            "type": "ActualCost",
            "dataSet": {
                "granularity": "None",
                "aggregation": {
                    "totalCost": {"name": "Cost", "function": "Sum"},
                    "totalCostUSD": {"name": "CostUSD", "function": "Sum"},
                },
                "grouping": [
                    {"type": "Dimension", "name": "ResourceType"},
                    {"type": "Dimension", "name": "ResourceGroupName"},
                ],
                "include": ["Tags"],
            },
            "timeframe": "Custom",
            "timePeriod": {
                "from": f"{yesterday}T00:00:00+00:00",
                "to": f"{yesterday}T23:59:59+00:00",
            },
        }
        return await self._query_async(
            "/providers/Microsoft.CostManagement/query",
            body=body,
            # here 10000 might be too high,
            # but I haven't found any useful documentation.
            # No "$top" means 1000
            params={"api-version": "2021-10-01", "$top": "10000"},
        )

    async def metrics(self, region, resource_ids, params):
        if self._regional_url is None:
            raise ValueError("Regional url not configured")

        params["api-version"] = "2023-10-01"
        try:
            return await self.request_async(
                "POST",
                full_uri=self._regional_url(region) + "/metrics:getBatch",
                body={"resourceids": resource_ids},
                params=params,
                key="values",
            )

        except ApiError as exc:
            retry_names = self._get_available_metrics_from_exception(
                params["metricnames"], exc, params["metricnamespace"]
            )
            if retry_names:
                params["metricnames"] = retry_names
                return await self.request_async(
                    "POST",
                    full_uri=self._regional_url(region) + "/metrics:getBatch",
                    body={"resourceids": resource_ids},
                    params=params,
                    key="values",
                )
            return []


# The following *Config objects provide a Configuration instance as described in
# CMK-513 (comment-12620).
# For now the passed commandline arguments are used to create it.


class GroupConfig:
    def __init__(self, name: str) -> None:
        super().__init__()
        if not name:
            raise ValueError("falsey group name: %r" % name)
        self.name = name
        self.resources: list = []

    @property
    def fetchall(self):
        return not self.resources

    def add_key(self, key: str, value: str) -> None:
        if key == "resources":
            self.resources = value.split(",")
            return
        raise ValueError("unknown config key: %s" % key)

    def __str__(self) -> str:
        if self.fetchall:
            return "[%s]\n  <fetchall>" % self.name
        return "[%s]\n" % self.name + "\n".join("resource: %s" % r for r in self.resources)


class ExplicitConfig:
    def __init__(self, raw_list: Sequence[str]) -> None:
        super().__init__()
        self.groups: dict = {}
        self.current_group = None
        for item in raw_list:
            if "=" not in item:
                raise ValueError("must be in <key>=<value> format: %r" % item)
            key, value = item.split("=", 1)
            self.add_key(key, value)

    @property
    def fetchall(self) -> bool:
        return not self.groups

    def add_key(self, key: str, value: str) -> None:
        if key == "group":
            group_name = value.lower()
            self.current_group = self.groups.setdefault(group_name, GroupConfig(group_name))
            return
        if self.current_group is None:
            raise RuntimeError("missing arg: group=<name>")
        self.current_group.add_key(key, value)

    def is_configured(self, resource: AzureResource) -> bool:
        if self.fetchall:
            return True
        group_config = self.groups.get(resource.info["group"].lower())
        if group_config is None:
            return False
        if group_config.fetchall:
            return True
        return resource.info["name"] in group_config.resources

    def __str__(self) -> str:
        if self.fetchall:
            return "[<fetchall>]"
        return "\n".join(str(group) for group in self.groups.values())


class TagBasedConfig:
    def __init__(self, required: Sequence[str], key_values: Sequence[Sequence[str]]) -> None:
        super().__init__()
        self._required = required
        self._values = key_values

    def is_configured(self, resource: AzureResource) -> bool:
        if not all(k in resource.tags for k in self._required):
            return False
        for key, val in self._values:
            if resource.tags.get(key) != val:
                return False
        return True

    def __str__(self) -> str:
        lines = []
        if self._required:
            lines.append("required tags: %s" % ", ".join(self._required))
        for key, val in self._values:
            lines.append(f"required value for {key!r}: {val!r}")
        return "\n".join(lines)


class Selector:
    def __init__(self, args: Args) -> None:
        super().__init__()
        self._explicit_config = ExplicitConfig(raw_list=args.explicit_config)
        self._tag_based_config = TagBasedConfig(args.require_tag, args.require_tag_value)

    def do_monitor(self, resource: AzureResource) -> bool:
        if not self._explicit_config.is_configured(resource):
            return False
        if not self._tag_based_config.is_configured(resource):
            return False
        return True

    def __str__(self) -> str:
        lines = [
            "Explicit configuration:\n  %s" % str(self._explicit_config).replace("\n", "\n  "),
            "Tag based configuration:\n  %s" % str(self._tag_based_config).replace("\n", "\n  "),
        ]
        return "\n".join(lines)


class Section:
    LOCK = Lock()

    def __init__(
        self,
        name: str,
        piggytargets: Iterable[str],
        separator: int,
        options: Sequence[str],
    ) -> None:
        super().__init__()
        self._sep = chr(separator)
        self._piggytargets = list(piggytargets)
        self._cont: list = []
        section_options = ":".join(["sep(%d)" % separator, *options])
        self._title = f"<<<{name.replace('-', '_')}:{section_options}>>>\n"

    def formatline(self, tokens):
        return self._sep.join(map(str, tokens)) + "\n"

    def add(self, info):
        if not info:
            return
        if isinstance(info[0], list | tuple):  # we got a list of lines
            for row in info:
                self._cont.append(self.formatline(row))
        else:  # assume one single line
            self._cont.append(self.formatline(info))

    def write(self, write_empty: bool = False) -> None:
        if not (write_empty or self._cont):
            return
        with self.LOCK:
            for piggytarget in self._piggytargets:
                sys.stdout.write(f"<<<<{piggytarget}>>>>\n")
                sys.stdout.write(self._title)
                sys.stdout.writelines(self._cont)
            sys.stdout.write("<<<<>>>>\n")
            sys.stdout.flush()


class AzureSection(Section):
    def __init__(
        self, name: str, piggytargets: Iterable[str] = ("",), separator: int = 124
    ) -> None:
        super().__init__("azure_%s" % name, piggytargets, separator=separator, options=[])


class LabelsSection(Section):
    def __init__(self, piggytarget: str) -> None:
        super().__init__("azure_labels", [piggytarget], separator=0, options=[])


class IssueCollector:
    def __init__(self) -> None:
        super().__init__()
        self._list: list[tuple[str, str]] = []

    def add(self, issue_type: str, issued_by: str, issue_msg: str) -> None:
        issue = {"type": issue_type, "issued_by": issued_by, "msg": issue_msg}
        self._list.append(("issue", json.dumps(issue)))

    def dumpinfo(self) -> list[tuple[str, str]]:
        return self._list

    def __len__(self) -> int:
        return len(self._list)


def create_metric_dict(metric, aggregation, interval_id):
    name = metric["name"]["value"]
    metric_dict = {
        "name": name,
        "aggregation": aggregation,
        "value": None,
        "unit": metric["unit"].lower(),
        "timestamp": None,
        "interval_id": interval_id,
        "interval": None,
    }

    timeseries = metric.get("timeseries")
    if not timeseries:
        return None

    for measurement in reversed(timeseries):
        dataset = measurement.get("data", ())
        if not dataset:
            continue

        try:
            metric_dict["interval"] = str(
                datetime.datetime.strptime(dataset[-1]["timeStamp"], "%Y-%m-%dT%H:%M:%SZ")
                - datetime.datetime.strptime(dataset[-2]["timeStamp"], "%Y-%m-%dT%H:%M:%SZ")
            )
        except (IndexError, TypeError):
            pass

        for data in reversed(dataset):
            LOGGER.debug("data: %s", data)
            metric_dict["value"] = data.get(aggregation)
            if metric_dict["value"] is not None:
                metric_dict["timestamp"] = data["timeStamp"]
                return metric_dict

    return None


def get_attrs_from_uri(uri: str) -> Mapping[str, str]:
    """The uri contains info on subscription, resource group, provider."""
    attrs = {}
    segments = uri.split("/")
    for idx, segment in enumerate(segments):
        if segment in ("subscriptions", "providers"):
            attrs[segment[:-1]] = segments[idx + 1]
        if segment.lower() == "resourcegroups":
            # we have seen "resouceGroups" and "resourcegroups"
            attrs["group"] = segments[idx + 1]
    return attrs


class AzureResource:
    def __init__(
        self,
        info: Mapping[str, Any],
        tag_key_pattern: TagsOption,
    ) -> None:
        super().__init__()
        self.tags = self._filter_tags(info.get("tags", {}), tag_key_pattern)
        self.info = {**info, "tags": self.tags}
        self.info.update(get_attrs_from_uri(info["id"]))

        self.section = info["type"].split("/")[-1].lower()
        self.piggytargets = []
        if group := self.info.get("group"):
            self.info["group"] = group.lower()
            self.piggytargets.append(group.lower())
        self.metrics: list = []

    def dumpinfo(self) -> Sequence[tuple]:
        # TODO: Hmmm, should the variable-length tuples actually be lists?
        lines: list[tuple[str | int, ...]] = [("Resource",), (json.dumps(self.info),)]
        if self.metrics:
            lines += [("metrics following", len(self.metrics))]
            lines += [(json.dumps(m),) for m in self.metrics]
        return lines

    def _filter_tags(self, tags: dict[str, str], tag_key_pattern: TagsOption) -> dict[str, str]:
        if tag_key_pattern == TagsImportPatternOption.import_all:
            return tags
        if tag_key_pattern == TagsImportPatternOption.ignore_all:
            return {}
        return {key: value for key, value in tags.items() if re.search(tag_key_pattern, key)}


def filter_keys(mapping: Mapping, keys: Iterable[str]) -> Mapping:
    items = ((k, mapping.get(k)) for k in keys)
    return {k: v for k, v in items if v is not None}


def get_params_from_azure_id(
    resource_id: str, resource_types: Sequence[str] | None = None
) -> Sequence[str]:
    values = resource_id.lower().split("/")
    type_strings = list(map(str.lower, resource_types)) if resource_types else []
    index_keywords = ["subscriptions", "resourcegroups"] + type_strings
    return [values[values.index(keyword) + 1] for keyword in index_keywords]


async def get_frontend_ip_configs(
    mgmt_client: MgmtApiClient, resource: Mapping
) -> dict[str, dict[str, object]]:
    frontend_ip_configs: dict[str, dict[str, object]] = {}

    for ip_config in resource["properties"]["frontendIPConfigurations"]:
        ip_config_data = {
            **filter_keys(ip_config, ("id", "name")),
            **filter_keys(
                ip_config["properties"],
                ("privateIPAllocationMethod", "privateIPAddress"),
            ),
        }
        if "publicIPAddress" in ip_config.get("properties"):
            public_ip_id = ip_config["properties"]["publicIPAddress"]["id"]

            _, group, ip_name = get_params_from_azure_id(
                public_ip_id, resource_types=["publicIPAddresses"]
            )
            public_ip: Mapping = await mgmt_client.public_ip_view(group, ip_name)
            dns_settings = public_ip["properties"].get("dnsSettings")

            public_ip_keys = ("ipAddress", "publicIPAllocationMethod")
            ip_config_data["public_ip_address"] = {
                "dns_fqdn": dns_settings["fqdn"] if dns_settings else "",
                **filter_keys(public_ip, ("name", "location")),
                **filter_keys(public_ip["properties"], public_ip_keys),
            }

        frontend_ip_configs[ip_config_data["id"]] = ip_config_data

    return frontend_ip_configs


def get_routing_rules(app_gateway: Mapping) -> list[Mapping]:
    routing_rule_keys = ("httpListener", "backendAddressPool", "backendHttpSettings")
    return [
        {
            "name": r["name"],
            **filter_keys(r["properties"], routing_rule_keys),
        }
        for r in app_gateway["properties"]["requestRoutingRules"]
    ]


def get_http_listeners(app_gateway: Mapping) -> Mapping[str, Mapping]:
    listener_keys = (
        "port",
        "protocol",
        "hostNames",
        "frontendIPConfiguration",
        "frontendPort",
    )
    return {
        l["id"]: {
            "id": l["id"],
            "name": l["name"],
            **filter_keys(l["properties"], listener_keys),
        }
        for l in app_gateway["properties"]["httpListeners"]
    }


async def process_app_gateway(mgmt_client: MgmtApiClient, resource: AzureResource) -> None:
    app_gateway = await mgmt_client.app_gateway_view(resource.info["group"], resource.info["name"])
    frontend_ip_configs = await get_frontend_ip_configs(mgmt_client, app_gateway)

    resource.info["properties"] = {}
    resource.info["properties"]["operational_state"] = app_gateway["properties"]["operationalState"]
    resource.info["properties"]["frontend_api_configs"] = frontend_ip_configs
    resource.info["properties"]["routing_rules"] = get_routing_rules(app_gateway)
    resource.info["properties"]["http_listeners"] = get_http_listeners(app_gateway)

    if (
        waf_config := app_gateway["properties"].get("webApplicationFirewallConfiguration")
    ) is not None:
        resource.info["properties"]["waf_enabled"] = waf_config["enabled"]

    frontend_ports = {
        p["id"]: {"port": p["properties"]["port"]}
        for p in app_gateway["properties"]["frontendPorts"]
    }
    resource.info["properties"]["frontend_ports"] = frontend_ports

    backend_settings = {
        c["id"]: {
            "name": c["name"],
            **filter_keys(c["properties"], ("port", "protocol")),
        }
        for c in app_gateway["properties"]["backendHttpSettingsCollection"]
    }
    resource.info["properties"]["backend_settings"] = backend_settings

    backend_pools = {p["id"]: p for p in app_gateway["properties"]["backendAddressPools"]}
    resource.info["properties"]["backend_address_pools"] = backend_pools


def _get_standard_network_interface_config(
    mgmt_client: MgmtApiClient, nic_id: str
) -> Mapping[str, Mapping]:
    _, group, nic_name, ip_conf_name = get_params_from_azure_id(
        nic_id, resource_types=["networkInterfaces", "ipConfigurations"]
    )
    return mgmt_client.nic_ip_conf_view(group, nic_name, ip_conf_name)


def _get_vmss_network_interface_config(
    mgmt_client: MgmtApiClient, nic_id: str
) -> Mapping[str, Mapping]:
    _, group, vmss, vm_index, nic_name, ip_conf_name = get_params_from_azure_id(
        nic_id,
        resource_types=[
            "virtualMachineScaleSets",
            "virtualMachines",
            "networkInterfaces",
            "ipConfigurations",
        ],
    )
    return mgmt_client.nic_vmss_ip_conf_view(group, vmss, vm_index, nic_name, ip_conf_name)


def get_network_interface_config(mgmt_client: MgmtApiClient, nic_id: str) -> Mapping[str, Mapping]:
    if "virtualMachineScaleSets" in nic_id:
        return _get_vmss_network_interface_config(mgmt_client, nic_id)

    return _get_standard_network_interface_config(mgmt_client, nic_id)


async def get_inbound_nat_rules(
    mgmt_client: MgmtApiClient, load_balancer: Mapping
) -> list[dict[str, object]]:
    nat_rule_keys = ("frontendPort", "backendPort", "frontendIPConfiguration")
    nic_config_keys = ("privateIPAddress", "privateIPAllocationMethod")

    inbound_nat_rules: list[dict[str, object]] = []
    for inbound_nat_rule in load_balancer["properties"]["inboundNatRules"]:
        nat_rule_data = {
            "name": inbound_nat_rule["name"],
            **filter_keys(inbound_nat_rule["properties"], nat_rule_keys),
        }

        if "backendIPConfiguration" in inbound_nat_rule.get("properties"):
            ip_config_id = inbound_nat_rule["properties"]["backendIPConfiguration"]["id"]
            nic_config = get_network_interface_config(mgmt_client, ip_config_id)

            if "name" in nic_config and "properties" in nic_config:
                nat_rule_data["backend_ip_config"] = {
                    "name": nic_config["name"],
                    **filter_keys(nic_config["properties"], nic_config_keys),
                }

        inbound_nat_rules.append(nat_rule_data)

    return inbound_nat_rules


async def get_backend_address_pools(
    mgmt_client: MgmtApiClient, load_balancer: Mapping
) -> list[dict[str, object]]:
    backend_address_keys = ("privateIPAddress", "privateIPAllocationMethod", "primary")
    backend_pools: list[dict[str, object]] = []

    for backend_pool in load_balancer["properties"]["backendAddressPools"]:
        backend_addresses = []
        for backend_address in backend_pool["properties"].get("loadBalancerBackendAddresses", []):
            if "networkInterfaceIPConfiguration" in backend_address.get("properties"):
                ip_config_id = backend_address["properties"]["networkInterfaceIPConfiguration"][
                    "id"
                ]
                nic_config = get_network_interface_config(mgmt_client, ip_config_id)

                if "name" in nic_config and "properties" in nic_config:
                    backend_address_data = {
                        "name": nic_config["name"],
                        **filter_keys(nic_config["properties"], backend_address_keys),
                    }
                    backend_addresses.append(backend_address_data)

        backend_pools.append(
            {
                "id": backend_pool["id"],
                "name": backend_pool["name"],
                "addresses": backend_addresses,
            }
        )

    return backend_pools


async def process_load_balancer(mgmt_client: MgmtApiClient, resource: AzureResource) -> None:
    load_balancer = await mgmt_client.load_balancer_view(
        resource.info["group"], resource.info["name"]
    )
    frontend_ip_configs = await get_frontend_ip_configs(mgmt_client, load_balancer)
    inbound_nat_rules = await get_inbound_nat_rules(mgmt_client, load_balancer)
    backend_pools = await get_backend_address_pools(mgmt_client, load_balancer)

    resource.info["properties"] = {}
    resource.info["properties"]["frontend_ip_configs"] = frontend_ip_configs
    resource.info["properties"]["inbound_nat_rules"] = inbound_nat_rules
    resource.info["properties"]["backend_pools"] = {p["id"]: p for p in backend_pools}

    outbound_rule_keys = ("protocol", "idleTimeoutInMinutes", "backendAddressPool")
    outbound_rules = [
        {"name": r["name"], **filter_keys(r["properties"], outbound_rule_keys)}
        for r in load_balancer["properties"].get("outboundRules", [])
    ]
    resource.info["properties"]["outbound_rules"] = outbound_rules


async def get_remote_peerings(
    mgmt_client: MgmtApiClient, resource: dict
) -> Sequence[Mapping[str, object]]:
    peering_keys = ("name", "peeringState", "peeringSyncLevel")

    vnet_peerings = []
    for vnet_peering in resource["properties"].get("remoteVirtualNetworkPeerings", []):
        vnet_peering_id = vnet_peering["id"]
        subscription, group, providers, vnet_id, vnet_peering_id = get_params_from_azure_id(
            vnet_peering_id,
            resource_types=[
                "providers",
                "virtualNetworks",
                "virtualNetworkPeerings",
            ],
        )
        # skip vNet peerings that belong to another Azure subscription
        if subscription != mgmt_client.subscription:
            continue

        peering_view = await mgmt_client.vnet_peering_view(
            group, providers, vnet_id, vnet_peering_id
        )
        vnet_peering = {
            **filter_keys(peering_view, peering_keys),
            **filter_keys(peering_view["properties"], peering_keys),
        }
        vnet_peerings.append(vnet_peering)

    return vnet_peerings


async def get_vnet_gw_health(mgmt_client: MgmtApiClient, resource: Mapping) -> Mapping[str, object]:
    health_keys = ("availabilityState", "summary", "reasonType", "occuredTime")

    _, group, providers, vnet_gw = get_params_from_azure_id(
        resource["id"], resource_types=["providers", "virtualNetworkGateways"]
    )
    health_view = await mgmt_client.vnet_gateway_health(group, providers, vnet_gw)
    return filter_keys(health_view["properties"], health_keys)


async def process_virtual_net_gw(mgmt_client: MgmtApiClient, resource: AzureResource) -> None:
    gw_keys = (
        "bgpSettings",
        "disableIPSecReplayProtection",
        "gatewayType",
        "vpnType",
        "activeActive",
        "enableBgp",
    )

    gw_view = await mgmt_client.vnet_gateway_view(resource.info["group"], resource.info["name"])
    resource.info["specific_info"] = filter_keys(gw_view["properties"], gw_keys)

    resource.info["properties"] = {}
    resource.info["properties"]["remote_vnet_peerings"] = await get_remote_peerings(
        mgmt_client, gw_view
    )
    resource.info["properties"]["health"] = await get_vnet_gw_health(mgmt_client, gw_view)


class MetricCache(DataCache):
    def __init__(
        self,
        *,
        metric_definition: tuple[str, str, str],
        resource_type: str,
        region: str,
        cache_id: str,
        ref_time: datetime.datetime,
        debug: bool = False,
    ) -> None:
        self.metric_definition = metric_definition
        metric_names = metric_definition[0]
        super().__init__(
            self.get_cache_path(cache_id, resource_type, region),
            metric_names,
            debug=debug,
        )
        self.remaining_reads = None
        self.timedelta = {
            "PT1M": datetime.timedelta(minutes=1),
            "PT5M": datetime.timedelta(minutes=5),
            "PT1H": datetime.timedelta(hours=1),
        }[metric_definition[1]]
        # For 1-min metrics, the start time should be at least 4 minutes before because of the
        # ingestion time of Azure metrics (we had to change from 3 minutes to 5 minutes because we
        # were missing some metrics with 3 minutes).
        # More info on Azure Monitor Ingestion time:
        # https://docs.microsoft.com/en-us/azure/azure-monitor/logs/data-ingestion-time
        self.start_time = (ref_time - 5 * self.timedelta).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.end_time = ref_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def get_cache_path(cache_id: str, resource_type: str, region: str) -> Path:
        valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
        subdir = "".join(c if c in valid_chars else "_" for c in f"{region}_{resource_type}")
        return AZURE_CACHE_FILE_PATH / cache_id / subdir

    @property
    def cache_interval(self) -> int:
        return self.timedelta.seconds

    def get_validity_from_args(self, *args: Any) -> bool:
        return True

    async def get_live_data(self, *args: Any) -> Any:
        mgmt_client: MgmtApiClient = args[0]
        region: str = args[1]
        resource_ids: Sequence[str] = args[2]
        resource_type: str = args[3]
        err: IssueCollector = args[4]

        metric_names, interval, aggregation = self.metric_definition

        params = {
            "starttime": self.start_time,
            "endtime": self.end_time,
            "interval": interval,
            "metricnames": metric_names,
            "metricnamespace": resource_type,
            "aggregation": aggregation,
        }

        raw_metrics = []
        for chunk in _chunks(resource_ids):
            raw_metrics += await mgmt_client.metrics(region, chunk, params)

        metrics = defaultdict(list)

        for resource_metrics in raw_metrics:
            resource_id = resource_metrics["resourceid"]

            for raw_metric in resource_metrics["value"]:
                parsed_metric = create_metric_dict(raw_metric, aggregation, interval)
                if parsed_metric is not None:
                    metrics[resource_id].append(parsed_metric)
                else:
                    metric_name = raw_metric["name"]["value"]
                    if metric_name in OPTIONAL_METRICS.get(resource_type, []):
                        continue

                    msg = f"metric not found: {metric_name} ({aggregation})"
                    err.add("info", resource_id, msg)
                    LOGGER.info(msg)

        return metrics

    async def get_data_async(self, *args, **kwargs):
        use_cache = kwargs.pop("use_cache", True)
        if use_cache and self.get_validity_from_args(*args) and self._cache_is_valid():
            try:
                return self.get_cached_data()
            except (OSError, ValueError) as exc:
                logging.info("Getting live data (failed to read from cache: %s).", exc)
                if self.debug:
                    raise

        live_data = await self.get_live_data(*args)
        try:
            self._write_to_cache(live_data)
        except (OSError, TypeError) as exc:
            logging.info("Failed to write data to cache file: %s", exc)
            if self.debug:
                raise
        return live_data


async def process_users(graph_api_client: BaseAsyncApiClient) -> AzureSection:
    users_count = await graph_api_client.request_async(
        "GET",
        uri_end="users",
        params={"$top": 1, "$count": "true"},
        key="@odata.count",
        headers_expansion={"ConsistencyLevel": "eventual"},
    )
    section = AzureSection("ad")
    section.add(["users_count", users_count])

    return section


async def process_organization(graph_api_client: BaseAsyncApiClient) -> AzureSection:
    orgs = await graph_api_client.get_async("organization", key="value")
    section = AzureSection("ad")
    section.add(["ad_connect", json.dumps(orgs)])

    return section


async def process_app_registrations(graph_api_client: BaseAsyncApiClient) -> AzureSection:
    apps = await graph_api_client.get_async(
        "applications", key="value", next_page_key="@odata.nextLink"
    )

    key_subset = {"id", "appId", "displayName", "passwordCredentials"}
    apps = [{k: app[k] for k in key_subset} for app in apps if app["passwordCredentials"]]

    section = AzureSection("app_registration", separator=0)
    for app_reg in apps:
        section.add([json.dumps(app_reg)])

    return section


async def process_metrics(
    mgmt_client: MgmtApiClient, resources: Sequence[AzureResource], args: Args
) -> None:
    errors = await _gather_metrics(mgmt_client, resources, args)

    if not errors:
        return

    agent_info_section = AzureSection("agent_info")
    agent_info_section.add(errors.dumpinfo())
    agent_info_section.write()


async def _gather_metrics(
    mgmt_client: MgmtApiClient, all_resources: Sequence[AzureResource], args: Args
) -> IssueCollector:
    """
    Gather metrics for all resources. Metrics are collected per resource type, region, metric
    aggregation and time resolution. One query collects metrics of all resources of a given type.
    """
    resource_dict = {resource.info["id"]: resource for resource in all_resources}
    err = IssueCollector()

    grouped_resource_ids = defaultdict(list)
    for resource in all_resources:
        grouped_resource_ids[(resource.info["type"], resource.info["location"])].append(
            resource.info["id"]
        )

    tasks = set()
    for group, resource_ids in grouped_resource_ids.items():
        resource_type, resource_region = group

        if resource_type == FetchedResource.virtual_machines.type:
            if args.piggyback_vms != "self":
                continue

        metric_definitions = ALL_METRICS.get(resource_type, [])
        for metric_definition in metric_definitions:
            cache = MetricCache(
                metric_definition=metric_definition,
                resource_type=resource_type,
                region=resource_region,
                cache_id=args.cache_id,
                ref_time=NOW,
                debug=args.debug,
            )

            tasks.add(
                cache.get_data_async(
                    mgmt_client,
                    resource_region,
                    resource_ids,
                    resource_type,
                    err,
                    use_cache=cache.cache_interval > 60,
                )
            )

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, BaseException):
            if args.debug:
                raise result
            err.add("exception", "metric collection", str(result))
            LOGGER.exception(result)
            continue

        for resource_id, metrics in result.items():
            if (resource_metric := resource_dict.get(resource_id)) is not None:
                resource_metric.metrics += metrics
            else:
                LOGGER.info(
                    "Resource %s found in metrics cache no longer monitored",
                    resource_id,
                )

    return err


def get_vm_labels_section(vm: AzureResource, group_labels: GroupLabels) -> LabelsSection:
    group_name = vm.info["group"]
    vm_labels = dict(vm.tags)

    for tag_name, tag_value in group_labels[group_name].items():
        if tag_name not in vm.tags:
            vm_labels[tag_name] = tag_value

    labels_section = LabelsSection(vm.info["name"])
    labels_section.add((json.dumps({"group_name": vm.info["group"], "vm_instance": True}),))
    labels_section.add((json.dumps(vm_labels),))
    return labels_section


async def get_group_labels(
    mgmt_client: MgmtApiClient,
    monitored_groups: Sequence[str],
    tag_key_pattern: TagsOption,
) -> GroupLabels:
    group_labels: dict[str, dict[str, str]] = {}

    resource_groups = await mgmt_client.get_async(
        "resourcegroups", key="value", params={"api-version": "2019-05-01"}
    )

    for group in resource_groups:
        name = group["name"].lower()

        if tag_key_pattern == TagsImportPatternOption.ignore_all:
            tags = {}
        else:
            tags = group.get("tags", {})
            if tag_key_pattern != TagsImportPatternOption.import_all:
                tags = {
                    key: value for key, value in tags.items() if re.search(tag_key_pattern, key)
                }

        if name in monitored_groups:
            group_labels[name] = tags

    return group_labels


def write_group_info(
    monitored_groups: Sequence[str],
    monitored_resources: Sequence[AzureResource],
    group_labels: GroupLabels,
) -> None:
    for group_name, tags in group_labels.items():
        labels_section = LabelsSection(group_name)
        labels_section.add((json.dumps({"group_name": group_name}),))
        labels_section.add((json.dumps(tags),))
        labels_section.write()

    section = AzureSection("agent_info")
    section.add(("monitored-groups", json.dumps(monitored_groups)))
    section.add(
        (
            "monitored-resources",
            json.dumps([r.info["name"] for r in monitored_resources]),
        )
    )
    section.write()
    # write empty agent_info section for all groups, otherwise
    # the service will only be discovered if something goes wrong
    AzureSection("agent_info", monitored_groups).write()


def write_remaining_reads(rate_limit: int | None) -> None:
    agent_info_section = AzureSection("agent_info")
    agent_info_section.add(("remaining-reads", rate_limit))
    agent_info_section.write()


def write_to_agent_info_section(message: str, component: str, status: int) -> None:
    value = json.dumps((status, f"{component}: {message}"))
    section = AzureSection("agent_info")
    section.add(("agent-bailout", value))
    section.write()


def write_exception_to_agent_info_section(exception, component):
    # those exceptions are quite noisy. try to make them more concise:
    msg = str(exception).split("Trace ID", 1)[0]
    msg = msg.split(":", 2)[-1].strip(" ,")

    if "does not have authorization to perform action" in msg:
        msg += "HINT: Make sure you have a proper role asigned to your client!"

    write_to_agent_info_section(msg, component, 2)


async def main_graph_client(args: Args, monitored_services: set[str]) -> None:
    tasks_map = {
        "users_count": process_users,
        "ad_connect": process_organization,
        "app_registrations": process_app_registrations,
    }
    if not any(service in monitored_services for service in tasks_map):
        return

    def _handle_graph_client_exception(exc: Exception, debug: bool) -> None:
        if isinstance(exc, ApiLoginFailed | ApiErrorAuthorizationRequestDenied):
            # We are not raising the exception in debug mode.
            # Having no permissions for the graph API is a legit configuration
            write_exception_to_agent_info_section(exc, "Graph client (async)")
        elif debug:
            raise exc
        else:
            write_exception_to_agent_info_section(exc, "Graph client (async)")

    graph_client = BaseAsyncApiClient(
        _get_graph_authority_urls(args.authority),
        deserialize_http_proxy_config(args.proxy),
    )

    try:
        graph_client.login(args.tenant, args.client, args.secret)
    except Exception as exc:
        _handle_graph_client_exception(exc, args.debug)

    tasks = {
        task_call(graph_client)
        for service, task_call in tasks_map.items()
        if service in monitored_services
    }

    for coroutine in asyncio.as_completed(tasks):
        try:
            section = await coroutine
            section.write()
        except Exception as exc:
            _handle_graph_client_exception(exc, args.debug)


async def get_usage_data(client: MgmtApiClient, args: Args) -> Sequence[Mapping[str, Any]]:
    NO_CONSUMPTION_API = (
        "offer MS-AZR-0145P",
        "offer MS-AZR-0146P",
        "offer MS-AZR-159P",
        "offer MS-AZR-0036P",
        "offer MS-AZR-0143P",
        "offer MS-AZR-0015P",
        "offer MS-AZR-0144P",
        "Customer does not have the privilege to see the cost",
    )

    LOGGER.debug("get usage details")

    try:
        usage_data = await client.usagedetails()
    except ApiError as exc:
        if any(s in exc.args[0] for s in NO_CONSUMPTION_API):
            raise NoConsumptionAPIError
        raise

    LOGGER.debug("yesterdays usage details: %d", len(usage_data))

    for usage in usage_data:
        usage["type"] = "Microsoft.Consumption/usageDetails"
        usage["group"] = usage["properties"]["ResourceGroupName"]

    return usage_data


def write_usage_section(
    usage_data: Sequence[Mapping[str, Any]],
    monitored_groups: list[str],
    tag_key_pattern: TagsOption,
) -> None:
    if not usage_data:
        AzureSection("usagedetails", monitored_groups + [""]).write(write_empty=True)

    for usage in usage_data:
        usage_resource = AzureResource(usage, tag_key_pattern)
        piggytargets = [g for g in usage_resource.piggytargets if g in monitored_groups] + [""]

        section = AzureSection(usage_resource.section, piggytargets)
        section.add(usage_resource.dumpinfo())
        section.write()


async def process_usage_details(
    mgmt_client: MgmtApiClient, monitored_groups: list[str], args: Args
) -> None:
    if "usage_details" not in args.services:
        return

    try:
        usage_section = await get_usage_data(mgmt_client, args)
        if not usage_section:
            write_to_agent_info_section(
                "Azure API did not return any usage details", "Usage client", 0
            )
            return

        write_usage_section(usage_section, monitored_groups, args.tag_key_pattern)

    except NoConsumptionAPIError:
        LOGGER.debug("Azure offer doesn't support querying the cost API")
        return

    except Exception as exc:
        if args.debug:
            raise
        LOGGER.warning("%s", exc)
        write_exception_to_agent_info_section(exc, "Usage client")
        write_usage_section([], monitored_groups, args.tag_key_pattern)


async def process_resource_health(
    mgmt_client: MgmtApiClient,
    monitored_resources_by_id: Mapping[str, AzureResource],
) -> Sequence[AzureSection]:
    response = await mgmt_client.get_async(
        "providers/Microsoft.ResourceHealth/availabilityStatuses",
        params={
            "api-version": "2025-05-01",
            "$top": "1000",  # retrieves up to 1000 (still not clear what) per request
        },
        key="value",
    )

    return _write_resource_health_section(response, monitored_resources_by_id)


async def process_virtual_machines(
    api_client: MgmtApiClient,
    args: Args,
    group_labels: GroupLabels,
    monitored_resources_by_id: Mapping[str, AzureResource],
) -> Sequence[AzureSection]:
    response = await api_client.get_async(
        "providers/Microsoft.Compute/virtualMachines",
        params={
            "api-version": "2024-11-01",
            "statusOnly": "true",  # fetching only run time status
        },
        key="value",
    )

    virtual_machines: list[AzureResource] = []
    for vm in response:
        try:
            resource = monitored_resources_by_id[vm["id"].lower()]
        except KeyError:
            raise ApiErrorMissingData(
                f"Virtual machine not found in monitored resources: {vm['id']}"
            )

        try:
            statuses = vm.pop("properties")["instanceView"]["statuses"]
        except KeyError:
            raise ApiErrorMissingData("Virtual machine instance's statuses must be present")

        resource.info["specific_info"] = {"statuses": statuses}
        virtual_machines.append(resource)

    sections = []
    for resource in virtual_machines:
        if args.piggyback_vms == "self":
            labels_section = get_vm_labels_section(resource, group_labels)
            labels_section.write()

        section = AzureSection(
            FetchedResource.virtual_machines.section,
            [resource.info["name"] if args.piggyback_vms == "self" else resource.info["group"]],
        )
        section.add(resource.dumpinfo())
        sections.append(section)

    return sections


async def process_vault(
    api_client: MgmtApiClient,
    resource: AzureResource,
) -> AzureSection:
    vault_properties = (
        "friendlyName",
        "backupManagementType",
        "protectedItemType",
        "lastBackupTime",
        "lastBackupStatus",
        "protectionState",
        "protectionStatus",
        "policyName",
        "isArchiveEnabled",
    )

    response = await api_client.get_async(
        f"resourceGroups/{resource.info['group']}/providers/Microsoft.RecoveryServices/vaults/{resource.info['name']}/backupProtectedItems",
        params={
            "api-version": "2025-02-01",
        },
        key="value",
    )

    try:
        properties = filter_keys(response[0]["properties"], vault_properties)
    except KeyError:
        write_exception_to_agent_info_section(
            ApiErrorMissingData("Vault properties must be present"), "Vaults"
        )
        raise ApiErrorMissingData("Vault properties must be present")

    resource.info["properties"] = {}
    resource.info["properties"]["backup_containers"] = [properties]

    section = AzureSection(
        FetchedResource.vaults.section,
        resource.piggytargets,
    )
    section.add(resource.dumpinfo())

    return section


class ResourceHealth(TypedDict, total=False):
    id: Required[str]
    properties: Required[Mapping[str, str]]


def _write_resource_health_section(
    resource_health_view: list[ResourceHealth],
    resources_by_id: Mapping[str, AzureResource],
) -> Sequence[AzureSection]:
    health_section: defaultdict[str, list[str]] = defaultdict(list)

    for health in resource_health_view:
        health_id = health["id"]
        _, group = get_params_from_azure_id(health_id)
        resource_id = "/".join(health_id.split("/")[:-4])

        try:
            resource = resources_by_id[resource_id.lower()]
        except KeyError:
            continue

        health_data = {
            "id": health_id,
            "name": "/".join(health_id.split("/")[-6:-4]),
            **filter_keys(
                health["properties"],
                ("availabilityState", "summary", "reasonType", "occuredTime"),
            ),
            "tags": resource.tags,
        }

        health_section[group].append(json.dumps(health_data))

    sections = []
    for group, values in health_section.items():
        section = AzureSection("resource_health", [group.lower()])
        for value in values:
            section.add([value])
        sections.append(section)

    return sections


def _test_connection(args: Args, subscription: str) -> int | tuple[int, str]:
    """We test the connection only via the Management API client, not via the Graph API client.
    The Graph API client is used for three specific services, which are disabled in the default
    setup when configured via the UI.
    The Management API client is used for all other services, so we assume here that this is the
    connection that's essential for the vast majority of setups."""
    mgmt_client = MgmtApiClient(
        _get_mgmt_authority_urls(args.authority, subscription),
        deserialize_http_proxy_config(args.proxy),
        subscription,
    )
    try:
        mgmt_client.login(args.tenant, args.client, args.secret)
    except (ApiLoginFailed, ValueError) as exc:
        error_msg = f"Connection failed with: {exc}\n"
        sys.stdout.write(error_msg)
        return 2, error_msg
    except requests.exceptions.ProxyError as exc:
        error_msg = f"Connection failed due to a proxy error: {exc}\n"
        sys.stdout.write(error_msg)
        return 2, error_msg
    return 0


def get_bulk_tasks(
    mgmt_client: MgmtApiClient,
    args: Args,
    group_labels: GroupLabels,
    monitored_services: set[str],
    monitored_resources_by_id: Mapping[str, AzureResource],
) -> Iterator[asyncio.Task]:
    if FetchedResource.virtual_machines.type in monitored_services:
        yield asyncio.create_task(
            process_virtual_machines(mgmt_client, args, group_labels, monitored_resources_by_id)
        )


async def process_single_resources(
    mgmt_client: MgmtApiClient,
    args: Args,
    monitored_resources_by_id: Mapping[str, AzureResource],
) -> Sequence[Section]:
    sections = []
    tasks = set()
    for resource_id, resource in monitored_resources_by_id.items():
        resource_type = resource.info["type"]
        if resource_type in BULK_QUERIED_RESOURCES:
            continue

        # TODO: convert to real async:
        elif resource_type == "Microsoft.Network/applicationGateways":
            await process_app_gateway(mgmt_client, resource)
        elif resource_type == "Microsoft.Network/virtualNetworkGateways":
            await process_virtual_net_gw(mgmt_client, resource)
        elif resource_type == "Microsoft.Network/loadBalancers":
            await process_load_balancer(mgmt_client, resource)
        # ----

        if resource_type == FetchedResource.vaults.type:
            tasks.add(process_vault(mgmt_client, resource))
        else:
            # simple sections without further processing
            if resource_type in SUPPORTED_FLEXIBLE_DATABASE_SERVER_RESOURCE_TYPES:
                resource.section = "servers"  # use the same section as for single servers

            section = AzureSection(resource.section, resource.piggytargets)
            section.add(resource.dumpinfo())
            sections.append(section)

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for section_async in results:
        if isinstance(section_async, BaseException):
            if args.debug:
                raise section_async
            write_exception_to_agent_info_section(section_async, "Process single resources (async)")
            continue

        sections.append(section_async)

    return sections


async def process_resources(
    mgmt_client: MgmtApiClient,
    args: Args,
    group_labels: GroupLabels,
    selected_resources: Sequence[AzureResource],
    monitored_services: set[str],
) -> None:
    monitored_resources_by_id = {
        r.info["id"].lower(): r for r in selected_resources if r.info["type"] in monitored_services
    }

    tasks = {
        process_resource_health(mgmt_client, monitored_resources_by_id),
        *get_bulk_tasks(
            mgmt_client,
            args,
            group_labels,
            monitored_services,
            monitored_resources_by_id,
        ),
        process_single_resources(mgmt_client, args, monitored_resources_by_id),
    }

    for coroutine in asyncio.as_completed(tasks):
        try:
            for section in await coroutine:
                section.write()
        except Exception as e:
            if args.debug:
                raise
            write_exception_to_agent_info_section(e, "Management client (async)")


async def _collect_resources(
    mgmt_client: MgmtApiClient, args: Args, selector: Selector
) -> tuple[Sequence[AzureResource], list[str]]:
    resources = await mgmt_client.get_async(
        "resources", key="value", params={"api-version": "2019-05-01"}
    )

    all_resources = (AzureResource(r, args.tag_key_pattern) for r in resources)

    # Selected resources are all the resources that match the selector.
    # They are NOT the "monitored resources", which also depend on the *services* selected via command line call.
    # Here, we need all these resources to be able to create the `monitored_groups` sections.
    # -> I don't know if this is actually intended (we are populating the agent information `monitored-resources`
    #    with resources not really monitored), but the agent behaved like this before.
    selected_resources = [r for r in all_resources if selector.do_monitor(r)]
    monitored_groups = sorted({r.info["group"] for r in selected_resources})

    return selected_resources, monitored_groups


async def main_subscription(
    args: Args, selector: Selector, subscription: str, monitored_services: set[str]
) -> None:
    mgmt_client = MgmtApiClient(
        _get_mgmt_authority_urls(args.authority, subscription),
        deserialize_http_proxy_config(args.proxy),
        subscription,
    )

    try:
        mgmt_client.login(args.tenant, args.client, args.secret)
        selected_resources, monitored_groups = await _collect_resources(mgmt_client, args, selector)

    except Exception as exc:
        if args.debug:
            raise
        write_exception_to_agent_info_section(exc, "Management client")
        return

    group_labels = await get_group_labels(mgmt_client, monitored_groups, args.tag_key_pattern)
    write_group_info(monitored_groups, selected_resources, group_labels)

    await process_metrics(mgmt_client, selected_resources, args)

    tasks = {
        process_usage_details(mgmt_client, monitored_groups, args)
        if "usage_details" in monitored_services
        else None,
        process_resources(mgmt_client, args, group_labels, selected_resources, monitored_services),
    }
    tasks.discard(None)
    await asyncio.gather(*tasks)  # type: ignore[arg-type]

    write_remaining_reads(mgmt_client.ratelimit)


def _get_subscriptions(args: Args) -> set[str]:
    if args.subscriptions:
        return set(args.subscriptions)

    if args.all_subscriptions:
        api_client = BaseApiClient(
            _get_mgmt_authority_urls(args.authority, ""),
            deserialize_http_proxy_config(args.proxy),
        )
        api_client.login(args.tenant, args.client, args.secret)
        response = api_client.request(
            method="GET",
            full_uri="https://management.azure.com/subscriptions",
            params={"api-version": "2022-12-01"},
        )
        return {item["subscriptionId"] for item in response.get("value", [])}

    return set()  # no subscriptions


def test_connections(args: Args, subscriptions: set[str]) -> int:
    for subscription in subscriptions:
        if (test_result := _test_connection(args, subscription)) != 0:
            if isinstance(test_result, tuple):
                sys.stderr.write(test_result[1])
                return test_result[0]
            return test_result
    return 0


async def collect_info(args: Args, selector: Selector, subscriptions: set[str]) -> None:
    monitored_services = set(args.services)
    await asyncio.gather(
        main_graph_client(args, monitored_services),
        *{
            main_subscription(args, selector, subscription, monitored_services)
            for subscription in subscriptions
        },
    )


def main(argv=None):
    if argv is None:
        password_store.replace_passwords()
        argv = sys.argv[1:]

    args = parse_arguments(argv)
    selector = Selector(args)
    if args.dump_config:
        sys.stdout.write("Configuration:\n%s\n" % selector)
        return 0

    subscriptions = _get_subscriptions(args)
    # TODO:
    # * fix connection test in case of no subscriptions
    # * make connection test async?
    if args.connection_test:
        return test_connections(args, subscriptions)

    asyncio.run(collect_info(args, selector, subscriptions))
    LOGGER.debug("%s", selector)
    return 0


if __name__ == "__main__":
    main()
