#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin, PluginConfig
from cmk.base.plugins.bakery.mk_site_object_counts import get_mk_site_object_counts_files


def test_mk_site_object_counts_files_with_tags() -> None:
    conf = {"deployment": ("sync", None), "tags": ["prod", "test"]}
    result = sorted(get_mk_site_object_counts_files(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("mk_site_object_counts"), interval=None),
            PluginConfig(
                base_os=OS.LINUX,
                lines=["TAGS=prod test"],
                target=Path("site_object_counts.cfg"),
                include_header=True,
            ),
        ],
        key=repr,
    )
    assert result == expected


def test_mk_site_object_counts_files_with_service_check_commands() -> None:
    conf = {"deployment": ("sync", None), "service_check_commands": ["check_mk", "check_ping"]}
    result = sorted(get_mk_site_object_counts_files(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("mk_site_object_counts"), interval=None),
            PluginConfig(
                base_os=OS.LINUX,
                lines=["SERVICE_CHECK_COMMANDS=check_mk check_ping"],
                target=Path("site_object_counts.cfg"),
                include_header=True,
            ),
        ],
        key=repr,
    )
    assert result == expected


def test_mk_site_object_counts_files_with_sites() -> None:
    conf = {
        "deployment": ("sync", None),
        "sites": [
            {"site_name": "site1", "tags": ["tag1", "tag2"], "service_check_commands": ["cmd1"]},
            {"site_name": "site2", "tags": [], "service_check_commands": ["cmd2", "cmd3"]},
        ],
    }
    result = sorted(get_mk_site_object_counts_files(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("mk_site_object_counts"), interval=None),
            PluginConfig(
                base_os=OS.LINUX,
                lines=[
                    "TAGS_site1=tag1 tag2",
                    "SERVICE_CHECK_COMMANDS_site1=cmd1",
                    "SERVICE_CHECK_COMMANDS_site2=cmd2 cmd3",
                    "SITES=site1 site2",
                ],
                target=Path("site_object_counts.cfg"),
                include_header=True,
            ),
        ],
        key=repr,
    )
    assert result == expected


def test_mk_site_object_counts_files_empty_conf() -> None:
    conf: dict[str, object] = {"deployment": ("sync", None)}
    result = sorted(get_mk_site_object_counts_files(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("mk_site_object_counts"), interval=None),
            PluginConfig(
                base_os=OS.LINUX,
                lines=[],
                target=Path("site_object_counts.cfg"),
                include_header=True,
            ),
        ],
        key=repr,
    )
    assert result == expected


def test_mk_site_object_counts_files_all_options() -> None:
    conf = {
        "deployment": ("sync", None),
        "tags": ["global_tag"],
        "service_check_commands": ["global_cmd"],
        "sites": [
            {"site_name": "mysite", "tags": ["local_tag"], "service_check_commands": ["local_cmd"]},
        ],
    }
    result = sorted(get_mk_site_object_counts_files(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("mk_site_object_counts"), interval=None),
            PluginConfig(
                base_os=OS.LINUX,
                lines=[
                    "TAGS=global_tag",
                    "SERVICE_CHECK_COMMANDS=global_cmd",
                    "TAGS_mysite=local_tag",
                    "SERVICE_CHECK_COMMANDS_mysite=local_cmd",
                    "SITES=mysite",
                ],
                target=Path("site_object_counts.cfg"),
                include_header=True,
            ),
        ],
        key=repr,
    )
    assert result == expected


def test_mk_site_object_counts_do_not_deploy() -> None:
    conf: dict[str, object] = {"deployment": ("do_not_deploy", None)}
    result = list(get_mk_site_object_counts_files(conf))
    assert result == []


def test_mk_site_object_counts_cached_deployment() -> None:
    conf = {"deployment": ("cached", 3600.0)}
    result = sorted(get_mk_site_object_counts_files(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("mk_site_object_counts"), interval=3600),
            PluginConfig(
                base_os=OS.LINUX,
                lines=[],
                target=Path("site_object_counts.cfg"),
                include_header=True,
            ),
        ],
        key=repr,
    )
    assert result == expected
