#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Generator

import pytest
from pytest_mock import MockerFixture

from cmk.automations.results import DeleteHostsResult, GetServicesLabelsResult
from cmk.ccc.hostaddress import HostName
from cmk.ccc.user import UserId
from cmk.gui.watolib.audit_log import AuditLogStore
from cmk.gui.watolib.hosts_and_folders import folder_tree, Host
from cmk.gui.watolib.rulesets import (
    EnabledDisabledServicesEditor,
    FolderRulesets,
    Rule,
    RuleConditions,
    RuleOptions,
    Ruleset,
    service_description_to_condition,
)
from cmk.utils.automation_config import LocalAutomationConfig


@pytest.fixture(name="sample_host")
def fixture_sample_host(
    request_context: None,
    with_admin_login: UserId,
) -> Generator[Host]:
    hostname = HostName("heute")
    root_folder = folder_tree().root_folder()
    root_folder.create_hosts([(hostname, {}, None)], pprint_value=False, use_git=False)
    host = root_folder.host(hostname)
    assert host is not None
    yield host
    root_folder.delete_hosts(
        [hostname],
        automation=lambda *args, **kwargs: DeleteHostsResult(),
        pprint_value=False,
        debug=False,
        use_git=False,
    )


@pytest.fixture(name="mock_get_services_labels")
def fixture_mock_get_services_labels(mocker: MockerFixture) -> None:
    """The editor calls get_services_labels() via an automation to check whether a service is
    still disabled by other rules. Short-circuit it to empty labels per requested service so the
    test does not need a running site."""
    mocker.patch(
        "cmk.gui.watolib.rulesets.get_services_labels",
        side_effect=lambda _config, _host, services, **_kw: GetServicesLabelsResult(
            labels={service: {} for service in services}
        ),
    )


@pytest.fixture(name="mock_analyse_ruleset_no_other_match")
def fixture_mock_analyse_ruleset_no_other_match(mocker: MockerFixture) -> None:
    """The editor also calls Ruleset.analyse_ruleset() to check whether services are still
    disabled by other rules; that in turn issues an analyze-service-rule-matches automation.
    In these tests no other rule exists, so pretend no rule matches."""
    mocker.patch(
        "cmk.gui.watolib.rulesets.Ruleset.analyse_ruleset",
        return_value=(None, []),
    )


def _seed_host_disable_rule(host: Host, service_descriptions: list[str]) -> None:
    """Persist an ignored_services rule that disables ``service_descriptions`` on ``host``."""
    folder = host.folder()
    ruleset = Ruleset("ignored_services")
    ruleset.append_rule(
        folder,
        Rule(
            id_="seeded-rule",
            folder=folder,
            ruleset=ruleset,
            conditions=RuleConditions(
                host_folder=folder.path(),
                host_name=[host.name()],
                service_description=[
                    service_description_to_condition(s) for s in service_descriptions
                ],
            ),
            options=RuleOptions(
                disabled=False,
                description="",
                comment="",
                docu_url="",
            ),
            value=True,
        ),
    )
    FolderRulesets({ruleset.name: ruleset}, folder=folder).save_folder(
        pprint_value=False, debug=False
    )


def _new_ignored_services_entries(entries_before: int) -> list[AuditLogStore.Entry]:
    """Return audit entries added since ``entries_before`` that mention the Disabled services
    ruleset."""
    return [
        e
        for e in AuditLogStore().read()[entries_before:]
        if 'rule set "Disabled services"' in str(e.text)
    ]


@pytest.mark.usefixtures("mock_get_services_labels", "mock_analyse_ruleset_no_other_match")
def test_disable_service_produces_audit_log_entry(sample_host: Host) -> None:
    """Disabling a service on a host with no existing ignored_services rule must produce a
    'new-rule' audit-log entry for the Disabled services ruleset."""
    entries_before = len(AuditLogStore().read())

    EnabledDisabledServicesEditor(sample_host).save_host_service_enable_disable_rules(
        to_enable=set(),
        to_disable={"Foo"},
        automation_config=LocalAutomationConfig(),
        pprint_value=False,
        debug=False,
        use_git=False,
    )

    new_entries = _new_ignored_services_entries(entries_before)
    assert len(new_entries) == 1, (
        f"expected exactly one Disabled-services audit entry, got {len(new_entries)}: "
        f"{[(e.action, str(e.text)) for e in new_entries]}"
    )
    assert new_entries[0].action == "new-rule"


@pytest.mark.usefixtures("mock_get_services_labels", "mock_analyse_ruleset_no_other_match")
def test_disable_second_service_produces_audit_log_entry(sample_host: Host) -> None:
    """Disabling another service on a host that already has an ignored_services rule must
    produce an 'edit-rule' audit-log entry for the Disabled services ruleset."""
    _seed_host_disable_rule(sample_host, ["Foo"])
    entries_before = len(AuditLogStore().read())

    EnabledDisabledServicesEditor(sample_host).save_host_service_enable_disable_rules(
        to_enable=set(),
        to_disable={"Bar"},
        automation_config=LocalAutomationConfig(),
        pprint_value=False,
        debug=False,
        use_git=False,
    )

    new_entries = _new_ignored_services_entries(entries_before)
    assert len(new_entries) == 1, (
        f"expected exactly one Disabled-services audit entry, got {len(new_entries)}: "
        f"{[(e.action, str(e.text)) for e in new_entries]}"
    )
    assert new_entries[0].action == "edit-rule"


@pytest.mark.usefixtures("mock_get_services_labels", "mock_analyse_ruleset_no_other_match")
def test_enable_last_disabled_service_produces_audit_log_entry(sample_host: Host) -> None:
    """Enabling the only disabled service of a host deletes the ignored_services rule and must
    produce an 'edit-rule' / 'Deleted rule' audit-log entry. This is the one path that already
    works today; the test guards against regression as we rewrite the editor."""
    _seed_host_disable_rule(sample_host, ["Foo"])
    entries_before = len(AuditLogStore().read())

    EnabledDisabledServicesEditor(sample_host).save_host_service_enable_disable_rules(
        to_enable={"Foo"},
        to_disable=set(),
        automation_config=LocalAutomationConfig(),
        pprint_value=False,
        debug=False,
        use_git=False,
    )

    new_entries = _new_ignored_services_entries(entries_before)
    assert len(new_entries) == 1, (
        f"expected exactly one Disabled-services audit entry, got {len(new_entries)}: "
        f"{[(e.action, str(e.text)) for e in new_entries]}"
    )
    assert new_entries[0].action == "edit-rule"
    assert "Deleted rule" in str(new_entries[0].text)


@pytest.mark.usefixtures("mock_get_services_labels", "mock_analyse_ruleset_no_other_match")
def test_enable_one_of_multiple_disabled_services_produces_audit_log_entry(
    sample_host: Host,
) -> None:
    """Enabling one of several disabled services trims the ignored_services rule but keeps it
    alive. That path currently emits no audit entry."""
    _seed_host_disable_rule(sample_host, ["Foo", "Bar"])
    entries_before = len(AuditLogStore().read())

    EnabledDisabledServicesEditor(sample_host).save_host_service_enable_disable_rules(
        to_enable={"Foo"},
        to_disable=set(),
        automation_config=LocalAutomationConfig(),
        pprint_value=False,
        debug=False,
        use_git=False,
    )

    new_entries = _new_ignored_services_entries(entries_before)
    assert len(new_entries) == 1, (
        f"expected exactly one Disabled-services audit entry, got {len(new_entries)}: "
        f"{[(e.action, str(e.text)) for e in new_entries]}"
    )
    assert new_entries[0].action == "edit-rule"
