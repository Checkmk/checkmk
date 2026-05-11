#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.bakery.v2_unstable import OS, Plugin, PluginConfig
from cmk.plugins.nvidia.bakery.nvidia_smi import bakery_plugin_nvidia_smi


@pytest.mark.parametrize(
    "conf, expected_files",
    [
        (
            {
                "deployment": ("sync", None),
                "nvidia_smi_path": r"C:\Windows\System32\nvidia-smi.exe",
            },
            [
                Plugin(base_os=OS.LINUX, source=Path("nvidia_smi"), interval=None),
                Plugin(base_os=OS.WINDOWS, source=Path("nvidia_smi.ps1"), interval=None),
                PluginConfig(
                    base_os=OS.WINDOWS,
                    lines=[r"$nvidia_smi_path = 'C:\Windows\System32\nvidia-smi.exe'"],
                    target=Path("nvidia_smi_cfg.ps1"),
                    include_header=True,
                ),
            ],
        ),
        (
            {"deployment": ("sync", None)},
            [
                Plugin(base_os=OS.LINUX, source=Path("nvidia_smi"), interval=None),
                Plugin(base_os=OS.WINDOWS, source=Path("nvidia_smi.ps1"), interval=None),
            ],
        ),
        (
            {"deployment": ("do_not_deploy", None)},
            [],
        ),
    ],
)
def test_nvidia_smi_files(
    conf: dict[str, object],
    expected_files: list[Plugin | PluginConfig],
) -> None:
    parsed = bakery_plugin_nvidia_smi.parameter_parser(conf)
    result = list(bakery_plugin_nvidia_smi.files_function(parsed))
    assert result == expected_files
