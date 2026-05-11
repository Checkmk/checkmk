#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin, PluginConfig
from cmk.base.plugins.bakery.ibm_mq import get_ibm_mq_files


def test_ibm_mq_files_with_only_qm() -> None:
    conf = {"deployment": ("sync", None), "only_qm": ["QM1", "QM2"]}
    result = sorted(get_ibm_mq_files(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("ibm_mq")),
            PluginConfig(
                base_os=OS.LINUX,
                lines=["ONLY_QM=QM1 QM2\n"],
                target=Path("ibm_mq.cfg"),
                include_header=True,
            ),
        ],
        key=repr,
    )
    assert result == expected


def test_ibm_mq_files_with_skip_qm() -> None:
    conf = {"deployment": ("sync", None), "skip_qm": ["QM3"]}
    result = sorted(get_ibm_mq_files(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("ibm_mq")),
            PluginConfig(
                base_os=OS.LINUX,
                lines=["SKIP_QM=QM3\n"],
                target=Path("ibm_mq.cfg"),
                include_header=True,
            ),
        ],
        key=repr,
    )
    assert result == expected


def test_ibm_mq_files_with_mqm_user() -> None:
    conf = {"deployment": ("sync", None), "execute_as_another_user": "mqm"}
    result = sorted(get_ibm_mq_files(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("ibm_mq")),
            PluginConfig(
                base_os=OS.LINUX,
                lines=["EXEC_USER=MQM"],
                target=Path("ibm_mq.cfg"),
                include_header=True,
            ),
        ],
        key=repr,
    )
    assert result == expected


def test_ibm_mq_files_no_config() -> None:
    """When conf has no queue config, only the plugin is yielded (no config file)."""
    conf = {"deployment": ("sync", None)}
    result = list(get_ibm_mq_files(conf))
    assert result == [Plugin(base_os=OS.LINUX, source=Path("ibm_mq"))]


def test_ibm_mq_files_do_not_deploy() -> None:
    conf = {"deployment": ("do_not_deploy", None)}
    result = list(get_ibm_mq_files(conf))
    assert result == []


def test_ibm_mq_files_all_options() -> None:
    conf = {
        "deployment": ("sync", None),
        "only_qm": ["QM1"],
        "skip_qm": ["QM2"],
        "execute_as_another_user": "mqm",
    }
    result = sorted(get_ibm_mq_files(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("ibm_mq")),
            PluginConfig(
                base_os=OS.LINUX,
                lines=["ONLY_QM=QM1\n", "SKIP_QM=QM2\n", "EXEC_USER=MQM"],
                target=Path("ibm_mq.cfg"),
                include_header=True,
            ),
        ],
        key=repr,
    )
    assert result == expected
