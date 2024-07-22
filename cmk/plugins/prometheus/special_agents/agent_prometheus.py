#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent for monitoring Prometheus with Checkmk.
"""

import argparse
import ast
import json
import logging
import sys
import traceback
from collections import defaultdict, OrderedDict
from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import Any

import requests

from cmk.plugins.lib.prometheus import (
    add_authentication_args,
    authentication_from_args,
    extract_connection_args,
    generate_api_session,
)
from cmk.special_agents.utils.node_exporter import (  # pylint: disable=cmk-module-layer-violation
    NodeExporter,
    PromQLMetric,
    SectionStr,
)
from cmk.special_agents.v0_unstable.request_helper import ApiSession

LOGGER = logging.getLogger()  # root logger for now


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
        "--timeout",
        default=10,
        type=int,
        help="""Timeout for individual processes in seconds (default 10)""",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="The configuration is passed as repr object. This option will change in the future.",
    )
    add_authentication_args(parser)
    args = parser.parse_args(argv)
    return args


def parse_pod_name(labels: dict[str, str], prepend_namespace: bool = False) -> str:
    pod = labels["pod"]
    namespace = labels["namespace"]
    if prepend_namespace:
        return f"{namespace}_{pod}"
    return pod


class CAdvisorExporter:
    def __init__(self, api_client, options) -> None:  # type: ignore[no-untyped-def]
        self.api_client = api_client
        self.container_name_option = options.get("container_id", "short")
        self.pod_containers: dict = {}
        self.container_ids: dict = {}
        self.prepend_namespaces = options.get("prepend_namespaces", True)
        self.namespace_include_patterns = options.get("namespace_include_patterns", [])

    def _pod_name(self, labels):
        return parse_pod_name(labels, self.prepend_namespaces)

    def update_pod_containers(self):
        result: dict[str, list[str]] = {}
        container_ids = {}
        temp_result = self.api_client.query_promql('container_last_seen{container!="", pod!=""}')
        for container_info in temp_result:
            container_name = container_info.label_value("name")
            result.setdefault(self._pod_name(container_info.labels), []).append(container_name)

            id_long = container_info.label_value("id").split("/")[-1]
            container_ids[container_name] = {
                "short": id_long[0:12],
                "long": id_long,
                "name": container_name,
            }
        self.pod_containers.update(result)
        self.container_ids.update(container_ids)

    def diskstat_summary(self, group_element: str) -> list[dict[str, dict[str, Any]]]:
        logging.debug("Parsing cAdvisor diskstat")
        disk_info = {
            "disk_utilisation": "sum by ({{group_element}})(container_fs_usage_bytes{exclusion}) / "
            "sum by({{group_element}})(container_fs_limit_bytes{exclusion}) * 100",
            "disk_write_operation": "sum by ({{group_element}})(rate(container_fs_writes_total{exclusion}[5m]))",
            "disk_read_operation": "sum by ({{group_element}})(rate(container_fs_reads_total{exclusion}[5m]))",
            "disk_write_throughput": "sum by ({{group_element}})(rate(container_fs_writes_bytes_total{exclusion}[5m]))",
            "disk_read_throughput": "sum by ({{group_element}})(rate(container_fs_reads_bytes_total{exclusion}[5m]))",
        }
        return self._retrieve_formatted_cadvisor_info(disk_info, group_element)

    def cpu_summary(self, group_element: str) -> list[dict[str, dict[str, Any]]]:
        # Reference ID: 34923788
        logging.debug("Parsing cAdvisor CPU")
        cpu_info = {
            "cpu_user": "sum by ({{group_element}})(rate(container_cpu_user_seconds_total{exclusion}[5m])*100)",
            "cpu_system": "sum by ({{group_element}})(rate(container_cpu_system_seconds_total{exclusion}[5m])*100)",
        }
        return self._retrieve_formatted_cadvisor_info(cpu_info, group_element)

    def df_summary(self, group_element: str) -> list[dict[str, dict[str, Any]]]:
        logging.debug("Parsing cAdvisor df")
        df_info = {
            "df_size": "sum by ({{group_element}})(container_fs_limit_bytes{exclusion})",
            "df_used": "sum by ({{group_element}})(container_fs_usage_bytes{exclusion})",
            "inodes_total": "sum by ({{group_element}})(container_fs_inodes_total{exclusion})",
            "inodes_free": "sum by ({{group_element}})(container_fs_inodes_free{exclusion})",
        }
        return self._retrieve_formatted_cadvisor_info(df_info, group_element)

    def if_summary(self, group_element: str) -> list[dict[str, dict[str, Any]]]:
        logging.debug("Parsing cAdvisor if")
        if_info = {
            "if_in_total": "sum by ({{group_element}})(rate(container_network_receive_bytes_total{exclusion}[5m]))",
            "if_in_discards": "sum by ({{group_element}})(rate(container_network_receive_packets_dropped_total{exclusion}[5m]))",
            "if_in_errors": "sum by ({{group_element}})(rate(container_network_receive_errors_total{exclusion}[5m]))",
            "if_out_total": "sum by ({{group_element}})(rate(container_network_transmit_bytes_total{exclusion}[5m]))",
            "if_out_discards": "sum by ({{group_element}})(rate(container_network_transmit_packets_dropped_total{exclusion}[5m]))",
            "if_out_errors": "sum by ({{group_element}})(rate(container_network_transmit_errors_total{exclusion}[5m]))",
        }
        return self._retrieve_formatted_cadvisor_info(if_info, group_element)

    def memory_pod_summary(self, _group_element: str) -> list[dict[str, dict[str, Any]]]:
        logging.debug("Parsing cAdvisor pod memory")

        memory_info = [
            (
                "memory_usage_pod",
                'container_memory_usage_bytes{pod!="", container=""{namespace_filter}}',
            ),
            (
                "memory_limit",
                'sum by(pod, namespace, instance)(container_spec_memory_limit_bytes{container!=""{namespace_filter}})',
            ),
            (
                "memory_rss",
                'sum by(pod, namespace, instance)(container_memory_rss{container!=""{namespace_filter}})',
            ),
            (
                "memory_swap",
                'sum by(pod, namespace, instance)(container_memory_swap{container!=""{namespace_filter}})',
            ),
            (
                "memory_cache",
                'sum by(pod, namespace, instance)(container_memory_cache{container!=""{namespace_filter}})',
            ),
        ]

        pods_raw, pod_machine_associations = self._retrieve_pods_memory_summary(memory_info)
        required_memory_stats = [
            stat_name for stat_name, _query in memory_info if stat_name != "memory_limit"
        ]
        pods_complete, pods_missing_limit = self._filter_out_incomplete(
            pods_raw, required_memory_stats
        )
        pods_complete.update(
            self._complement_machine_memory(pods_missing_limit, pod_machine_associations)
        )
        return self._format_for_service(pods_complete)

    def _retrieve_pods_memory_summary(
        self, memory_info: list[tuple[str, str]]
    ) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
        result: dict[str, dict[str, str | dict[str, str]]] = {}
        associations = {}
        for memory_stat, promql_query in memory_info:
            promql_query = promql_query.replace("{namespace_filter}", self._namespace_query_part())
            for pod_memory_info in self.api_client.query_promql(promql_query):
                pod_name = self._pod_name(pod_memory_info.labels)
                pod = result.setdefault(pod_name, {})
                pod[memory_stat] = {
                    "value": pod_memory_info.value(),
                    "labels": pod_memory_info.labels,
                }
                if pod_name not in associations:
                    associations[pod_name] = pod_memory_info.label_value("instance")

        return result, associations

    def _format_for_service(self, pods: dict) -> list[dict[str, dict[str, Any]]]:
        result = []
        for pod_name, pod_info in pods.items():
            pod_formatted = {
                pod_name: {stat_name: [stat_info] for stat_name, stat_info in pod_info.items()}
            }
            result.append(pod_formatted)
        return result

    def _filter_out_incomplete(
        self, pods_memory: dict[str, dict[str, Any]], required_stats: list[str]
    ) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        """Filter out the pods which do not have the complete set of required stats memory values

        Separate the remaining pods as having and missing memory limits

        """
        pods_complete = {}
        pods_missing_limit = {}
        for pod_name, pod_info in pods_memory.items():
            if not all(stat in pod_info for stat in required_stats):
                continue
            if self._verify_valid_memory_limit(pod_info):
                pods_complete[pod_name] = pod_info
                continue
            pods_missing_limit[pod_name] = {stat: pod_info[stat] for stat in required_stats}
        return pods_complete, pods_missing_limit

    def _verify_valid_memory_limit(self, pod_info):
        if "memory_limit" not in pod_info:
            return False

        try:
            return float(pod_info["memory_limit"]["value"]) != 0.0
        except ValueError:
            return False

    def _complement_machine_memory(
        self, pods: dict[str, dict[str, Any]], pod_machine_associations: dict[str, str]
    ) -> dict[str, dict[str, Any]]:
        """Add the machine memory limit to pods of their hosting machine"""
        machines_memory = self._retrieve_machines_memory()
        for pod_name, pod_info in pods.items():
            pod_info.update({"memory_machine": machines_memory[pod_machine_associations[pod_name]]})
        return pods

    def _retrieve_machines_memory(self) -> dict[str, dict[str, Any]]:
        machine_memory_info = self.api_client.query_promql("machine_memory_bytes")
        machine = {}
        for machine_info in machine_memory_info:
            machine_instance = machine_info.label_value("instance")
            machine[machine_instance] = {
                "value": machine_info.value(),
                "labels": machine_info.labels,
            }
        return machine

    def memory_container_summary(self, _group_element: str) -> list[dict[str, dict[str, Any]]]:
        logging.debug("Parsing cAdvisor container memory")
        memory_info = {
            "memory_usage_container": 'sum by (pod, namespace, container, name)(container_memory_usage_bytes{container!=""{namespace_filter}})',
            "memory_rss": 'container_memory_rss{container!=""{namespace_filter}}',
            "memory_swap": 'container_memory_swap{container!=""{namespace_filter}}',
            "memory_cache": 'container_memory_cache{container!=""{namespace_filter}}',
        }
        memory_info = {
            k: v.replace("{namespace_filter}", self._namespace_query_part())
            for k, v in memory_info.items()
        }
        result_temp = self._retrieve_cadvisor_info(memory_info, group_element="name")

        extra_result = {}
        for pod_memory_info in self.api_client.query_promql(
            f'sum by (pod, namespace)(container_memory_usage_bytes{{pod!="", container=""{self._namespace_query_part()}}})'
        ):
            pod_name = self._pod_name(pod_memory_info.labels)
            for container_name in self.pod_containers[pod_name]:
                extra_result[container_name] = {
                    "memory_usage_pod": [
                        {
                            "value": pod_memory_info.value(as_string=True),
                            "labels": pod_memory_info.labels,
                        }
                    ]
                }
        extra_result = self._apply_container_name_option(extra_result)
        result_temp.append(extra_result)
        return result_temp

    def _retrieve_formatted_cadvisor_info(
        self, entity_info: dict[str, str], group_element: str
    ) -> list[dict[str, dict[str, Any]]]:
        exclusion_element = (
            '{{container!="POD",container!=""{namespace_filter}}}'
            if group_element == "container"
            else '{{container!=""{namespace_filter}}}'
        )
        exclusion_element = exclusion_element.replace(
            "{namespace_filter}", self._namespace_query_part()
        )

        for metric_name, metric_promql in entity_info.items():
            entity_info[metric_name] = metric_promql.format(exclusion=exclusion_element)

        return self._retrieve_cadvisor_info(entity_info, group_element)

    def _retrieve_cadvisor_info(
        self, entity_info: dict[str, str], group_element: str
    ) -> list[dict[str, dict[str, Any]]]:
        result = []
        group_element = "name" if group_element in ("name", "container") else "pod, namespace"
        for entity_name, entity_promql in entity_info.items():
            promql_result = self.api_client.query_promql(
                self._prepare_query(entity_promql, group_element)
            )

            if group_element in ("container", "name"):
                piggybacked_services = parse_piggybacked_services(
                    promql_result,
                    metric_description=entity_name,
                    label_as_piggyback_host=group_element,
                )
                if self.container_name_option in ("short", "long"):
                    piggybacked_services = self._apply_container_name_option(piggybacked_services)
            else:
                piggybacked_services = parse_piggybacked_services(
                    promql_result,
                    metric_description=entity_name,
                    piggyback_parser=self._pod_name,
                )

            result.append(piggybacked_services)
        return result

    def _prepare_query(self, entity_promql, group_element):
        if "{group_element}" in entity_promql:
            promql_query = entity_promql.format(group_element=group_element)
        else:
            promql_query = entity_promql
        return promql_query

    def _namespace_query_part(self):
        if not self.namespace_include_patterns:
            return ""
        return f", namespace=~'{'|'.join(self.namespace_include_patterns)}'"

    def _apply_container_name_option(self, promql_result):
        promql_result_new = {}
        for piggyback_host_name, piggyback_data in promql_result.items():
            promql_result_new[
                self.container_ids[piggyback_host_name][self.container_name_option]
            ] = piggyback_data
        return promql_result_new


class PromQLResponse:
    def __init__(self, promql_response: list[dict[str, Any]]) -> None:
        self.response = promql_response

    def process_single_result(self) -> dict[str, Any]:
        """Process the PromQL response which is restricted to 1 single element

        Returns: The queried PromQL metric for entity_name, entity_promql in entity_info.items()

        """
        if len(self.response) == 1 and (value := self.response[0].get("value")) is not None:
            return {"value": value[1]}

        # different cases for invalid/failed query expression
        inv_info = {
            0: "query error",
            1: "no value",
        }.get(len(self.response), "unsupported query")
        return {"invalid_info": inv_info}


class PromQLResult:
    """The PromQL result object representation for internal usage"""

    def __init__(self, raw_response: dict[str, Any]) -> None:
        """

        Args:
            raw_response:
                the raw format of a single PromQl queried result
                metric key represents the labels of the entry

                {"metric": {"job": "sample", "instance": "minikube"},
                "value": [0, 1.45]}

        """
        self.labels = raw_response["metric"]
        self.internal_values = raw_response["value"]

    def label_value(self, key: str) -> str:
        return self.labels.get(key)

    def value(self, default_value: float | int | None = None, as_string: bool = False) -> float:
        try:
            value = self.internal_values[1]
            if as_string:
                return value
            return float(value)
        except (KeyError, AttributeError) as e:
            if default_value:
                return default_value
            raise e


def parse_piggybacked_services(
    promql_results: list[PromQLResult],
    metric_description: str,
    label_as_piggyback_host: str | None = None,
    piggyback_parser: Callable | None = None,
) -> dict[str, dict[str, list[dict[str, float]]]]:
    """Prepare the PromQLResults to a dict format for Piggyback parsing

    Args:
        promql_results:
            List of PromQLResult objects

        metric_description:
            metric name for the va

        label_as_piggyback_host:
            label key which is used to determine the piggyback host from the PromQLResult labels

        piggyback_parser:
            function which parses the piggyback host name using the labels

    Returns:
        dict which represents piggybacked services (host -> service -> metric)

    """
    result: dict[str, dict[str, list[dict[str, float]]]] = {}
    for promql_result in promql_results:
        if piggyback_parser:
            piggyback_host = piggyback_parser(promql_result.labels)
        elif label_as_piggyback_host:
            piggyback_host = promql_result.label_value(label_as_piggyback_host)
        else:
            return result

        result.setdefault(piggyback_host, {}).setdefault(metric_description, []).append(
            {"value": promql_result.value(), "labels": promql_result.labels}
        )
    return result


class PromQLMultiResponse(PromQLResponse):
    """PromQL Response where one or more metric results are expected"""

    def __init__(self, promql_response: list[dict[str, Any]]) -> None:
        super().__init__(promql_response)
        self.labels_overall_frequencies: dict[str, dict[str, float]] = {}
        self.promql_metrics = self._process_multi_result()

    def _process_multi_result(self) -> list[PromQLMetric]:
        result: list[PromQLMetric] = []
        if not self.response:
            return result
        for metric in self.response:
            if (value := metric.get("value")) is None:
                continue
            self._update_labels_overall_frequencies(metric["metric"])
            result.append({"value": value[1], "labels": metric["metric"]})
        return result

    def _update_labels_overall_frequencies(self, metric_labels: dict[str, str]) -> None:
        for promql_specific_label, metric_specific_label in metric_labels.items():
            promql_specific_label_frequencies = self.labels_overall_frequencies.setdefault(
                promql_specific_label, defaultdict(int)
            )
            promql_specific_label_frequencies[metric_specific_label] += 1
            promql_specific_label_frequencies["total_count"] += 1


class PrometheusServer:
    """
    Query and process general information from the Prometheus Server including
    its own status and the connected scrape targets
    """

    def __init__(self, api_client: "PrometheusAPI") -> None:
        self.api_client = api_client

    def build_info(self):
        result: dict[str, Any] = {}
        result.update({"scrape_target": self._scrape_targets()})

        version = self._prometheus_version()
        if version:
            result["version"] = version

        storage_retention = self._storage_retention()
        if storage_retention:
            result["storage_retention"] = storage_retention

        reload_config_status = self._reload_config_status()
        if reload_config_status:
            result["reload_config_status"] = reload_config_status

        return result

    def health(self) -> dict[str, Any]:
        response = self.api_client.query_static_endpoint("/-/healthy")
        return {"status_code": response.status_code, "status_text": response.reason}

    def _prometheus_version(self) -> Sequence[str]:
        try:
            endpoint_result = self.api_client.query_static_endpoint("/status/buildinfo")
            return [json.loads(endpoint_result.content)["data"]["version"]]
        except requests.exceptions.HTTPError as e:  # This endpoint is only available from v2.14
            if e.response is None or e.response.status_code not in (404, 405):
                raise e

        promql_result = self.api_client.perform_multi_result_promql("prometheus_build_info")
        if promql_result is None:
            raise ApiError("Missing Prometheus version")

        return [instance["labels"]["version"] for instance in promql_result.promql_metrics]

    def _scrape_targets(self) -> dict[str, Any]:
        down_targets = []
        promql_result = self.api_client.perform_multi_result_promql("up")

        if promql_result is None:
            raise ApiError("Missing Scrape Targets information")

        scrape_targets = promql_result.promql_metrics
        for scrape_target in scrape_targets:
            if not scrape_target["value"]:
                down_targets.append(scrape_target["labels"]["job"])
        return {"targets_number": len(scrape_targets), "down_targets": down_targets}

    def _reload_config_status(self) -> str | None:
        runtime_details = self._runtime_info()
        return runtime_details.get("reloadConfigSuccess")

    def _storage_retention(self) -> str | None:
        runtime_details = self._runtime_info()
        return runtime_details.get("storageRetention")

    def _runtime_info(self) -> dict[str, Any]:
        try:
            endpoint_result = self.api_client.query_static_endpoint("/status/runtimeinfo")
        except requests.exceptions.HTTPError:  # This endpoint is only available from v2.14
            return {}

        return json.loads(endpoint_result.content)["data"]


class PrometheusAPI:
    """
    Realizes communication with the Prometheus API
    """

    def __init__(self, session: ApiSession) -> None:
        self.session = session

    def perform_specified_promql_queries(
        self, custom_services: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Prepare Host & Piggyback data from custom defined PromQL expressions

        For custom Prometheus services, only allow PromQL expressions which
        return one single Prometheus metric.

        Args:
            custom_services: list of dicts where each dict specifies the details
                             a Prometheus custom service including the associating
                             metrics. Each metric is the result of a PromQL expression

        Returns: dict where the key is the Piggyback Host Name and the value is
                 a list of services for that host. Each list element
                 contains the information of one service including the service metrics

        """
        result: dict[str, dict[str, Any]] = {}
        for service in custom_services:
            # Per default assign resulting service to Prometheus Host
            host_name = service.get("host_name", "")
            host_services = result.setdefault(host_name, {})

            service_description = service["service_description"]
            service_metrics = []
            for metric in service["metric_components"]:
                metric_info = {
                    "name": metric.get("metric_name"),
                    "label": metric["metric_label"],
                    "promql_query": metric["promql_query"],
                    "levels": metric.get("levels"),
                }
                try:
                    promql_response = PromQLResponse(
                        self._perform_promql_query(metric["promql_query"])
                    )
                except (KeyError, ValueError, requests.exceptions.Timeout) as exc:
                    LOGGER.exception(exc)
                    continue
                metric_info.update(promql_response.process_single_result())
                service_metrics.append(metric_info)

            host_services[service_description] = {
                "service_metrics": service_metrics,
            }
        return result

    def query_static_endpoint(self, endpoint: str) -> requests.models.Response:
        """Query the given endpoint of the Prometheus API expecting a text response

        Args:
            endpoint: Param which contains the Prometheus API endpoint to be queried

        Returns:
            Returns a response object containing the status code and description
        """
        response = self.session.get(endpoint)
        response.raise_for_status()
        return response

    def perform_multi_result_promql(self, promql_expression: str) -> PromQLMultiResponse | None:
        """Performs a PromQL query where multi metrics response is allowed"""
        try:
            promql_response = PromQLMultiResponse(self._perform_promql_query(promql_expression))
        except (KeyError, ValueError, requests.exceptions.Timeout) as exc:
            logging.exception(exc)
            return None

        return promql_response

    def query_promql(self, promql: str) -> list[PromQLResult]:
        try:
            return [PromQLResult(info) for info in self._perform_promql_query(promql)]
        except (KeyError, ValueError, requests.exceptions.Timeout) as exc:
            logging.exception(exc)
            return []

    def _perform_promql_query(self, promql: str) -> list[dict[str, Any]]:
        response = self.session.get("query", params={"query": promql})
        response.raise_for_status()
        return response.json()["data"]["result"]

    def _query_json_endpoint(self, endpoint: str) -> dict[str, Any]:
        """Query the given endpoint of the Prometheus API expecting a json response"""
        result = self._process_json_request(endpoint)
        return result

    def _process_json_request(self, api_request: str) -> dict[str, Any]:
        response = self.session.get(api_request)
        response.raise_for_status()
        return response.json()


