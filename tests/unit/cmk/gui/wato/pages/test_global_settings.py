#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterator

import pytest

import cmk.utils.paths
from cmk.ccc import store
from cmk.gui.htmllib.html import _load_vue_manifest
from cmk.gui.watolib.paths import wato_var_dir
from tests.testlib.gui.web_test_app import WebTestAppForCMK


@pytest.fixture(name="frontend_vue_manifest")
def fixture_frontend_vue_manifest() -> Iterator[None]:
    base = cmk.utils.paths.web_dir / "htdocs/cmk-frontend-vue"
    base.mkdir(parents=True, exist_ok=True)
    (base / ".manifest.json").write_text(
        json.dumps(
            {
                "src/main.ts": {"file": "main.js"},
                "src/nav_sidebar.ts": {"file": "nav_sidebar.js"},
                "src/stage1.ts": {"file": "stage1.js"},
            }
        )
    )
    _load_vue_manifest.cache_clear()
    yield
    _load_vue_manifest.cache_clear()


@pytest.mark.usefixtures("frontend_vue_manifest", "patch_theme")
@pytest.mark.parametrize(
    ("old_url", "new_url"),
    [
        ("wato.py?mode=globalvars", "global_settings.py"),
        ("wato.py?mode=edit_configvar&varname=debug", "global_settings.py?varname=debug"),
        ("wato.py?mode=edit_site_globals&site=remote", "site_specific_settings.py?site=remote"),
        (
            "wato.py?mode=edit_site_configvar&site=remote&varname=debug",
            "site_specific_settings.py?site=remote&varname=debug",
        ),
        ("wato.py?mode=mkeventd_config", "event_console_settings.py"),
        (
            "wato.py?mode=mkeventd_edit_configvar&varname=debug",
            "event_console_settings.py?varname=debug",
        ),
    ],
)
def test_a_retired_mode_redirects_to_its_settings_page(
    logged_in_admin_wsgi_app: WebTestAppForCMK, old_url: str, new_url: str
) -> None:
    response = logged_in_admin_wsgi_app.get(f"/NO_SITE/check_mk/{old_url}", status=302)

    assert response.headers["Location"] == new_url


def _config_generation() -> int:
    return int(store.load_object_from_file(wato_var_dir() / "config-generation.mk", default=0))


@pytest.mark.usefixtures("frontend_vue_manifest", "patch_theme")
def test_a_stale_action_url_redirects_without_recording_a_change(
    logged_in_admin_wsgi_app: WebTestAppForCMK,
) -> None:
    generation_before = _config_generation()

    logged_in_admin_wsgi_app.get(
        "/NO_SITE/check_mk/wato.py?mode=globalvars&_action=toggle&_varname=debug&_transid=stale",
        status=302,
    )

    assert _config_generation() == generation_before
