#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent azure: Monitoring Azure cloud applications with Checkmk
"""
import abc
import argparse
import datetime
import json
import logging
import string
import sys
import time
from multiprocessing import Lock, Process, Queue
from pathlib import Path
from queue import Empty as QueueEmpty
from typing import Any, List, Mapping, Sequence, Tuple

import adal  # type: ignore[import] # pylint: disable=import-error
import requests

from cmk.utils import password_store
from cmk.utils.paths import tmp_dir

from cmk.special_agents.utils import DataCache, get_seconds_since_midnight, vcrtrace

Args = argparse.Namespace
GroupLabels = Mapping[str, Mapping[str, str]]


LOGGER = logging.getLogger()  # root logger for now

METRICS_SELECTED = {
    # to add a new metric, just add a made up name, run the
    # agent, and you'll get a error listing available metrics!
    # key: list of (name(s), interval, aggregation, filter)
    # NB: Azure API won't have requests with more than 20 metric names at once
    "Microsoft.Network/virtualNetworkGateways": [
        ("AverageBandwidth,P2SBandwidth", "PT5M", "average", None),
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
            "UsedCapacity,Ingress,Egress,Transactions,"
            "SuccessServerLatency,SuccessE2ELatency,Availability",
            "PT1H",
            "total",
            None,
        ),
    ],
    "Microsoft.Web/sites": [
        ("CpuTime,AverageResponseTime,Http5xx", "PT1M", "total", None),
    ],
}

AZURE_CACHE_FILE_PATH = Path(tmp_dir) / "agents" / "agent_azure"

NOW = datetime.datetime.utcnow()


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
             If omitted, all groups and resources are fetched.
             If specified, every 'group=<name>' argument starts a new group configuration,
             and every 'resource=<name>' arguments specifies a resource.""",
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


class BaseApiClient(abc.ABC):
    AUTHORITY = "https://login.microsoftonline.com"

    def __init__(self, base_url):
        self._ratelimit = float("Inf")
        self._headers = {}
        self._base_url = base_url

    @property
    @abc.abstractmethod
    def resource(self):
        pass

    def login(self, tenant, client, secret):
        context = adal.AuthenticationContext("%s/%s" % (self.AUTHORITY, tenant))
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
        json_data = self._get_json_from_url(self._base_url + uri_end, params=params)

        if key is None:
            return json_data

        data = self._lookup(json_data, key)

        # The API will not send more than 1000 recources at once.
        # See if we must fetch another page:
        next_link = json_data.get("nextLink")
        while next_link is not None:
            json_data = self._get_json_from_url(next_link)
            # we only know of lists. Let exception happen otherwise
            data += self._lookup(json_data, key)
            next_link = json_data.get("nextLink")

        return data

    def _get_json_from_url(self, url, *, params=None):
        response = requests.get(url, params=params, headers=self._headers)
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
            raise ApiError(error.get("message", json_data))


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


class MgmtApiClient(BaseApiClient):
    def __init__(self, subscription):
        base_url = "%s/subscriptions/%s/" % (self.resource, subscription)
        super().__init__(base_url)

    @staticmethod
    def _get_available_metrics_from_exception(desired_names, api_error):
        if not (
            api_error.message.startswith("Failed to find metric configuration for provider")
            and "Valid metrics: " in api_error.message
        ):
            return None

        available_names = api_error.message.split("Valid metrics: ")[1]
        retry_names = set(desired_names.split(",")) & set(available_names.split(","))
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

    def usagedetails(self):
        return self._get(
            "providers/Microsoft.Consumption/usageDetails",
            key="value",
            params={"api-version": "2019-01-01"},
        )

    def metrics(self, resource_id, **params):
        url = resource_id.split("/", 3)[-1] + "/providers/microsoft.insights/metrics"
        params["api-version"] = "2018-01-01"
        try:
            return self._get(url, key="value", params=params)
        except ApiError as exc:
            retry_names = self._get_available_metrics_from_exception(params["metricnames"], exc)
            if retry_names:
                params["metricnames"] = retry_names
                return self._get(url, key="value", params=params)
            raise


# The following *Config objects provide a Configuration instance as described in
# CMK-513 (comment-12620).
# For now the passed commandline arguments are used to create it.


class GroupConfig:
    def __init__(self, name):
        super().__init__()
        if not name:
            raise ValueError("falsey group name: %r" % name)
        self.name = name
        self.resources = []

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
    def __init__(self, raw_list=()):
        super().__init__()
        self.groups = {}
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

    def is_configured(self, resource) -> bool:
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
    def __init__(self, required, key_values):
        super().__init__()
        self._required = required
        self._values = key_values

    def is_configured(self, resource) -> bool:
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
            lines.append("required value for %r: %r" % (key, val))
        return "\n".join(lines)


