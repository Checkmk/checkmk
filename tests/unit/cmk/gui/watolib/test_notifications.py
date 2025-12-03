#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.ccc import version
from cmk.gui.watolib.notifications import ContactSelection, NotificationRule
from cmk.utils.notify_types import EventRule, NotificationRuleID


def _create_base_event_rule() -> EventRule:
    """Create a minimal valid EventRule for testing."""
    return EventRule(
        rule_id=NotificationRuleID("test-rule-id"),
        allow_disable=True,
        contact_all=False,
        contact_all_with_email=False,
        contact_object=True,
        description="Test notification rule",
        disabled=False,
        notify_plugin=("mail", None),
    )


def test_contact_selection_explicit_email_addresses_in_cloud_edition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that explicit_email_addresses is None in CLOUD edition even if contact_emails exists."""
    monkeypatch.setattr(
        "cmk.gui.watolib.notifications.version.edition",
        lambda _: version.Edition.CLOUD,
    )

    event_rule = _create_base_event_rule()
    event_rule["contact_emails"] = ["test@example.com", "admin@example.com"]

    contact_selection = ContactSelection.from_mk_file_format(event_rule)

    assert contact_selection.explicit_email_addresses is None


@pytest.mark.parametrize(
    "edition",
    [
        version.Edition.COMMUNITY,
        version.Edition.PRO,
        version.Edition.ULTIMATE,
        version.Edition.ULTIMATEMT,
    ],
)
def test_contact_selection_explicit_email_addresses_in_non_cloud_editions(
    monkeypatch: pytest.MonkeyPatch, edition: version.Edition
) -> None:
    """Test that explicit_email_addresses is available and parsed in all non-cloud editions."""
    monkeypatch.setattr(
        "cmk.gui.watolib.notifications.version.edition",
        lambda _: edition,
    )

    event_rule = _create_base_event_rule()
    event_rule["contact_emails"] = ["test@example.com", "admin@example.com"]

    contact_selection = ContactSelection.from_mk_file_format(event_rule)

    assert contact_selection.explicit_email_addresses is not None
    assert contact_selection.explicit_email_addresses.value == [
        "test@example.com",
        "admin@example.com",
    ]


def test_contact_selection_from_mk_file_can_be_converted_to_api_response_cloud(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that ContactSelection from mk file format can be converted to API response in CLOUD."""
    monkeypatch.setattr(
        "cmk.gui.watolib.notifications.version.edition",
        lambda _: version.Edition.CLOUD,
    )

    event_rule = _create_base_event_rule()
    event_rule["contact_object"] = True
    event_rule["contact_users"] = ["user1", "user2"]
    event_rule["contact_groups"] = ["group1"]
    event_rule["contact_emails"] = ["ignored@example.com"]  # Should be ignored in cloud

    contact_selection = ContactSelection.from_mk_file_format(event_rule)
    api_response = contact_selection.api_response()

    # Verify API response structure
    assert api_response["all_contacts_of_the_notified_object"]["state"] == "enabled"
    assert api_response["the_following_users"]["state"] == "enabled"
    assert api_response["the_following_users"]["value"] == ["user1", "user2"]
    assert api_response["members_of_contact_groups"]["state"] == "enabled"
    assert api_response["members_of_contact_groups"]["value"] == ["group1"]
    # explicit_email_addresses should not be in the API response for cloud
    assert "explicit_email_addresses" not in api_response


@pytest.mark.parametrize(
    "edition",
    [
        version.Edition.COMMUNITY,
        version.Edition.PRO,
        version.Edition.ULTIMATE,
        version.Edition.ULTIMATEMT,
    ],
)
def test_contact_selection_from_mk_file_can_be_converted_to_api_response_non_cloud(
    monkeypatch: pytest.MonkeyPatch, edition: version.Edition
) -> None:
    """Test that ContactSelection from mk file format can be converted to API response in non-cloud editions."""
    monkeypatch.setattr(
        "cmk.gui.watolib.notifications.version.edition",
        lambda _: edition,
    )

    event_rule = _create_base_event_rule()
    event_rule["contact_object"] = True
    event_rule["contact_users"] = ["user1", "user2"]
    event_rule["contact_groups"] = ["group1"]
    event_rule["contact_emails"] = ["test@example.com", "admin@example.com"]

    contact_selection = ContactSelection.from_mk_file_format(event_rule)
    api_response = contact_selection.api_response()

    # Verify API response structure
    assert api_response["all_contacts_of_the_notified_object"]["state"] == "enabled"
    assert api_response["the_following_users"]["state"] == "enabled"
    assert api_response["the_following_users"]["value"] == ["user1", "user2"]
    assert api_response["members_of_contact_groups"]["state"] == "enabled"
    assert api_response["members_of_contact_groups"]["value"] == ["group1"]
    # explicit_email_addresses SHOULD be in the API response for non-cloud editions
    assert "explicit_email_addresses" in api_response
    assert api_response["explicit_email_addresses"]["state"] == "enabled"
    assert api_response["explicit_email_addresses"]["value"] == [
        "test@example.com",
        "admin@example.com",
    ]


