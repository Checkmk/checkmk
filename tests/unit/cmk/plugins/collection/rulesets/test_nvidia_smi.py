#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.legacy_bakery_rulesets.nvidia_smi import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            {"nvidia_smi_path": r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"},
            {
                "deployment": ("sync", None),
                "nvidia_smi_path": r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
            },
            id="deploy_with_path",
        ),
        pytest.param(
            {},
            {"deployment": ("sync", None)},
            id="deploy_without_path",
        ),
        pytest.param(
            None,
            {"deployment": ("do_not_deploy", None)},
            id="do_not_deploy",
        ),
        pytest.param(
            {"deployment": ("sync", None), "nvidia_smi_path": r"C:\path\nvidia-smi.exe"},
            {"deployment": ("sync", None), "nvidia_smi_path": r"C:\path\nvidia-smi.exe"},
            id="already_migrated",
        ),
        pytest.param(
            {"deployment": ("do_not_deploy", None)},
            {"deployment": ("do_not_deploy", None)},
            id="already_migrated_do_not_deploy",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected
