#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path

import pytest

from cmk.ccc.version import Edition

from cmk.gui.theme._theme_type import Theme


def test_theme_loading_and_setting(tmp_path: Path) -> None:
    local_theme_path = tmp_path / "local" / "htdocs" / "themes"
    local_theme_path.mkdir(parents=True)
    my_theme_dir = local_theme_path / "my_theme"
    my_theme_dir.mkdir()
    (my_theme_dir / "theme.json").open(mode="w", encoding="utf-8").write(
        str(json.dumps({"title": "Määh Theme :-)"}))
    )

    theme = Theme(
        edition=Edition.CRE,
        web_dir=tmp_path,
        local_web_dir=tmp_path / "local",
    )
    theme.from_config("facelift")
    assert theme.get() == "facelift"

    theme.set("")
    assert theme.get() == "facelift"

    theme.set("not_existing")
    assert theme.get() == "facelift"

    theme.set("my_theme")
    assert theme.get() == "my_theme"


@pytest.mark.parametrize("edition", Edition)
@pytest.mark.parametrize("with_logo", [True, False])
def test_has_custom_logo(tmp_path: Path, edition: Edition, with_logo: bool) -> None:
    theme = Theme(
        edition=edition,
        web_dir=tmp_path,
        local_web_dir=tmp_path / "local",
    )
    logo = theme.base_dir().joinpath("images", "login_logo.png")
    if with_logo:
        logo.parent.mkdir(parents=True, exist_ok=True)
        logo.touch()
    elif logo.exists():
        logo.unlink()
    assert theme.has_custom_logo("login_logo") is (edition is Edition.CME and with_logo)
