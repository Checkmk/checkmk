#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import json
import os
import re
import shutil
import subprocess
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from cmk.diagnostics.internal import (
    collect_command_output,
    CollectContext,
    CollectInfo,
    DiagnosticsPlugin,
    DumpItem,
    GeneratedContent,
    Help,
    Sensitivity,
)
from cmk.plugins.diagnostics.lib.topics import TOPIC_OPERATING_SYSTEM


def _collect_environment_variables(_context: CollectContext) -> Iterable[DumpItem]:
    yield DumpItem(
        PurePosixPath("environment.json"),
        GeneratedContent(json.dumps(dict(os.environ), sort_keys=True, indent=4).encode()),
    )


diagnostics_plugin_environment_variables = DiagnosticsPlugin(
    name="environment_variables",
    description=Help("The environment variables of the site user"),
    sensitivity=Sensitivity.MEDIUM,
    topic=TOPIC_OPERATING_SYSTEM,
    handler=_collect_environment_variables,
)


def _try_to_read(filename: str | Path) -> list[str]:
    try:
        with open(filename) as f:
            return [l.rstrip() for l in f.readlines()]
    except PermissionError, FileNotFoundError:
        return []


#   ---hardware---------------------------------------------------------------


_PROC_PATH = Path("/proc")


def _meminfo_proc_parser(content: list[str]) -> dict[str, str]:
    info: dict[str, str] = {}

    for line in content:
        if line == "":
            continue

        key, value = (w.strip() for w in line.split(":", 1))
        info[key.replace(" ", "_")] = value

    return info


def _cpuinfo_proc_parser(content: list[str]) -> dict[str, str]:
    cpu_info: dict[str, Any] = {}
    physical_ids: list[str] = []
    num_processors = 0

    # Example lines from /proc/cpuinfo output:
    # >>> pprint.pprint(content)
    # ['processor\t: 0',
    #  'cpu family\t: 6',
    #  'cpu MHz\t\t: 2837.021',
    #  'core id\t\t: 0',
    #  'power management:',
    # ...
    #  '',
    #  'processor\t: 1',
    #  'cpu family\t: 6',
    #  'cpu MHz\t\t: 2100.000',
    #  'core id\t\t: 1',
    #  'power management:',
    #  '',
    # ...

    # Keys that have different values for each processor
    _KEYS_TO_IGNORE = [
        "apicid",
        "core_id",
        "cpu_MHz",
        "initial_apicid",
        "processor",
    ]

    # Remove empty keys, empty values and ignore some keys
    for line in content:
        if line == "":
            continue

        key, value = (w.strip() for w in line.split(":", 1))
        key = key.replace(" ", "_")

        if key not in _KEYS_TO_IGNORE:
            cpu_info[key] = value

        if key == "processor":
            num_processors += 1

        if key == "physical_id" and value not in physical_ids:
            physical_ids.append(value)

    cpu_info["num_logical_processors"] = str(num_processors)
    cpu_info["cpus"] = len(physical_ids)

    return cpu_info


def _load_avg_proc_parser(content: list[str]) -> dict[str, str]:
    return dict(zip(["loadavg_1", "loadavg_5", "loadavg_15"], content[0].split()))


def _collect_hw_info(
    _context: CollectContext, *, proc_path: Path = _PROC_PATH
) -> Iterable[DumpItem]:
    hw_info: dict[str, dict[str, str]] = {}
    for procfile, parser in [
        ("meminfo", _meminfo_proc_parser),
        ("loadavg", _load_avg_proc_parser),
        ("cpuinfo", _cpuinfo_proc_parser),
    ]:
        if content := _try_to_read(proc_path / procfile):
            hw_info[procfile] = parser(content)
    yield DumpItem(
        PurePosixPath("hwinfo.json"),
        GeneratedContent(json.dumps(hw_info, sort_keys=True, indent=4).encode()),
    )


diagnostics_plugin_hw_info = DiagnosticsPlugin(
    name="hw_info",
    description=Help("Hardware information like memory, CPU load and CPU model"),
    sensitivity=Sensitivity.LOW,
    topic=TOPIC_OPERATING_SYSTEM,
    always=True,
    handler=_collect_hw_info,
)


_DMI_ID_PATH = Path("/sys/class/dmi/id")


