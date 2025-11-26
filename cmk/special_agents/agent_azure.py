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
from concurrent.futures import Executor, ThreadPoolExecutor
from multiprocessing import Lock
from pathlib import Path
from typing import Any, Literal, NamedTuple, TypeVar

import msal  # type: ignore[import-untyped]
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
    "Microsoft.Network/loadBalancers": ["AllocatedSnatPorts", "UsedSnatPorts"],
    "Microsoft.Compute/virtualMachines": [
        "CPU Credits Consumed",
        "CPU Credits Remaining",
    ],
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

    parser.add_argument(
        "--subscription",
        dest="subscriptions",
        action="append",
        default=[],
        help="Azure subscription IDs",
    )

    # REQUIRED
    parser.add_argument("--client", required=True, help="Azure client ID")
    parser.add_argument("--tenant", required=True, help="Azure tenant ID")
    parser.add_argument("--secret", required=True, help="Azure authentication secret")
    parser.add_argument(
        "--cache-id", required=True, help="Unique id for this special agent configuration"
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


class ApiErrorMissingData(ApiError):
    pass


class NoConsumptionAPIError(ApiError):
    pass


class ApiErrorAuthorizationRequestDenied(ApiError):
    pass


class ApiErrorFactory:
    _ERROR_CLASS_BY_CODE: dict[str, type[ApiError]] = {
        "Authorization_RequestDenied": ApiErrorAuthorizationRequestDenied
    }

    # Setting the type of `error_data` to Any because it is data fetched remotely and we want to
    # handle any type of data in this method
    @staticmethod
    def error_from_data(error_data: Any) -> ApiError:
        try:
            error_code = error_data["code"]
            error_cls = ApiErrorFactory._ERROR_CLASS_BY_CODE.get(error_code, ApiError)
            return error_cls(error_data.get("message", error_data))
        except Exception:
            return ApiError(error_data)


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
            raise ApiErrorFactory.error_from_data(error)

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
            raise ApiErrorFactory.error_from_data(json_data)


class GraphApiClient(BaseApiClient):
    def users(self, data=None, uri=None):
        if data is None:
            data = []

        # the uri is the link to the next page for pagination of results
        if uri:
            response = self._get(uri)
        else:
            response = self._get("users?$top=%s" % 500)
        data += response.get("value", [])

        # check if there is a next page, otherwise return result
        next_page = response.get("@odata.nextLink")
        if next_page is None:
            return data

        # if there is another page, remove the base url to get uri
        uri = next_page.replace(self._base_url, "")
        return self.users(data=data, uri=uri)

    def organization(self):
        return self._get("organization", key="value")

    def applications(self):
        applications = self._get("applications", key="value", next_page_key="@odata.nextLink")
        return self._filter_out_applications(applications)

    @staticmethod
    def _filter_out_applications(
        applications: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        key_subset = {"id", "appId", "displayName", "passwordCredentials"}
        return [
            {k: app[k] for k in key_subset} for app in applications if app["passwordCredentials"]
        ]


class MgmtApiClient(BaseApiClient):
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

    def resourcegroups(self):
        return self._get("resourcegroups", key="value", params={"api-version": "2019-05-01"})

    def resources(self):
        return self._get("resources", key="value", params={"api-version": "2019-05-01"})

    def vmview(self, group, name):
        temp = "resourceGroups/%s/providers/Microsoft.Compute/virtualMachines/%s/instanceView"
        return self._get(temp % (group, name), params={"api-version": "2018-06-01"})

    def app_gateway_view(self, group, name):
        url = "resourceGroups/{}/providers/Microsoft.Network/applicationGateways/{}"
        return self._get(url.format(group, name), params={"api-version": "2022-01-01"})

    def load_balancer_view(self, group, name):
        url = "resourceGroups/{}/providers/Microsoft.Network/loadBalancers/{}"
        return self._get(url.format(group, name), params={"api-version": "2022-01-01"})

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

    def public_ip_view(self, group, name):
        url = "resourceGroups/{}/providers/Microsoft.Network/publicIPAddresses/{}"
        return self._get(url.format(group, name), params={"api-version": "2022-01-01"})

    def vnet_gateway_view(self, group, name):
        url = "resourceGroups/{}/providers/Microsoft.Network/virtualNetworkGateways/{}"
        return self._get(url.format(group, name), params={"api-version": "2022-01-01"})

    def backup_containers_view(self, group, name):
        url = (
            "resourceGroups/{}/providers/Microsoft.RecoveryServices/vaults/{}/backupProtectedItems"
        )
        return self._get(url.format(group, name), params={"api-version": "2022-05-01"})

    def vnet_peering_view(self, group, providers, vnet_id, vnet_peering_id):
        url = "resourceGroups/{}/providers/{}/virtualNetworks/{}/virtualNetworkPeerings/{}"
        return self._get(
            url.format(group, providers, vnet_id, vnet_peering_id),
            params={"api-version": "2022-01-01"},
        )

    def vnet_gateway_health(self, group, providers, vnet_gw):
        url = (
            "resourceGroups/{}/providers/{}/virtualNetworkGateways/{}/providers/"
            "Microsoft.ResourceHealth/availabilityStatuses/current"
        )
        return self._get(
            url.format(group, providers, vnet_gw), params={"api-version": "2015-01-01"}
        )

    def resource_health_view(self, resource_group):
        path = "/resourceGroups/{}/providers/Microsoft.ResourceHealth/availabilityStatuses"
        return self._get(
            path.format(resource_group), key="value", params={"api-version": "2022-05-01"}
        )

    def usagedetails(self):
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
        return self._query(
            "/providers/Microsoft.CostManagement/query",
            body=body,
            # here 10000 might be too high,
            # but I haven't found any useful documentation.
            # No "$top" means 1000
            params={"api-version": "2021-10-01", "$top": "10000"},
        )

    def metrics(self, region, resource_ids, params):
        if self._regional_url is None:
            raise ValueError("Regional url not configured")

        params["api-version"] = "2023-10-01"
        try:
            return self._request(
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
                return self._request(
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
    def __init__(self, name) -> None:  # type: ignore[no-untyped-def]
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
    def __init__(self, raw_list=()) -> None:  # type: ignore[no-untyped-def]
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

    def __init__(  # type: ignore[no-untyped-def]
        self, name, piggytargets, separator, options
    ) -> None:
        super().__init__()
        self._sep = chr(separator)
        self._piggytargets = list(piggytargets)
        self._cont: list = []
        section_options = ":".join(["sep(%d)" % separator] + options)
        self._title = f"<<<{name.replace('-', '_')}:{section_options}>>>\n"

    def formatline(self, tokens):
        return self._sep.join(map(str, tokens)) + "\n"

    def add(self, info):
        if not info:
            return
        if isinstance(info[0], (list, tuple)):  # we got a list of lines
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
    def __init__(  # type: ignore[no-untyped-def]
        self,
        info,
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


def process_vm(mgmt_client: MgmtApiClient, vmach: AzureResource, args: Args) -> None:
    use_keys = ("statuses",)

    inst_view = mgmt_client.vmview(vmach.info["group"], vmach.info["name"])
    vmach.info["specific_info"] = filter_keys(inst_view, use_keys)

    if args.piggyback_vms == "self":
        vmach.piggytargets.remove(vmach.info["group"])
        vmach.piggytargets.append(vmach.info["name"])


def get_params_from_azure_id(
    resource_id: str, resource_types: Sequence[str] | None = None
) -> Sequence[str]:
    values = resource_id.lower().split("/")
    type_strings = list(map(str.lower, resource_types)) if resource_types else []
    index_keywords = ["subscriptions", "resourcegroups"] + type_strings
    return [values[values.index(keyword) + 1] for keyword in index_keywords]


def get_frontend_ip_configs(
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
            public_ip: Mapping = mgmt_client.public_ip_view(group, ip_name)
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


def process_app_gateway(mgmt_client: MgmtApiClient, resource: AzureResource) -> None:
    app_gateway = mgmt_client.app_gateway_view(resource.info["group"], resource.info["name"])
    frontend_ip_configs = get_frontend_ip_configs(mgmt_client, app_gateway)

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


def get_inbound_nat_rules(
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


def get_backend_address_pools(
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


def process_load_balancer(mgmt_client: MgmtApiClient, resource: AzureResource) -> None:
    load_balancer = mgmt_client.load_balancer_view(resource.info["group"], resource.info["name"])
    frontend_ip_configs = get_frontend_ip_configs(mgmt_client, load_balancer)
    inbound_nat_rules = get_inbound_nat_rules(mgmt_client, load_balancer)
    backend_pools = get_backend_address_pools(mgmt_client, load_balancer)

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


def get_remote_peerings(
    mgmt_client: MgmtApiClient, resource: dict
) -> Sequence[Mapping[str, object]]:
    peering_keys = ("name", "peeringState", "peeringSyncLevel")

    vnet_peerings = []
    for vnet_peering in resource["properties"].get("remoteVirtualNetworkPeerings", []):
        vnet_peering_id = vnet_peering["id"]
        (
            subscription,
            group,
            providers,
            vnet_id,
            vnet_peering_id,
        ) = get_params_from_azure_id(
            vnet_peering_id,
            resource_types=["providers", "virtualNetworks", "virtualNetworkPeerings"],
        )
        # skip vNet peerings that belong to another Azure subscription
        if subscription != mgmt_client.subscription:
            continue

        peering_view = mgmt_client.vnet_peering_view(group, providers, vnet_id, vnet_peering_id)
        vnet_peering = {
            **filter_keys(peering_view, peering_keys),
            **filter_keys(peering_view["properties"], peering_keys),
        }
        vnet_peerings.append(vnet_peering)

    return vnet_peerings


def get_vnet_gw_health(mgmt_client: MgmtApiClient, resource: Mapping) -> Mapping[str, object]:
    health_keys = ("availabilityState", "summary", "reasonType", "occuredTime")

    _, group, providers, vnet_gw = get_params_from_azure_id(
        resource["id"], resource_types=["providers", "virtualNetworkGateways"]
    )
    health_view = mgmt_client.vnet_gateway_health(group, providers, vnet_gw)
    return filter_keys(health_view["properties"], health_keys)


def process_virtual_net_gw(mgmt_client: MgmtApiClient, resource: AzureResource) -> None:
    gw_keys = (
        "bgpSettings",
        "disableIPSecReplayProtection",
        "gatewayType",
        "vpnType",
        "activeActive",
        "enableBgp",
    )

    gw_view = mgmt_client.vnet_gateway_view(resource.info["group"], resource.info["name"])
    resource.info["specific_info"] = filter_keys(gw_view["properties"], gw_keys)

    resource.info["properties"] = {}
    resource.info["properties"]["remote_vnet_peerings"] = get_remote_peerings(mgmt_client, gw_view)
    resource.info["properties"]["health"] = get_vnet_gw_health(mgmt_client, gw_view)


def process_recovery_services_vaults(mgmt_client: MgmtApiClient, resource: AzureResource) -> None:
    backup_keys = (
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
    backup_view = mgmt_client.backup_containers_view(resource.info["group"], resource.info["name"])

    backup_containers = [filter_keys(b["properties"], backup_keys) for b in backup_view["value"]]
    resource.info["properties"] = {}
    resource.info["properties"]["backup_containers"] = backup_containers


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
            self.get_cache_path(cache_id, resource_type, region), metric_names, debug=debug
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
        # For some 1-hour metrics, the ingestion time can be up to 6 hours (i.e. the SuccessServerLatency),
        # that's the reason why we use 'ref_time - 6' here.
        # More info on Azure Monitor Ingestion time:
        # https://docs.microsoft.com/en-us/azure/azure-monitor/logs/data-ingestion-time
        self.start_time = (ref_time - 6 * self.timedelta).strftime("%Y-%m-%dT%H:%M:%SZ")
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

    def get_live_data(self, *args: Any) -> Any:
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
            raw_metrics += mgmt_client.metrics(region, chunk, params)

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

                    msg = "metric not found: {} ({})".format(metric_name, aggregation)
                    err.add("info", resource_id, msg)
                    LOGGER.info(msg)

        return metrics


def write_section_ad(
    graph_client: GraphApiClient, section: AzureSection, args: argparse.Namespace
) -> None:
    enabled_services = set(args.services)
    # users
    if "users_count" in enabled_services:
        users = graph_client.users()
        section.add(["users_count", len(users)])

    # organization
    if "ad_connect" in enabled_services:
        orgas = graph_client.organization()
        section.add(["ad_connect", json.dumps(orgas)])

    section.write()


def write_section_app_registrations(graph_client: GraphApiClient, args: argparse.Namespace) -> None:
    if "app_registrations" not in args.services:
        return

    section = AzureSection("app_registration", separator=0)

    # app registration with client secrets
    apps = graph_client.applications()
    for app_reg in apps:
        section.add([json.dumps(app_reg)])

    section.write()


def gather_metrics(
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
        if (
            resource.info["type"] == "Microsoft.Compute/virtualMachines"
            and args.piggyback_vms == "grouphost"
        ):
            continue

        grouped_resource_ids[(resource.info["type"], resource.info["location"])].append(
            resource.info["id"]
        )

    for group, resource_ids in grouped_resource_ids.items():
        resource_type, resource_region = group

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
            try:
                metrics = cache.get_data(
                    mgmt_client,
                    resource_region,
                    resource_ids,
                    resource_type,
                    err,
                    use_cache=cache.cache_interval > 60,
                )

                for resource_id, resource_metrics in metrics.items():
                    if (metric_resource := resource_dict.get(resource_id)) is not None:
                        metric_resource.metrics += resource_metrics
                    else:
                        LOGGER.info(
                            "Resource %s found in metrics cache no longer monitored",
                            resource_id,
                        )

            except ApiError as exc:
                if args.debug:
                    raise
                err.add("exception", "metric collection", str(exc))
                LOGGER.exception(exc)

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


def process_resource(
    mgmt_client: MgmtApiClient,
    resource: AzureResource,
    group_labels: GroupLabels,
    args: Args,
) -> Sequence[Section]:
    sections: list[Section] = []
    enabled_services = set(args.services)
    resource_type = resource.info.get("type")
    if resource_type not in enabled_services:
        return sections

    if resource_type == "Microsoft.Compute/virtualMachines":
        process_vm(mgmt_client, resource, args)

        if args.piggyback_vms == "self":
            sections.append(get_vm_labels_section(resource, group_labels))

    elif resource_type == "Microsoft.Network/applicationGateways":
        process_app_gateway(mgmt_client, resource)
    elif resource_type == "Microsoft.RecoveryServices/vaults":
        process_recovery_services_vaults(mgmt_client, resource)
    elif resource_type == "Microsoft.Network/virtualNetworkGateways":
        process_virtual_net_gw(mgmt_client, resource)
    elif resource_type == "Microsoft.Network/loadBalancers":
        process_load_balancer(mgmt_client, resource)
    elif resource_type == "Microsoft.DBforMySQL/flexibleServers":
        resource.section = "servers"  # use the same section as for single servers

    section = AzureSection(resource.section, resource.piggytargets)
    section.add(resource.dumpinfo())
    sections.append(section)

    return sections


def process_resources(
    mgmt_client: MgmtApiClient,
    resources: Sequence[AzureResource],
    group_labels: GroupLabels,
    args: Args,
) -> Iterator[Sequence[Section]]:
    for resource in resources:
        try:
            yield process_resource(mgmt_client, resource, group_labels, args)
        except Exception as exc:
            if args.debug:
                raise
            write_exception_to_agent_info_section(exc, "Management client")


def get_group_labels(
    mgmt_client: MgmtApiClient,
    monitored_groups: Sequence[str],
    tag_key_pattern: TagsOption,
) -> GroupLabels:
    group_labels: dict[str, dict[str, str]] = {}

    for group in mgmt_client.resourcegroups():
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


def main_graph_client(args: Args) -> None:
    graph_client = GraphApiClient(
        _get_graph_authority_urls(args.authority),
        deserialize_http_proxy_config(args.proxy),
    )
    try:
        graph_client.login(args.tenant, args.client, args.secret)
        write_section_ad(graph_client, AzureSection("ad"), args)
        write_section_app_registrations(graph_client, args)
    except ApiErrorAuthorizationRequestDenied as exc:
        # We are not raising the exception in debug mode.
        # Having no permissions for the graph API is a legit configuration
        write_exception_to_agent_info_section(exc, "Graph client")
    except Exception as exc:
        if args.debug:
            raise
        write_exception_to_agent_info_section(exc, "Graph client")


def get_usage_data(client: MgmtApiClient, args: Args) -> Sequence[object]:
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
        usage_data = client.usagedetails()
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
    usage_data: Sequence[object],
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


def usage_details(mgmt_client: MgmtApiClient, monitored_groups: list[str], args: Args) -> None:
    if "usage_details" not in args.services:
        return

    try:
        usage_section = get_usage_data(mgmt_client, args)
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


def _get_monitored_resource(
    resource_id: str,
    monitored_resources: Sequence[AzureResource],
    args: Args,
) -> AzureResource | None:
    for resource in monitored_resources:
        # different endpoints deliver ids in different case
        if resource_id.lower() == resource.info["id"].lower():
            return resource if resource.info["type"] in args.services else None

    return None


def process_resource_health(
    mgmt_client: MgmtApiClient,
    monitored_resources: Sequence[AzureResource],
    args: Args,
    pool_executor: Executor,
) -> Iterator[AzureSection]:
    def _fetch_and_build_section_for_resource(resource_group: str) -> dict[str, list[str]]:
        """Fetch health data for a *single* resource group"""
        try:
            resource_health_view = mgmt_client.resource_health_view(resource_group)
            health_entries = defaultdict(list)
            for health in resource_health_view:
                health_id = health.get("id")
                _, group = get_params_from_azure_id(health_id)
                resource_id = "/".join(health_id.split("/")[:-4])

                # we get the health for *all* resources in the group, filter here
                if (
                    resource := _get_monitored_resource(resource_id, monitored_resources, args)
                ) is None:
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

                health_entries[group].append(json.dumps(health_data))

            return health_entries
        except ApiError:
            LOGGER.warning("Could not fetch resource health for resource group %s", resource_group)
            return {}

    resource_groups_with_monitored_resources = {r.info["group"] for r in monitored_resources}
    health_section: defaultdict[str, list[str]] = defaultdict(list)
    try:
        # query each resource group in a separate thread
        results = pool_executor.map(
            _fetch_and_build_section_for_resource, resource_groups_with_monitored_resources
        )
        for group_result in results:
            for group, values in group_result.items():
                health_section[group].extend(values)
    except Exception as exc:
        if args.debug:
            raise
        write_exception_to_agent_info_section(exc, "Management client")
        return

    for group, values in health_section.items():
        section = AzureSection(
            "resource_health",
            piggytargets=[group.lower()],
            separator=0,
        )
        for value in values:
            section.add([value])
        yield section


def main_subscription(args: Args, selector: Selector, subscription: str) -> None:
    mgmt_client = MgmtApiClient(
        _get_mgmt_authority_urls(args.authority, subscription),
        deserialize_http_proxy_config(args.proxy),
        subscription,
    )

    try:
        mgmt_client.login(args.tenant, args.client, args.secret)

        all_resources = (AzureResource(r, args.tag_key_pattern) for r in mgmt_client.resources())

        monitored_resources = [r for r in all_resources if selector.do_monitor(r)]

        monitored_groups = sorted({r.info["group"] for r in monitored_resources})
    except Exception as exc:
        if args.debug:
            raise
        write_exception_to_agent_info_section(exc, "Management client")
        return

    group_labels = get_group_labels(mgmt_client, monitored_groups, args.tag_key_pattern)
    write_group_info(monitored_groups, monitored_resources, group_labels)

    usage_details(mgmt_client, monitored_groups, args)

    if err := gather_metrics(mgmt_client, monitored_resources, args):
        agent_info_section = AzureSection("agent_info")
        agent_info_section.add(err.dumpinfo())
        agent_info_section.write()

    all_sections = process_resources(mgmt_client, monitored_resources, group_labels, args)
    for resource_sections in all_sections:
        for section in resource_sections:
            section.write()

    with ThreadPoolExecutor() as pool_executor:
        for section in process_resource_health(
            mgmt_client, monitored_resources, args, pool_executor
        ):
            section.write()

    write_remaining_reads(mgmt_client.ratelimit)


def main(argv=None):
    if argv is None:
        password_store.replace_passwords()
        argv = sys.argv[1:]

    args = parse_arguments(argv)
    selector = Selector(args)
    if args.dump_config:
        sys.stdout.write("Configuration:\n%s\n" % selector)
        return

    LOGGER.debug("%s", selector)
    main_graph_client(args)
    for subscription in args.subscriptions:
        main_subscription(args, selector, subscription)


if __name__ == "__main__":
    sys.exit(main())
