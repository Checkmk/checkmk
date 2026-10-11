#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

import pytest

from cmk.ccc.version import Edition
from cmk.gui.config import Config
from cmk.gui.logged_in import LoggedInSuperUser
from cmk.gui.quick_setup.handlers.utils import InfoLogger
from cmk.gui.quick_setup.v0_unstable.predefined import build_formspec_map_from_stages
from cmk.gui.quick_setup.v0_unstable.setups import (
    QuickSetupAction,
    QuickSetupActionMode,
    QuickSetupContext,
    QuickSetupStage,
)
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId
from cmk.gui.wato.pages.notifications.quick_setup import (
    custom_macros_cannot_be_empty,
    filter_for_hosts_and_services,
    general_properties,
    IsValidRegularExpression,
    load_notifications,
    NonEmptyString,
    notification_method,
    quick_setup_notifications,
    recipient,
    sending_conditions,
    supports_bulk,
    triggering_events,
    validate_at_least_one_event,
)
from cmk.gui.watolib.hosts_and_folders import make_folder_tree
from cmk.gui.watolib.notifications import NotificationRuleConfigFile
from cmk.gui.watolib.user_scripts import NotificationUserScripts
from cmk.rulesets.v1.form_specs.validators import ValidationError
from tests.unit.cmk.gui.helpers.notification_rule_test_helper import mail_rule

_FILTER_FORM_SPEC_IDS = [
    "ec_alert_filters",
    "host_filters",
    "service_filters",
    "assignee_filters",
    "general_filters",
]


# fmt: off
@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    "stage, expected_ids",
    [
        pytest.param(triggering_events, ["triggering_events"], id="triggering_events"),
        pytest.param(filter_for_hosts_and_services, _FILTER_FORM_SPEC_IDS, id="filter_for_hosts_and_services"),
        pytest.param(notification_method, ["notification_method"], id="notification_method"),
        pytest.param(sending_conditions, ["sending_conditions"], id="sending_conditions"),
        pytest.param(general_properties, ["general_properties"], id="general_properties"),
    ],
)
# fmt: on
def test_stage_offers_its_form_specs(
    stage: Callable[[], QuickSetupStage], expected_ids: list[str]
) -> None:
    assert list(build_formspec_map_from_stages([stage()], _context(Config()))) == expected_ids


@pytest.mark.usefixtures("request_context")
def test_recipient_stage_offers_its_form_spec(test_edition: Edition) -> None:
    assert list(
        build_formspec_map_from_stages([recipient(test_edition)], _context(Config()))
    ) == ["recipient"]


# fmt: off
@pytest.mark.parametrize(
    "trigger_events, message",
    [
        pytest.param({}, "At least one triggering event", id="nothing"),
        pytest.param({"host_events": []}, "At least one host event", id="empty-host-events"),
        pytest.param({"service_events": []}, "At least one service event", id="empty-service-events"),
    ],
)
# fmt: on
def test_at_least_one_event_is_required(trigger_events: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        validate_at_least_one_event(trigger_events)


def test_non_empty_string_rejects_whitespace() -> None:
    with pytest.raises(ValidationError, match="Input cannot be empty"):
        NonEmptyString()("   ")


def test_non_empty_string_accepts_text() -> None:
    NonEmptyString()("text")


def test_regular_expression_validator_rejects_invalid_pattern() -> None:
    with pytest.raises(ValidationError, match="regular expression"):
        IsValidRegularExpression()("(unclosed")


def test_regular_expression_validator_accepts_valid_pattern() -> None:
    IsValidRegularExpression()("^web.*$")


@pytest.mark.parametrize(
    "custom_macros, message",
    [
        pytest.param([(" ", " ")], "A macro name and a regular expression", id="both-empty"),
        pytest.param([("", "regex")], "A macro name is required", id="name-empty"),
        pytest.param([("NAME", "")], "A regular expression is required", id="regex-empty"),
    ],
)
def test_custom_macros_need_name_and_regex(
    custom_macros: list[tuple[str, str]], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        custom_macros_cannot_be_empty(custom_macros)


@pytest.mark.parametrize(
    "script_name, expected",
    [
        pytest.param("bulk_script", True, id="bulk"),
        pytest.param("single_script", False, id="no-bulk"),
        pytest.param("unknown", False, id="unknown"),
    ],
)
def test_supports_bulk(script_name: str, expected: bool) -> None:
    scripts: NotificationUserScripts = {
        "bulk_script": {"bulk": True, "title": "Bulk"},
        "single_script": {"bulk": False, "title": "Single"},
    }

    assert supports_bulk(script_name, scripts) is expected


def _rule_descriptions() -> list[str]:
    return [rule["description"] for rule in NotificationRuleConfigFile().load_for_reading()]


def _action(action_id: str, edition: Edition) -> QuickSetupAction:
    return next(
        action for action in quick_setup_notifications(edition).actions if action.id == action_id
    )


def _context(config: Config) -> QuickSetupContext:
    return QuickSetupContext(
        tree=make_folder_tree(config),
        user=LoggedInSuperUser(),
        site_configs=config.sites,
        debug=False,
        use_git=False,
        pprint_value=False,
    )


@pytest.mark.usefixtures("with_admin_login")
def test_loading_an_unknown_rule_yields_no_form_data() -> None:
    assert load_notifications("unknown") == {}


@pytest.mark.usefixtures("with_admin_login")
@pytest.mark.parametrize(
    "action_id, expected_mode",
    [
        pytest.param("apply_and_create_new", "mode=notification_rule_quick_setup", id="new"),
        pytest.param("apply_and_test", "mode=test_notifications", id="test"),
    ],
)
def test_saving_appends_a_rule(
    action_id: str, expected_mode: str, load_config: Config, test_edition: Edition
) -> None:
    NotificationRuleConfigFile().save([mail_rule("existing")], pprint_value=False)
    form_data = load_notifications("existing")

    url = _action(action_id, test_edition).action(
        form_data, QuickSetupActionMode.SAVE, InfoLogger(), None, _context(load_config)
    )

    assert expected_mode in url
    assert _rule_descriptions() == ["existing", "existing"]


@pytest.mark.usefixtures("with_admin_login")
def test_editing_replaces_the_rule_with_the_given_id(
    load_config: Config, test_edition: Edition
) -> None:
    NotificationRuleConfigFile().save(
        [mail_rule("first"), mail_rule("second")], pprint_value=False
    )
    form_data = dict(load_notifications("first"))
    form_data[FormSpecId("general_properties")] = {
        **form_data[FormSpecId("general_properties")],
        "description": "edited",
    }

    url = _action("apply_and_view", test_edition).action(
        form_data, QuickSetupActionMode.EDIT, InfoLogger(), "second", _context(load_config)
    )

    assert "mode=notifications" in url
    assert _rule_descriptions() == ["first", "edited"]
