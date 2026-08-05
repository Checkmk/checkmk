#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from tests.testlib.site import Site

import cmk.utils.paths

from cmk.gui import http, main_modules
from cmk.gui.utils import get_failed_plugins
from cmk.gui.utils.script_helpers import session_wsgi_app
from cmk.gui.utils.theme import Theme, theme


@pytest.fixture(name="load_plugins", scope="session")
def fixture_load_plugins() -> None:
    main_modules.load_plugins()
    if errors := get_failed_plugins():
        raise Exception(f"The following errors occured during plug-in loading: {errors}")


@pytest.fixture(name="request_context")
def request_context(load_plugins: None) -> Iterator[None]:
    """This fixture registers a global htmllib.html() instance just like the regular GUI"""
    flask_app = session_wsgi_app(testing=True)

    with flask_app.test_request_context():
        flask_app.preprocess_request()
        yield
        flask_app.process_response(http.Response())


@pytest.fixture(name="omd_site")
def fixture_omd_site(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("OMD_SITE", "NO_SITE")


@pytest.fixture(name="patch_web_dir")
def fixture_patch_web_dir(tmp_path: Path, monkeypatch: MonkeyPatch, site: Site) -> None:
    web_dir = (site.root / "version" / "share" / "check_mk" / "web").as_posix()
    monkeypatch.setattr(cmk.utils.paths, "web_dir", web_dir)


@pytest.fixture(name="patch_local_web_dir")
def fixture_patch_local_web_dir(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    local_theme_path = tmp_path / "local" / "htdocs" / "themes"
    local_theme_path.mkdir(parents=True)
    monkeypatch.setattr(cmk.utils.paths, "local_web_dir", tmp_path / "local")
    return local_theme_path


@pytest.fixture(name="local_theme")
def fixture_local_theme(patch_local_web_dir: Path) -> None:
    # create a custom theme in the local folder
    my_dir = patch_local_web_dir / "my_theme"
    my_dir.mkdir()
    (my_dir / "theme.json").open(mode="w", encoding="utf-8").write(
        str(json.dumps({"title": "Määh Theme :-)"}))
    )


@pytest.fixture(name="th")
def fixture_th() -> Theme:
    th = Theme(validate_choices=True)
    th.from_config("modern-dark")
    assert th.get() == "modern-dark"
    return th


@pytest.mark.usefixtures("local_theme", "omd_site", "request_context")
def test_theme_request_context_integration() -> None:
    theme.from_config("facelift")
    assert theme.get() == "facelift"

    theme.set("")
    assert theme.get() == "facelift"

    theme.set("not_existing")
    assert theme.get() == "facelift"

    theme.set("my_theme")
    assert theme.get() == "my_theme"


@pytest.mark.usefixtures("patch_web_dir")
def test_icon_themes(th: Theme) -> None:
    assert th.icon_themes() == ["modern-dark", "facelift"]

    th.set("facelift")
    assert th.get() == "facelift"
    assert th.icon_themes() == ["facelift"]


@pytest.mark.usefixtures("patch_web_dir")
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


@pytest.mark.usefixtures("patch_web_dir")
def test_url(th: Theme) -> None:
    assert th.url("asd/eee") == "themes/modern-dark/asd/eee"


@pytest.mark.usefixtures("patch_web_dir")
def test_base_dir(th: Theme) -> None:
    assert th.base_dir() == cmk.utils.paths.local_web_dir / "htdocs" / "themes" / "modern-dark"


@pytest.mark.usefixtures("patch_web_dir")
@pytest.mark.parametrize(
    "edition",
    [
        cmk.ccc.version.Edition.CRE,
        cmk.ccc.version.Edition.CEE,
        cmk.ccc.version.Edition.CME,
        cmk.ccc.version.Edition.CCE,
    ],
)
@pytest.mark.parametrize("with_logo", [True, False])
def test_has_custom_logo(
    monkeypatch: MonkeyPatch, th: Theme, edition: cmk.ccc.version.Edition, with_logo: bool
) -> None:
    monkeypatch.setattr("cmk.gui.utils.theme.edition", lambda *args, **kw: edition)
    logo = th.base_dir().joinpath("images", "login_logo.png")
    if with_logo:
        logo.parent.mkdir(parents=True, exist_ok=True)
        logo.touch()
    elif logo.exists():
        logo.unlink()
    assert th.has_custom_logo("login_logo") is (
        edition is cmk.ccc.version.Edition.CME and with_logo
    )


@pytest.mark.usefixtures("patch_web_dir")
def test_modern_dark_images(th: Theme) -> None:
    """For each modern dark image there must be a (default) facelift variant, i.e. a file under the
    same name (may have a different file extension) within the facelift images dir. This holds only
    for the root theme dirs where the builtin images are located, not for the local theme dirs
    (th.base_dir())."""
    root_themes_dir: Path = Path(cmk.utils.paths.web_dir, "htdocs/themes")
    md_images_dir: Path = root_themes_dir / th.get() / "images"
    fl_images_dir: Path = root_themes_dir / "facelift" / "images"

    for md_image in md_images_dir.iterdir():
        if md_image.is_file():
            assert any(
                fl_images_dir.glob(
                    md_image.stem + ".*"
                )  # accept different file extensions per theme as our code does
            ), f"Missing image '{md_image.stem}.*' in the facelift theme"
