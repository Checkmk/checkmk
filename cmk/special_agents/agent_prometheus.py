#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""
Special agent for monitoring Prometheus with Checkmk.
"""
import ast
import sys
import argparse
import json
import logging
from typing import List, Dict, Any, Mapping, DefaultDict, Optional, Iterator, Tuple, Callable, Union
from collections import OrderedDict, defaultdict
import math
from urllib.parse import quote, urljoin
import requests

PromQLMetric = Dict[str, Any]

LOGGER = logging.getLogger()  # root logger for now


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--debug",
                        action="store_true",
                        help='''Debug mode: raise Python exceptions''')
    parser.add_argument("-v",
                        "--verbose",
                        action="count",
                        default=0,
                        help='''Verbose mode (for even more output use -vvv)''')
    parser.add_argument("--timeout",
                        default=10,
                        type=int,
                        help='''Timeout for individual processes in seconds (default 10)''')

    args = parser.parse_args(argv)
    return args


def setup_logging(verbosity):
    if verbosity >= 3:
        lvl = logging.DEBUG
    elif verbosity == 2:
        lvl = logging.INFO
    elif verbosity == 1:
        lvl = logging.WARN
    else:
        logging.disable(logging.CRITICAL)
        lvl = logging.CRITICAL
    logging.basicConfig(level=lvl, format='%(asctime)s %(levelname)s %(message)s')


class CAdvisorExporter:
    def __init__(self, api_client, options):
        self.api_client = api_client
        self.container_name_option = options["container_id"]
        self.pod_containers = {}
        self.container_ids = {}

    def update_pod_containers(self):
        result = {}
        container_ids = {}
        temp_result = self.api_client.perform_multi_result_promql(
            'container_last_seen{container!="", pod!=""}').promql_metrics
        for container_details_dict in temp_result:
            labels = container_details_dict["labels"]
            result.setdefault(labels["pod"], []).append(labels["name"])

            id_long = labels["id"].split("/")[-1]
            container_ids[labels["name"]] = {"short": id_long[0:12], "long": id_long}
        self.container_ids.update(container_ids)
        self.pod_containers.update(result)

    def diskstat_summary(self, group_element):
        # type: (str) -> List[Dict[str, Dict[str, Any]]]
        disk_info = {
            "disk_utilisation":
                'sum by ({{group_element}})(container_fs_usage_bytes{exclusion}) / '
                'sum by({{group_element}})(container_fs_limit_bytes{exclusion}) * 100',
            "disk_write_operation": 'sum by ({{group_element}})(rate(container_fs_writes_total{exclusion}[5m]))',
            "disk_read_operation": 'sum by ({{group_element}})(rate(container_fs_reads_total{exclusion}[5m]))',
            "disk_write_throughput": 'sum by ({{group_element}})(rate(container_fs_writes_bytes_total{exclusion}[5m]))',
            "disk_read_throughput": 'sum by ({{group_element}})(rate(container_fs_reads_bytes_total{exclusion}[5m]))'
        }
        return self._retrieve_formatted_cadvisor_info(disk_info, group_element)

    def cpu_summary(self, group_element):
        # type: (str) -> List[Dict[str, Dict[str, Any]]]
        # Reference ID: 34923788
        cpu_info = {
            "cpu_user": 'sum by ({{group_element}})(rate(container_cpu_user_seconds_total{exclusion}[5m])*100)',
            "cpu_system": 'sum by ({{group_element}})(rate(container_cpu_system_seconds_total{exclusion}[5m])*100)',
        }
        return self._retrieve_formatted_cadvisor_info(cpu_info, group_element)

    def df_summary(self, group_element):
        # type: (str) -> List[Dict[str, Dict[str, Any]]]
        df_info = {
            "df_size": 'sum by ({{group_element}})(container_fs_limit_bytes{exclusion})',
            "df_used": 'sum by ({{group_element}})(container_fs_usage_bytes{exclusion})',
            "inodes_total": 'sum by ({{group_element}})(container_fs_inodes_total{exclusion})',
            "inodes_free": 'sum by ({{group_element}})(container_fs_inodes_free{exclusion})',
        }
        return self._retrieve_formatted_cadvisor_info(df_info, group_element)

    def if_summary(self, group_element):
        # type: (str) -> List[Dict[str, Dict[str, Any]]]
        if_info = {
            "if_in_total": 'sum by ({{group_element}})(rate(container_network_receive_bytes_total{exclusion}[5m]))',
            "if_in_discards": 'sum by ({{group_element}})(rate(container_network_receive_packets_dropped_total{exclusion}[5m]))',
            "if_in_errors": 'sum by ({{group_element}})(rate(container_network_receive_errors_total{exclusion}[5m]))',
            "if_out_total": 'sum by ({{group_element}})(rate(container_network_transmit_bytes_total{exclusion}[5m]))',
            "if_out_discards": 'sum by ({{group_element}})(rate(container_network_transmit_packets_dropped_total{exclusion}[5m]))',
            "if_out_errors": 'sum by ({{group_element}})(rate(container_network_transmit_errors_total{exclusion}[5m]))',
        }
        return self._retrieve_formatted_cadvisor_info(if_info, group_element)

    def memory_pod_summary(self, group_element):
        # type: (str) -> List[Dict[str, Dict[str, Any]]]
        memory_info = {
            "memory_usage_pod": 'container_memory_usage_bytes{pod!="", container=""}',
            "memory_limit": 'sum by(pod)(container_spec_memory_limit_bytes{container!=""})',
            "memory_rss": 'sum by(pod)(container_memory_rss{container!=""})',
            "memory_swap": 'sum by(pod)(container_memory_swap{container!=""})',
            "memory_cache": 'sum by(pod)(container_memory_cache{container!=""})'
        }
        result_temp = self._retrieve_cadvisor_info(memory_info, group_element)

        extra_info = self.api_client.perform_multi_result_promql(
            'machine_memory_bytes').promql_metrics
        result_temp.append({
            piggyback_pod_host: {
                "memory_machine": extra_info
            } for piggyback_pod_host in result_temp[0].keys()
        })

        return result_temp

    def memory_container_summary(self, group_element):
        # type: (str) -> List[Dict[str, Dict[str, Any]]]
        memory_info = {
            "memory_usage_container": 'sum by (pod, container, name)(container_memory_usage_bytes{container!=""})',
            "memory_rss": 'container_memory_rss{container!=""}',
            "memory_swap": 'container_memory_swap{container!=""}',
            "memory_cache": 'container_memory_cache{container!=""}',
        }
        result_temp = self._retrieve_cadvisor_info(memory_info, group_element="name")
        pods_memory_result = self.api_client.perform_multi_result_promql(
            'sum by (pod)(container_memory_usage_bytes{pod!="", container=""})').promql_metrics

        extra_result = {}
        for pod_memory_dict in pods_memory_result:
            pod_name = pod_memory_dict["labels"]["pod"]
            for container_name in self.pod_containers[pod_name]:
                extra_result[container_name] = {"memory_usage_pod": [pod_memory_dict]}
        extra_result = self._apply_container_name_option(extra_result)
        result_temp.append(extra_result)

        return result_temp

    def _retrieve_formatted_cadvisor_info(self, entity_info, group_element):
        # type: (Dict[str, str], str) ->  List[Dict[str, Dict[str, Any]]]

        exclusion_element = '{{container!="POD",container!=""}}' if group_element == "container" else '{{container!=""}}'

        for metric_name, metric_promql in entity_info.items():
            entity_info[metric_name] = metric_promql.format(exclusion=exclusion_element)

        return self._retrieve_cadvisor_info(entity_info, group_element)

    def _retrieve_cadvisor_info(self, entity_info, group_element):
        # type: (Dict[str, str], str) -> List[Dict[str, Dict[str, Any]]]
        result = []
        group_element = "name" if group_element == "container" else group_element
        for entity_name, entity_promql in entity_info.items():

            if "{group_element}" in entity_promql:
                promql_query = entity_promql.format(group_element=group_element)
            else:
                promql_query = entity_promql

            promql_result = self.api_client.perform_multi_result_promql(
                promql_query).get_piggybacked_services(metric_description=entity_name,
                                                       promql_label_for_piggyback=group_element)

            if group_element in ("name", "container") and self.container_name_option in ("short",
                                                                                         "long"):
                promql_result = self._apply_container_name_option(promql_result)
            result.append(promql_result)
        return result

    def _apply_container_name_option(self, promql_result):
        promql_result_new = {}
        for piggyback_host_name, piggyback_data in promql_result.items():
            promql_result_new[self.container_ids[piggyback_host_name][
                self.container_name_option]] = piggyback_data
        return promql_result_new


class KubeStateExporter:
    def __init__(self, api_client, clustername):
        self.api_client = api_client
        self.cluster_name = clustername

    # CLUSTER SECTION

    def cluster_resources_summary(self):
        # type: () -> List[Dict[str, Dict[str, Any]]]
        # Cluster Section
        resources_list = [
            ("allocatable", "cpu", "sum(kube_node_status_allocatable_cpu_cores)"),
            ("allocatable", "memory", "sum(kube_node_status_allocatable_memory_bytes)"),
            ("allocatable", "pods", "sum(kube_node_status_allocatable_pods)"),
            ("capacity", "cpu", "sum(kube_node_status_capacity_cpu_cores)"),
            ("capacity", "memory", "sum(kube_node_status_capacity_memory_bytes)"),
            ("capacity", "pods", "sum(kube_node_status_capacity_pods)"),
            ("requests", "cpu", "sum(kube_pod_container_resource_requests_cpu_cores)"),
            ("requests", "memory", "sum(kube_pod_container_resource_requests_memory_bytes)"),
        ]
        result = {}  # type: Dict[str, Dict[str, Any]]
        for resource_family, resource_type, promql_query in resources_list:
            for cluster_info in self.api_client.perform_multi_result_promql(
                    promql_query).promql_metrics:
                cluster_value = int(cluster_info["value"]) if resource_type == "pods" else float(
                    cluster_info["value"])
                result.setdefault(self.cluster_name,
                                  {}).setdefault(resource_family, {})[resource_type] = cluster_value
        # Adding the limits seperately
        result[self.cluster_name].update(self._cluster_limits())
        return [result]

    def _cluster_limits(self):
        # type: () -> Dict[str, Dict[str, float]]
        cluster_limit_queries = {
            "cpu": "sum(kube_pod_container_resource_limits_cpu_cores)",
            "memory": "sum(kube_pod_container_resource_limits_memory_bytes)"
        }
        valid_node_limits = self._nodes_limits()
        node_number = int(
            self.api_client.perform_multi_result_promql("count(kube_node_info)").promql_metrics[0]
            ["value"])
        cluster_limits = {}
        for limit_type, nodes in valid_node_limits.items():
            if len(nodes) == node_number:
                limit_value = float(
                    self.api_client.perform_multi_result_promql(
                        cluster_limit_queries[limit_type]).promql_metrics[0]["value"])
            else:
                limit_value = float("inf")
            cluster_limits[limit_type] = limit_value
        return {"limits": cluster_limits}

    def storage_classes_summary(self):
        # type: () -> List[Dict[str, Dict[str, Any]]]

        result = {}  # type: Dict[str, Dict[str, Any]]
        for cluster_storage_dict in self.api_client.perform_multi_result_promql(
                "kube_storageclass_info").promql_metrics:
            storage_labels = cluster_storage_dict["labels"]
            storage_dict = result.setdefault(self.cluster_name,
                                             {}).setdefault(storage_labels["storageclass"], {})
            storage_dict["reclaim_policy"] = storage_labels["reclaimPolicy"]
            storage_dict["provisioner"] = storage_labels["provisioner"]
        return [result]

    def namespaces_summary(self):
        # type: () -> List[Dict[str, Dict[str, Any]]]

        # Cluster Section
        node_result = {}  # type: Dict[str, Dict[str, Any]]
        for namespace_dict in self.api_client.perform_multi_result_promql(
                "kube_namespace_status_phase").promql_metrics:
            namespace_labels = namespace_dict["labels"]
            if int(namespace_dict["value"]):
                node_result.setdefault(self.cluster_name,
                                       {}).setdefault(namespace_labels["namespace"],
                                                      {})["status"] = {
                                                          "phase": namespace_labels["phase"]
                                                      }
        return [node_result]

    def cluster_node_info(self):
        # type: () -> List[Dict[str, Dict[str, Any]]]

        nodes_list = [
            node_info["labels"]["node"] for node_info in
            self.api_client.perform_multi_result_promql("kube_node_info").promql_metrics
        ]
        return [{self.cluster_name: {"nodes": nodes_list}}]

    # NODE SECTION

    def node_conditions_summary(self):
        # type: () -> List[Dict[str, Dict[str, Any]]]

        # Eventually consider adding PID Pressure in check
        node_conditions_info = {
            "DiskPressure": 'kube_node_status_condition{condition="DiskPressure"}',
            "MemoryPressure": 'kube_node_status_condition{condition="MemoryPressure"}',
            "Ready": 'kube_node_status_condition{condition="Ready"}',
        }
        result = []  # type: List[Dict[str, Dict[str, Any]]]
        for entity_name, promql_query in node_conditions_info.items():
            node_result = {}  # type: Dict[str, Dict[str, Any]]
            for node_condition_dict in self.api_client.perform_multi_result_promql(
                    promql_query).promql_metrics:
                node_condition_labels = node_condition_dict["labels"]
                if int(node_condition_dict["value"]):
                    node_result.setdefault(
                        node_condition_labels["node"],
                        {})[entity_name] = node_condition_labels["status"].capitalize()
            result.append(node_result)
        return result

    def node_resources(self):
        # type: () -> List[Dict[str, Dict[str, Any]]]

        resources_list = [
            ("allocatable", "cpu", "sum by (node)(kube_node_status_allocatable_cpu_cores)"),
            ("allocatable", "memory", "sum by (node)(kube_node_status_allocatable_memory_bytes)"),
            ("allocatable", "pods", "sum by (node)(kube_node_status_allocatable_pods)"),
            ("capacity", "cpu", 'kube_node_status_capacity{resource="cpu"}'),
            ("capacity", "memory", 'kube_node_status_capacity{resource="memory"}'),
            ("capacity", "pods", 'kube_node_status_capacity{resource="pods"}'),
            ("requests", "cpu", "sum by (node)(kube_pod_container_resource_requests_cpu_cores)"),
            ("requests", "memory",
             "sum by (node)(kube_pod_container_resource_requests_memory_bytes)"),
            ("requests", "pods", "count by (node)(kube_pod_info)"),
            ("limits", "cpu", "sum by (node)(kube_pod_container_resource_limits_cpu_cores)"),
            ("limits", "memory", "sum by (node)(kube_pod_container_resource_limits_memory_bytes)"),
        ]

        node_valid_limits = self._nodes_limits()

        result = {}  # type: Dict[str, Dict[str, Any]]
        for resource_family, resource_type, promql_query in resources_list:
            for node_info in self.api_client.perform_multi_result_promql(
                    promql_query).promql_metrics:
                if resource_family == "limits" and node_info["labels"][
                        "node"] not in node_valid_limits[resource_type]:
                    value = float("inf")
                else:
                    value = int(node_info["value"]) if resource_type == "pods" else float(
                        node_info["value"])
                result.setdefault(node_info["labels"]["node"],
                                  {}).setdefault(resource_family, {})[resource_type] = value
        return [result]

    def _nodes_limits(self):
        # type: () -> Dict[str, List[str]]

        pods_count_expressions = [
            ("total", "count by (node)(kube_pod_info)"),
            ("with_cpu_limits",
             "count by (node)(count by (pod, node)(kube_pod_container_resource_limits_cpu_cores))"),
            ("with_memory_limits",
             "count by (node)(count by (pod, node)(kube_pod_container_resource_requests_memory_bytes))"
            )
        ]

        node_pods = {}  # type: Dict[str, Dict[str, str]]
        for pod_count_type, promql_query in pods_count_expressions:
            for count_result in self.api_client.perform_multi_result_promql(
                    promql_query).promql_metrics:
                node_pods.setdefault(count_result["labels"]["node"],
                                     {})[pod_count_type] = count_result["value"]

        nodes_with_limits = {"memory": [], "cpu": []}  # type: Dict[str, List[str]]

        for node, pods_count in node_pods.items():
            entity_total_pods = pods_count["total"]
            if entity_total_pods == pods_count["with_cpu_limits"]:
                nodes_with_limits["cpu"].append(node)
            if entity_total_pods == pods_count["with_memory_limits"]:
                nodes_with_limits["memory"].append(node)
        return nodes_with_limits

    # PODS SECTION

    def pod_conditions_summary(self):
        # type: () -> List[Dict[str, Dict[str, Any]]]

        # Unschedulable missing for now
        pod_conditions_info = [
            ("PodScheduled", "kube_pod_status_scheduled"),
            ("Ready", "kube_pod_status_ready"),
            ("ContainersReady",
             "sum by (pod)(kube_pod_container_status_ready) / count by (pod)(kube_pod_container_status_ready)"
            ),
        ]
        result = []
        for promql_metric, promql_query in pod_conditions_info:
            promql_result = self.api_client.perform_multi_result_promql(promql_query).promql_metrics
            if promql_metric == "ContainersReady":
                for node_ready_dict in promql_result:
                    ready_result = {}
                    ready_status = "True" if int(node_ready_dict["value"]) == 1 else "False"
                    ready_result[node_ready_dict["labels"]["pod"]] = {promql_metric: ready_status}
                    result.append(ready_result)
            else:
                schedule_result = {}  # type: Dict[str, Dict[str, Any]]
                for node_condition_dict in promql_result:
                    node_condition_labels = node_condition_dict["labels"]
                    if int(node_condition_dict["value"]):
                        schedule_result.setdefault(
                            node_condition_labels["pod"],
                            {})[promql_metric] = node_condition_labels["condition"].capitalize()
                result.append(schedule_result)
        return result

    def pod_container_summary(self):
        # type: () -> List[Dict[str, Dict[str, Any]]]

        info = [("waiting", "kube_pod_container_status_waiting"),
                ("running", "kube_pod_container_status_running"),
                ("ready", "kube_pod_container_status_ready"),
                ("terminated", "kube_pod_container_status_terminated")]
        pod_container_result = []
        for condition, promql_query in info:
            temp_result = {}  # type: Dict[str, Dict[str, Any]]
            for container_info in self.api_client.perform_multi_result_promql(
                    promql_query).promql_metrics:
                labels = container_info["labels"]
                query_value = int(container_info["value"])
                metric_dict = temp_result.setdefault(labels["pod"],
                                                     {}).setdefault(labels["container"], {})

                if condition == "ready":
                    metric_dict["ready"] = bool(query_value)
                elif condition == "terminated":
                    metric_dict["state_exit_code"] = query_value
                    if query_value:
                        metric_dict["state"] = "terminated"
                else:
                    if query_value:
                        metric_dict["state"] = condition

                if temp_result:
                    pod_container_result.append(temp_result)

        return pod_container_result

    def pod_resources_summary(self):
        # type: () -> List[Dict[str, Dict[str, Any]]]

        pods_container_count = self.api_client.perform_multi_result_promql(
            "count by (pod)(kube_pod_container_info)").get_value_only_dict("pod")

        resources_list = [
            ("requests", "cpu", "sum by (pod)(kube_pod_container_resource_requests_cpu_cores)"),
            ("requests", "memory", "kube_pod_container_resource_requests_memory_bytes"),
            ("limits", "cpu", "kube_pod_container_resource_limits_cpu_cores"),
            ("limits", "memory", "kube_pod_container_resource_limits_memory_bytes")
        ]

        def _process_resources(resource, query):
            # type: (str, str) -> Dict[str, Dict[str, Dict[str, float]]]

            pod_resources = {}  # type: Dict[str, Dict[str, Dict[str, float]]]
            promql_result = self.api_client.perform_multi_result_promql(
                query).get_value_only_piggybacked_services(resource, "pod")
            for pod in pods_container_count.keys():
                resource_value = 0.0 if pod not in promql_result else promql_result[pod][resource]
                pod_resources.setdefault(pod, {}).setdefault(resource_family,
                                                             {})[resource] = resource_value
            return pod_resources

        def _process_limits(resource, query):
            # type: (str, str) -> Dict[str, Dict[str, Dict[str, float]]]

            promql_limits = self.api_client.perform_multi_result_promql(
                "sum by (pod)(%s)" % query).get_value_only_dict("pod")
            promql_counts = self.api_client.perform_multi_result_promql(
                "count by (pod)(%s)" % query).get_value_only_dict("pod")

            pod_limits = {}  # type: Dict[str, Dict[str, Dict[str, float]]]
            for pod in pods_container_count.keys():
                if pod in promql_limits and promql_counts[pod] == pods_container_count[pod]:
                    limit_value = promql_limits[pod]
                else:
                    limit_value = float("inf")
                pod_limits.setdefault(pod, {}).setdefault("limits", {})[resource] = limit_value
            return pod_limits

        result = []
        for resource_family, resource_type, promql_query in resources_list:
            if resource_family == "requests":
                resource_results = _process_resources(resource_type, promql_query)
            else:
                resource_results = _process_limits(resource_type, promql_query)
            result.append(resource_results)

        return result

    def daemon_pods_summary(self):
        # type: () -> List[Dict[str, Dict[str, Any]]]

        daemon_pods_info = {
            "number_ready": "kube_daemonset_status_number_ready",
            "desired_number_scheduled": "kube_daemonset_status_desired_number_scheduled",
            "current_number_scheduled": "kube_daemonset_status_current_number_scheduled",
            "updated_number_scheduled": "kube_daemonset_updated_number_scheduled",
            "number_available": "kube_daemonset_status_number_available",
            "number_unavailable": "kube_daemonset_status_number_unavailable"
        }
        result = []
        for entity_name, promql_query in daemon_pods_info.items():
            promql_result = self.api_client.perform_multi_result_promql(
                promql_query).get_value_only_piggybacked_services(
                    metric_description=entity_name,
                    promql_label_for_piggyback="daemonset",
                    number_convert="int")
            result.append(promql_result)
        return result

    def services_selector(self):
        # type: () -> List[Dict[str, Dict[str, Any]]]

        # Cluster Section
        service_label_translation = {
            "label_k8s_app": "k8s-app",
            "label_app_kubernetes_io_name": "app.kubernetes.io/name"
        }
        result = {}  # type: Dict[str, Dict[str, Any]]
        for service_info in self.api_client.perform_multi_result_promql(
                "kube_service_labels").promql_metrics:
            service_labels = service_info["labels"]
            service_piggyback = result.setdefault(service_labels["service"], {})
            if len(service_labels) == 5:
                service_piggyback["name"] = service_labels["service"]
            else:
                for label_key, label_value in service_labels.items():
                    if label_value == service_labels["service"] and label_key != "service":
                        service_piggyback.update(
                            {service_label_translation.get(label_key, label_key): label_value})
        return [result]

    def services_info(self):
        # type: () -> List[Dict[str, Dict[str, Any]]]

        result = {}  # type: Dict[str, Dict[str, Any]]
        for service_info in self.api_client.perform_multi_result_promql(
                "kube_service_info").promql_metrics:
            service_labels = service_info["labels"]
            service_piggyback = result.setdefault(service_labels["service"], {})
            service_piggyback.update({
                "cluster_ip": service_labels["cluster_ip"],
                "load_balance_ip": service_labels["load_balancer_ip"]
                                   if service_labels["load_balancer_ip"] else "null"
            })
        return [result]


class PromQLResponse:
    def __init__(self, promql_response):
        # type: (List[Dict[str, Any]]) -> None
        self.response = promql_response

    def process_single_result(self):
        # type: () -> Dict[str, Any]
        """Process the PromQL response which is restricted to 1 single element

        Returns: The queried PromQL metric for entity_name, entity_promql in entity_info.items()

        """
        if len(self.response) == 1 and "value" in self.response[0]:
            return PromQLResponse._extract_metric_value(self.response[0])

        # different cases for invalid/failed query expression
        inv_info = {
            0: "query error",
            1: "no value",
        }.get(len(self.response), "unsupported query")
        return {"invalid_info": inv_info}

    @staticmethod
    def _extract_metric_value(promql_metric):
        # type: (Dict[str, Any]) -> Dict[str, float]

        if "value" in promql_metric:
            return {"value": promql_metric["value"][1]}
        return {}

    @staticmethod
    def _identify_metric_scrape_target(promql_metric_info):
        # type: (PromQLMetric) -> str

        promql_metric_labels = promql_metric_info["labels"]
        scrape_target_name = "%s-%s" % (promql_metric_labels["job"],
                                        promql_metric_labels["instance"])
        return scrape_target_name

    @staticmethod
    def _extract_metric_label(promql_metric_info, label_key):
        # type: (PromQLMetric, str) -> str
        return promql_metric_info["labels"][label_key]

    @staticmethod
    def _extract_metric_labels(metric_labels_dict, promql_labels_subset):
        # type: (Dict[str, str], List[str]) -> str

        metric_labels_holder = ""
        for promql_label in promql_labels_subset:
            metric_labels_holder += metric_labels_dict[promql_label]
        return metric_labels_holder


class PromQLMultiResponse(PromQLResponse):
    """PromQL Response where one or more metric results are expected
    """
    def __init__(self, promql_response):
        # type: (List[Dict[str, Any]]) -> None
        super(PromQLMultiResponse, self).__init__(promql_response)
        self.labels_overall_frequencies = {}  # type: Dict[str, Dict[str, float]]
        self.promql_metrics = self._process_multi_result()

    def get_piggybacked_services(self, metric_description, promql_label_for_piggyback=None):
        # type: (str, Optional[str]) -> Dict[str, Dict[str, Any]]
        """Process PromQL response to get "piggybacked" services

        Args:
            metric_description: Name of Metric
            promql_label_for_piggyback: PromQL label used to determine the piggyback host

        Returns:
            Dict: where key is the piggyback host and the value is a dict containing the services metrics

        """
        result = {}  # type: Dict[str, Dict[str, Any]]
        for promql_metric in self.promql_metrics:
            if promql_label_for_piggyback is not None:
                piggyback_host = self._extract_metric_label(promql_metric,
                                                            promql_label_for_piggyback)
                promql_metric.update({"host_selection_label": promql_label_for_piggyback})
            else:
                piggyback_host = self._identify_metric_scrape_target(promql_metric)

            if piggyback_host == "":
                continue

            result.setdefault(piggyback_host, {}).setdefault(metric_description,
                                                             []).append(promql_metric)
        return result

    def get_value_only_piggybacked_services(self,
                                            metric_description,
                                            promql_label_for_piggyback=None,
                                            number_convert="float"):
        # type: (str, Optional[str], str) -> Dict[str, Dict[str, Union[int, float]]]

        result = {}  # type: Dict[str, Dict[str, Union[int, float]]]
        for promql_metric in self.promql_metrics:
            if promql_label_for_piggyback is not None:
                piggyback_host = self._extract_metric_label(promql_metric,
                                                            promql_label_for_piggyback)
            else:
                piggyback_host = self._identify_metric_scrape_target(promql_metric)

            if piggyback_host == "":
                continue

            if number_convert == "int":
                metric_value = int(promql_metric["value"])  # type: Union[int, float]
            elif number_convert == "float":
                metric_value = float(promql_metric["value"])
            result.setdefault(piggyback_host, {})[metric_description] = metric_value
        return result

    def get_value_only_dict(self, key_label):
        # type: (str) -> Dict[str, float]

        result = {}
        for promql_metric in self.promql_metrics:
            result[self._extract_metric_label(promql_metric,
                                              key_label)] = float(promql_metric["value"])
        return result

    def get_piggybacked_services_with_least_labels(self,
                                                   metric_description,
                                                   promql_label_for_piggyback=None):
        # type: (str, Optional[str]) -> Dict[str, Dict[str, Dict[str, Any]]]
        """Piggybacked services with subset of unique making PromQL labels

        Args:
            metric_description: Name of Metric
            promql_label_for_piggyback: PromQL label used to determine the piggyback host

        Returns:
            Piggybacked services dict which additionally includes the subset of PromQL labels

        """
        piggybacked_services = self.get_piggybacked_services(metric_description,
                                                             promql_label_for_piggyback)
        unique_least_promql_labels = self._get_unique_least_promql_labels()
        for _piggyback_host_name, service_info in piggybacked_services.items():
            service_info.setdefault("unique_labels",
                                    {})[metric_description] = unique_least_promql_labels
        return piggybacked_services

    def _process_multi_result(self):
        # type: () -> List[PromQLMetric]

        result = []  # type: List[PromQLMetric]
        if not self.response:
            return result
        for metric in self.response:
            metric_info = PromQLResponse._extract_metric_value(metric)
            if not metric_info:
                continue
            metric_info.update({"labels": metric["metric"]})
            self._update_labels_overall_frequencies(metric["metric"])
            result.append(metric_info)
        return result

    def _update_labels_overall_frequencies(self, metric_labels):
        # type: (Dict[str, str]) -> None

        for promql_specific_label, metric_specific_label in metric_labels.items():
            promql_specific_label_frequencies = self.labels_overall_frequencies.setdefault(
                promql_specific_label, defaultdict(int))
            promql_specific_label_frequencies[metric_specific_label] += 1
            promql_specific_label_frequencies["total_count"] += 1

    def _get_unique_least_promql_labels(self):
        # type: () -> List[str]

        information_gains = self._determine_promql_labels_information_gains()
        promql_labels_by_relevance = PromQLMultiResponse._extract_promql_labels_by_relevance(
            information_gains)
        unique_least_labels = self._determine_unique_least_labels_combination(
            promql_labels_by_relevance)
        return unique_least_labels

    def _determine_promql_labels_information_gains(self):
        # type: () -> Dict[str, float]
        """Calculates the information gain for each PromQL label

        An information gain value of 0 for a PromQL label signifies that all metric labels are the same across the
        list of metrics. In consequence, a higher information gain value signifies that more distinctive information is
        gained by analysing this PromQL label.

        """
        information_gains = {}
        for promql_label, metric_labels_frequencies in self.labels_overall_frequencies.items():
            promql_label_total_count = metric_labels_frequencies["total_count"]
            metric_label_probabilities = [
                metric_label_count / promql_label_total_count
                for metric_label, metric_label_count in metric_labels_frequencies.items()
                if metric_label != "total_count"
            ]
            information_gains[promql_label] = sum([
                PromQLMultiResponse._determine_single_entropy(metric_label_probability)
                for metric_label_probability in metric_label_probabilities
            ])
        return information_gains

    @staticmethod
    def _determine_single_entropy(p):
        # type: (float) -> float

        if p > 1.0 or p <= 0.0:
            return 0
        return -p * math.log2(p)

    @staticmethod
    def _extract_promql_labels_by_relevance(information_gains):
        # type: (Dict[str, float]) -> List[str]
        """Creates a list with the PromQL labels sorted by information gain relevance
        """
        promql_labels_by_relevance = [
            a for a, b in sorted(information_gains.items(), key=lambda x: x[1], reverse=True)
        ]
        if all(label in promql_labels_by_relevance for label in ("pod", "pod_name")):
            promql_labels_by_relevance.remove("pod_name")
        return promql_labels_by_relevance

    def _determine_unique_least_labels_combination(self, promql_labels_by_relevance):
        # type: (List[str]) -> List[str]
        """Determines the smallest, valid subset of PromQL labels which allows to uniquely identify
        each PromQL metric from the PromQL query result set. It should be noted that this approach does not
        find the exact solution to the underlying problem as the problem cannot be solved in polynomial time (NP-Hard)
        """
        promql_labels_subset = []

        for promql_label in promql_labels_by_relevance:
            promql_labels_subset.append(promql_label)
            if self._verify_all_unique(promql_labels_subset):
                return promql_labels_subset

        return promql_labels_by_relevance

    def _verify_all_unique(self, promql_labels_subset):
        # type: (List[str]) -> bool

        seen_labels_combination = []  # type: List[str]
        for promql_metric in self.promql_metrics:
            metric_labels_dict = promql_metric["labels"]
            metric_labels_subset = PromQLMultiResponse._extract_metric_labels(
                metric_labels_dict, promql_labels_subset)

            if metric_labels_subset in seen_labels_combination:
                # this subset was already seen before meaning that the current selection of promql labels
                # does not make each metric unique of the given promql query
                return False

            seen_labels_combination.append(metric_labels_subset)
        return True


class PrometheusServer:
    """
    Query and process general information from the Prometheus Server including
    its own status and the connected scrape targets
    """
    def __init__(self, api_client):
        # type: ('PrometheusAPI') -> None

        self.api_client = api_client

    def scrape_targets_health(self):
        # type: () -> Dict[str, Dict[str, Any]]

        result = {}
        for scrape_target_name, attributes in self.api_client.scrape_targets_attributes():
            result[scrape_target_name] = {
                "health": attributes["health"],
                "lastScrape": attributes["lastScrape"],
                "labels": attributes["labels"]
            }
        return result

    def health(self):
        # type: () -> Dict[str, Any]

        response = self.api_client.query_static_endpoint("/-/healthy")
        return {"status_code": response.status_code, "status_text": response.reason}


class PrometheusAPI:
    """
    Realizes communication with the Prometheus API
    """
    def __init__(self, server_address):
        # type: (str) -> None

        self.server_address = "http://%s" % server_address
        self.api_endpoint = "%s/api/v1/" % self.server_address
        self.scrape_targets_dict = self._connected_scrape_targets()

    def scrape_targets_attributes(self):
        # type: () -> Iterator[Tuple[str, Dict[str, Any]]]
        """Format the scrape_targets_dict for information processing

        Returns:
              Tuples consisting of the Scrape Target name and its general attributes. The
              job-instance labels combination is hereby omitted

        """
        for _scrape_target_label, info in self.scrape_targets_dict.items():
            scrape_target_name = info["name"]
            yield scrape_target_name, info["attributes"]

    def perform_specified_promql_queries(self, custom_services):
        # type: (List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]
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
        result = {}  # type:  Dict[str, Dict[str, Any]]
        for service in custom_services:
            # Per default assign resulting service to Prometheus Host
            host_name = service.get("host_name", "")
            host_services = result.setdefault(host_name, {})

            service_description = service["service_description"]
            service_metrics = []
            for metric in service["metric_components"]:
                metric_info = {
                    "name": metric["metric_name"],
                    "promql_query": metric["promql_query"]
                }
                try:
                    promql_response = PromQLResponse(self._query_promql(metric["promql_query"]))
                except (KeyError, ValueError, requests.exceptions.Timeout) as exc:
                    LOGGER.exception(exc)
                    continue
                metric_info.update(promql_response.process_single_result())
                service_metrics.append(metric_info)

            host_services[service_description] = {
                "service_metrics": service_metrics,
            }
        return result

    def query_static_endpoint(self, endpoint):
        # type: (str) -> requests.models.Response
        """Query the given endpoint of the Prometheus API expecting a text response

        Args:
            endpoint: Param which contains the Prometheus API endpoint to be queried

        Returns:
            Returns a response object containing the status code and description
        """
        endpoint_request = "%s%s" % (self.server_address, endpoint)
        response = requests.get(endpoint_request)
        response.raise_for_status()
        return response

    def perform_multi_result_promql(self, promql_expression):
        # type: (str) -> Optional[PromQLMultiResponse]
        """Performs a PromQL query where multi metrics response is allowed
        """
        try:
            promql_response = PromQLMultiResponse(self._query_promql(promql_expression))
        except (KeyError, ValueError, requests.exceptions.Timeout) as exc:
            logging.exception(exc)
            return None

        return promql_response

    def _query_promql(self, promql):
        # type: (str) -> List[Dict[str, Any]]

        api_query_expression = "query?query=%s" % quote(promql)
        promql_request = urljoin(self.api_endpoint, api_query_expression)
        result = self._process_json_request(promql_request)["data"]["result"]
        return result

    def _query_json_endpoint(self, endpoint):
        # type: (str) -> Dict[str, Any]
        """Query the given endpoint of the Prometheus API expecting a json response
        """
        endpoint_request = "%s%s" % (self.server_address, endpoint)
        result = self._process_json_request(endpoint_request)
        return result

    def _connected_scrape_targets(self):
        # type: () -> Dict[str, Any]
        """Query and parse the information concerning the connected Scrape Targets
        """
        result = self._query_json_endpoint("/api/v1/targets")
        scrape_targets = self.test(result)
        return scrape_targets

    @staticmethod
    def _process_json_request(request):
        # type: (str) -> Dict[str, Any]

        response = requests.get(request)
        response.raise_for_status()
        return response.json()

    def test(self, result):
        # type: (Dict[str, Any]) -> Dict[str, Any]

        scrape_targets = {}
        scrape_target_names = defaultdict(int)  # type: DefaultDict[str, int]
        for scrape_target_info in result["data"]["activeTargets"]:
            scrape_target_labels = scrape_target_info["labels"]
            job_label = scrape_target_labels["job"]

            if job_label not in scrape_target_names:
                scrape_target_name = job_label
            else:
                scrape_target_name = "%s-%s" % (job_label, scrape_target_names[job_label])

            scrape_target_names[job_label] += 1
            instance_label = scrape_target_labels["instance"]
            scrape_targets.update({
                "%s:%s" % (job_label, instance_label): {
                    "name": scrape_target_name,
                    "attributes": scrape_target_info
                }
            })
        return scrape_targets


class Section:
    """
    An agent section.
    """
    def __init__(self):
        # type: () -> None

        self._content = OrderedDict()  # type: OrderedDict[str, Dict[str, Any]]

    def insert(self, check_data):
        # type: (Dict[str, Any])-> None

        for key, value in check_data.items():
            if key not in self._content:
                self._content[key] = value
            else:
                if isinstance(value, dict):
                    self._content[key].update(value)
                else:
                    raise ValueError('Key %s is already present and cannot be merged' % key)

    def output(self):
        # type: ()-> str

        return json.dumps(self._content)


class PiggybackHost:
    """
    An element that bundles a collection of sections.
    """
    def __init__(self):
        # type: ()-> None

        super(PiggybackHost, self).__init__()
        self._sections = OrderedDict()  # type: OrderedDict[str, Section]

    def get(self, section_name):
        # type: (str)-> Section

        if section_name not in self._sections:
            self._sections[section_name] = Section()
        return self._sections[section_name]

    def output(self):
        # type: () -> List[str]

        data = []
        for name, section in self._sections.items():
            data.append('<<<%s:sep(0)>>>' % name)
            data.append(section.output())
        return data


class PiggybackGroup:
    """
    A group of elements where an element is e.g. a piggyback host.
    """
    def __init__(self):
        # type: () -> None

        self._elements = OrderedDict()  # type: OrderedDict[str, PiggybackHost]

    def get(self, element_name):
        # type: (str)-> PiggybackHost

        if element_name not in self._elements:
            self._elements[element_name] = PiggybackHost()
        return self._elements[element_name]

    def join(self, section_name, pairs):
        # type: (str, Mapping[str, Dict[str, Any]])-> "PiggybackGroup"

        for element_name, data in pairs.items():
            section = self.get(element_name).get(section_name)
            section.insert(data)
        return self

    def output(self, piggyback_prefix=""):
        # type: (str)-> List[str]
        data = []
        for name, element in self._elements.items():
            data.append('<<<<%s>>>>' % (piggyback_prefix + name))
            data.extend(element.output())
            data.append('<<<<>>>>')
        return data


class ApiData:
    """
    Hub for all various metrics coming from different sources including the Prometheus
    Server & the Prometheus Exporters
    """
    def __init__(self, api_client, exporter_options):
        self.api_client = api_client
        self.prometheus_server = PrometheusServer(api_client)
        if "cadvisor" in exporter_options:
            self.cadvisor_exporter = CAdvisorExporter(api_client, exporter_options["cadvisor"])

        if "kube_state" in exporter_options:
            self.kube_state_exporter = KubeStateExporter(
                api_client, exporter_options["kube_state"]["cluster_name"])

    def promql_section(self, custom_services):
        # type: (List[Dict[str, Any]]) -> str

        logging.info("Prometheus PromQl queries")
        e = PiggybackGroup()
        e.join('prometheus_custom',
               self.api_client.perform_specified_promql_queries(custom_services))
        return '\n'.join(e.output())

    def server_info_section(self):
        # type: () -> str

        logging.info('Prometheus Server Info')
        g = PiggybackHost()
        g.get('prometheus_api_server').insert(self.prometheus_server.health())
        return '\n'.join(g.output())

    def scrape_targets_section(self):
        # type: () -> str

        e = PiggybackGroup()
        e.join('prometheus_scrape_target', self.prometheus_server.scrape_targets_health())
        return '\n'.join(e.output())

    def cadvisor_section(self, cadvisor_options):
        # type: (Dict[str, List[str]]) -> Iterator[str]

        self.cadvisor_exporter.update_pod_containers()

        cadvisor_summaries = {
            "diskio": self.cadvisor_exporter.diskstat_summary,
            "cpu": self.cadvisor_exporter.cpu_summary,
            "df": self.cadvisor_exporter.df_summary,
            "if": self.cadvisor_exporter.if_summary,
            "memory_pod": self.cadvisor_exporter.memory_pod_summary,
            "memory_container": self.cadvisor_exporter.memory_container_summary,
        }

        if "diskio" in cadvisor_options:
            yield from self._output_cadvisor_summary("cadvisor_diskstat",
                                                     cadvisor_summaries["diskio"],
                                                     cadvisor_options["diskio"])

        if "cpu" in cadvisor_options:
            yield from self._output_cadvisor_summary("cadvisor_cpu", cadvisor_summaries["cpu"],
                                                     cadvisor_options["cpu"])
        if "df" in cadvisor_options:
            yield from self._output_cadvisor_summary("cadvisor_df", cadvisor_summaries["df"],
                                                     cadvisor_options["df"])
        if "if" in cadvisor_options:
            yield from self._output_cadvisor_summary("cadvisor_if", cadvisor_summaries["if"],
                                                     cadvisor_options["if"])

        if "memory" in cadvisor_options:
            if "pod" in cadvisor_options["memory"]:
                yield from self._output_cadvisor_summary("cadvisor_memory",
                                                         cadvisor_summaries["memory_pod"], ["pod"])

            if "container" in cadvisor_options["memory"]:
                yield from self._output_cadvisor_summary("cadvisor_memory",
                                                         cadvisor_summaries["memory_container"],
                                                         ["container"])

    @staticmethod
    def _output_cadvisor_summary(cadvisor_service_name, retrieve_cadvisor_summary,
                                 summary_group_options):
        # type: (str, Callable, List[str]) -> Iterator[str]

        for group_option in summary_group_options:
            e = PiggybackGroup()
            promql_result = retrieve_cadvisor_summary(group_option)
            piggyback_prefix = "pod_" if group_option == "pod" else ""
            for diskio_element in promql_result:
                e.join(cadvisor_service_name, diskio_element)
            yield '\n'.join(e.output(piggyback_prefix=piggyback_prefix))

    def kube_state_section(self, kube_state_options):
        # type: (Dict[str, List[str]]) -> Iterator[str]

        kube_state_summaries = {
            "cluster_resources": self.kube_state_exporter.cluster_resources_summary,
            "storage_classes": self.kube_state_exporter.storage_classes_summary,
            "namespaces": self.kube_state_exporter.namespaces_summary,
            "cluster_node_info": self.kube_state_exporter.cluster_node_info,
            "node_conditions": self.kube_state_exporter.node_conditions_summary,
            "node_resources": self.kube_state_exporter.node_resources,
            "pod_conditions": self.kube_state_exporter.pod_conditions_summary,
            "pod_container": self.kube_state_exporter.pod_container_summary,
            "pod_resources": self.kube_state_exporter.pod_resources_summary,
            "daemon_pods": self.kube_state_exporter.daemon_pods_summary,
            "services_selector": self.kube_state_exporter.services_selector,
            "services_info": self.kube_state_exporter.services_info,
        }

        if "cluster" in kube_state_options:
            cluster_resources = {
                "service_name": "k8s_resources",
                "summary": kube_state_summaries["cluster_resources"]
            }

            namespaces = {
                "service_name": "k8s_namespaces",
                "summary": kube_state_summaries["namespaces"]
            }

            storage_classes = {
                "service_name": "k8s_namespaces",
                "summary": kube_state_summaries["storage_classes"]
            }
            yield from self._output_kube_state_summary(
                [cluster_resources, namespaces, storage_classes])

        if "nodes" in kube_state_options:
            node_resources = {
                "service_name": "k8s_resources",
                "summary": kube_state_summaries["node_resources"]
            }

            node_conditions = {
                "service_name": "k8s_conditions",
                "summary": kube_state_summaries["node_conditions"]
            }
            yield from self._output_kube_state_summary([node_resources, node_conditions])

        if "pods" in kube_state_options:
            pod_resources = {
                "service_name": "k8s_resources",
                "summary": kube_state_summaries["pod_resources"]
            }

            pod_conditions = {
                "service_name": "k8s_conditions",
                "summary": kube_state_summaries["pod_conditions"]
            }

            pod_container = {
                "service_name": "k8s_pod_container",
                "summary": kube_state_summaries["pod_container"]
            }
            yield from self._output_kube_state_summary(
                [pod_resources, pod_conditions, pod_container], piggyback_prefix="pod_")

        if "services" in kube_state_options:
            services_selector = {
                "service_name": "k8s_service_selector",
                "summary": kube_state_summaries["services_selector"]
            }

            services_info = {
                "service_name": "k8s_service_info",
                "summary": kube_state_summaries["services_info"]
            }

            yield from self._output_kube_state_summary([services_selector, services_info],
                                                       piggyback_prefix="service_")

        if "daemon_sets" in kube_state_options:
            daemon_pods = {
                "service_name": "k8s_daemon_pods",
                "summary": kube_state_summaries["daemon_pods"]
            }
            yield from self._output_kube_state_summary([daemon_pods])

    @staticmethod
    def _output_kube_state_summary(kube_state_services, piggyback_prefix=""):
        # type: (List[Dict[str, Any]], str) -> Iterator[str]
        e = PiggybackGroup()
        for kube_state_service_info in kube_state_services:
            promql_result = kube_state_service_info["summary"]()
            for element in promql_result:
                e.join(kube_state_service_info["service_name"], element)
        yield '\n'.join(e.output(piggyback_prefix=piggyback_prefix))


def _extract_config_args(config):
    server_address = config["host_address"]
    if "port" in config:
        server_address += ":%s" % config["port"]
    return {
        "server_address": server_address,
        "custom_services": config.get("promql_checks", []),
        "exporter_options": config.get("exporter", {})
    }


def _get_host_label(labels):
    return "%s:%s" % (labels["job"], labels["instance"])


class ApiError(Exception):
    pass


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = parse_arguments(argv)

    try:
        config = ast.literal_eval(sys.stdin.read())
        config_args = _extract_config_args(config)
        exporter_options = config_args["exporter_options"]
        # default cases always must be there
        api_client = PrometheusAPI(config_args["server_address"])
        api_data = ApiData(api_client, exporter_options)
        print(api_data.server_info_section())
        print(api_data.scrape_targets_section())
        print(api_data.promql_section(config_args["custom_services"]))

        if "cadvisor" in exporter_options:
            print(*list(api_data.cadvisor_section(exporter_options["cadvisor"])))
        if "kube_state" in exporter_options:
            print(*list(api_data.kube_state_section(exporter_options["kube_state"]["entities"])))
    except Exception as e:
        if args.debug:
            raise
        sys.stderr.write("%s\n" % e)
        return 1
    return 0
