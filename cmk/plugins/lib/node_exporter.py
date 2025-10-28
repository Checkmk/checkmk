#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
import time
import typing
from collections.abc import Mapping
from typing import NotRequired

import pydantic

SectionStr = typing.NewType("SectionStr", str)


class PromQLMetric(typing.TypedDict):
    value: float
    labels: Mapping[str, str]
    host_selection_label: NotRequired[str]


class PromQLGetter(typing.Protocol):
    def __call__(self, promql_expression: str) -> list[PromQLMetric]: ...


class NodeExporterQuery(enum.StrEnum):
    # node_boot_time_seconds: btime for /proc/stats
    # node_time_seconds: system time of the node, equal to btime + uptime from /proc/uptime
    node_uptime_seconds = "(node_time_seconds - node_boot_time_seconds)"
    # From /proc/meminfo
    node_memory_MemTotal_kibibytes = "node_memory_MemTotal_bytes/1024"
    node_memory_MemFree_kibibytes = "node_memory_MemFree_bytes/1024"
    node_memory_MemAvailable_kibibytes = "node_memory_MemAvailable_bytes/1024"
    node_memory_Buffers_kibibytes = "node_memory_Buffers_bytes/1024"
    node_memory_Cached_kibibytes = "node_memory_Cached_bytes/1024"
    node_memory_SwapCached_kibibytes = "node_memory_SwapCached_bytes/1024"
    node_memory_Active_kibibytes = "node_memory_Active_bytes/1024"
    node_memory_Inactive_kibibytes = "node_memory_Inactive_bytes/1024"
    node_memory_Active_anon_kibibytes = "node_memory_Active_anon_bytes/1024"
    node_memory_Inactive_anon_kibibytes = "node_memory_Inactive_anon_bytes/1024"
    node_memory_Active_file_kibibytes = "node_memory_Active_file_bytes/1024"
    node_memory_Inactive_file_kibibytes = "node_memory_Inactive_file_bytes/1024"
    node_memory_Unevictable_kibibytes = "node_memory_Unevictable_bytes/1024"
    node_memory_Mlocked_kibibytes = "node_memory_Mlocked_bytes/1024"
    node_memory_SwapTotal_kibibytes = "node_memory_SwapTotal_bytes/1024"
    node_memory_SwapFree_kibibytes = "node_memory_SwapFree_bytes/1024"
    node_memory_Dirty_kibibytes = "node_memory_Dirty_bytes/1024"
    node_memory_Writeback_kibibytes = "node_memory_Writeback_bytes/1024"
    node_memory_AnonPages_kibibytes = "node_memory_AnonPages_bytes/1024"
    node_memory_Mapped_kibibytes = "node_memory_Mapped_bytes/1024"
    node_memory_Shmem_kibibytes = "node_memory_Shmem_bytes/1024"
    node_memory_KReclaimable_kibibytes = "node_memory_KReclaimable_bytes/1024"
    node_memory_Slab_kibibytes = "node_memory_Slab_bytes/1024"
    node_memory_SReclaimable_kibibytes = "node_memory_SReclaimable_bytes/1024"
    node_memory_SUnreclaim_kibibytes = "node_memory_SUnreclaim_bytes/1024"
    node_memory_KernelStack_kibibytes = "node_memory_KernelStack_bytes/1024"
    node_memory_PageTables_kibibytes = "node_memory_PageTables_bytes/1024"
    node_memory_NFS_Unstable_kibibytes = "node_memory_NFS_Unstable_bytes/1024"
    node_memory_Bounce_kibibytes = "node_memory_Bounce_bytes/1024"
    node_memory_WritebackTmp_kibibytes = "node_memory_WritebackTmp_bytes/1024"
    node_memory_CommitLimit_kibibytes = "node_memory_CommitLimit_bytes/1024"
    node_memory_Committed_AS_kibibytes = "node_memory_Committed_AS_bytes/1024"
    node_memory_VmallocTotal_kibibytes = "node_memory_VmallocTotal_bytes/1024"
    node_memory_VmallocUsed_kibibytes = "node_memory_VmallocUsed_bytes/1024"
    node_memory_VmallocChunk_kibibytes = "node_memory_VmallocChunk_bytes/1024"
    node_memory_Percpu_kibibytes = "node_memory_Percpu_bytes/1024"
    node_memory_HardwareCorrupted_kibibytes = "node_memory_HardwareCorrupted_bytes/1024"
    node_memory_AnonHugePages_kibibytes = "node_memory_AnonHugePages_bytes/1024"
    node_memory_ShmemHugePages_kibibytes = "node_memory_ShmemHugePages_bytes/1024"
    node_memory_ShmemPmdMapped_kibibytes = "node_memory_ShmemPmdMapped_bytes/1024"
    node_memory_CmaTotal_kibibytes = "node_memory_CmaTotal_bytes/1024"
    node_memory_CmaFree_kibibytes = "node_memory_CmaFree_bytes/1024"
    node_memory_HugePages_Total = "node_memory_HugePages_Total"
    node_memory_HugePages_Free = "node_memory_HugePages_Free"
    node_memory_HugePages_Rsvd = "node_memory_HugePages_Rsvd"
    node_memory_HugePages_Surp = "node_memory_HugePages_Surp"
    node_memory_Hugepagesize_kibibytes = "node_memory_Hugepagesize_bytes/1024"
    node_memory_Hugetlb_kibibytes = "node_memory_Hugetlb_bytes/1024"
    node_memory_DirectMap4k_kibibytes = "node_memory_DirectMap4k_bytes/1024"
    node_memory_DirectMap2M_kibibytes = "node_memory_DirectMap2M_bytes/1024"
    node_memory_DirectMap1G_kibibytes = "node_memory_DirectMap1G_bytes/1024"
    # From /proc/loadavg
    node_load1 = "node_load1"
    node_load5 = "node_load5"
    node_load15 = "node_load15"
    node_processes_threads = "node_processes_threads"  # Thread count
    # Example rule from node exporter
    instance_node_cpus_count = 'count(node_cpu_seconds_total{mode="idle"}) without (cpu,mode)'
    # From /proc/sys/kernel/max-threads
    node_processes_max_threads = "node_processes_max_threads"


