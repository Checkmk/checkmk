#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from tests.testlib.site import Site

from cmk.gui.theme import Theme


@pytest.fixture(name="th")
def fixture_th(tmp_path: Path, site: Site) -> Theme:
    th = Theme(
        edition=site.edition.edition_data,
        web_dir=site.root / "share" / "check_mk" / "web",
        local_web_dir=tmp_path,
    )
    th.from_config("modern-dark")
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
    assert (
        th.detect_icon_path("snmpmib", prefix="icon_")
        == "themes/modern-dark/images/icon_snmpmib.svg"
    )


def test_url(th: Theme) -> None:
    assert th.url("asd/eee") == "themes/modern-dark/asd/eee"


def test_base_dir(th: Theme) -> None:
    assert th.base_dir() == th._local_web_dir / "htdocs" / "themes" / "modern-dark"


def test_modern_dark_images(th: Theme) -> None:
    """For each modern dark image there must be a (default) facelift variant, i.e. a file under the
    same name (may have a different file extension) within the facelift images dir. This holds only
    for the root theme dirs where the builtin images are located, not for the local theme dirs
    (th.base_dir())."""
    root_themes_dir = th._web_dir / "htdocs" / "themes"
    md_images_dir = root_themes_dir / th.get() / "images"
    fl_images_dir = root_themes_dir / "facelift" / "images"

    for md_image in md_images_dir.iterdir():
        if md_image.is_file():
            assert any(
                fl_images_dir.glob(
                    md_image.stem + ".*"
                )  # accept different file extensions per theme as our code does
            ), f"Missing image '{md_image.stem}.*' in the facelift theme"
