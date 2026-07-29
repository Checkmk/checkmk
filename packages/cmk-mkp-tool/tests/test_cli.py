#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.mkp_tool import PackageStore, PathConfig
from cmk.mkp_tool.cli import main, SiteContext


@pytest.fixture(name="site_context")
def fixture_site_context(package_store: PackageStore, tmp_path: Path) -> SiteContext:
    return SiteContext(
        package_store=package_store,
        installed_packages_dir=tmp_path / "installed_packages_dir",
        callbacks={},
        post_package_change_actions=lambda _manifests: None,
        version="2.5.0",
        parse_version=lambda v: (v,),
    )


@pytest.mark.parametrize("command", ["add", "inspect"])
def test_unreadable_file_is_reported(
    command: str,
    site_context: SiteContext,
    path_config: PathConfig,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # a directory can't be read as a file, no matter which user we are
    unreadable = tmp_path / "coolstuff.mkp"
    unreadable.mkdir()
    monkeypatch.setattr("sys.argv", ["mkp", command, str(unreadable)])

    assert main(path_config, site_context, lambda _path, _content: None) == 1

    assert str(unreadable) in capsys.readouterr().err
