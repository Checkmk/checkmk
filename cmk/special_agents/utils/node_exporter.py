#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
import typing
from collections.abc import Mapping

from typing_extensions import NotRequired


class PromQLMetric(typing.TypedDict):
    value: float
    labels: Mapping[str, str]
    host_selection_label: NotRequired[str]


class PromQLGetter(typing.Protocol):
    def __call__(self, promql_expression: str) -> list[PromQLMetric]:
        ...


class FilesystemInfo:
    def __init__(  # type:ignore[no-untyped-def]
        self, name, fstype, mountpoint, size=None, available=None, used=None
    ) -> None:
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
    def __init__(self, get_promql: PromQLGetter) -> None:
        self.get_promql = get_promql

    def df_summary(self) -> dict[str, list[str]]:

        # value division by 1000 because of Prometheus format
        df_list = [
            ("available", "node_filesystem_avail_bytes/1000"),
            ("size", "node_filesystem_size_bytes/1000"),
            ("used", "(node_filesystem_size_bytes - node_filesystem_free_bytes)/1000"),
        ]
        return self._process_filesystem_info(self._retrieve_filesystem_info(df_list))

    def df_inodes_summary(self) -> dict[str, list[str]]:

        # no value division for inodes as format already correct
        inodes_list = [
            ("available", "node_filesystem_files_free"),
            ("used", "node_filesystem_files - node_filesystem_files_free"),
            ("size", "node_filesystem_files"),
        ]
        return self._process_filesystem_info(self._retrieve_filesystem_info(inodes_list))

    def _process_filesystem_info(
        self, retrieved_filesystem_info: dict[str, dict[str, FilesystemInfo]]
    ) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for node_name, node_dict in retrieved_filesystem_info.items():
            temp_list: list[str] = []
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
        self, promql_list: list[tuple[str, str]]
    ) -> dict[str, dict[str, FilesystemInfo]]:
        result: dict[str, dict[str, FilesystemInfo]] = {}

        for entity_name, promql_query in promql_list:
            for mountpoint_info in self.get_promql(promql_query):
                labels = mountpoint_info["labels"]
                node = result.setdefault(labels["instance"], {})
                if labels["device"] not in node:
                    node[labels["device"]] = FilesystemInfo(
                        labels["device"], labels["fstype"], labels["mountpoint"]
                    )

                device = node[labels["device"]]
                device.set_entity(entity_name, int(float(mountpoint_info["value"])))
        return result

    def diskstat_summary(self) -> dict[str, list[str]]:

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
        diskstat_list: list[tuple[str, str]],
        diskstat_node_dict: dict[str, dict[str, dict[str, int | str]]],
    ) -> dict[str, list[str]]:

        result: dict[str, list[str]] = {}
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
        self, diskstat_list: list[tuple[str, str]]
    ) -> dict[str, dict[str, dict[str, int | str]]]:
        result: dict[str, dict[str, dict[str, int | str]]] = {}
        for entity_name, promql_query in diskstat_list:
            for node_info in self.get_promql(promql_query):
                node = result.setdefault(node_info["labels"]["instance"], {})
                device = node.setdefault(node_info["labels"]["device"], {})
                if "device" not in device:
                    device["device"] = node_info["labels"]["device"]
                device[entity_name] = int(float(node_info["value"]))
        return result

    def memory_summary(self) -> dict[str, list[str]]:
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

    def _generate_memory_stats(self, promql_list: list[tuple[str, str]]) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for entity_name, promql_query in promql_list:
            for node_element in self.get_promql(promql_query):
                node_mem = result.setdefault(node_element["labels"]["instance"], [])
                node_mem.append("{}: {} kB".format(entity_name, node_element["value"]))
        return result

    def kernel_summary(self) -> dict[str, list[str]]:

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
        temp_result: dict[str, dict[str, dict[str, int]]]
    ) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for node_name, cpu_result in temp_result.items():
            temp: list[str] = ["%d" % time.time()]
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
        self, kernel_list: list[tuple[str, str]]
    ) -> dict[str, dict[str, dict[str, int]]]:
        result: dict[str, dict[str, dict[str, int]]] = {}

        for entity_name, promql_query in kernel_list:
            for device_info in self.get_promql(promql_query):
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
