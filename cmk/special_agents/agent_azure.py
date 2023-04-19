#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent azure: Monitoring Azure cloud applications with Checkmk
"""

from __future__ import annotations

import abc
import argparse
import datetime
import json
import logging
import re
import string
import sys
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping, Sequence
from multiprocessing import Lock, Process, Queue
from queue import Empty as QueueEmpty
from typing import Any

import adal  # type: ignore[import] # pylint: disable=import-error
import requests

from cmk.utils import password_store
from cmk.utils.paths import tmp_dir

from cmk.special_agents.utils import DataCache, vcrtrace

Args = argparse.Namespace
GroupLabels = Mapping[str, Mapping[str, str]]

LOGGER = logging.getLogger()  # root logger for now

AZURE_CACHE_FILE_PATH = tmp_dir / "agents" / "agent_azure"

NOW = datetime.datetime.utcnow()

ALL_METRICS: dict[str, list[tuple]] = {
    # to add a new metric, just add a made up name, run the
    # agent, and you'll get a error listing available metrics!
    # key: list of (name(s), interval, aggregation, filter)
    # NB: Azure API won't have requests with more than 20 metric names at once
    # Also remember to add the service to the WATO rule:
    # cmk/gui/plugins/wato/special_agents/azure.py
    "Microsoft.Network/virtualNetworkGateways": [
        ("AverageBandwidth,P2SBandwidth", "PT5M", "average", None),
        ("TunnelIngressBytes", "PT5M", "count", None),
        ("TunnelEgressBytes", "PT5M", "count", None),
        ("TunnelIngressPacketDropCount", "PT5M", "count", None),
        ("TunnelEgressPacketDropCount", "PT5M", "count", None),
        ("P2SConnectionCount", "PT1M", "maximum", None),
    ],
    "Microsoft.Sql/servers/databases": [
        (
            "storage_percent,deadlock,cpu_percent,dtu_consumption_percent,"
            "connection_successful,connection_failed",
            "PT1M",
            "average",
            None,
        ),
    ],
    "Microsoft.Storage/storageAccounts": [
        (
            "UsedCapacity,Ingress,Egress,Transactions",
            "PT1H",
            "total",
            None,
        ),
        (
            "SuccessServerLatency,SuccessE2ELatency,Availability",
            "PT1H",
            "average",
            None,
        ),
    ],
    "Microsoft.Web/sites": [
        ("CpuTime,AverageResponseTime,Http5xx", "PT1M", "total", None),
    ],
    "Microsoft.DBforMySQL/servers": [
        (
            "cpu_percent,memory_percent,io_consumption_percent,serverlog_storage_percent,"
            "storage_percent,active_connections",
            "PT1M",
            "average",
            None,
        ),
        (
            "connections_failed,network_bytes_ingress,network_bytes_egress",
            "PT1M",
            "total",
            None,
        ),
        (
            "seconds_behind_master",
            "PT1M",
            "maximum",
            None,
        ),
    ],
    "Microsoft.DBforPostgreSQL/servers": [
        (
            "cpu_percent,memory_percent,io_consumption_percent,serverlog_storage_percent,"
            "storage_percent,active_connections",
            "PT1M",
            "average",
            None,
        ),
        (
            "connections_failed,network_bytes_ingress,network_bytes_egress",
            "PT1M",
            "total",
            None,
        ),
        (
            "pg_replica_log_delay_in_seconds",
            "PT1M",
            "maximum",
            None,
        ),
    ],
    "Microsoft.Network/trafficmanagerprofiles": [
        (
            "QpsByEndpoint",
            "PT1M",
            "total",
            None,
        ),
        (
            "ProbeAgentCurrentEndpointStateByProfileResourceId",
            "PT1M",
            "maximum",
            None,
        ),
    ],
    "Microsoft.Network/loadBalancers": [
        (
            "ByteCount",
            "PT1M",
            "total",
            None,
        ),
        (
            "AllocatedSnatPorts,UsedSnatPorts,VipAvailability,DipAvailability",
            "PT1M",
            "average",
            None,
        ),
    ],
    "Microsoft.Network/applicationGateways": [
        ("HealthyHostCount", "PT1M", "average", None),
        ("FailedRequests", "PT1M", "count", None),
    ],
    "Microsoft.Compute/virtualMachines": [
        (
            "Percentage CPU,CPU Credits Consumed,CPU Credits Remaining,Available Memory Bytes,Disk Read Operations/Sec,Disk Write Operations/Sec",
            "PT1M",
            "average",
            None,
        ),
        (
            "Network In Total,Network Out Total,Disk Read Bytes,Disk Write Bytes",
            "PT1M",
            "total",
            None,
        ),
    ],
}


def parse_arguments(argv):
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
        help="""(implies --sequential)""",
    )
    parser.add_argument(
        "--sequential", action="store_true", help="""Sequential mode: do not use multiprocessing"""
    )
    parser.add_argument(
        "--dump-config", action="store_true", help="""Dump parsed configuration and exit"""
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
    args = parser.parse_args(argv)

    if args.vcrtrace:
        args.sequential = True

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


class BaseApiClient(abc.ABC):
    AUTHORITY = "https://login.microsoftonline.com"

    def __init__(self, base_url) -> None:  # type: ignore[no-untyped-def]
        self._ratelimit = float("Inf")
        self._headers: dict = {}
        self._base_url = base_url

    @property
    @abc.abstractmethod
    def resource(self):
        pass

    def login(self, tenant, client, secret):
        context = adal.AuthenticationContext(f"{self.AUTHORITY}/{tenant}")
        token = context.acquire_token_with_client_credentials(self.resource, client, secret)
        self._headers.update(
            {
                "Authorization": "Bearer %s" % token["accessToken"],
                "Content-Type": "application/json",
            }
        )

    @property
    def ratelimit(self):
        if isinstance(self._ratelimit, int):
            return self._ratelimit
        return None

    def _update_ratelimit(self, response):
        try:
            new_value = int(response.headers["x-ms-ratelimit-remaining-subscription-reads"])
        except (KeyError, ValueError, TypeError):
            return
        self._ratelimit = min(self._ratelimit, new_value)

    def _get(self, uri_end, key=None, params=None):
        return self._request(method="GET", uri_end=uri_end, key=key, params=params)

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

    def _request(self, method, uri_end, body=None, key=None, params=None):
        json_data = self._request_json_from_url(
            method, self._base_url + uri_end, body=body, params=params
        )

        if key is None:
            return json_data

        data = self._lookup(json_data, key)

        # The API will not send more than 1000 recources at once.
        # See if we must fetch another page:
        next_link = json_data.get("nextLink")
        while next_link is not None:
            json_data = self._request_json_from_url(method, next_link, body=body)
            # we only know of lists. Let exception happen otherwise
            data += self._lookup(json_data, key)
            next_link = json_data.get("nextLink")

        return data

    def _request_json_from_url(self, method, url, *, body=None, params=None):
        response = requests.request(method, url, json=body, params=params, headers=self._headers)
        self._update_ratelimit(response)
        json_data = response.json()
        LOGGER.debug("response: %r", json_data)
        return json_data

    @staticmethod
    def _lookup(json_data, key):
        try:
            return json_data[key]
        except KeyError:
            error = json_data.get("error", json_data)
            raise ApiErrorFactory.error_from_data(error)


class GraphApiClient(BaseApiClient):
    def __init__(self) -> None:
        base_url = "%s/v1.0/" % self.resource
        super().__init__(base_url)

    @property
    def resource(self):
        return "https://graph.microsoft.com"

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
        apps = self._get("applications", key="value")

        key_subset = {"id", "appId", "displayName", "passwordCredentials"}
        apps_selected = [
            {k: app[k] for k in key_subset} for app in apps if app["passwordCredentials"]
        ]

        return apps_selected


class MgmtApiClient(BaseApiClient):
    def __init__(self, subscription) -> None:  # type: ignore[no-untyped-def]
        base_url = f"{self.resource}/subscriptions/{subscription}/"
        super().__init__(base_url)

    @staticmethod
    def _get_available_metrics_from_exception(
        desired_names: str, api_error: ApiError, resource_id: str
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
            LOGGER.debug("None of the expected metrics are available for resource %s", resource_id)
            return None

        return ",".join(sorted(retry_names))

    @property
    def resource(self):
        return "https://management.azure.com"

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
            url.format(group, nic_name, ip_conf_name), params={"api-version": "2022-01-01"}
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

    def resource_health_view(self):
        path = "providers/Microsoft.ResourceHealth/availabilityStatuses"
        return self._get(path, params={"api-version": "2022-05-01"})

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
            params={"api-version": "2021-10-01", "$top": "100"},
        )

    def metrics(self, resource_id, **params):
        url = resource_id.split("/", 3)[-1] + "/providers/microsoft.insights/metrics"
        params["api-version"] = "2018-01-01"
        try:
            return self._get(url, key="value", params=params)
        except ApiError as exc:
            retry_names = self._get_available_metrics_from_exception(
                params["metricnames"], exc, resource_id
            )
            if retry_names:
                params["metricnames"] = retry_names
                return self._get(url, key="value", params=params)
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

    def add_key(self, key, value):
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
    def fetchall(self):
        return not self.groups

    def add_key(self, key, value):
        if key == "group":
            self.current_group = self.groups.setdefault(value, GroupConfig(value))
            return
        if self.current_group is None:
            raise RuntimeError("missing arg: group=<name>")
        self.current_group.add_key(key, value)

    def is_configured(self, resource) -> bool:  # type: ignore[no-untyped-def]
        if self.fetchall:
            return True
        group_config = self.groups.get(resource.info["group"])
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
    def __init__(self, required, key_values) -> None:  # type: ignore[no-untyped-def]
        super().__init__()
        self._required = required
        self._values = key_values

    def is_configured(self, resource) -> bool:  # type: ignore[no-untyped-def]
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
    def __init__(self, args) -> None:  # type: ignore[no-untyped-def]
        super().__init__()
        self._explicit_config = ExplicitConfig(raw_list=args.explicit_config)
        self._tag_based_config = TagBasedConfig(args.require_tag, args.require_tag_value)

    def do_monitor(self, resource):
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

    def write(self, write_empty=False):
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
    def __init__(self, name, piggytargets=("",)) -> None:  # type: ignore[no-untyped-def]
        super().__init__("azure_%s" % name, piggytargets, separator=124, options=[])


class LabelsSection(Section):
    def __init__(self, piggytarget) -> None:  # type: ignore[no-untyped-def]
        super().__init__("labels", [piggytarget], separator=0, options=[])


class IssueCollecter:
    def __init__(self) -> None:
        super().__init__()
        self._list: list[tuple[str, str]] = []

    def add(self, issue_type, issued_by, issue_msg) -> None:  # type: ignore[no-untyped-def]
        issue = {"type": issue_type, "issued_by": issued_by, "msg": issue_msg}
        self._list.append(("issue", json.dumps(issue)))

    def dumpinfo(self) -> list[tuple[str, str]]:
        return self._list

    def __len__(self) -> int:
        return len(self._list)


def create_metric_dict(metric, aggregation, interval_id, filter_):
    name = metric["name"]["value"]
    metric_dict = {
        "name": name,
        "aggregation": aggregation,
        "value": None,
        "unit": metric["unit"].lower(),
        "timestamp": None,
        "filter": filter_,
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


def get_attrs_from_uri(uri):
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
    def __init__(self, info) -> None:  # type: ignore[no-untyped-def]
        super().__init__()
        self.info = info
        self.info.update(get_attrs_from_uri(info["id"]))
        self.tags = self.info.get("tags", {})

        self.section = info["type"].split("/")[-1].lower()
        self.piggytargets = []
        group = self.info.get("group")
        if group:
            self.piggytargets.append(group)
        self.metrics: list = []

    def dumpinfo(self):
        # TODO: Hmmm, should the variable-length tuples actually be lists?
        lines: list[tuple] = [("Resource",), (json.dumps(self.info),)]
        if self.metrics:
            lines += [("metrics following", len(self.metrics))]
            lines += [(json.dumps(m),) for m in self.metrics]
        return lines


def filter_keys(mapping: Mapping, keys: Iterable[str]) -> Mapping:
    items = ((k, mapping.get(k)) for k in keys)
    return {k: v for k, v in items if v is not None}


def process_vm(mgmt_client, vmach, args):
    use_keys = ("statuses",)

    inst_view = mgmt_client.vmview(vmach.info["group"], vmach.info["name"])
    vmach.info["specific_info"] = filter_keys(inst_view, use_keys)

    if args.piggyback_vms not in ("grouphost",):
        vmach.piggytargets.remove(vmach.info["group"])
    if args.piggyback_vms in ("self",):
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
                ip_config["properties"], ("privateIPAllocationMethod", "privateIPAddress")
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
    listener_keys = ("port", "protocol", "hostNames", "frontendIPConfiguration", "frontendPort")
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
        c["id"]: {"name": c["name"], **filter_keys(c["properties"], ("port", "protocol"))}
        for c in app_gateway["properties"]["backendHttpSettingsCollection"]
    }
    resource.info["properties"]["backend_settings"] = backend_settings

    backend_pools = {p["id"]: p for p in app_gateway["properties"]["backendAddressPools"]}
    resource.info["properties"]["backend_address_pools"] = backend_pools


def get_network_interface_config(mgmt_client: MgmtApiClient, nic_id: str) -> Mapping[str, Mapping]:
    _, group, nic_name, ip_conf_name = get_params_from_azure_id(
        nic_id, resource_types=["networkInterfaces", "ipConfigurations"]
    )
    return mgmt_client.nic_ip_conf_view(group, nic_name, ip_conf_name)


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
        for backend_address in backend_pool["properties"]["loadBalancerBackendAddresses"]:
            if "networkInterfaceIPConfiguration" in backend_address.get("properties"):
                ip_config_id = backend_address["properties"]["networkInterfaceIPConfiguration"][
                    "id"
                ]
                nic_config = get_network_interface_config(mgmt_client, ip_config_id)

                backend_address_data = {
                    "name": nic_config["name"],
                    **filter_keys(nic_config["properties"], backend_address_keys),
                }
                backend_addresses.append(backend_address_data)

        backend_pools.append(
            {"id": backend_pool["id"], "name": backend_pool["name"], "addresses": backend_addresses}
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
        for r in load_balancer["properties"]["outboundRules"]
    ]
    resource.info["properties"]["outbound_rules"] = outbound_rules


def get_remote_peerings(
    mgmt_client: MgmtApiClient, resource: dict
) -> Sequence[Mapping[str, object]]:
    peering_keys = ("name", "peeringState", "peeringSyncLevel")

    vnet_peerings = []
    for vnet_peering in resource["properties"].get("remoteVirtualNetworkPeerings", []):
        vnet_peering_id = vnet_peering["id"]
        _, group, providers, vnet_id, vnet_peering_id = get_params_from_azure_id(
            vnet_peering_id,
            resource_types=["providers", "virtualNetworks", "virtualNetworkPeerings"],
        )

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
    def __init__(  # type: ignore[no-untyped-def]
        self, resource, metric_definition, ref_time, debug=False
    ) -> None:
        self.metric_definition = metric_definition
        metricnames = metric_definition[0]
        super().__init__(self.get_cache_path(resource), metricnames, debug=debug)
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
        start = ref_time - 5 * self.timedelta
        self._timespan = "{}/{}".format(
            start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ref_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    @staticmethod
    def get_cache_path(resource):
        valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
        subdir = "".join(c if c in valid_chars else "_" for c in resource.info["id"])
        return AZURE_CACHE_FILE_PATH / subdir

    @property
    def cache_interval(self) -> int:
        return self.timedelta.seconds

    def get_validity_from_args(self, *args: Any) -> bool:
        return True

    def get_live_data(self, *args: Any) -> Any:
        mgmt_client, resource_id, err = args
        metricnames, interval, aggregation, filter_ = self.metric_definition

        raw_metrics = mgmt_client.metrics(
            resource_id,
            timespan=self._timespan,
            interval=interval,
            metricnames=metricnames,
            aggregation=aggregation,
            filter=filter_,
        )

        metrics = []
        for raw_metric in raw_metrics:
            parsed_metric = create_metric_dict(raw_metric, aggregation, interval, filter_)
            if parsed_metric is not None:
                metrics.append(parsed_metric)
            else:
                msg = "metric not found: {} ({})".format(raw_metric["name"]["value"], aggregation)
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

    section = AzureSection("app_registration")

    # app registration with client secrets
    apps = graph_client.applications()
    for app_reg in apps:
        section.add([json.dumps(app_reg)])

    section.write()


def gather_metrics(mgmt_client, resource, debug=False):
    """
    Gather all metrics for a resource. These metrics have different time
    resolutions, so every metric needs its own cache.
    Along the way collect ocurrring errors.
    """
    err = IssueCollecter()
    metric_definitions = ALL_METRICS.get(resource.info["type"], [])
    for metric_def in metric_definitions:
        cache = MetricCache(resource, metric_def, NOW, debug=debug)
        try:
            resource.metrics += cache.get_data(
                mgmt_client, resource.info["id"], err, use_cache=cache.cache_interval > 60
            )
        except ApiError as exc:
            if debug:
                raise
            err.add("exception", resource.info["id"], str(exc))
            LOGGER.exception(exc)
    return err


def get_vm_labels_section(vm: AzureResource, group_labels: GroupLabels) -> LabelsSection:
    group_name = vm.info["group"]
    vm_labels = dict(vm.tags)

    for tag_name, tag_value in group_labels[group_name].items():
        if tag_name not in vm.tags:
            vm_labels[tag_name] = tag_value

    vm_labels["cmk/azure/vm"] = "instance"

    labels_section = LabelsSection(vm.info["name"])
    labels_section.add((json.dumps(vm_labels),))
    return labels_section


def process_resource(
    function_args: tuple[MgmtApiClient, AzureResource, GroupLabels, Args]
) -> Sequence[Section]:
    mgmt_client, resource, group_labels, args = function_args
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

    # metrics aren't collected for VMs if they are mapped to a resource host
    err = (
        gather_metrics(mgmt_client, resource, debug=args.debug)
        if resource_type != "Microsoft.Compute/virtualMachines" or args.piggyback_vms != "grouphost"
        else None
    )

    if err:
        agent_info_section = AzureSection("agent_info")
        agent_info_section.add(err.dumpinfo())
        sections.append(agent_info_section)

    section = AzureSection(resource.section, resource.piggytargets)
    section.add(resource.dumpinfo())
    sections.append(section)

    return sections


def get_group_labels(mgmt_client: MgmtApiClient, monitored_groups: Sequence[str]) -> GroupLabels:
    group_labels: dict[str, dict[str, str]] = {}

    for group in mgmt_client.resourcegroups():
        name = group["name"]
        tags = group.get("tags", {})
        if name in monitored_groups:
            # label is being renamed to "cmk/azure/resource_group", remove for version 2.3.0
            deprecated_label = {"resource_group": name}
            group_labels[name] = {**tags, **deprecated_label, **{"cmk/azure/resource_group": name}}

    return group_labels


def write_group_info(
    monitored_groups: Sequence[str],
    monitored_resources: Sequence[AzureResource],
    group_labels: GroupLabels,
) -> None:
    for group_name, tags in group_labels.items():
        labels_section = LabelsSection(group_name)
        labels_section.add((json.dumps(tags),))
        labels_section.write()

    section = AzureSection("agent_info")
    section.add(("monitored-groups", json.dumps(monitored_groups)))
    section.add(("monitored-resources", json.dumps([r.info["name"] for r in monitored_resources])))
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


def get_mapper(debug, sequential, timeout):
    """Return a function similar to the builtin 'map'

    However, these functions won't stop upon an exception
    (unless debug is set).
    Also, there's an async variant available.
    """
    if sequential:

        def sequential_mapper(func, args_iter):
            for args in args_iter:
                try:
                    yield func(args)
                except Exception:
                    if debug:
                        raise

        return sequential_mapper

    def async_mapper(func, args_iter):
        """Async drop-in replacement for builtin 'map'

        which does not require the involved values to be pickle-able,
        nor third party modules such as 'multiprocess' or 'dill'.

        Usage:
                 for results in async_mapper(function, arguments_iter):
                     do_stuff()

        Note that the order of the results does not correspond
        to that of the arguments.
        """
        queue: Queue[tuple[Any, bool, Any]] = Queue()
        jobs = {}

        def produce(id_, args):
            try:
                queue.put((id_, True, func(args)))
            except Exception:  # pylint: disable=broad-except
                queue.put((id_, False, None))
                if debug:
                    raise

        # start
        for id_, args in enumerate(args_iter):
            jobs[id_] = Process(target=produce, args=(id_, args))
            jobs[id_].start()

        # consume
        while jobs:
            try:
                id_, success, result = queue.get(block=True, timeout=timeout)
            except QueueEmpty:
                break
            if success:
                yield result
            jobs.pop(id_)

        for job in jobs.values():
            job.terminate()

    return async_mapper


def main_graph_client(args):
    graph_client = GraphApiClient()
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
) -> None:
    if not usage_data:
        AzureSection("usagedetails", monitored_groups + [""]).write(write_empty=True)

    for usage in usage_data:
        usage_resource = AzureResource(usage)
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

        write_usage_section(usage_section, monitored_groups)

    except NoConsumptionAPIError:
        LOGGER.debug("Azure offer doesn't support querying the cost API")
        return

    except Exception as exc:
        if args.debug:
            raise
        LOGGER.warning("%s", exc)
        write_exception_to_agent_info_section(exc, "Usage client")
        write_usage_section([], monitored_groups)


def _is_monitored(
    resource_id: str,
    monitored_resources: Sequence[AzureResource],
    args: Args,
) -> bool:
    for resource in monitored_resources:
        # different endpoints deliver ids in different case
        if resource_id.lower() == resource.info["id"].lower():
            return resource.info["type"] in args.services

    return False


def process_resource_health(
    mgmt_client: MgmtApiClient, monitored_resources: Sequence[AzureResource], args: Args
) -> Iterator[AzureSection]:
    try:
        resource_health_view = mgmt_client.resource_health_view()
    except Exception as exc:
        if args.debug:
            raise
        write_exception_to_agent_info_section(exc, "Management client")
        return

    health_section: defaultdict[str, list[str]] = defaultdict(list)

    for health in resource_health_view.get("value", []):
        health_id = health.get("id")
        _, group = get_params_from_azure_id(health_id)
        resource_id = "/".join(health_id.split("/")[:-4])

        if not _is_monitored(resource_id, monitored_resources, args):
            continue

        health_data = {
            "id": health_id,
            "name": "/".join(health_id.split("/")[-6:-4]),
            **filter_keys(
                health["properties"], ("availabilityState", "summary", "reasonType", "occuredTime")
            ),
        }

        health_section[group].append(json.dumps(health_data))

    for group, values in health_section.items():
        section = AzureSection("resource_health", [group])
        for value in values:
            section.add([value])
        yield section


def main_subscription(args, selector, subscription):
    mgmt_client = MgmtApiClient(subscription)

    try:
        mgmt_client.login(args.tenant, args.client, args.secret)

        all_resources = (AzureResource(r) for r in mgmt_client.resources())

        monitored_resources = [r for r in all_resources if selector.do_monitor(r)]

        monitored_groups = sorted({r.info["group"] for r in monitored_resources})
    except Exception as exc:
        if args.debug:
            raise
        write_exception_to_agent_info_section(exc, "Management client")
        return

    group_labels = get_group_labels(mgmt_client, monitored_groups)
    write_group_info(monitored_groups, monitored_resources, group_labels)

    usage_details(mgmt_client, monitored_groups, args)

    func_args = ((mgmt_client, resource, group_labels, args) for resource in monitored_resources)
    mapper = get_mapper(args.debug, args.sequential, args.timeout)
    for sections in mapper(process_resource, func_args):
        for section in sections:
            section.write()

    for section in process_resource_health(mgmt_client, monitored_resources, args):
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