def _collect_vendor_info(
    _context: CollectContext, *, dmi_id_path: Path = _DMI_ID_PATH
) -> Iterable[DumpItem]:
    _SYS_FILES = [
        "bios_vendor",
        "bios_version",
        "sys_vendor",
        "product_name",
        "chassis_asset_tag",
    ]
    _AZURE_TAG = "7783-7084-3265-9085-8269-3286-77"
    vendor_info = {}
    for sys_file in _SYS_FILES:
        file_content = (dmi_id_path / sys_file).read_text().replace("\n", "")
        vendor_info[sys_file] = (
            ("Azure" if file_content == _AZURE_TAG else "Other")
            if sys_file == "chassis_asset_tag"
            else file_content
        )
    yield DumpItem(
        PurePosixPath("vendorinfo.json"),
        GeneratedContent(json.dumps(vendor_info, sort_keys=True, indent=4).encode()),
    )


diagnostics_plugin_vendor_info = DiagnosticsPlugin(
    name="vendor_info",
    description=Help("Vendor information from the DMI table of the Checkmk server"),
    sensitivity=Sensitivity.LOW,
    topic=TOPIC_OPERATING_SYSTEM,
    always=True,
    handler=_collect_vendor_info,
)


def _collect_appliance_info(_context: CollectContext) -> Iterable[DumpItem]:
    cma_infos: dict[str, str | dict[str, str]] = {}
    if hw_content := _try_to_read("/etc/cma/hw"):
        cma_infos["hw"] = dict([l.replace("'", "").split("=") for l in hw_content if "=" in l])
    if fw_content := _try_to_read("/ro/usr/share/cma/version"):
        cma_infos["fw"] = fw_content[0]
    yield DumpItem(
        PurePosixPath("appliance.json"),
        GeneratedContent(json.dumps(cma_infos, sort_keys=True, indent=4).encode()),
    )


diagnostics_plugin_appliance_info = DiagnosticsPlugin(
    name="appliance_info",
    description=Help("Checkmk appliance hardware and version information"),
    sensitivity=Sensitivity.LOW,
    topic=TOPIC_OPERATING_SYSTEM,
    always=True,
    handler=_collect_appliance_info,
)


#   ---installed software-------------------------------------------------------


def _collect_selinux(_context: CollectContext) -> Iterable[DumpItem]:
    yield DumpItem(
        PurePosixPath("selinux.json"),
        GeneratedContent(
            json.dumps(
                {
                    line.split(":")[0]: line.split(":")[1].lstrip()
                    for line in subprocess.check_output(selinux_binary, text=True).split("\n")
                    if ":" in line
                }
                if (selinux_binary := shutil.which("sestatus"))
                else {},
                sort_keys=True,
                indent=4,
            ).encode()
        ),
    )


diagnostics_plugin_selinux = DiagnosticsPlugin(
    name="selinux",
    description=Help("The SELinux status of the operating system ('sestatus')"),
    sensitivity=Sensitivity.LOW,
    topic=TOPIC_OPERATING_SYSTEM,
    always=True,
    handler=_collect_selinux,
)


def _dpkg_packages_csv() -> str:
    if not (dpkg_binary := shutil.which("dpkg")):
        return ""

    dpkg_output = subprocess.check_output([dpkg_binary, "-l"], text=True)
    return "\n".join(
        [";".join(l.split(maxsplit=4)) for l in dpkg_output.split("\n") if len(l.split()) > 4]
    )


def _rpm_packages_csv() -> str:
    if not (rpm_binary := shutil.which("rpm")):
        return ""

    try:
        output = subprocess.check_output(
            [
                rpm_binary,
                "-qa",
                "--queryformat",
                r"%{NAME};%{VERSION};%{RELEASE};%{ARCH}\n",
            ],
            text=True,
            stderr=subprocess.STDOUT,
        )

    except subprocess.CalledProcessError:
        return ""

    return "\n".join(sorted(output.split("\n")))


def _collect_os_packages(_context: CollectContext) -> Iterable[DumpItem]:
    empty = True
    for filename, contents in (
        ("dpkg_packages.csv", _dpkg_packages_csv()),
        ("rpm_packages.csv", _rpm_packages_csv()),
    ):
        if contents:
            empty = False
            yield DumpItem(PurePosixPath(filename), GeneratedContent(contents.encode()))
    if empty:
        raise CollectInfo("No data")