class CPULoad(pydantic.BaseModel):
    """section: prometheus_cpu_v1"""

    load1: float
    load5: float
    load15: float
    num_cpus: int


class Uptime(pydantic.BaseModel):
    """section: prometheus_uptime_v1"""

    seconds: float


class FilesystemInfo:
    def __init__(self, name: str, fstype: str, mountpoint: str) -> None:
        self.name = name
        self.fstype = fstype
        self.mountpoint = mountpoint
        self.size: int | None = None
        self.available: int | None = None
        self.used: int | None = None

    def set_entity(self, entity_name: str, value: int) -> None:
        setattr(self, entity_name, value)

    def is_complete(self) -> bool:
        for entity in [a for a in dir(self) if not a.startswith("__")]:
            if not getattr(self, entity):
                return False
        return True


class NodeExporter:
    def __init__(self, get_promql: PromQLGetter) -> None:
        self.get_promql = get_promql

    def df_summary(self) -> dict[str, SectionStr]:
        df_result = self._df_summary()
        df_inodes_result = self._df_inodes_summary()

        return {
            node_name: _create_section(
                "df",
                [
                    *node_df_info,
                    "[df_inodes_start]",
                    *df_inodes_result[node_name],
                    "[df_inodes_end]",
                ],
            )
            for node_name, node_df_info in df_result.items()
            if node_df_info and node_name in df_inodes_result
        }

    def _df_summary(self) -> dict[str, list[str]]:
        # value division by 1000 because of Prometheus format
        df_list = [
            ("available", "node_filesystem_avail_bytes/1000"),
            ("size", "node_filesystem_size_bytes/1000"),
            ("used", "(node_filesystem_size_bytes - node_filesystem_free_bytes)/1000"),
        ]
        return self._process_filesystem_info(self._retrieve_filesystem_info(df_list))

    def _df_inodes_summary(self) -> dict[str, list[str]]:
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
                    device_parsed = f"{device_info.name} {device_info.fstype} {device_info.size} {device_info.used} {device_info.available} None {device_info.mountpoint}"
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

    def diskstat_summary(self) -> dict[str, SectionStr]:
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
    ) -> dict[str, SectionStr]:
        result: dict[str, SectionStr] = {}
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
                result[node_name] = _create_section("diskstat", temp_result)
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

    def memory_summary(self) -> dict[str, SectionStr]:
        result: dict[str, list[str]] = {}
        memory = self._retrieve_memory()
        for query_name, query in memory:
            for node_element in query:
                node_mem = result.setdefault(node_element["labels"]["instance"], [])
                node_mem.append("{}: {} kB".format(query_name, int(node_element["value"])))
        return {node: _create_section("mem", section_list) for node, section_list in result.items()}

    def _retrieve_memory(self) -> list[tuple[str, list[PromQLMetric]]]:
        return [
            (query_name, self.get_promql(query))
            for query_name, query in [
                ("MemTotal", NodeExporterQuery.node_memory_MemTotal_kibibytes),
                ("MemFree", NodeExporterQuery.node_memory_MemFree_kibibytes),
                ("MemAvailable", NodeExporterQuery.node_memory_MemAvailable_kibibytes),
                ("Buffers", NodeExporterQuery.node_memory_Buffers_kibibytes),
                ("Cached", NodeExporterQuery.node_memory_Cached_kibibytes),
                ("SwapCached", NodeExporterQuery.node_memory_SwapCached_kibibytes),
                ("Active", NodeExporterQuery.node_memory_Active_kibibytes),
                ("Inactive", NodeExporterQuery.node_memory_Inactive_kibibytes),
                ("Active(anon)", NodeExporterQuery.node_memory_Active_anon_kibibytes),
                ("Inactive(anon)", NodeExporterQuery.node_memory_Inactive_anon_kibibytes),
                ("Active(file)", NodeExporterQuery.node_memory_Active_file_kibibytes),
                ("Inactive(file)", NodeExporterQuery.node_memory_Inactive_file_kibibytes),
                ("Unevictable", NodeExporterQuery.node_memory_Unevictable_kibibytes),
                ("Mlocked", NodeExporterQuery.node_memory_Mlocked_kibibytes),
                ("SwapTotal", NodeExporterQuery.node_memory_SwapTotal_kibibytes),
                ("SwapFree", NodeExporterQuery.node_memory_SwapFree_kibibytes),
                ("Dirty", NodeExporterQuery.node_memory_Dirty_kibibytes),
                ("Writeback", NodeExporterQuery.node_memory_Writeback_kibibytes),
                ("AnonPages", NodeExporterQuery.node_memory_AnonPages_kibibytes),
                ("Mapped", NodeExporterQuery.node_memory_Mapped_kibibytes),
                ("Shmem", NodeExporterQuery.node_memory_Shmem_kibibytes),
                ("KReclaimable", NodeExporterQuery.node_memory_KReclaimable_kibibytes),
                ("Slab", NodeExporterQuery.node_memory_Slab_kibibytes),
                ("SReclaimable", NodeExporterQuery.node_memory_SReclaimable_kibibytes),
                ("SUnreclaim", NodeExporterQuery.node_memory_SUnreclaim_kibibytes),
                ("KernelStack", NodeExporterQuery.node_memory_KernelStack_kibibytes),
                ("PageTables", NodeExporterQuery.node_memory_PageTables_kibibytes),
                ("NFS_Unstable", NodeExporterQuery.node_memory_NFS_Unstable_kibibytes),
                ("Bounce", NodeExporterQuery.node_memory_Bounce_kibibytes),
                ("WritebackTmp", NodeExporterQuery.node_memory_WritebackTmp_kibibytes),
                ("CommitLimit", NodeExporterQuery.node_memory_CommitLimit_kibibytes),
                ("Committed_AS", NodeExporterQuery.node_memory_Committed_AS_kibibytes),
                ("VmallocTotal", NodeExporterQuery.node_memory_VmallocTotal_kibibytes),
                ("VmallocUsed", NodeExporterQuery.node_memory_VmallocUsed_kibibytes),
                ("VmallocChunk", NodeExporterQuery.node_memory_VmallocChunk_kibibytes),
                ("Percpu", NodeExporterQuery.node_memory_Percpu_kibibytes),
                ("HardwareCorrupted", NodeExporterQuery.node_memory_HardwareCorrupted_kibibytes),
                ("AnonHugePages", NodeExporterQuery.node_memory_AnonHugePages_kibibytes),
                ("ShmemHugePages", NodeExporterQuery.node_memory_ShmemHugePages_kibibytes),
                ("ShmemPmdMapped", NodeExporterQuery.node_memory_ShmemPmdMapped_kibibytes),
                ("CmaTotal", NodeExporterQuery.node_memory_CmaTotal_kibibytes),
                ("CmaFree", NodeExporterQuery.node_memory_CmaFree_kibibytes),
                ("HugePages_Total", NodeExporterQuery.node_memory_HugePages_Total),
                ("HugePages_Free", NodeExporterQuery.node_memory_HugePages_Free),
                ("HugePages_Rsvd", NodeExporterQuery.node_memory_HugePages_Rsvd),
                ("HugePages_Surp", NodeExporterQuery.node_memory_HugePages_Surp),
                ("Hugepagesize", NodeExporterQuery.node_memory_Hugepagesize_kibibytes),
                ("Hugetlb", NodeExporterQuery.node_memory_Hugetlb_kibibytes),
                ("DirectMap4k", NodeExporterQuery.node_memory_DirectMap4k_kibibytes),
                ("DirectMap2M", NodeExporterQuery.node_memory_DirectMap2M_kibibytes),
                ("DirectMap1G", NodeExporterQuery.node_memory_DirectMap1G_kibibytes),
            ]
        ]

    def kernel_summary(self) -> dict[str, SectionStr]:
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
        temp_result: dict[str, dict[str, dict[str, int]]],
    ) -> dict[str, SectionStr]:
        result: dict[str, SectionStr] = {}
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
            result[node_name] = _create_section("kernel", temp)
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

    def uptime_summary(self) -> dict[str, SectionStr]:
        uptime_samples = self.get_promql(NodeExporterQuery.node_uptime_seconds)
        return {
            sample["labels"]["instance"]: _create_section(
                "prometheus_uptime_v1:sep(0)",
                [Uptime.model_validate({"seconds": sample["value"]}).model_dump_json()],
            )
            for sample in uptime_samples
        }

    def _retrieve_uptime(self) -> list[PromQLMetric]:
        return self.get_promql(NodeExporterQuery.node_uptime_seconds)

    def cpu_summary(self) -> dict[str, SectionStr]:
        cpu = self._retrieve_cpu()
        node_to_raw: dict[str, dict[str, float]] = {}
        for key, samples in cpu:
            for sample in samples:
                instance = sample["labels"]["instance"]
                raw = node_to_raw.setdefault(instance, {})
                raw[key] = sample["value"]
        return {
            node: _create_section(
                "prometheus_cpu_v1:sep(0)", [CPULoad.model_validate(raw).model_dump_json()]
            )
            for node, raw in node_to_raw.items()
        }

    def _retrieve_cpu(self) -> list[tuple[str, list[PromQLMetric]]]:
        return [
            ("load1", self.get_promql(NodeExporterQuery.node_load1)),
            ("load5", self.get_promql(NodeExporterQuery.node_load5)),
            ("load15", self.get_promql(NodeExporterQuery.node_load15)),
            ("num_cpus", self.get_promql(NodeExporterQuery.instance_node_cpus_count)),
        ]


def _create_section(section_name: str, section_list: list[str]) -> SectionStr:
    return SectionStr("\n".join([f"<<<{section_name}>>>", *section_list]))