class Selector:
    def __init__(self, args):
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

    def __init__(self, name, piggytargets, separator, options):
        super().__init__()
        self._sep = chr(separator)
        self._piggytargets = list(piggytargets)
        self._cont = []
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
    def __init__(self, name, piggytargets=("",)):
        super().__init__("azure_%s" % name, piggytargets, separator=124, options=[])


class LabelsSection(Section):
    def __init__(self, piggytarget):
        super().__init__("labels", [piggytarget], separator=0, options=[])


class UsageSection(Section):
    def __init__(self, usage_details, piggytargets, cacheinfo):
        options = ["cached(%d,%d)" % cacheinfo]
        super().__init__(
            "azure_%s" % usage_details.section, piggytargets, separator=124, options=options
        )
        self.add(usage_details.dumpinfo())


class IssueCollecter:
    def __init__(self) -> None:
        super().__init__()
        self._list: list[tuple[str, str]] = []

    def add(self, issue_type, issued_by, issue_msg) -> None:
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
    def __init__(self, info):
        super().__init__()
        self.info = info
        self.info.update(get_attrs_from_uri(info["id"]))
        self.tags = self.info.get("tags", {})

        self.section = info["type"].split("/")[-1].lower()
        self.piggytargets = []
        group = self.info.get("group")
        if group:
            self.piggytargets.append(group)
        self.metrics = []

    def dumpinfo(self):
        # TODO: Hmmm, should the variable-length tuples actually be lists?
        lines: List[Tuple] = [("Resource",), (json.dumps(self.info),)]
        if self.metrics:
            lines += [("metrics following", len(self.metrics))]
            lines += [(json.dumps(m),) for m in self.metrics]
        return lines


def process_vm(mgmt_client, vmach, args):
    use_keys = ("statuses",)

    inst_view = mgmt_client.vmview(vmach.info["group"], vmach.info["name"])
    items = ((k, inst_view.get(k)) for k in use_keys)
    vmach.info["specific_info"] = {k: v for k, v in items if v is not None}

    if args.piggyback_vms not in ("grouphost",):
        vmach.piggytargets.remove(vmach.info["group"])
    if args.piggyback_vms in ("self",):
        vmach.piggytargets.append(vmach.info["name"])