diagnostics_plugin_os_packages = DiagnosticsPlugin(
    name="os_packages",
    description=Help("The operating system packages installed on the Checkmk server"),
    sensitivity=Sensitivity.LOW,
    topic=TOPIC_OPERATING_SYSTEM,
    always=True,
    handler=_collect_os_packages,
)


def _collect_python_packages(_context: CollectContext) -> Iterable[DumpItem]:
    yield DumpItem(
        PurePosixPath("pip_freeze.json"),
        GeneratedContent(
            json.dumps(
                {
                    l.split("==")[0]: l.split("==")[1]
                    for l in subprocess.check_output(["pip3", "freeze", "--all"], text=True).split(
                        "\n"
                    )
                    if "==" in l
                },
                sort_keys=True,
                indent=4,
            ).encode()
        ),
    )


diagnostics_plugin_python_packages = DiagnosticsPlugin(
    name="python_packages",
    description=Help("The Python packages installed in the site ('pip freeze')"),
    sensitivity=Sensitivity.LOW,
    topic=TOPIC_OPERATING_SYSTEM,
    always=True,
    handler=_collect_python_packages,
)


#   ---system state-------------------------------------------------------------


def _collect_disk_usage(context: CollectContext) -> Iterable[DumpItem]:
    yield from collect_command_output(context, "df", ".out", ["df"])
    yield from collect_command_output(context, "df-i", ".out", ["df", "-i"])


diagnostics_plugin_disk_usage = DiagnosticsPlugin(
    name="disk_usage",
    description=Help("File system usage of the Checkmk server ('df')"),
    sensitivity=Sensitivity.LOW,
    topic=TOPIC_OPERATING_SYSTEM,
    always=True,
    handler=_collect_disk_usage,
)


def _collect_network_state(context: CollectContext) -> Iterable[DumpItem]:
    yield from collect_command_output(context, "ip-a", ".out", ["ip", "a"])
    yield from collect_command_output(context, "ss-tulpen", ".out", ["ss", "-tulpen"])


diagnostics_plugin_network_state = DiagnosticsPlugin(
    name="network_state",
    description=Help(
        "Network interfaces, addresses and sockets of the Checkmk server ('ip a', 'ss')"
    ),
    sensitivity=Sensitivity.MEDIUM,
    topic=TOPIC_OPERATING_SYSTEM,
    handler=_collect_network_state,
)


def _collect_processes_and_logins(context: CollectContext) -> Iterable[DumpItem]:
    yield from collect_command_output(context, "w", ".out", ["w"])
    yield from collect_command_output(
        context,
        "top",
        ".out",
        ["top", "-b", "-n", "1", "-H", "-c", "-w", "512", "-o", "-PID", "-1"],
    )


diagnostics_plugin_processes_and_logins = DiagnosticsPlugin(
    name="processes_and_logins",
    description=Help("Running processes and logged in users of the Checkmk server ('top', 'w')"),
    sensitivity=Sensitivity.MEDIUM,
    topic=TOPIC_OPERATING_SYSTEM,
    handler=_collect_processes_and_logins,
)


_TMP_FILE_REGEX = re.compile(r"^\..*\.new.*")


def _collect_file_sizes(context: CollectContext) -> Iterable[DumpItem]:
    csv_data = ["size;path;owner;group;mode;changed"]
    for dirpath, _dirnames, filenames in os.walk(context.omd_root):
        for file in filenames:
            f = Path(dirpath, file)
            if f.is_symlink():
                continue
            if re.match(_TMP_FILE_REGEX, f.name):
                continue
            csv_data.append(
                ";".join(
                    [
                        str(f.stat().st_size),
                        str(f),
                        f.owner(),
                        f.group(),
                        str(oct(f.stat().st_mode)),
                        datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    ]
                )
            )

    yield DumpItem(PurePosixPath("file_size.csv"), GeneratedContent("\n".join(csv_data).encode()))


diagnostics_plugin_file_sizes = DiagnosticsPlugin(
    name="file_sizes",
    description=Help("Size, owner and permissions of the files below the site directory"),
    sensitivity=Sensitivity.LOW,
    topic=TOPIC_OPERATING_SYSTEM,
    always=True,
    handler=_collect_file_sizes,
)
