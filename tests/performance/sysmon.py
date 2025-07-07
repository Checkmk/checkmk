#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
import json
import os
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from sys import argv
from typing import IO

import psutil

perf_dict = dict[str, int | float | str | None]
nested_perf_dict = dict[str, perf_dict]


def _named_section(name: str, data: perf_dict) -> perf_dict:
    for key in list(data.keys()):
        data[f"{name}.{key}"] = data.pop(key)
    return data


def get_cpu_info(count_cores: bool = False) -> perf_dict:
    data: perf_dict = {
        "cpu_freq": psutil.cpu_freq().current,
        "cpu_percent": psutil.cpu_percent(interval=0.1),
    }
    if count_cores:
        data |= {
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "cpu_count_logical": psutil.cpu_count(logical=True),
        }
    core_data: perf_dict = {
        f"cpu_percent_{core}": usage
        for core, usage in enumerate(psutil.cpu_percent(percpu=True, interval=0.1))
    }  # "percpu" -> "per core"
    data.update(core_data)
    return _named_section("cpu_info", data)


def get_disk_info() -> perf_dict:
    partitions = psutil.disk_partitions()
    data: perf_dict = {}
    for partition in partitions:
        partition_usage = psutil.disk_usage(partition.mountpoint)
        partition_info = {
            "total_space": partition_usage.total / (1024.0**3),
            "used_space": partition_usage.used / (1024.0**3),
            "free_space": partition_usage.free / (1024.0**3),
            "usage_percentage": partition_usage.percent,
        }
        for key, value in partition_info.items():
            data[f"{partition.mountpoint}.{key}"] = value
    return _named_section("disk_info", data)


def get_disk_io_counters() -> perf_dict:
    io_counters = psutil.disk_io_counters()
    data: perf_dict = {
        "read_count": io_counters.read_count if io_counters else 0,
        "write_count": io_counters.write_count if io_counters else 0,
        "read_bytes": io_counters.read_bytes if io_counters else 0,
        "write_bytes": io_counters.write_bytes if io_counters else 0,
        "read_time": io_counters.read_time if io_counters else 0,
        "write_time": io_counters.write_time if io_counters else 0,
    }
    return _named_section("disk_io_counters", data)


def get_kernel_info() -> perf_dict:
    data: perf_dict = {
        "kernel_version": os.uname().release,
        "system_name": os.uname().sysname,
        "node_name": os.uname().nodename,
        "machine": os.uname().machine,
    }
    return _named_section("kernel_info", data)


def get_load_average() -> perf_dict:
    load_avg_1, load_avg_5, load_avg_15 = psutil.getloadavg()
    data: perf_dict = {
        "load_average_1": load_avg_1,
        "load_average_5": load_avg_5,
        "load_average_15": load_avg_15,
    }
    return _named_section("load_average", data)


def get_memory_info() -> perf_dict:
    data: perf_dict = {
        "virtual_memory_total": psutil.virtual_memory().total / (1024.0**3),
        "virtual_memory_available": psutil.virtual_memory().available / (1024.0**3),
        "virtual_memory_percent": psutil.virtual_memory().percent,
        "virtual_memory_used": psutil.virtual_memory().used / (1024.0**3),
    }
    return _named_section("memory_info", data)


def get_net_io_counters() -> perf_dict:
    net_io_counters = psutil.net_io_counters()
    data: perf_dict = {
        "bytes_sent": net_io_counters.bytes_sent,
        "bytes_recv": net_io_counters.bytes_recv,
        "packets_sent": net_io_counters.packets_sent,
        "packets_recv": net_io_counters.packets_recv,
        "errin": net_io_counters.errin,
        "errout": net_io_counters.errout,
        "dropin": net_io_counters.dropin,
        "dropout": net_io_counters.dropout,
    }
    return _named_section("net_io_counters", data)


def get_process_info() -> perf_dict:
    processes: nested_perf_dict = {}
    for process in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]):
        try:
            processes[process.info["pid"]] = {
                "name": process.info["name"],
                "cpu_percent": process.info["cpu_percent"],
                "memory_percent": process.info["memory_percent"],
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    data = {}
    for pid, proc in processes.items():
        if type(proc) is perf_dict:
            data[f"{pid}.name_{proc['name']}.cpu_percent"] = proc["cpu_percent"]
            data[f"{pid}.name_{proc['name']}.memory_percent"] = proc["memory_percent"]
    return _named_section("process_info", data)


def get_system_uptime() -> str:
    boot_time_timestamp = psutil.boot_time()
    current_time_timestamp = time.time()
    uptime_seconds = current_time_timestamp - boot_time_timestamp
    uptime_minutes = uptime_seconds // 60
    uptime_hours = uptime_minutes // 60
    uptime_days = uptime_hours // 24
    return f"{int(uptime_days)}d {int(uptime_hours % 24)}h {int(uptime_minutes % 60)}m {int(uptime_seconds % 60)}s"


def get_statistics(timestamp: str, all: bool = False) -> perf_dict:
    statistics = (
        perf_dict({"time": timestamp}) | get_cpu_info() | get_memory_info() | get_disk_io_counters()
    )
    if not all:
        return statistics

    return (
        statistics
        | get_kernel_info()
        | get_disk_info()
        | get_process_info()
        | get_load_average()
        | get_net_io_counters()
    )


def write_statistics(file: IO, all: bool = False, close: bool = False) -> None:
    if close:
        file.write("[]" if file.tell() == 0 else "\n]")
        return
    timestamp = datetime.datetime.now().astimezone().isoformat()
    statistics = get_statistics(timestamp, all=all)
    data = json.dumps(statistics)
    data = ("[\n" if file.tell() == 0 else ",\n") + data
    file.write(data)


def _init_resources_file(suffix: str) -> Path:
    report_folder_path = Path(__file__).parent.parent.parent / "results" / "performance"

    benchmark_report_json = report_folder_path / next(
        (_.split("=", 1)[-1] for _ in argv if _.startswith("--benchmark-json=")),
        report_folder_path / "cmk.benchmark.json",
    )
    resource_statistics_json = (
        benchmark_report_json.parent
        / f"{benchmark_report_json.stem.split('.', 1)[0]}.{suffix}.resources.json"
    )
    resource_statistics_json.unlink(missing_ok=True)

    return resource_statistics_json


def _log_resources(
    file_path: Path, start_event: threading.Event, stop_event: threading.Event
) -> None:
    max_duration = 0.0
    statistics_interval = 1
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as stats_file:
        while not stop_event.is_set():
            start_time = time.time()
            if start_event.is_set():
                write_statistics(stats_file)
            end_time = time.time()
            duration = end_time - start_time
            max_duration = duration if duration > max_duration else max_duration
            # wait until next interval
            if duration < statistics_interval:
                time.sleep(statistics_interval - duration)
        write_statistics(stats_file, close=True)


@contextmanager
def track_resources(
    task_name: str,
    start_event: threading.Event | None = None,
    stop_event: threading.Event | None = None,
) -> Iterator[None]:
    file_path = _init_resources_file(task_name)
    if start_event is None:
        start_event = threading.Event()
        start_event.set()
    stop_event = stop_event or threading.Event()
    thread = threading.Thread(target=_log_resources, args=(file_path, start_event, stop_event))
    thread.start()

    yield

    start_event.clear()
    stop_event.set()
