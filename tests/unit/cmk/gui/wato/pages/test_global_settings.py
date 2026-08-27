#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterable
from typing import override

import pytest
from pytest import MonkeyPatch

from cmk.ccc.version import Edition
from cmk.gui.config import Config
from cmk.gui.form_specs import get_visitor, RawFrontendData, VisitorOptions
from cmk.gui.form_specs._utils import migrate_form_spec_disk_value
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.gui.http import request
from cmk.gui.i18n import _l
from cmk.gui.pages import PageContext
from cmk.gui.plugins.wato.utils import ConfigVariableGroupUserInterface
from cmk.gui.search.matchers import MatchItem
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.valuespec import Password as PasswordValuespec
from cmk.gui.valuespec import TextInput
from cmk.gui.wato._check_mk_configuration import ConfigVariableTableRowLimit
from cmk.gui.wato.pages import global_settings
from cmk.gui.wato.pages.global_settings import (
    DefaultModeEditGlobals,
    MatchItemGeneratorSettings,
)
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    ConfigVariable,
    ConfigVariableGroup,
    ConfigVariableRegistry,
    GlobalSettingsContext,
)
from cmk.gui.watolib.config_domains import ConfigDomainCore, ConfigDomainGUI
from cmk.gui.watolib.global_settings import global_settings_diff_text
from cmk.rulesets.internal.form_specs import SimplePassword
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    FormSpec,
    Integer,
    Password,
)


def test_match_item_generator_settings(
    monkeypatch: MonkeyPatch,
    request_context: None,
    test_edition: Edition,
) -> None:
    group = ConfigVariableGroup(
        title=_l("xyz"),
        sort_index=10,
    )

    config_variable = ConfigVariable(
        group=group,
        primary_domain=ConfigDomainCore,
        ident="ident",
        valuespec=lambda context: TextInput(title="title"),
    )

    class SomeSettingsMode(DefaultModeEditGlobals):
        @override
        def iter_all_configuration_variables(
            self, *, debug: bool
        ) -> Iterable[tuple[ConfigVariableGroup, Iterable[ConfigVariable]]]:
            return [
                (
                    group,
                    [config_variable],
                )
            ]

    monkeypatch.setattr(ABCConfigDomain, "get_all_default_globals", dict)

    assert list(
        MatchItemGeneratorSettings(
            "settings",
            "Settings",
            lambda: SomeSettingsMode(test_edition, PageContext(config=Config(), request=request)),
        ).generate_match_items(UserPermissions({}, {}, {}, []))
    ) == [
        MatchItem(
            title="title",
            topic="Settings",
            url="wato.py?mode=edit_configvar&varname=ident",
            match_texts=["title", "ident"],
        ),
    ]


def test_match_item_generator_settings_looks_through_transform(
    monkeypatch: MonkeyPatch,
    request_context: None,
    test_edition: Edition,
) -> None:
    # TransformDataForLegacyFormatOrRecomposeFunction is a transparent wrapper without a
    # title of its own, so the title has to be taken from the wrapped form spec.
    group = ConfigVariableGroup(
        title=_l("xyz"),
        sort_index=10,
    )

    config_variable = ConfigVariable(
        group=group,
        primary_domain=ConfigDomainCore,
        ident="ident",
        form_spec=lambda context: TransformDataForLegacyFormatOrRecomposeFunction(
            wrapped_form_spec=Integer(title=Title("Wrapped title")),
            from_disk=lambda value: value,
            to_disk=lambda value: value,
        ),
    )

    class SomeSettingsMode(DefaultModeEditGlobals):
        @override
        def iter_all_configuration_variables(
            self, *, debug: bool
        ) -> Iterable[tuple[ConfigVariableGroup, Iterable[ConfigVariable]]]:
            return [(group, [config_variable])]

    monkeypatch.setattr(ABCConfigDomain, "get_all_default_globals", dict)

    assert [
        match_item.title
        for match_item in MatchItemGeneratorSettings(
            "settings",
            "Settings",
            lambda: SomeSettingsMode(test_edition, PageContext(config=Config(), request=request)),
        ).generate_match_items(UserPermissions({}, {}, {}, []))
    ] == ["Wrapped title"]


@pytest.mark.usefixtures("load_config")
def test_parse_submitted_value_keeps_cleartext_password_for_storage(
    monkeypatch: MonkeyPatch,
    test_edition: Edition,
) -> None:
    registry = ConfigVariableRegistry()
    registry.register(
        ConfigVariable(
            group=ConfigVariableGroupUserInterface,
            primary_domain=ConfigDomainGUI,
            ident="test_secret",
            form_spec=lambda context: Password(title=Title("Secret")),
        )
    )
    monkeypatch.setattr(global_settings, "config_variable_registry", registry)

    request.set_var("varname", "test_secret")
    # PasswordVisitor frontend model: (type, password_id, password, encrypted)
    request.set_var("_vue_global_settings", json.dumps(["explicit_password", "", "hunter2", False]))

    submitted = global_settings.ModeEditGlobalSetting(
        test_edition, PageContext(config=Config(), request=request)
    )._parse_submitted_value()

    assert isinstance(submitted, tuple)
    password_id_and_value = submitted[2]
    assert isinstance(password_id_and_value, tuple)
    assert password_id_and_value[1] == "hunter2"


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


def _valuespec_config_variable() -> ConfigVariable:
    return ConfigVariable(
        group=ConfigVariableGroup(title=_l("Test"), sort_index=10),
        primary_domain=ConfigDomainCore,
        ident="test_setting",
        valuespec=lambda context: TextInput(),
    )


def _form_spec_config_variable() -> ConfigVariable:
    return ConfigVariable(
        group=ConfigVariableGroup(title=_l("Test"), sort_index=10),
        primary_domain=ConfigDomainCore,
        ident="test_setting",
        form_spec=lambda context: Integer(),
    )


def test_diff_text_valuespec_value_changed(
    global_settings_context: GlobalSettingsContext,
) -> None:
    assert (
        global_settings_diff_text(
            _valuespec_config_variable(),
            global_settings_context,
            {"test_setting": "before"},
            {"test_setting": "after"},
        )
        == 'Value of "test_setting" changed from "before" to "after".'
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


def test_diff_text_valuespec_secret_is_redacted(
    global_settings_context: GlobalSettingsContext,
) -> None:
    config_variable = ConfigVariable(
        group=ConfigVariableGroup(title=_l("Test"), sort_index=10),
        primary_domain=ConfigDomainCore,
        ident="test_setting",
        valuespec=lambda context: PasswordValuespec(),
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


def test_diff_text_form_spec_secret_is_redacted(
    global_settings_context: GlobalSettingsContext,
) -> None:
    config_variable = ConfigVariable(
        group=ConfigVariableGroup(title=_l("Test"), sort_index=10),
        primary_domain=ConfigDomainCore,
        ident="test_setting",
        form_spec=lambda context: SimplePassword(),
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
