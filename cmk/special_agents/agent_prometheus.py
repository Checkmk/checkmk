#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent for monitoring Prometheus with Checkmk.
"""
import argparse
import ast
import json
import logging
import math
import sys
import time
import traceback
from collections import defaultdict, OrderedDict
from typing import Any, Callable, DefaultDict, Dict, Iterator, List, Mapping, Optional, Tuple, Union
from urllib.parse import quote

import requests

from cmk.special_agents.utils.prometheus import extract_connection_args, generate_api_session

PromQLMetric = Dict[str, Any]

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
    logging.basicConfig(level=lvl, format="%(asctime)s %(levelname)s %(message)s")


def parse_pod_name(labels: Dict[str, str], prepend_namespace: bool = False):
    pod = labels["pod"]
    namespace = labels["namespace"]
    if prepend_namespace:
        return f"{namespace}_{pod}"
    return pod


class FilesystemInfo:
    def __init__(self, name, fstype, mountpoint, size=None, available=None, used=None):
        self.name = name
        self.fstype = fstype
        self.mountpoint = mountpoint
        self.size = size
        self.available = available
        self.used = used

    def set_entity(self, entity_name, value):
        setattr(self, entity_name, value)

    def is_complete(self) -> bool:
        for entity in [a for a in dir(self) if not a.startswith("__")]:
            if not getattr(self, entity):
                return False
        return True


class NodeExporter:
    def __init__(self, api_client):
        self.api_client = api_client

    def df_summary(self) -> Dict[str, List[str]]:

        # value division by 1000 because of Prometheus format
        df_list = [
            ("available", "node_filesystem_avail_bytes/1000"),
            ("size", "node_filesystem_size_bytes/1000"),
            ("used", "(node_filesystem_size_bytes - node_filesystem_free_bytes)/1000"),
        ]
        return self._process_filesystem_info(self._retrieve_filesystem_info(df_list))

    def df_inodes_summary(self) -> Dict[str, List[str]]:

        # no value division for inodes as format already correct
        inodes_list = [
            ("available", "node_filesystem_files_free"),
            ("used", "node_filesystem_files - node_filesystem_files_free"),
            ("size", "node_filesystem_files"),
        ]
        return self._process_filesystem_info(self._retrieve_filesystem_info(inodes_list))

    def _process_filesystem_info(
        self, retrieved_filesystem_info: Dict[str, Dict[str, FilesystemInfo]]
    ) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {}
        for node_name, node_dict in retrieved_filesystem_info.items():
            temp_list: List[str] = []
            for _device, device_info in node_dict.items():
                if device_info.is_complete():
                    device_parsed = "{0.name} {0.fstype} {0.size} {0.used} {0.available} None {0.mountpoint}".format(
                        device_info
                    )
                    temp_list.append(device_parsed)
            if temp_list:
                result[node_name] = temp_list
        return result

    def _retrieve_filesystem_info(
        self, promql_list: List[Tuple[str, str]]
    ) -> Dict[str, Dict[str, FilesystemInfo]]:
        result: Dict[str, Dict[str, FilesystemInfo]] = {}

        for entity_name, promql_query in promql_list:
            for mountpoint_info in self.api_client.perform_multi_result_promql(
                promql_query
            ).promql_metrics:
                labels = mountpoint_info["labels"]
                node = result.setdefault(labels["instance"], {})
                if labels["device"] not in node:
                    node[labels["device"]] = FilesystemInfo(
                        labels["device"], labels["fstype"], labels["mountpoint"]
                    )

                device = node[labels["device"]]
                device.set_entity(entity_name, int(float(mountpoint_info["value"])))
        return result

    def diskstat_summary(self) -> Dict[str, List[str]]:

        diskstat_list = [
            ("reads_completed", "node_disk_reads_completed_total"),
            ("reads_merged", "node_disk_reads_merged_total"),
            ("sectors_read", "node_disk_read_bytes_total/512"),
            ("time_reading", "node_disk_read_time_seconds_total*1000"),
            ("writes_completed", "node_disk_writes_completed_total"),
            ("writes_merged", "node_disk_writes_merged_total"),
            ("sectors_written", "node_disk_written_bytes_total/512"),
            ("time_spent_writing", "node_disk_write_time_seconds_total*1000"),
            ("ios_progress", "node_disk_io_now"),
            ("time_io", "node_disk_io_time_seconds_total*1000"),
            ("weighted_time_io", "node_disk_io_time_weighted_seconds_total"),
            ("discards_completed", "node_disk_io_time_weighted_seconds_total"),
            ("discards_merged", "node_disk_io_time_weighted_seconds_total"),
            ("sectors_discarded", "node_disk_discarded_sectors_total"),
            ("time_discarding", "node_disk_discard_time_seconds_total * 1000"),
        ]

        return self._process_diskstat_info(
            diskstat_list, self._retrieve_diskstat_info(diskstat_list)
        )

    def _process_diskstat_info(
        self,
        diskstat_list: List[Tuple[str, str]],
        diskstat_node_dict: Dict[str, Dict[str, Dict[str, Union[int, str]]]],
    ) -> Dict[str, List[str]]:

        result: Dict[str, List[str]] = {}
        diskstat_entities_list = [diskstat_info[0] for diskstat_info in diskstat_list]
        for node_name, diskstat_info_dict in diskstat_node_dict.items():
            temp_result = ["%d" % time.time()]
            for _device_name, device_info in diskstat_info_dict.items():
                if all(k in device_info for k in diskstat_entities_list):
                    device_parsed = (
                        "None None {device} {reads_completed} {reads_merged} {sectors_read} {time_reading} {writes_completed} "
                        "{writes_merged} {sectors_written} {time_spent_writing} {ios_progress} {time_io} {weighted_time_io} "
                        "{discards_completed} {discards_merged} {sectors_discarded} {time_discarding}".format(
                            **device_info
                        )
                    )
                    temp_result.append(device_parsed)
            if temp_result:
                result[node_name] = temp_result
        return result

    def _retrieve_diskstat_info(
        self, diskstat_list: List[Tuple[str, str]]
    ) -> Dict[str, Dict[str, Dict[str, Union[int, str]]]]:
        result: Dict[str, Dict[str, Dict[str, Union[int, str]]]] = {}
        for entity_name, promql_query in diskstat_list:
            for node_info in self.api_client.perform_multi_result_promql(
                promql_query
            ).promql_metrics:
                node = result.setdefault(node_info["labels"]["instance"], {})
                device = node.setdefault(node_info["labels"]["device"], {})
                if "device" not in device:
                    device["device"] = node_info["labels"]["device"]
                device[entity_name] = int(float(node_info["value"]))
        return result

    def memory_summary(self) -> Dict[str, List[str]]:
        memory_list = [
            ("MemTotal", "node_memory_MemTotal_bytes/1024"),
            ("MemFree", "node_memory_MemFree_bytes/1024"),
            ("MemAvailable", "node_memory_MemAvailable_bytes/1024"),
            ("Buffers", "node_memory_Buffers_bytes/1024"),
            ("Cached", "node_memory_Cached_bytes/1024"),
            ("SwapCached", "node_memory_SwapCached_bytes/1024"),
            ("Active", "node_memory_Active_bytes/1024"),
            ("Inactive", "node_memory_Inactive_bytes/1024"),
            ("Active(anon)", "node_memory_AnonPages_bytes/1024"),
            ("Inactive(anon)", "node_memory_Inactive_anon_bytes/1024"),
            ("Active(file)", "node_memory_Active_file_bytes/1024"),
            ("Inactive(file)", "node_memory_Inactive_bytes/1024"),
            ("Unevictable", "node_memory_Unevictable_bytes/1024"),
            ("Mlocked", "node_memory_Mlocked_bytes/1024"),
            ("SwapTotal", "node_memory_SwapTotal_bytes/1024"),
            ("SwapFree", "node_memory_SwapFree_bytes/1024"),
            ("Dirty", "node_memory_Dirty_bytes/1024"),
            ("Writeback", "node_memory_Writeback_bytes/1024"),
            ("AnonPages", "node_memory_AnonPages_bytes/1024"),
            ("Mapped", "node_memory_AnonPages_bytes/1024"),
            ("Shmem", "node_memory_Shmem_bytes/1024"),
            ("KReclaimable", "node_memory_KReclaimable_bytes/1024"),
            ("Slab", "node_memory_Slab_bytes/1024"),
            ("SReclaimable", "node_memory_SReclaimable_bytes/1024"),
            ("SUnreclaim", "node_memory_SUnreclaim_bytes/1024"),
            ("KernelStack", "node_memory_KernelStack_bytes/1024"),
            ("PageTables", "node_memory_PageTables_bytes/1024"),
            ("NFS_Unstable", "node_memory_NFS_Unstable_bytes/1024"),
            ("Bounce", "node_memory_Bounce_bytes/1024"),
            ("WritebackTmp", "node_memory_WritebackTmp_bytes/1024"),
            ("CommitLimit", "node_memory_CommitLimit_bytes/1024"),
            ("Committed_AS", "node_memory_Committed_AS_bytes/1024"),
            ("VmallocTotal", "node_memory_VmallocTotal_bytes/1024"),
            ("VmallocUsed", "node_memory_VmallocUsed_bytes/1024"),
            ("VmallocChunk", "node_memory_VmallocChunk_bytes/1024"),
            ("Percpu", "node_memory_Percpu_bytes/1024"),
            ("HardwareCorrupted", "node_memory_HardwareCorrupted_bytes/1024"),
            ("AnonHugePages", "node_memory_AnonHugePages_bytes/1024"),
            ("ShmemHugePages", "node_memory_ShmemHugePages_bytes/1024"),
            ("ShmemPmdMapped", "node_memory_ShmemPmdMapped_bytes/1024"),
            ("CmaTotal", "node_memory_CmaTotal_bytes/1024"),
            ("CmaFree", "node_memory_CmaFree_bytes/1024"),
            ("HugePages_Total", "node_memory_HugePages_Total/1024"),
            ("HugePages_Free", "node_memory_HugePages_Free/1024"),
            ("HugePages_Rsvd", "node_memory_HugePages_Rsvd/1024"),
            ("HugePages_Surp", "node_memory_HugePages_Surp/1024"),
            ("Hugepagesize", "node_memory_Hugepagesize_bytes/1024"),
            ("Hugetlb", "node_memory_Hugetlb_bytes/1024"),
            ("DirectMap4k", "node_memory_DirectMap4k_bytes/1024"),
            ("DirectMap2M", "node_memory_DirectMap2M_bytes/1024"),
            ("DirectMap1G", "node_memory_DirectMap1G_bytes/1024"),
        ]
        return self._generate_memory_stats(memory_list)

    def _generate_memory_stats(self, promql_list: List[Tuple[str, str]]) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {}
        for entity_name, promql_query in promql_list:
            promql_result = self.api_client.perform_multi_result_promql(promql_query).promql_metrics
            for node_element in promql_result:
                node_mem = result.setdefault(node_element["labels"]["instance"], [])
                node_mem.append("{}: {} kB".format(entity_name, node_element["value"]))
        return result

    def kernel_summary(self) -> Dict[str, List[str]]:

        kernel_list = [
            ("cpu", "sum by (mode, instance)(node_cpu_seconds_total*100)"),
            ("cpu", "node_cpu_seconds_total*100"),
            ("guest", "sum by (mode, instance)(node_cpu_guest_seconds_total)"),
            ("guest", "node_cpu_guest_seconds_total"),
            ("ctxt", "node_context_switches_total"),
            ("pswpin", "node_vmstat_pswpin"),
            ("pwpout", "node_vmstat_pswpout"),
            ("pgmajfault", "node_vmstat_pgmajfault"),
        ]
        return self._process_kernel_info(self._retrieve_kernel_info(kernel_list))

    @staticmethod
    def _process_kernel_info(
        temp_result: Dict[str, Dict[str, Dict[str, int]]]
    ) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {}
        for node_name, cpu_result in temp_result.items():
            temp: List[str] = ["%d" % time.time()]
            for entity_name, entity_info in cpu_result.items():
                if entity_name.startswith("cpu"):
                    entity_parsed = (
                        "{cpu} {user} {nice} {system} {idle} {iowait} {irq} "
                        "{softirq} {steal} {guest_user} {guest_nice}".format(
                            cpu=entity_name, **entity_info
                        )
                    )
                    temp.append(entity_parsed)
                else:
                    temp.append("{} {}".format(entity_name, entity_info["value"]))
            result[node_name] = temp
        return result

    def _retrieve_kernel_info(
        self, kernel_list: List[Tuple[str, str]]
    ) -> Dict[str, Dict[str, Dict[str, int]]]:
        result: Dict[str, Dict[str, Dict[str, int]]] = {}

        for entity_name, promql_query in kernel_list:
            for device_info in self.api_client.perform_multi_result_promql(
                promql_query
            ).promql_metrics:
                metric_value = int(float(device_info["value"]))
                labels = device_info["labels"]
                node = result.setdefault(labels["instance"], {})
                if entity_name in ("cpu", "guest"):
                    cpu_name = "cpu{}".format(labels["cpu"]) if "cpu" in labels else "cpu"
                    mode_name = (
                        "guest_{}".format(labels["mode"])
                        if entity_name == "guest"
                        else labels["mode"]
                    )
                    node.setdefault(cpu_name, {})[mode_name] = metric_value
                else:
                    node[entity_name] = {"value": metric_value}
        return result


class CAdvisorExporter:
    def __init__(self, api_client, options):
        self.api_client = api_client
        self.container_name_option = options.get("container_id", "short")
        self.pod_containers = {}
        self.container_ids = {}
        self.prepend_namespaces = options.get("prepend_namespaces", True)
        self.namespace_include_patterns = options.get("namespace_include_patterns", [])

    def _pod_name(self, labels):
        return parse_pod_name(labels, self.prepend_namespaces)

    def update_pod_containers(self):
        result: Dict[str, List[str]] = {}
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

    def diskstat_summary(self, group_element: str) -> List[Dict[str, Dict[str, Any]]]:
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

    def cpu_summary(self, group_element: str) -> List[Dict[str, Dict[str, Any]]]:
        # Reference ID: 34923788
        logging.debug("Parsing cAdvisor CPU")
        cpu_info = {
            "cpu_user": "sum by ({{group_element}})(rate(container_cpu_user_seconds_total{exclusion}[5m])*100)",
            "cpu_system": "sum by ({{group_element}})(rate(container_cpu_system_seconds_total{exclusion}[5m])*100)",
        }
        return self._retrieve_formatted_cadvisor_info(cpu_info, group_element)

    def df_summary(self, group_element: str) -> List[Dict[str, Dict[str, Any]]]:
        logging.debug("Parsing cAdvisor df")
        df_info = {
            "df_size": "sum by ({{group_element}})(container_fs_limit_bytes{exclusion})",
            "df_used": "sum by ({{group_element}})(container_fs_usage_bytes{exclusion})",
            "inodes_total": "sum by ({{group_element}})(container_fs_inodes_total{exclusion})",
            "inodes_free": "sum by ({{group_element}})(container_fs_inodes_free{exclusion})",
        }
        return self._retrieve_formatted_cadvisor_info(df_info, group_element)

    def if_summary(self, group_element: str) -> List[Dict[str, Dict[str, Any]]]:
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

    def memory_pod_summary(self, _group_element: str) -> List[Dict[str, Dict[str, Any]]]:
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
        self, memory_info: List[Tuple[str, str]]
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:

        result: Dict[str, Dict[str, Union[str, Dict[str, str]]]] = {}
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

    def _format_for_service(self, pods: Dict) -> List[Dict[str, Dict[str, Any]]]:
        result = []
        for pod_name, pod_info in pods.items():
            pod_formatted = {
                pod_name: {stat_name: [stat_info] for stat_name, stat_info in pod_info.items()}
            }
            result.append(pod_formatted)
        return result

    def _filter_out_incomplete(
        self, pods_memory: Dict[str, Dict[str, Any]], required_stats: List[str]
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
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
        self, pods: Dict[str, Dict[str, Any]], pod_machine_associations: Dict[str, str]
    ) -> Dict[str, Dict[str, Any]]:
        """Add the machine memory limit to pods of their hosting machine"""
        machines_memory = self._retrieve_machines_memory()
        for pod_name, pod_info in pods.items():
            pod_info.update({"memory_machine": machines_memory[pod_machine_associations[pod_name]]})
        return pods

    def _retrieve_machines_memory(self) -> Dict[str, Dict[str, Any]]:
        machine_memory_info = self.api_client.query_promql("machine_memory_bytes")
        machine = {}
        for machine_info in machine_memory_info:
            machine_instance = machine_info.label_value("instance")
            machine[machine_instance] = {
                "value": machine_info.value(),
                "labels": machine_info.labels,
            }
        return machine

    def memory_container_summary(self, _group_element: str) -> List[Dict[str, Dict[str, Any]]]:
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
        self, entity_info: Dict[str, str], group_element: str
    ) -> List[Dict[str, Dict[str, Any]]]:

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
        self, entity_info: Dict[str, str], group_element: str
    ) -> List[Dict[str, Dict[str, Any]]]:

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
                    promql_result, metric_description=entity_name, piggyback_parser=self._pod_name
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


class KubeStateExporter:
    def __init__(self, api_client, options: Dict[str, Any]):
        self.api_client = api_client
        self.cluster_name = options["cluster_name"]
        self.prepend_namespaces = options.get("prepend_namespaces", True)
        self.namespace_include_patterns = options.get("namespace_include_patterns", [])

    def _pod_name(self, labels: Dict[str, str]):
        return parse_pod_name(labels, self.prepend_namespaces)

    # CLUSTER SECTION
    def cluster_resources_summary(self) -> List[Dict[str, Dict[str, Any]]]:
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
        result: Dict[str, Dict[str, Any]] = {}
        for resource_family, resource_type, promql_query in resources_list:
            for cluster_info in self.api_client.query_promql(promql_query):
                cluster_value = (
                    int(cluster_info.value())
                    if resource_type == "pods"
                    else float(cluster_info.value())
                )
                result.setdefault(self.cluster_name, {}).setdefault(resource_family, {})[
                    resource_type
                ] = cluster_value

        # Adding the limits seperately
        if self.cluster_name in result:
            result[self.cluster_name].update(self._cluster_limits())
        return [result]

    def _cluster_limits(self) -> Dict[str, Dict[str, float]]:
        cluster_limit_queries = {
            "cpu": "sum(kube_pod_container_resource_limits_cpu_cores)",
            "memory": "sum(kube_pod_container_resource_limits_memory_bytes)",
        }
        valid_node_limits = self._nodes_limits()
        node_number = int(self.api_client.query_promql("count(kube_node_info)")[0].value())
        cluster_limits = {}
        for limit_type, nodes in valid_node_limits.items():
            if len(nodes) == node_number:
                limit_value = float(
                    self.api_client.query_promql(cluster_limit_queries[limit_type])[0].value()
                )
            else:
                limit_value = float("inf")
            cluster_limits[limit_type] = limit_value
        return {"limits": cluster_limits}

    def storage_classes_summary(self) -> List[Dict[str, Dict[str, Any]]]:
        # namespace independent
        logging.debug("Parsing kube storage classes")
        result: Dict[str, Dict[str, Any]] = {}
        for cluster_storage_info in self.api_client.query_promql("kube_storageclass_info"):
            expected_label_entries = ["reclaimPolicy", "provisioner"]
            if not cluster_storage_info.has_labels(expected_label_entries):
                continue
            storage_dict = result.setdefault(self.cluster_name, {}).setdefault(
                cluster_storage_info.label_value("storageclass"), {}
            )
            storage_dict.update(
                {
                    label: value
                    for label, value in cluster_storage_info.labels.items()
                    if label in expected_label_entries
                }
            )
        return [result]

    def namespaces_summary(self) -> List[Dict[str, Dict[str, Any]]]:
        # Cluster Section
        logging.debug("Parsing kube namespaces summary")
        node_result: Dict[str, Dict[str, Any]] = {}
        for namespace_info in self._perform_query("kube_namespace_status_phase{namespace_filter}"):
            if not namespace_info.has_labels(["namespace", "phase"]) or not int(
                namespace_info.value()
            ):
                continue

            namespace = node_result.setdefault(self.cluster_name, {}).setdefault(
                namespace_info.label_value("namespace"), {}
            )
            namespace["status"] = {"phase": namespace_info.label_value("phase")}
        return [node_result]

    def cluster_node_info(self) -> List[Dict[str, Dict[str, Any]]]:
        logging.debug("Parsing kube cluster node info")
        nodes_list = []
        for node_info in self.api_client.query_promql("kube_node_info"):
            if not node_info.has_labels(["node"]):
                continue
            nodes_list.append(node_info.label_value("node"))
        if not nodes_list:
            return []
        return [{self.cluster_name: {"nodes": nodes_list}}]

    # NODE SECTION

    def node_conditions_summary(self) -> List[Dict[str, Dict[str, Any]]]:
        logging.debug("Parsing kube node conditions")
        # Eventually consider adding PID Pressure in check
        node_conditions_info = {
            "DiskPressure": 'kube_node_status_condition{condition="DiskPressure"}',
            "MemoryPressure": 'kube_node_status_condition{condition="MemoryPressure"}',
            "Ready": 'kube_node_status_condition{condition="Ready"}',
        }
        result: Dict[str, Dict[str, Any]] = {}
        for entity_name, promql_query in node_conditions_info.items():
            # node_result: Dict[str, Dict[str, Any]] = {}
            for node_condition_info in self.api_client.query_promql(promql_query):
                if not node_condition_info.has_labels(["node", "status"]):
                    continue

                if int(node_condition_info.value()):
                    node_result = result.setdefault(node_condition_info.label_value("node"), {})
                    node_result[entity_name] = node_condition_info.label_value(
                        "status"
                    ).capitalize()
        return [result]

    def node_resources(self) -> List[Dict[str, Dict[str, Any]]]:
        logging.debug("Parsing kube node ressources")
        resources_list = [
            ("allocatable", "cpu", "sum by (node)(kube_node_status_allocatable_cpu_cores)"),
            ("allocatable", "memory", "sum by (node)(kube_node_status_allocatable_memory_bytes)"),
            ("allocatable", "pods", "sum by (node)(kube_node_status_allocatable_pods)"),
            ("capacity", "cpu", 'kube_node_status_capacity{resource="cpu"}'),
            ("capacity", "memory", 'kube_node_status_capacity{resource="memory"}'),
            ("capacity", "pods", 'kube_node_status_capacity{resource="pods"}'),
            ("requests", "cpu", "sum by (node)(kube_pod_container_resource_requests_cpu_cores)"),
            (
                "requests",
                "memory",
                "sum by (node)(kube_pod_container_resource_requests_memory_bytes)",
            ),
            ("requests", "pods", "count by (node)(kube_pod_info)"),
            ("limits", "cpu", "sum by (node)(kube_pod_container_resource_limits_cpu_cores)"),
            ("limits", "memory", "sum by (node)(kube_pod_container_resource_limits_memory_bytes)"),
        ]

        node_valid_limits = self._nodes_limits()
        result: Dict[str, Dict[str, Any]] = {}
        for resource_family, resource_type, promql_query in resources_list:
            for node_info in self.api_client.query_promql(promql_query):
                if not node_info.has_labels(["node"]):
                    continue

                if (
                    resource_family == "limits"
                    and node_info.label_value("node") not in node_valid_limits[resource_type]
                ):
                    value = float("inf")
                else:
                    value = (
                        int(node_info.value())
                        if resource_type == "pods"
                        else float(node_info.value())
                    )
                result.setdefault(node_info.label_value("node"), {}).setdefault(
                    resource_family, {}
                )[resource_type] = value
        return [result]

    def _nodes_limits(self) -> Dict[str, List[str]]:
        logging.debug("Parsing kube node limits")
        pods_count_expressions = [
            ("total", "count by (node)(kube_pod_info)"),
            (
                "with_cpu_limits",
                "count by (node)(count by (pod, node)(kube_pod_container_resource_limits_cpu_cores))",
            ),
            (
                "with_memory_limits",
                "count by (node)(count by (pod, node)(kube_pod_container_resource_requests_memory_bytes))",
            ),
        ]

        node_pods: Dict[str, Dict[str, str]] = {}
        for pod_count_type, promql_query in pods_count_expressions:
            for count_result in self.api_client.query_promql(promql_query):
                if not count_result.has_labels(["node"]):
                    continue
                limit_value = count_result.value(default_value=0)
                if limit_value:
                    node_pods.setdefault(count_result.label_value("node"), {})[
                        pod_count_type
                    ] = count_result.value()

        nodes_with_limits: Dict[str, List[str]] = {"memory": [], "cpu": []}

        for node, pods_count in node_pods.items():
            if "total" not in pods_count:
                continue
            entity_total_pods = pods_count["total"]
            if entity_total_pods == pods_count.get("with_cpu_limits"):
                nodes_with_limits["cpu"].append(node)
            if entity_total_pods == pods_count.get("with_memory_limits"):
                nodes_with_limits["memory"].append(node)
        return nodes_with_limits

    # PODS SECTION

    def pod_conditions_summary(self) -> List[Dict[str, Dict[str, Any]]]:
        logging.debug("Parsing kube pod conditions")
        # Unschedulable missing for now
        pod_conditions_info = [
            ("PodScheduled", "kube_pod_status_scheduled{namespace_filter}"),
            ("Ready", "kube_pod_status_ready{namespace_filter}"),
            (
                "ContainersReady",
                "sum by (pod, namespace)(kube_pod_container_status_ready{namespace_filter}) / count by (pod, namespace)(kube_pod_container_status_ready{namespace_filter})",
            ),
        ]
        result = []
        for promql_metric, promql_query in pod_conditions_info:
            promql_result = self._perform_query(promql_query)
            if promql_metric == "ContainersReady":
                for node_result in promql_result:
                    if not node_result.has_labels(["pod", "namespace"]):
                        continue
                    ready_result = {}
                    ready_status = "True" if int(node_result.value()) == 1 else "False"
                    ready_result[self._pod_name(node_result.labels)] = {promql_metric: ready_status}
                    result.append(ready_result)
            else:
                schedule_result: Dict[str, Dict[str, Any]] = {}
                for node_result in promql_result:
                    if not node_result.has_labels(["pod", "condition", "namespace"]):
                        continue
                    if int(node_result.value()):
                        schedule_result.setdefault(self._pod_name(node_result.labels), {})[
                            promql_metric
                        ] = node_result.label_value("condition").capitalize()
                result.append(schedule_result)
        return result

    def pod_container_summary(self) -> List[Dict[str, Dict[str, Any]]]:
        logging.debug("Parsing kube pod container")

        info = [
            ("waiting", "kube_pod_container_status_waiting{namespace_filter}"),
            ("running", "kube_pod_container_status_running{namespace_filter}"),
            ("ready", "kube_pod_container_status_ready{namespace_filter}"),
            ("terminated", "kube_pod_container_status_terminated{namespace_filter}"),
        ]
        pod_container_result = []
        for condition, promql_query in info:
            temp_result: Dict[str, Dict[str, Any]] = {}
            for container_info in self._perform_query(promql_query):
                if not container_info.has_labels(["pod", "container", "namespace"]):
                    continue
                query_value = int(container_info.value())
                metric_dict = temp_result.setdefault(
                    self._pod_name(container_info.labels), {}
                ).setdefault(container_info.label_value("container"), {})

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

    def pod_resources_summary(self) -> List[Dict[str, Dict[str, Any]]]:
        logging.debug("Parsing kube pod resources")

        pods_container_count = {
            self._pod_name(pod_info.labels): pod_info.value()
            for pod_info in self._perform_query(
                "count by (pod, namespace)(kube_pod_container_info{namespace_filter})"
            )
        }

        resources_list = [
            (
                "requests",
                "cpu",
                "sum by (pod, namespace)(kube_pod_container_resource_requests_cpu_cores{namespace_filter})",
            ),
            (
                "requests",
                "memory",
                "kube_pod_container_resource_requests_memory_bytes{namespace_filter}",
            ),
            ("limits", "cpu", "kube_pod_container_resource_limits_cpu_cores{namespace_filter}"),
            (
                "limits",
                "memory",
                "kube_pod_container_resource_limits_memory_bytes{namespace_filter}",
            ),
        ]

        def _process_resources(resource: str, query: str) -> Dict[str, Dict[str, Dict[str, float]]]:
            pod_resources: Dict[str, Dict[str, Dict[str, float]]] = {}
            resource_result = {
                self._pod_name(pod_info.labels): pod_info.value()
                for pod_info in self._perform_query(query)
            }
            for pod in pods_container_count.keys():
                resource_value = 0.0 if pod not in resource_result else resource_result[pod]
                pod_resources.setdefault(pod, {}).setdefault(resource_family, {})[
                    resource
                ] = resource_value
            return pod_resources

        def _process_limits(resource: str, query: str) -> Dict[str, Dict[str, Dict[str, float]]]:
            promql_limits = {
                self._pod_name(pod_info.labels): pod_info.value()
                for pod_info in self._perform_query("sum by (pod, namespace)(%s)" % query)
            }
            promql_counts = {
                self._pod_name(pod_info.labels): pod_info.value()
                for pod_info in self._perform_query("count by (pod, namespace)(%s)" % query)
            }

            pod_limits: Dict[str, Dict[str, Dict[str, float]]] = {}
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

    def daemon_pods_summary(self) -> List[Dict[str, Dict[str, Any]]]:
        logging.debug("Parsing kube daemon pods")

        daemon_pods_info = {
            "number_ready": "kube_daemonset_status_number_ready{namespace_filter}",
            "desired_number_scheduled": "kube_daemonset_status_desired_number_scheduled{namespace_filter}",
            "current_number_scheduled": "kube_daemonset_status_current_number_scheduled{namespace_filter}",
            "updated_number_scheduled": "kube_daemonset_updated_number_scheduled{namespace_filter}",
            "number_available": "kube_daemonset_status_number_available{namespace_filter}",
            "number_unavailable": "kube_daemonset_status_number_unavailable{namespace_filter}",
        }
        result = []
        for entity_name, promql_query in daemon_pods_info.items():
            piggybacked_services = parse_piggybacked_values(
                self._perform_query(promql_query),
                metric_description=entity_name,
                label_as_piggyback_host="daemonset",
                values_as_int=True,
            )
            result.append(piggybacked_services)
        return result

    def services_selector(self) -> List[Dict[str, Dict[str, Any]]]:
        # Cluster Section
        logging.debug("Parsing kube services selection")

        service_label_translation = {
            "label_k8s_app": "k8s-app",
            "label_app_kubernetes_io_name": "app.kubernetes.io/name",
        }
        result: Dict[str, Dict[str, Any]] = {}
        for service_result in self._perform_query("kube_service_labels{namespace_filter}"):
            if not service_result.has_labels(["service"]):
                continue

            service_piggyback = result.setdefault(service_result.label_value("service"), {})
            if len(service_result.labels) == 5:
                service_piggyback["name"] = service_result.label_value("service")
            else:
                for label_key, label_value in service_result.labels.items():
                    if (
                        label_value == service_result.label_value("service")
                        and label_key != "service"
                    ):
                        service_piggyback.update(
                            {service_label_translation.get(label_key, label_key): label_value}
                        )

        return [result]

    def services_info(self) -> List[Dict[str, Dict[str, Any]]]:
        logging.debug("Parsing kube services info")

        result: Dict[str, Dict[str, Any]] = {}
        for service_result in self._perform_query("kube_service_info{namespace_filter}"):
            if not service_result.has_labels(["service", "cluster_ip"]):
                continue
            service_piggyback = result.setdefault(service_result.label_value("service"), {})
            service_piggyback.update(
                {
                    "cluster_ip": service_result.label_value("cluster_ip"),
                    "load_balance_ip": service_result.label_value(
                        "load_balancer_ip", default="null"
                    ),
                }
            )
        return [result]

    def _perform_query(self, promql_query):
        if "namespace_filter" in promql_query:
            if self.namespace_include_patterns:
                namespace_detail = f"{{namespace=~'{'|'.join(self.namespace_include_patterns)}'}}"
                promql_query = promql_query.format(namespace_filter=namespace_detail)
            else:
                promql_query = promql_query.format(namespace_filter="")
        return self.api_client.query_promql(promql_query)

    @staticmethod
    def _retrieve_promql_specific(metrics, entries):
        result = {}
        for entry in entries:
            try:
                promql_value = metrics[entry]
                result[entry] = promql_value
            except KeyError as e:
                logging.debug("Missing PromQl value for %s", e)
        return result


class PromQLResponse:
    def __init__(self, promql_response: List[Dict[str, Any]]) -> None:
        self.response = promql_response

    def process_single_result(self) -> Dict[str, Any]:
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
    def _extract_metric_value(promql_metric: Dict[str, Any]) -> Dict[str, float]:

        if "value" in promql_metric:
            return {"value": promql_metric["value"][1]}
        return {}

    @staticmethod
    def _identify_metric_scrape_target(promql_metric_info: PromQLMetric) -> str:

        promql_metric_labels = promql_metric_info["labels"]
        scrape_target_name = "%s-%s" % (
            promql_metric_labels["job"],
            promql_metric_labels["instance"],
        )
        return scrape_target_name

    @staticmethod
    def _extract_metric_label(promql_metric_info: PromQLMetric, label_key: str) -> str:
        return promql_metric_info["labels"][label_key]

    @staticmethod
    def _extract_metric_labels(
        metric_labels_dict: Dict[str, str], promql_labels_subset: List[str]
    ) -> str:

        metric_labels_holder = ""
        for promql_label in promql_labels_subset:
            metric_labels_holder += metric_labels_dict[promql_label]
        return metric_labels_holder


class PromQLResult:
    """The PromQL result object representation for internal usage"""

    def __init__(self, raw_response: Dict[str, Any]):
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

    def label_value(self, key: str, default=None) -> str:
        return self.labels.get(key, default)

    def has_labels(self, keys: List[str]) -> bool:
        for key in keys:
            if key not in self.labels:
                return False
        return True

    def value(
        self, default_value: Optional[Union[float, int]] = None, as_string: bool = False
    ) -> float:
        try:
            value = self.internal_values[1]
            if as_string:
                return value
            return float(value)
        except (KeyError, AttributeError) as e:
            if default_value:
                return default_value
            raise e


def parse_piggybacked_values(
    promql_results: List[PromQLResult],
    metric_description: str,
    label_as_piggyback_host: str,
    values_as_int: bool = False,
) -> Dict[str, Dict[str, Union[int, float]]]:

    result: Dict[str, Dict[str, Union[int, float]]] = {}
    for promql_result in promql_results:
        piggyback_host = promql_result.label_value(label_as_piggyback_host)
        if piggyback_host == "":
            continue

        if values_as_int:
            metric_value: Union[int, float] = int(promql_result.value())
        else:
            metric_value = promql_result.value()

        result.setdefault(piggyback_host, {})[metric_description] = metric_value
    return result


def parse_piggybacked_services(
    promql_results: List[PromQLResult],
    metric_description: str,
    label_as_piggyback_host: Optional[str] = None,
    piggyback_parser: Optional[Callable] = None,
) -> Dict[str, Dict[str, List[Dict[str, float]]]]:
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
    result: Dict[str, Dict[str, List[Dict[str, float]]]] = {}
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

    def __init__(self, promql_response: List[Dict[str, Any]]) -> None:
        super().__init__(promql_response)
        self.labels_overall_frequencies: Dict[str, Dict[str, float]] = {}
        self.promql_metrics = self._process_multi_result()

    def get_piggybacked_services(
        self, metric_description: str, promql_label_for_piggyback: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Process PromQL response to get "piggybacked" services

        Args:
            metric_description: Name of Metric
            promql_label_for_piggyback: PromQL label used to determine the piggyback host

        Returns:
            Dict: where key is the piggyback host and the value is a dict containing the services metrics

        """
        result: Dict[str, Dict[str, Any]] = {}
        for promql_metric in self.promql_metrics:
            if promql_label_for_piggyback is not None:
                piggyback_host = self._extract_metric_label(
                    promql_metric, promql_label_for_piggyback
                )
                promql_metric.update({"host_selection_label": promql_label_for_piggyback})
            else:
                piggyback_host = self._identify_metric_scrape_target(promql_metric)

            if piggyback_host == "":
                continue

            result.setdefault(piggyback_host, {}).setdefault(metric_description, []).append(
                promql_metric
            )
        return result

    def get_value_only_piggybacked_services(
        self,
        metric_description: str,
        promql_label_for_piggyback: Optional[str] = None,
        number_convert: str = "float",
    ) -> Dict[str, Dict[str, Union[int, float]]]:

        result: Dict[str, Dict[str, Union[int, float]]] = {}
        for promql_metric in self.promql_metrics:
            if promql_label_for_piggyback is not None:
                piggyback_host = self._extract_metric_label(
                    promql_metric, promql_label_for_piggyback
                )
            else:
                piggyback_host = self._identify_metric_scrape_target(promql_metric)

            if piggyback_host == "":
                continue

            if number_convert == "int":
                metric_value: Union[int, float] = int(promql_metric["value"])
            elif number_convert == "float":
                metric_value = float(promql_metric["value"])
            result.setdefault(piggyback_host, {})[metric_description] = metric_value
        return result

    def get_value_only_dict(self, key_label: str) -> Dict[str, float]:

        result = {}
        for promql_metric in self.promql_metrics:
            result[self._extract_metric_label(promql_metric, key_label)] = float(
                promql_metric["value"]
            )
        return result

    def get_piggybacked_services_with_least_labels(
        self, metric_description: str, promql_label_for_piggyback: Optional[str] = None
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Piggybacked services with subset of unique making PromQL labels

        Args:
            metric_description: Name of Metric
            promql_label_for_piggyback: PromQL label used to determine the piggyback host

        Returns:
            Piggybacked services dict which additionally includes the subset of PromQL labels

        """
        piggybacked_services = self.get_piggybacked_services(
            metric_description, promql_label_for_piggyback
        )
        unique_least_promql_labels = self._get_unique_least_promql_labels()
        for _piggyback_host_name, service_info in piggybacked_services.items():
            service_info.setdefault("unique_labels", {})[
                metric_description
            ] = unique_least_promql_labels
        return piggybacked_services

    def _process_multi_result(self) -> List[PromQLMetric]:

        result: List[PromQLMetric] = []
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

    def _update_labels_overall_frequencies(self, metric_labels: Dict[str, str]) -> None:

        for promql_specific_label, metric_specific_label in metric_labels.items():
            promql_specific_label_frequencies = self.labels_overall_frequencies.setdefault(
                promql_specific_label, defaultdict(int)
            )
            promql_specific_label_frequencies[metric_specific_label] += 1
            promql_specific_label_frequencies["total_count"] += 1

    def _get_unique_least_promql_labels(self) -> List[str]:

        information_gains = self._determine_promql_labels_information_gains()
        promql_labels_by_relevance = PromQLMultiResponse._extract_promql_labels_by_relevance(
            information_gains
        )
        unique_least_labels = self._determine_unique_least_labels_combination(
            promql_labels_by_relevance
        )
        return unique_least_labels

    def _determine_promql_labels_information_gains(self) -> Dict[str, float]:
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
            information_gains[promql_label] = sum(
                [
                    PromQLMultiResponse._determine_single_entropy(metric_label_probability)
                    for metric_label_probability in metric_label_probabilities
                ]
            )
        return information_gains

    @staticmethod
    def _determine_single_entropy(p: float) -> float:

        if p > 1.0 or p <= 0.0:
            return 0
        return -p * math.log2(p)

    @staticmethod
    def _extract_promql_labels_by_relevance(information_gains: Dict[str, float]) -> List[str]:
        """Creates a list with the PromQL labels sorted by information gain relevance"""
        promql_labels_by_relevance = [
            a for a, b in sorted(information_gains.items(), key=lambda x: x[1], reverse=True)
        ]
        if all(label in promql_labels_by_relevance for label in ("pod", "pod_name")):
            promql_labels_by_relevance.remove("pod_name")
        return promql_labels_by_relevance

    def _determine_unique_least_labels_combination(
        self, promql_labels_by_relevance: List[str]
    ) -> List[str]:
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

    def _verify_all_unique(self, promql_labels_subset: List[str]) -> bool:

        seen_labels_combination: List[str] = []
        for promql_metric in self.promql_metrics:
            metric_labels_dict = promql_metric["labels"]
            metric_labels_subset = PromQLMultiResponse._extract_metric_labels(
                metric_labels_dict, promql_labels_subset
            )

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

    def __init__(self, api_client: "PrometheusAPI") -> None:
        self.api_client = api_client

    def build_info(self):
        result: Dict[str, Any] = {}
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

    def scrape_targets_health(self) -> Dict[str, Dict[str, Any]]:
        result = {}
        for scrape_target_name, attributes in self.api_client.scrape_targets_attributes():
            result[scrape_target_name] = {
                "health": attributes["health"],
                "lastScrape": attributes["lastScrape"],
                "labels": attributes["labels"],
            }
        return result

    def health(self) -> Dict[str, Any]:

        response = self.api_client.query_static_endpoint("/-/healthy")
        return {"status_code": response.status_code, "status_text": response.reason}

    def _prometheus_version(self) -> str:
        promql_result = self.api_client.perform_multi_result_promql("prometheus_build_info")

        if promql_result is None:
            raise ApiError("Missing Prometheus version")

        try:
            version = promql_result.promql_metrics[0]["labels"]["version"]
        except IndexError:
            return ""

        if len(promql_result.promql_metrics) > 1:
            for prometheus_instance in promql_result.promql_metrics:
                if prometheus_instance["labels"]["version"] != version:
                    raise ApiError(
                        "Multiple Prometheus instances with different versions connected"
                    )

        return version

    def _scrape_targets(self) -> Dict[str, Any]:
        down_targets = []
        promql_result = self.api_client.perform_multi_result_promql("up")

        if promql_result is None:
            raise ApiError("Missing Scrape Targets information")

        scrape_targets = promql_result.promql_metrics
        for scrape_target in scrape_targets:
            if not scrape_target["value"]:
                down_targets.append(scrape_target["labels"]["job"])
        return {"targets_number": len(scrape_targets), "down_targets": down_targets}

    def _reload_config_status(self) -> Optional[str]:
        runtime_details = self._runtime_info()
        return runtime_details.get("reloadConfigSuccess")

    def _storage_retention(self) -> Optional[str]:
        runtime_details = self._runtime_info()
        return runtime_details.get("storageRetention")

    def _runtime_info(self) -> Dict[str, Any]:
        try:
            endpoint_result = self.api_client.query_static_endpoint("/api/v1/status/runtimeinfo")
        except requests.exceptions.HTTPError:  # This endpoint is only available from v2.14
            return {}

        return json.loads(endpoint_result.content)["data"]


class PrometheusAPI:
    """
    Realizes communication with the Prometheus API
    """

    def __init__(self, session) -> None:
        self.session = session
        self.scrape_targets_dict = self._connected_scrape_targets()

    def scrape_targets_attributes(self) -> Iterator[Tuple[str, Dict[str, Any]]]:
        """Format the scrape_targets_dict for information processing

        Returns:
              Tuples consisting of the Scrape Target name and its general attributes. The
              job-instance labels combination is hereby omitted

        """
        for _scrape_target_label, info in self.scrape_targets_dict.items():
            scrape_target_name = info["name"]
            yield scrape_target_name, info["attributes"]

    def perform_specified_promql_queries(
        self, custom_services: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
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
        result: Dict[str, Dict[str, Any]] = {}
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

    def perform_multi_result_promql(self, promql_expression: str) -> Optional[PromQLMultiResponse]:
        """Performs a PromQL query where multi metrics response is allowed"""
        try:
            promql_response = PromQLMultiResponse(self._perform_promql_query(promql_expression))
        except (KeyError, ValueError, requests.exceptions.Timeout) as exc:
            logging.exception(exc)
            return None

        return promql_response

    def query_promql(self, promql: str) -> List[PromQLResult]:
        try:
            return [PromQLResult(info) for info in self._perform_promql_query(promql)]
        except (KeyError, ValueError, requests.exceptions.Timeout) as exc:
            logging.exception(exc)
            return []

    def _perform_promql_query(self, promql: str) -> List[Dict[str, Any]]:
        api_query_expression = "query?query=%s" % quote(promql)
        result = self._process_json_request(api_query_expression)["data"]["result"]
        return result

    def _query_json_endpoint(self, endpoint: str) -> Dict[str, Any]:
        """Query the given endpoint of the Prometheus API expecting a json response"""
        result = self._process_json_request(endpoint)
        return result

    def _connected_scrape_targets(self) -> Dict[str, Any]:
        """Query and parse the information concerning the connected Scrape Targets"""
        result = self._query_json_endpoint("targets")
        scrape_targets = self.test(result)
        return scrape_targets

    def _process_json_request(self, api_request: str) -> Dict[str, Any]:
        response = self.session.get(api_request)
        response.raise_for_status()
        return response.json()

    def test(self, result: Dict[str, Any]) -> Dict[str, Any]:

        scrape_targets = {}
        scrape_target_names: DefaultDict[str, int] = defaultdict(int)
        for scrape_target_info in result["data"]["activeTargets"]:
            scrape_target_labels = scrape_target_info["labels"]
            job_label = scrape_target_labels["job"]

            if job_label not in scrape_target_names:
                scrape_target_name = job_label
            else:
                scrape_target_name = "%s-%s" % (job_label, scrape_target_names[job_label])

            scrape_target_names[job_label] += 1
            instance_label = scrape_target_labels["instance"]
            scrape_targets.update(
                {
                    "%s:%s"
                    % (job_label, instance_label): {
                        "name": scrape_target_name,
                        "attributes": scrape_target_info,
                    }
                }
            )
        return scrape_targets


class Section:
    """
    An agent section.
    """

    def __init__(self) -> None:

        self._content: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    def insert(self, check_data: Dict[str, Any]) -> None:

        for key, value in check_data.items():
            if key not in self._content:
                self._content[key] = value
            else:
                if isinstance(value, dict):
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

    def output(self) -> List[str]:

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

    def join(self, section_name: str, pairs: Mapping[str, Dict[str, Any]]) -> "PiggybackGroup":

        for element_name, data in pairs.items():
            section = self.get(element_name).get(section_name)
            section.insert(data)
        return self

    def output(self, piggyback_prefix: str = "") -> List[str]:
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

    def __init__(self, api_client, exporter_options):
        self.api_client = api_client
        self.prometheus_server = PrometheusServer(api_client)
        if "cadvisor" in exporter_options:
            self.cadvisor_exporter = CAdvisorExporter(api_client, exporter_options["cadvisor"])

        if "kube_state" in exporter_options:
            self.kube_state_exporter = KubeStateExporter(
                api_client,
                exporter_options["kube_state"],
            )

        if "node_exporter" in exporter_options:
            self.node_exporter = NodeExporter(api_client)

    def prometheus_build_section(self) -> str:
        e = PiggybackHost()
        e.get("prometheus_build").insert(self.prometheus_server.build_info())
        return "\n".join(e.output())

    def promql_section(self, custom_services: List[Dict[str, Any]]) -> str:
        logging.info("Prometheus PromQl queries")
        e = PiggybackGroup()
        e.join(
            "prometheus_custom", self.api_client.perform_specified_promql_queries(custom_services)
        )
        return "\n".join(e.output())

    def server_info_section(self) -> str:

        logging.info("Prometheus Server Info")
        g = PiggybackHost()
        g.get("prometheus_api_server").insert(self.prometheus_server.health())
        return "\n".join(g.output())

    def scrape_targets_section(self) -> str:

        e = PiggybackGroup()
        e.join("prometheus_scrape_target", self.prometheus_server.scrape_targets_health())
        return "\n".join(e.output())

    def cadvisor_section(self, cadvisor_options: Dict[str, Any]) -> Iterator[str]:

        grouping_option = {"both": ["container", "pod"], "container": ["container"], "pod": ["pod"]}

        self.cadvisor_exporter.update_pod_containers()

        cadvisor_summaries = {
            "diskio": self.cadvisor_exporter.diskstat_summary,
            "cpu": self.cadvisor_exporter.cpu_summary,
            "df": self.cadvisor_exporter.df_summary,
            "if": self.cadvisor_exporter.if_summary,
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
                "cadvisor_cpu", cadvisor_summaries["cpu"], grouping_option[cadvisor_grouping]
            )
        if "df" in entities:
            yield from self._output_cadvisor_summary(
                "cadvisor_df", cadvisor_summaries["df"], grouping_option[cadvisor_grouping]
            )
        if "if" in entities:
            yield from self._output_cadvisor_summary(
                "cadvisor_if", cadvisor_summaries["if"], grouping_option[cadvisor_grouping]
            )

        if "memory" in entities:
            if "pod" in grouping_option[cadvisor_grouping]:
                yield from self._output_cadvisor_summary(
                    "cadvisor_memory", cadvisor_summaries["memory_pod"], ["pod"]
                )

            if "container" in grouping_option[cadvisor_grouping]:
                yield from self._output_cadvisor_summary(
                    "cadvisor_memory", cadvisor_summaries["memory_container"], ["container"]
                )

    @staticmethod
    def _output_cadvisor_summary(
        cadvisor_service_name: str,
        retrieve_cadvisor_summary: Callable,
        summary_group_options: List[str],
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

    def kube_state_section(self, kube_state_options: Dict[str, List[str]]) -> Iterator[str]:

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
                "summary": kube_state_summaries["cluster_resources"],
            }

            namespaces = {
                "service_name": "k8s_namespaces",
                "summary": kube_state_summaries["namespaces"],
            }

            storage_classes = {
                "service_name": "k8s_namespaces",
                "summary": kube_state_summaries["storage_classes"],
            }

            yield from self._output_kube_state_summary(
                [cluster_resources, namespaces, storage_classes]
            )

        if "nodes" in kube_state_options:
            node_resources = {
                "service_name": "k8s_resources",
                "summary": kube_state_summaries["node_resources"],
            }

            node_conditions = {
                "service_name": "k8s_conditions",
                "summary": kube_state_summaries["node_conditions"],
            }
            yield from self._output_kube_state_summary([node_resources, node_conditions])

        if "pods" in kube_state_options:
            pod_resources = {
                "service_name": "k8s_resources",
                "summary": kube_state_summaries["pod_resources"],
            }

            pod_conditions = {
                "service_name": "k8s_conditions",
                "summary": kube_state_summaries["pod_conditions"],
            }

            pod_container = {
                "service_name": "k8s_pod_container",
                "summary": kube_state_summaries["pod_container"],
            }
            yield from self._output_kube_state_summary(
                [pod_resources, pod_conditions, pod_container], piggyback_prefix="pod_"
            )

        if "services" in kube_state_options:
            services_selector = {
                "service_name": "k8s_service_selector",
                "summary": kube_state_summaries["services_selector"],
            }

            services_info = {
                "service_name": "k8s_service_info",
                "summary": kube_state_summaries["services_info"],
            }

            yield from self._output_kube_state_summary(
                [services_selector, services_info], piggyback_prefix="service_"
            )

        if "daemon_sets" in kube_state_options:
            daemon_pods = {
                "service_name": "k8s_daemon_pods",
                "summary": kube_state_summaries["daemon_pods"],
            }
            yield from self._output_kube_state_summary([daemon_pods])

    @staticmethod
    def _output_kube_state_summary(
        kube_state_services: List[Dict[str, Any]], piggyback_prefix: str = ""
    ) -> Iterator[str]:
        group = PiggybackGroup()
        for kube_state_service_info in kube_state_services:
            promql_result = kube_state_service_info["summary"]()
            for element in promql_result:
                group.join(kube_state_service_info["service_name"], element)
        yield "\n".join(group.output(piggyback_prefix=piggyback_prefix))

    def node_exporter_section(
        self, node_options: Dict[str, Union[List[str], str]]
    ) -> Iterator[str]:
        node_entities = node_options["entities"]
        if "host_mapping" in node_options:
            host_mapping = [node_options["host_mapping"]]
        else:
            host_mapping = ["localhost", node_options["host_address"], node_options["host_name"]]

        if "df" in node_entities:
            df_result = self.node_exporter.df_summary()
            df_inodes_result = self.node_exporter.df_inodes_summary()

            for node_name, node_df_info in df_result.items():
                piggyback_host_name = self._get_node_piggyback_host_name(node_name)
                if node_df_info and node_name in df_inodes_result:
                    df_section = [
                        "<<<df>>>",
                        "\n".join(node_df_info),
                        "<<<df>>>",
                        "[df_inodes_start]",
                        "\n".join(df_inodes_result[node_name]),
                        "[df_inodes_end]\n",
                    ]

                    if piggyback_host_name not in host_mapping:
                        df_section.insert(0, "<<<<%s>>>>" % piggyback_host_name)
                        df_section.append("<<<<>>>>\n")
                    else:
                        df_section.append("\n")
                    yield "\n".join(df_section)

        if "diskstat" in node_entities:
            diskstat_result = self.node_exporter.diskstat_summary()
            if diskstat_result:
                yield from self._output_node_section("diskstat", diskstat_result, host_mapping)

        if "mem" in node_entities:
            mem_result = self.node_exporter.memory_summary()
            if mem_result:
                yield from self._output_node_section("mem", mem_result, host_mapping)

        if "kernel" in node_entities:
            kernel_result = self.node_exporter.kernel_summary()
            if kernel_result:
                yield from self._output_node_section("kernel", kernel_result, host_mapping)

    def _output_node_section(self, service_name, entity_result, host_mapping):
        for node_name, node_entity_summary in entity_result.items():
            if len(node_entity_summary) > 1:
                piggyback_host_name = self._get_node_piggyback_host_name(node_name)
                entity_section = ["<<<%s>>>" % service_name, "\n".join(node_entity_summary)]

                if piggyback_host_name not in host_mapping:
                    entity_section.insert(0, "<<<<%s>>>>" % piggyback_host_name)
                    entity_section.append("<<<<>>>>\n")
                else:
                    entity_section.append("\n")
                yield "\n".join(entity_section)

    @staticmethod
    def _get_node_piggyback_host_name(node_name):
        return node_name.split(":")[0]


def _extract_config_args(config: Dict[str, Any]) -> Dict[str, Any]:
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
                {"host_address": config["host_address"], "host_name": config["host_name"]}
            )
            exporter_options[exporter_name] = exporter_info
        elif exporter_name == "kube_state":
            exporter_info.update(
                {"prepend_namespaces": exporter_info["prepend_namespaces"] != "omit_namespace"}
            )
            exporter_options[exporter_name] = exporter_info
        else:
            exporter_options[exporter_name] = exporter_info

    return {
        "custom_services": config.get("promql_checks", []),
        "exporter_options": exporter_options,
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
        session = generate_api_session(extract_connection_args(config))
        exporter_options = config_args["exporter_options"]
        # default cases always must be there
        api_client = PrometheusAPI(session)
        api_data = ApiData(api_client, exporter_options)
        print(api_data.prometheus_build_section())
        print(api_data.promql_section(config_args["custom_services"]))
        if "cadvisor" in exporter_options:
            print(*list(api_data.cadvisor_section(exporter_options["cadvisor"])), sep="\n")
        if "kube_state" in exporter_options:
            print(
                *list(api_data.kube_state_section(exporter_options["kube_state"]["entities"])),
                sep="\n",
            )
        if "node_exporter" in exporter_options:
            print(
                *list(api_data.node_exporter_section(exporter_options["node_exporter"])), sep="\n"
            )

    except Exception as e:
        if args.debug:
            raise
        logging.debug(traceback.format_exc())
        sys.stderr.write("%s\n" % e)
        return 1
    return 0