class Section:
    """
    An agent section.
    """

    def __init__(self) -> None:
        self._content: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def insert(self, check_data: dict[str, Any]) -> None:
        for key, value in check_data.items():
            if key not in self._content:
                self._content[key] = value
            elif isinstance(value, dict):
                self._content[key].update(value)
            else:
                raise ValueError("Key %s is already present and cannot be merged" % key)

    def output(self) -> str:
        return json.dumps(self._content)


class PiggybackHost:
    """
    An element that bundles a collection of sections.
    """

    def __init__(self) -> None:
        super().__init__()
        self._sections: OrderedDict[str, Section] = OrderedDict()

    def get(self, section_name: str) -> Section:
        if section_name not in self._sections:
            self._sections[section_name] = Section()
        return self._sections[section_name]

    def output(self) -> list[str]:
        data = []
        for name, section in self._sections.items():
            data.append("<<<%s:sep(0)>>>" % name)
            data.append(section.output())
        return data


class PiggybackGroup:
    """
    A group of elements where an element is e.g. a piggyback host.
    """

    def __init__(self) -> None:
        self._elements: OrderedDict[str, PiggybackHost] = OrderedDict()

    def get(self, element_name: str) -> PiggybackHost:
        if element_name not in self._elements:
            self._elements[element_name] = PiggybackHost()
        return self._elements[element_name]

    def join(self, section_name: str, pairs: Mapping[str, dict[str, Any]]) -> "PiggybackGroup":
        for element_name, data in pairs.items():
            section = self.get(element_name).get(section_name)
            section.insert(data)
        return self

    def output(self, piggyback_prefix: str = "") -> list[str]:
        data = []
        for name, element in self._elements.items():
            data.append("<<<<%s>>>>" % (piggyback_prefix + name))
            data.extend(element.output())
            data.append("<<<<>>>>")
        return data


