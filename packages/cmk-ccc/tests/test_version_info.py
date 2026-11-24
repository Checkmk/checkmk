#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path

import pytest

from cmk.ccc.version_info import (
    general_version_infos,
    general_version_infos_from_env,
    get_general_version_infos,
)


def test_version_infos_take_edition_and_core_from_their_callbacks() -> None:
    infos = general_version_infos(edition=lambda: "pro", core=lambda: "cmc")

    assert (infos["edition"], infos["core"]) == ("pro", "cmc")


def _omd_root(tmp_path: Path, site_conf: str, version: str) -> Path:
    (tmp_path / "etc" / "omd").mkdir(parents=True)
    (tmp_path / "etc" / "omd" / "site.conf").write_text(site_conf, encoding="utf-8")
    (tmp_path / "version").symlink_to(f"/omd/versions/{version}")
    return tmp_path


def test_version_infos_of_a_site_have_its_core_and_edition(tmp_path: Path) -> None:
    omd_root = _omd_root(tmp_path, "CONFIG_CORE='nagios'\n", "2.5.0p1.ultimate")

    infos = get_general_version_infos(omd_root)

    assert (infos["core"], infos["edition"]) == ("nagios", "ultimate")


def test_version_infos_of_a_site_without_a_core_have_an_unknown_one(tmp_path: Path) -> None:
    omd_root = _omd_root(tmp_path, "CONFIG_APACHE_MODE='own'\n", "2.5.0p1.pro")

    assert get_general_version_infos(omd_root)["core"] == "UNKNOWN"


def test_version_infos_from_env_come_from_cmk_general_version_infos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    printed = {
        "core": "cmc",
        "python_version": "3.15.0",
        "edition": "pro",
        "python_paths": ["/omd/sites/heute/lib/python3"],
        "version": "2.5.0p1",
        "time": 1764000000.0,
        "os": "Ubuntu 24.04.3 LTS",
    }
    (executable := tmp_path / "cmk-general-version-infos").write_text(
        f"#!/bin/sh\necho '{json.dumps(printed)}'\n", encoding="utf-8"
    )
    executable.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))

    assert general_version_infos_from_env() == printed
