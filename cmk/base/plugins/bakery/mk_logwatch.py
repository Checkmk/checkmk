#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="type-arg"

from collections.abc import Collection, Iterable
from pathlib import Path
from shlex import quote
from typing import Any, TypedDict

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register

ClusterSectionConfig = list[dict[str, Any]]
FileSectionConfig = dict[str, Any]


class LogwatchConfig(TypedDict, total=False):
    cluster_section: ClusterSectionConfig
    file_section: FileSectionConfig
    logfiles: Any


LogwatchConfigListEntry = bool | LogwatchConfig | None
LegacyLogwatchConfigListEntry = dict | LogwatchConfigListEntry | None
LogwatchConfigList = list[LogwatchConfigListEntry]


def _transform_mk_logwatch(rule_value: LogwatchConfigListEntry) -> LogwatchConfigListEntry:
    """Transform pre 1.6.0b3 rules"""
    if isinstance(rule_value, dict) and "logfiles" in rule_value:
        return LogwatchConfig(file_section=rule_value)  # type: ignore[typeddict-item]
    return rule_value


def _get_applicable_rule_values(
    matched_rule_values: LogwatchConfigList,
) -> tuple[bool, list[LogwatchConfig]]:
    """
    Return a flag wether we need to deploy the plugin, and
    a list of applicable rule values
    """
    deploy = False
    applicable = []
    for rule_value in matched_rule_values:
        if rule_value is None:
            break
        deploy = True
        if rule_value is True:
            break
        assert not isinstance(rule_value, bool)
        applicable.append(rule_value)
    return deploy, applicable


def _get_global_option_lines(global_options: Collection[tuple[str, object]]) -> list[str]:
    if not global_options:
        return []
    return [
        "",
        "GLOBAL OPTIONS",
        *(f" {key} {value}" for key, value in global_options),
    ]


def _get_file_section_lines(file_sections: Iterable[FileSectionConfig]) -> list[str]:
    def _get_logfile_header_line(entry: FileSectionConfig) -> str:
        """Generates a single line string from subsequent dict k,v pairs (entries)."""
        parts = ['"%s"' % logfile for logfile in entry["logfiles"]]
        if (regex := entry.get("regex")) is not None:
            parts.append(f"{regex[0]}={quote(regex[1])}")
        for key in (
            "encoding",
            "maxlines",
            "maxtime",
            "overflow",
            "maxfilesize",
            "maxlinesize",
            "maxoutputsize",
            "skipconsecutiveduplicated",
        ):
            if key in entry:
                parts.append(f"{key}={entry[key]}")
        if not entry.get("context"):  # Need True/False here
            parts.append("nocontext=True")
        if entry.get("maxcontextlines"):
            parts.append("maxcontextlines=%d,%d" % entry["maxcontextlines"])
        if entry.get("fromstart"):
            parts.append("fromstart=True")
        return " ".join(parts)

    lines = []

    for entry in file_sections:
        logfiles_line = _get_logfile_header_line(entry)
        if logfiles_line:
            lines.append("")
            lines.append(logfiles_line)
        for state, regex in entry["patterns"]:
            if not regex:
                regex = ".*"
            lines.append(f" {state} {regex}")

    return lines


def _get_cluster_section_lines(cluster_sections: ClusterSectionConfig) -> list[str]:
    lines = []

    for cluster in cluster_sections:
        lines.append("")
        lines.append("CLUSTER %s" % cluster["name"])
        for ip_addr in cluster["ips"]:
            lines.append(" %s" % ip_addr)

    return lines


def get_mk_logwatch_files(conf: LogwatchConfigList) -> FileGenerator:
    matched_rule_values = [_transform_mk_logwatch(rule_value) for rule_value in conf]
    deploy, applicable_values = _get_applicable_rule_values(matched_rule_values)

    if not deploy:
        return

    yield from (
        Plugin(base_os=base_os, source=Path("mk_logwatch.py"))
        for base_os in (OS.LINUX, OS.SOLARIS, OS.AIX, OS.WINDOWS)
    )

    if not applicable_values:
        return

    yield from (
        PluginConfig(
            base_os=base_os,
            lines=list(_get_mk_logwatch_config(applicable_values)),
            target=Path("logwatch.cfg"),
            include_header=True,
        )
        for base_os in (OS.LINUX, OS.SOLARIS, OS.AIX, OS.WINDOWS)
    )


def _get_mk_logwatch_config(applicable_values: list[LogwatchConfig]) -> Iterable[str]:
    global_options = {
        k[7:]: v
        for rule_value in reversed(applicable_values)
        for k, v in rule_value.items()
        if k.startswith("global_")
    }
    file_sections = (
        rule_value["file_section"]
        for rule_value in applicable_values
        if "file_section" in rule_value
    )
    cluster_sections = [
        x for rule_value in applicable_values for x in rule_value.get("cluster_section", [])
    ]

    yield from _get_global_option_lines(global_options.items())
    yield from _get_file_section_lines(file_sections)
    yield from _get_cluster_section_lines(cluster_sections)


register.bakery_plugin(
    name="mk_logwatch",
    files_function=get_mk_logwatch_files,
)