class MetricCache(DataCache):
    def __init__(self, resource, metric_definition, ref_time, debug=False):
        self.metric_definition = metric_definition
        metricnames = metric_definition[0]
        super().__init__(self.get_cache_path(resource), metricnames, debug=debug)
        self.remaining_reads = None
        self.timedelta = {
            "PT1M": datetime.timedelta(minutes=1),
            "PT5M": datetime.timedelta(minutes=5),
            "PT1H": datetime.timedelta(hours=1),
        }[metric_definition[1]]
        start = ref_time - 3 * self.timedelta
        self._timespan = "%s/%s" % (
            start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ref_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    @staticmethod
    def get_cache_path(resource):
        valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
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
                msg = "metric not found: %s (%s)" % (raw_metric["name"]["value"], aggregation)
                err.add("info", resource_id, msg)
                LOGGER.info(msg)

        return metrics


class UsageClient(DataCache):
    NO_CONSUPTION_API = (
        "offer MS-AZR-0145P",
        "offer MS-AZR-0146P",
        "offer MS-AZR-159P",
        "offer MS-AZR-0036P",
        "offer MS-AZR-0143P",
        "offer MS-AZR-0015P",
        "offer MS-AZR-0144P",
    )

    def __init__(self, client, subscription, debug=False):
        super().__init__(AZURE_CACHE_FILE_PATH, "%s-usage" % subscription, debug=debug)
        self._client = client

    @property
    def cache_interval(self) -> int:
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = int(get_seconds_since_midnight(NOW))
        LOGGER.debug("Maximal allowed age of usage data cache: %s sec", cache_interval)
        return cache_interval

    @classmethod
    def offerid_has_no_consuption_api(cls, errmsg):
        return any(s in errmsg for s in cls.NO_CONSUPTION_API)

    def get_validity_from_args(self, *args: Any) -> bool:
        return True

    def get_live_data(self, *args: Any) -> Any:
        LOGGER.debug("UsageClient: get live data")

        try:
            # (mo) I am unable to get the filter for usage_end working :-(
            unfiltered_usages = self._client.usagedetails()
        except ApiError as exc:
            if self.offerid_has_no_consuption_api(exc.args[0]):
                return []
            raise
        LOGGER.debug("unfiltered usage details: %d", len(unfiltered_usages))
        if not unfiltered_usages:  # do not save this in the cache!
            raise ApiErrorMissingData("Azure API did not return any usage details")

        yesterday = (NOW - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        usages = [u for u in unfiltered_usages if u["properties"]["usageEnd"].startswith(yesterday)]
        LOGGER.debug("yesterdays usage details: %d", len(usages))

        # add group info:
        for usage in usages:
            attrs = get_attrs_from_uri(usage["properties"]["instanceId"])
            if "group" in attrs:
                usage["group"] = attrs["group"]

        return usages

    def write_sections(self, monitored_groups):
        try:
            usage_data = self.get_data()
        except ApiErrorMissingData if self.debug else Exception as exc:
            LOGGER.warning("%s", exc)
            write_exception_to_agent_info_section(exc, "Usage client")
            # write an empty section to all groups:
            AzureSection("usagedetails", monitored_groups + [""]).write(write_empty=True)
            return

        cacheinfo = (self.cache_timestamp or time.time(), self.cache_interval)
        for usage_details in usage_data:
            usage_resource = AzureResource(usage_details)
            piggytargets = [g for g in usage_resource.piggytargets if g in monitored_groups] + [""]
            UsageSection(usage_resource, piggytargets, cacheinfo).write()


def write_section_ad(graph_client):
    section = AzureSection("ad")

    # users
    users = graph_client.users()
    section.add(["users_count", len(users)])

    # organization
    orgas = graph_client.organization()
    section.add(["ad_connect", json.dumps(orgas)])

    section.write()


def gather_metrics(mgmt_client, resource, debug=False):
    """
    Gather all metrics for a resource. These metrics have different time
    resolutions, so every metric needs its own cache.
    Along the way collect ocurrring errors.
    """
    err = IssueCollecter()
    metric_definitions = METRICS_SELECTED.get(resource.info["type"], [])
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

    labels_section = LabelsSection(vm.info["name"])
    labels_section.add(((json.dumps(vm_labels),)))
    return labels_section


def process_resource(
    function_args: Tuple[MgmtApiClient, AzureResource, GroupLabels, Args]
) -> Sequence[Section]:
    mgmt_client, resource, group_labels, args = function_args
    sections: list[Section] = []

    resource_type = resource.info.get("type")
    if resource_type == "Microsoft.Compute/virtualMachines":
        process_vm(mgmt_client, resource, args)

        if args.piggyback_vms == "self":
            sections.append(get_vm_labels_section(resource, group_labels))

    err = gather_metrics(mgmt_client, resource, debug=args.debug)

    agent_info_section = AzureSection("agent_info")
    agent_info_section.add(("remaining-reads", mgmt_client.ratelimit))
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
            group_labels[name] = {**tags, **{"resource_group": name}}

    return group_labels


def write_group_info(
    monitored_groups: Sequence[str],
    monitored_resources: Sequence[AzureResource],
    group_labels: GroupLabels,
) -> None:
    for group_name, tags in group_labels.items():
        labels_section = LabelsSection(group_name)
        labels_section.add(((json.dumps(tags),)))
        labels_section.write()

    section = AzureSection("agent_info")
    section.add(("monitored-groups", json.dumps(monitored_groups)))
    section.add(("monitored-resources", json.dumps([r.info["name"] for r in monitored_resources])))
    section.write()
    # write empty agent_info section for all groups, otherwise
    # the service will only be discovered if something goes wrong
    AzureSection("agent_info", monitored_groups).write()


def write_exception_to_agent_info_section(exception, component):
    # those exceptions are quite noisy. try to make them more concise:
    msg = str(exception).split("Trace ID", 1)[0]
    msg = msg.split(":", 2)[-1].strip(" ,")

    if "does not have authorization to perform action" in msg:
        msg += "HINT: Make sure you have a proper role asigned to your client!"

    value = json.dumps((2, "%s: %s" % (component, msg)))
    section = AzureSection("agent_info")
    section.add(("agent-bailout", value))
    section.write()


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
        queue: Queue[Tuple[Any, bool, Any]] = Queue()
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
        write_section_ad(graph_client)
    except Exception as exc:
        if args.debug:
            raise
        write_exception_to_agent_info_section(exc, "Graph client")


def main_subscription(args, selector, subscription):
    mgmt_client = MgmtApiClient(subscription)

    try:
        mgmt_client.login(args.tenant, args.client, args.secret)

        all_resources = (AzureResource(r) for r in mgmt_client.resources())

        monitored_resources = [r for r in all_resources if selector.do_monitor(r)]

        monitored_groups = sorted(set(r.info["group"] for r in monitored_resources))
    except Exception as exc:
        if args.debug:
            raise
        write_exception_to_agent_info_section(exc, "Management client")
        return

    group_labels = get_group_labels(mgmt_client, monitored_groups)
    write_group_info(monitored_groups, monitored_resources, group_labels)

    usage_client = UsageClient(mgmt_client, subscription, args.debug)
    usage_client.write_sections(monitored_groups)

    func_args = ((mgmt_client, resource, group_labels, args) for resource in monitored_resources)
    mapper = get_mapper(args.debug, args.sequential, args.timeout)
    for sections in mapper(process_resource, func_args):
        for section in sections:
            section.write()


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