class ApiData:
    """
    Hub for all various metrics coming from different sources including the Prometheus
    Server & the Prometheus Exporters
    """

    def __init__(self, api_client: "PrometheusAPI", exporter_options: dict) -> None:
        self.api_client = api_client
        self.prometheus_server = PrometheusServer(api_client)
        if "cadvisor" in exporter_options:
            self.cadvisor_exporter = CAdvisorExporter(api_client, exporter_options["cadvisor"])

        if "node_exporter" in exporter_options:

            def get_promql(promql_expression: str) -> list[PromQLMetric]:
                result = api_client.perform_multi_result_promql(promql_expression)
                if result is None:
                    raise ApiError("Missing PromQL result for %s" % promql_expression)
                return result.promql_metrics

            self.node_exporter = NodeExporter(get_promql)

    def prometheus_build_section(self) -> str:
        e = PiggybackHost()
        e.get("prometheus_build").insert(self.prometheus_server.build_info())
        return "\n".join(e.output())

    def promql_section(self, custom_services: list[dict[str, Any]]) -> str:
        logging.info("Prometheus PromQl queries")
        e = PiggybackGroup()
        e.join(
            "prometheus_custom",
            self.api_client.perform_specified_promql_queries(custom_services),
        )
        return "\n".join(e.output())

    def server_info_section(self) -> str:
        logging.info("Prometheus Server Info")
        g = PiggybackHost()
        g.get("prometheus_api_server").insert(self.prometheus_server.health())
        return "\n".join(g.output())

    def cadvisor_section(self, cadvisor_options: dict[str, Any]) -> Iterator[str]:
        grouping_option = {
            "both": ["container", "pod"],
            "container": ["container"],
            "pod": ["pod"],
        }

        self.cadvisor_exporter.update_pod_containers()

        cadvisor_summaries = {
            "diskio": self.cadvisor_exporter.diskstat_summary,
            "cpu": self.cadvisor_exporter.cpu_summary,
            "df": self.cadvisor_exporter.df_summary,
            "interfaces": self.cadvisor_exporter.if_summary,
            "memory_pod": self.cadvisor_exporter.memory_pod_summary,
            "memory_container": self.cadvisor_exporter.memory_container_summary,
        }

        cadvisor_grouping = cadvisor_options["grouping_option"]
        entities = cadvisor_options["entities"]

        if "diskio" in entities:
            yield from self._output_cadvisor_summary(
                "cadvisor_diskstat",
                cadvisor_summaries["diskio"],
                grouping_option[cadvisor_grouping],
            )

        if "cpu" in entities:
            yield from self._output_cadvisor_summary(
                "cadvisor_cpu",
                cadvisor_summaries["cpu"],
                grouping_option[cadvisor_grouping],
            )
        if "df" in entities:
            yield from self._output_cadvisor_summary(
                "cadvisor_df",
                cadvisor_summaries["df"],
                grouping_option[cadvisor_grouping],
            )
        if "interfaces" in entities:
            yield from self._output_cadvisor_summary(
                "cadvisor_if",
                cadvisor_summaries["interfaces"],
                grouping_option[cadvisor_grouping],
            )

        if "memory" in entities:
            if "pod" in grouping_option[cadvisor_grouping]:
                yield from self._output_cadvisor_summary(
                    "cadvisor_memory", cadvisor_summaries["memory_pod"], ["pod"]
                )

            if "container" in grouping_option[cadvisor_grouping]:
                yield from self._output_cadvisor_summary(
                    "cadvisor_memory",
                    cadvisor_summaries["memory_container"],
                    ["container"],
                )

    @staticmethod
    def _output_cadvisor_summary(
        cadvisor_service_name: str,
        retrieve_cadvisor_summary: Callable,
        summary_group_options: list[str],
    ) -> Iterator[str]:
        for group_option in summary_group_options:
            group = PiggybackGroup()
            promql_result = retrieve_cadvisor_summary(group_option)
            piggyback_prefix = "pod_" if group_option == "pod" else ""
            for diskio_element in promql_result:
                if diskio_element:
                    group.join(cadvisor_service_name, diskio_element)
            result = group.output(piggyback_prefix=piggyback_prefix)
            if result:
                yield "\n".join(group.output(piggyback_prefix=piggyback_prefix))

    def node_exporter_section(self, node_options: dict[str, list[str] | str]) -> Iterator[str]:
        node_entities = node_options["entities"]
        if "host_mapping" in node_options:
            host_mapping = [node_options["host_mapping"]]
        else:
            host_mapping = [
                "localhost",
                node_options["host_address"],
                node_options["host_name"],
            ]

        if "df" in node_entities:
            df_result = self.node_exporter.df_summary()
            yield from self._output_node_section(df_result, host_mapping)

        if "diskstat" in node_entities:
            diskstat_result = self.node_exporter.diskstat_summary()
            yield from self._output_node_section(diskstat_result, host_mapping)

        if "mem" in node_entities:
            mem_result = self.node_exporter.memory_summary()
            yield from self._output_node_section(mem_result, host_mapping)

        if "kernel" in node_entities:
            kernel_result = self.node_exporter.kernel_summary()
            yield from self._output_node_section(kernel_result, host_mapping)

    def _output_node_section(
        self,
        node_to_section_str: dict[str, SectionStr],
        host_mapping: list[list[str] | str],
    ) -> Iterator[str]:
        for node, section_str in node_to_section_str.items():
            if section_str:
                piggyback_host_name = self._get_node_piggyback_host_name(node)
                if piggyback_host_name not in host_mapping:
                    yield f"<<<<{piggyback_host_name}>>>>\n{section_str}\n<<<<>>>>\n"
                else:
                    yield f"{section_str}\n"

    @staticmethod
    def _get_node_piggyback_host_name(node_name):
        return node_name.split(":")[0]


