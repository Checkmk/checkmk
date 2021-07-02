#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
import json
import cmk.utils.paths
import cmk.gui.config as config
from cmk.gui.utils.theme import Theme
from cmk.gui.globals import theme
from testlib import cmk_path


@pytest.fixture(name="theme_dirs")
def fixture_theme_dirs(tmp_path, monkeypatch):
    theme_path = tmp_path / "htdocs" / "themes"
    theme_path.mkdir(parents=True)

    local_theme_path = tmp_path / "local" / "htdocs" / "themes"
    local_theme_path.mkdir(parents=True)

    monkeypatch.setattr(cmk.utils.paths, "web_dir", str(tmp_path))
    monkeypatch.setattr(cmk.utils.paths, "local_web_dir", tmp_path / "local")

    return theme_path, local_theme_path


@pytest.fixture(name="my_theme")
def fixture_my_theme(theme_dirs):
    theme_path = theme_dirs[0]
    my_dir = theme_path / "my_theme"
    my_dir.mkdir()
    (my_dir / "theme.json").open(mode="w", encoding="utf-8").write(
        str(json.dumps({"title": "Määh Theme :-)"})))
    return my_dir


def test_theme_request_context_integration(my_theme, register_builtin_html):
    theme.from_config("facelift", config.theme_choices())

    theme.set("")
    assert theme.get() == "facelift"

    theme.set("not_existing")
    assert theme.get() == "facelift"

    theme.set("my_theme")
    assert theme.get() == "my_theme"


@pytest.fixture(name="th")
def fixture_th() -> Theme:
    th = Theme()
    th.from_config("modern-dark", config.theme_choices())
    assert th.get() == "modern-dark"
    return th


def test_icon_themes(th: Theme) -> None:
    assert th.icon_themes() == ["modern-dark", "facelift"]

    th.set("facelift")
    assert th.get() == "facelift"
    assert th.icon_themes() == ["facelift"]


def test_detect_icon_path(th: Theme) -> None:
    assert th.get() == "modern-dark"
    assert th.detect_icon_path("xyz", prefix="icon_") == "themes/facelift/images/icon_missing.svg"
    assert th.detect_icon_path("ldap", prefix="icon_") == "themes/facelift/images/icon_ldap.svg"
    assert th.detect_icon_path("email", prefix="icon_") == "themes/facelift/images/icon_email.png"
    assert th.detect_icon_path("window_list", prefix="icon_") == "images/icons/window_list.png"
    assert th.detect_icon_path("snmpmib",
                               prefix="icon_") == "themes/modern-dark/images/icon_snmpmib.svg"


def test_url(th: Theme) -> None:
    assert th.url("asd/eee") == "themes/modern-dark/asd/eee"