def test_notification_rule_ignores_explicit_email_addresses_cloud(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that NotificationRule works correctly when explicit_email_addresses is None (CLOUD edition)."""
    monkeypatch.setattr(
        "cmk.gui.watolib.notifications.version.edition",
        lambda _: version.Edition.CLOUD,
    )

    # Create a complete EventRule with contact_emails
    event_rule = _create_base_event_rule()
    event_rule["contact_object"] = True
    event_rule["contact_users"] = ["user1"]
    event_rule["contact_emails"] = ["should_be_ignored@cloud.com"]

    # Create NotificationRule from mk file format
    notification_rule = NotificationRule.from_mk_file_format(event_rule)

    # Verify ContactSelection has None for explicit_email_addresses
    assert notification_rule.contact_selection.explicit_email_addresses is None

    # Test api_response() doesn't crash and doesn't include explicit_email_addresses
    api_response = notification_rule.api_response()
    assert "explicit_email_addresses" not in api_response["contact_selection"]

    # Test to_mk_file_format() doesn't include contact_emails
    mk_format = notification_rule.to_mk_file_format(pprint_value=False)
    assert "contact_emails" not in mk_format


@pytest.mark.parametrize(
    "edition",
    [
        version.Edition.COMMUNITY,
        version.Edition.PRO,
        version.Edition.ULTIMATE,
        version.Edition.ULTIMATEMT,
    ],
)
def test_notification_rule_with_explicit_email_addresses_non_cloud(
    monkeypatch: pytest.MonkeyPatch, edition: version.Edition
) -> None:
    """Test that NotificationRule works correctly when explicit_email_addresses has a value (non-CLOUD editions)."""
    monkeypatch.setattr(
        "cmk.gui.watolib.notifications.version.edition",
        lambda _: edition,
    )

    # Create a complete EventRule with contact_emails
    event_rule = _create_base_event_rule()
    event_rule["contact_object"] = True
    event_rule["contact_users"] = ["user1"]
    event_rule["contact_emails"] = ["test@example.com", "admin@example.com"]

    # Create NotificationRule from mk file format
    notification_rule = NotificationRule.from_mk_file_format(event_rule)

    # Verify ContactSelection has explicit_email_addresses populated
    assert notification_rule.contact_selection.explicit_email_addresses is not None
    assert notification_rule.contact_selection.explicit_email_addresses.value == [
        "test@example.com",
        "admin@example.com",
    ]

    # Test api_response() includes explicit_email_addresses
    api_response = notification_rule.api_response()
    assert "explicit_email_addresses" in api_response["contact_selection"]
    assert api_response["contact_selection"]["explicit_email_addresses"]["state"] == "enabled"
    assert api_response["contact_selection"]["explicit_email_addresses"]["value"] == [
        "test@example.com",
        "admin@example.com",
    ]

    # Test to_mk_file_format() includes contact_emails
    mk_format = notification_rule.to_mk_file_format(pprint_value=False)
    assert mk_format["contact_emails"] == ["test@example.com", "admin@example.com"]


def test_notification_rule_roundtrip_ignores_explicit_email_addresses_handling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.watolib.notifications.version.edition",
        lambda _: version.Edition.CLOUD,
    )

    event_rule_cloud = _create_base_event_rule()
    event_rule_cloud["contact_emails"] = ["cloud@example.com"]
    event_rule_cloud["contact_users"] = ["user1"]

    rule_cloud = NotificationRule.from_mk_file_format(event_rule_cloud)
    mk_format_cloud = rule_cloud.to_mk_file_format(pprint_value=False)

    assert "contact_emails" not in mk_format_cloud
    assert mk_format_cloud["contact_users"] == ["user1"]


@pytest.mark.parametrize(
    "edition",
    [
        version.Edition.COMMUNITY,
        version.Edition.PRO,
        version.Edition.ULTIMATE,
        version.Edition.ULTIMATEMT,
    ],
)
def test_notification_rule_roundtrip_preserves_explicit_email_addresses_handling(
    monkeypatch: pytest.MonkeyPatch, edition: version.Edition
) -> None:
    monkeypatch.setattr(
        "cmk.gui.watolib.notifications.version.edition",
        lambda _: edition,
    )

    event_rule_cloud = _create_base_event_rule()
    event_rule_cloud["contact_emails"] = ["cloud@example.com"]
    event_rule_cloud["contact_users"] = ["user1"]

    rule_cloud = NotificationRule.from_mk_file_format(event_rule_cloud)
    mk_format_cloud = rule_cloud.to_mk_file_format(pprint_value=False)

    assert mk_format_cloud["contact_users"] == ["user1"]
    assert mk_format_cloud["contact_emails"] == ["cloud@example.com"]