def _extract_config_args(config: dict[str, Any]) -> dict[str, Any]:
    exporter_options = {}
    for exporter in config["exporter"]:
        exporter_name, exporter_info = exporter
        if exporter_name == "cadvisor":
            grouping_info = exporter_info["entity_level"]
            grouping_option = grouping_info[0]
            exporter_options[exporter_name] = {
                "grouping_option": grouping_option,
                "container_id": grouping_info[1].get("container_id", "short"),
                "entities": exporter_info["entities"],
            }
            if grouping_option in ("pod", "both"):
                exporter_options[exporter_name].update(
                    {
                        "prepend_namespaces": grouping_info[1]["prepend_namespaces"]
                        != "omit_namespace"
                    }
                )
            if "namespace_include_patterns" in exporter_info:
                exporter_options[exporter_name].update(
                    {"namespace_include_patterns": exporter_info["namespace_include_patterns"]}
                )
        elif exporter_name == "node_exporter":
            exporter_info.update(
                {
                    "host_address": config["host_address"],
                    "host_name": config["host_name"],
                }
            )
            exporter_options[exporter_name] = exporter_info
        else:
            exporter_options[exporter_name] = exporter_info

    return {
        "custom_services": config.get("promql_checks", []),
        "exporter_options": exporter_options,
    }


class ApiError(Exception):
    pass


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = parse_arguments(argv)
    try:
        config = ast.literal_eval(args.config)
        config_args = _extract_config_args(config)
        session = generate_api_session(
            extract_connection_args(
                config,
                authentication_from_args(args),
            )
        )
        exporter_options = config_args["exporter_options"]
        # default cases always must be there
        api_client = PrometheusAPI(session)
        api_data = ApiData(api_client, exporter_options)
        print(api_data.prometheus_build_section())
        print(api_data.promql_section(config_args["custom_services"]))
        if "cadvisor" in exporter_options:
            print(*list(api_data.cadvisor_section(exporter_options["cadvisor"])), sep="\n")
        if "node_exporter" in exporter_options:
            print(
                *list(api_data.node_exporter_section(exporter_options["node_exporter"])),
                sep="\n",
            )

    except Exception as e:
        if args.debug:
            raise
        logging.debug(traceback.format_exc())
        sys.stderr.write("%s\n" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
