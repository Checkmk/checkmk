#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from tests.component.test_lib.config_file_system import create_config_folder


def test_latest_config_sets_symlink(tmpdir: Path) -> None:
    root = Path(tmpdir)
    cf1 = create_config_folder(root, ["relay1", "relay2"])
    cf2 = create_config_folder(root, ["relay1", "relay2", "relay3"])
    assert cf1.serial != cf2.serial

    assert (root / "var/check_mk/core/helper_config/latest").resolve() == Path(
        root / f"var/check_mk/core/helper_config/{cf2.serial}"
    )


def test_file_content(tmpdir: Path) -> None:
    root = Path(tmpdir)
    cf1 = create_config_folder(root, ["relay1", "relay2"])
    cf2 = create_config_folder(root, ["relay1", "relay2", "relay3"])

    assert_file(
        root / f"var/check_mk/core/helper_config/{cf1.serial}/relays/relay1/some-config1.json",
        cf1.files["relay1"]["some-config1.json"],
    )

    assert_file(
        root / f"var/check_mk/core/helper_config/{cf1.serial}/relays/relay1/workers/worker2.json",
        cf1.files["relay1"]["workers/worker2.json"],
    )

    assert_file(
        root / f"var/check_mk/core/helper_config/{cf2.serial}/relays/relay3/workers/worker1.json",
        cf2.files["relay3"]["workers/worker1.json"],
    )

    assert not (root / f"var/check_mk/core/helper_config/{cf1.serial}/relays/relay3").exists()


def assert_file(file: Path, content: str) -> None:
    assert file.read_text() == content
