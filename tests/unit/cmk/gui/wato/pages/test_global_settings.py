#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterator

import pytest

import cmk.utils.paths
from cmk.ccc import store
from cmk.gui.form_specs import get_visitor, RawFrontendData, VisitorOptions
from cmk.gui.form_specs._utils import migrate_form_spec_disk_value
from cmk.gui.htmllib.html import _load_vue_manifest
from cmk.gui.i18n import _l
from cmk.gui.wato._check_mk_configuration import ConfigVariableTableRowLimit
from cmk.gui.watolib.config_domain_name import (
    ConfigVariable,
    ConfigVariableGroup,
    GlobalSettingsContext,
)
from cmk.gui.watolib.config_domains import ConfigDomainCore
from cmk.gui.watolib.global_settings import global_settings_diff_text
from cmk.gui.watolib.paths import wato_var_dir
from cmk.rulesets.internal.form_specs import SimplePassword
from cmk.rulesets.v1.form_specs import DefaultValue, FormSpec, Integer
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


def _table_row_limit_form_spec(context: GlobalSettingsContext) -> Integer:
    form_spec = ConfigVariableTableRowLimit.value_model(context)
    assert isinstance(form_spec, Integer)
    return form_spec


def test_table_row_limit_uses_form_spec_backend(
    global_settings_context: GlobalSettingsContext,
) -> None:
    assert isinstance(ConfigVariableTableRowLimit.value_model(global_settings_context), FormSpec)


def test_table_row_limit_default_matches_general_config(
    global_settings_context: GlobalSettingsContext,
) -> None:
    assert _table_row_limit_form_spec(global_settings_context).prefill == DefaultValue(100)


def test_table_row_limit_valid_value_round_trips_as_int(
    global_settings_context: GlobalSettingsContext,
) -> None:
    visitor = get_visitor(
        _table_row_limit_form_spec(global_settings_context),
        VisitorOptions(migrate_values=False, mask_values=False),
    )
    assert visitor.validate(RawFrontendData(50)) == []
    assert visitor.to_disk(RawFrontendData(50)) == 50


def test_table_row_limit_rejects_value_below_minimum(
    global_settings_context: GlobalSettingsContext,
) -> None:
    visitor = get_visitor(
        _table_row_limit_form_spec(global_settings_context),
        VisitorOptions(migrate_values=False, mask_values=False),
    )
    assert visitor.validate(RawFrontendData(0))


def test_table_row_limit_upgrade_keeps_stored_int(
    global_settings_context: GlobalSettingsContext,
) -> None:
    assert (
        migrate_form_spec_disk_value(_table_row_limit_form_spec(global_settings_context), 42) == 42
    )


def _form_spec_config_variable() -> ConfigVariable:
    return ConfigVariable(
        group=ConfigVariableGroup(title=_l("Test"), sort_index=10),
        primary_domain=ConfigDomainCore,
        ident="test_setting",
        form_spec=lambda context: Integer(),  # noqa: ARG005
    )


def test_diff_text_form_spec_value_changed(
    global_settings_context: GlobalSettingsContext,
) -> None:
    assert (
        global_settings_diff_text(
            _form_spec_config_variable(),
            global_settings_context,
            {"test_setting": 100},
            {"test_setting": 66},
        )
        == 'Value of "test_setting" changed from 100 to 66.'
    )


def test_diff_text_first_override_reads_as_added(
    global_settings_context: GlobalSettingsContext,
) -> None:
    assert (
        global_settings_diff_text(
            _form_spec_config_variable(),
            global_settings_context,
            {},
            {"test_setting": 66},
        )
        == 'Attribute "test_setting" with value 66 added.'
    )


def test_diff_text_reset_reads_as_removed(
    global_settings_context: GlobalSettingsContext,
) -> None:
    assert (
        global_settings_diff_text(
            _form_spec_config_variable(),
            global_settings_context,
            {"test_setting": 100},
            {},
        )
        == 'Attribute "test_setting" with value 100 removed.'
    )


def test_diff_text_form_spec_secret_is_redacted(
    global_settings_context: GlobalSettingsContext,
) -> None:
    config_variable = ConfigVariable(
        group=ConfigVariableGroup(title=_l("Test"), sort_index=10),
        primary_domain=ConfigDomainCore,
        ident="test_setting",
        form_spec=lambda context: SimplePassword(),  # noqa: ARG005
    )
    diff_text = global_settings_diff_text(
        config_variable,
        global_settings_context,
        {"test_setting": "old-secret"},
        {"test_setting": "new-secret"},
    )
    assert diff_text == "Redacted secrets changed."
    assert "old-secret" not in diff_text
    assert "new-secret" not in diff_text
