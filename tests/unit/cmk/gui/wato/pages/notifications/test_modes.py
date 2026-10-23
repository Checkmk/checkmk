#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Sequence
from datetime import datetime

import pytest
from bs4 import BeautifulSoup
from pytest_mock import MockerFixture

import cmk.utils.paths
from cmk.automations.internal import AutomationResult
from cmk.automations.results import (
    NotificationAnalyseResult,
    NotificationGetBulksResult,
    NotificationReplayResult,
    NotificationTestResult,
)
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId
from cmk.ccc.version import __version__, Edition
from cmk.events.notify_types import (
    AlwaysBulkParameters,
    EventRule,
    NotificationParameterGeneralInfos,
    NotificationParameterID,
    NotificationParameterItem,
    NotifyAnalysisInfo,
    NotifyBulks,
)
from cmk.gui import userdb
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.logged_in import save_user_file
from cmk.gui.wato.pages.notifications.modes import (
    get_disabled_notifications_infos,
    get_total_sent_notifications,
    ModeAnalyzeNotifications,
    ModeEditNotificationParameter,
    ModeEditUserNotificationRule,
    ModeNotificationParameters,
    ModeNotificationParametersOverview,
    ModeNotifications,
    ModePersonalUserNotifications,
    ModeTestNotifications,
    ModeUserNotifications,
)
from cmk.gui.watolib.notifications import (
    NotificationParameterConfigFile,
    NotificationRuleConfigFile,
)
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.unit.cmk.gui.helpers.notification_rule_test_helper import mail_rule
from tests.unit.cmk.gui.helpers.setup_mode_test_helper import (
    data_table,
    form_values,
    icon_titles,
    link_vars,
    page_context,
    redirect_vars,
    render_page,
    set_request_vars,
    submit,
    table_rows,
    TableRow,
)

pytestmark = pytest.mark.usefixtures("request_context", "with_admin_login", "patch_theme")


class _Automations:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []
        self.results: dict[str, AutomationResult] = {
            "notification-get-bulks": NotificationGetBulksResult(result=[]),
        }
        self.failing: set[str] = set()

    def local(
        self, *, command: str, args: Sequence[str] | None = None, **_kw: object
    ) -> tuple[Sequence[str], str]:
        self.calls.append((command, tuple(args or ())))
        if command in self.failing:
            raise MKGeneralException(f"{command} failed")
        return ["cmk", "--automation", command], self.results[command].serialize(__version__)


@pytest.fixture(name="automations")
def fixture_automations(mocker: MockerFixture) -> _Automations:
    # Tech debt: the automation helpers hard-code their transport, so there is nothing to inject.
    automations = _Automations()
    mocker.patch(
        "cmk.gui.watolib.check_mk_automations.check_mk_local_automation_serialized",
        side_effect=automations.local,
    )
    return automations


def _save_rules(rules: list[EventRule]) -> None:
    NotificationRuleConfigFile().save(rules, pprint_value=False)


def _rule_descriptions() -> list[str]:
    return [rule["description"] for rule in NotificationRuleConfigFile().load_for_reading()]


def _save_user_rules(user_id: UserId, rules: list[EventRule]) -> None:
    users = userdb.load_users(lock=True)
    users[user_id]["notification_rules"] = rules
    userdb.save_users(
        users,
        userdb.get_user_attributes([]),
        [],
        now=datetime.now(),
        pprint_value=False,
        call_users_saved_hook=False,
    )


def _user_rule_descriptions(user_id: UserId) -> list[str]:
    return [
        rule["description"] for rule in userdb.load_users()[user_id].get("notification_rules", [])
    ]


def _save_backlog(backlog: list[dict[str, str]]) -> None:
    path = cmk.utils.paths.var_dir / "notify/backlog.mk"
    path.parent.mkdir(parents=True, exist_ok=True)
    store.save_object_to_file(path, backlog)


def _save_parameters(method: str, descriptions: Sequence[str]) -> list[NotificationParameterID]:
    parameter_ids = [NotificationParameterID(f"param_{nr}") for nr in range(len(descriptions))]
    NotificationParameterConfigFile().save(
        {
            method: {
                parameter_id: NotificationParameterItem(
                    general=NotificationParameterGeneralInfos(
                        description=description, comment="", docu_url="https://docs.example"
                    ),
                    parameter_properties={},
                )
                for parameter_id, description in zip(parameter_ids, descriptions)
            }
        },
        pprint_value=False,
    )
    return parameter_ids


def _parameter_descriptions(method: str) -> list[str]:
    return [
        parameter["general"]["description"]
        for parameter in NotificationParameterConfigFile().load_for_reading()[method].values()
    ]


@pytest.fixture(name="live")
def fixture_live(mock_livestatus: MockLiveStatusConnection) -> MockLiveStatusConnection:
    mock_livestatus.set_sites(["NO_SITE"])
    status_row = mock_livestatus.tables["status"]["NO_SITE"][0]
    mock_livestatus.add_table("status", [{**status_row, "enable_notifications": 0}])
    now = int(time.time())
    mock_livestatus.add_table(
        "log",
        [
            {
                "class": 3,
                "time": now,
                "log_time": now,
                "log_state": state,
                "log_type": log_type,
                "log_command_name": command,
            }
            for state, log_type, command in [
                (0, "HOST NOTIFICATION RESULT", "mail"),
                (2, "SERVICE NOTIFICATION RESULT", "mail"),
                (0, "HOST NOTIFICATION RESULT", "check-mk-notify"),
            ]
        ],
    )
    return mock_livestatus


def test_sites_with_disabled_notifications_are_reported(live: MockLiveStatusConnection) -> None:
    live.expect_query(["GET status", "Columns: enable_notifications"], match_type="loose")

    with live:
        assert get_disabled_notifications_infos() == (1, ["NO_SITE"])


def test_sent_notifications_exclude_the_internal_notify_command(
    live: MockLiveStatusConnection,
) -> None:
    live.expect_query(["GET log", "Stats: class = 3"], match_type="loose")

    with live:
        assert get_total_sent_notifications(from_timestamp=0) == 2


def test_overview_shows_the_notification_figures(
    live: MockLiveStatusConnection,
    load_config: Config,
    test_edition: Edition,
    with_admin_login: UserId,
) -> None:
    save_user_file("acknowledged_notifications", int(time.time()) - 60, with_admin_login)
    live.expect_query(["GET status", "Columns: enable_notifications"], match_type="loose")
    live.expect_query(["GET log", "Stats: class = 3"], match_type="loose")
    live.expect_query(["GET log", "Stats: log_state != 0"], match_type="loose")

    with live:
        page = render_page(ModeNotifications(test_edition, page_context(load_config)), load_config)

    overview_tag = BeautifulSoup(page, "html.parser").select_one("cmk-notification-overview")
    assert overview_tag is not None
    overview = json.loads(str(overview_tag["data"]))
    assert overview["notification_stats"]["num_sent_notifications"] == 2
    assert overview["notification_stats"]["num_failed_notifications"] == 1
    assert overview["core_stats"]["sites"] == ["NO_SITE"]
    assert overview["fallback_warning"] is not None


def _detailed_rule() -> EventRule:
    rule = mail_rule("detailed rule")
    rule["disabled"] = True
    rule["contact_all"] = True
    rule["contact_all_with_email"] = True
    rule["contact_users"] = ["ghost"]
    rule["contact_groups"] = ["admins"]
    rule["contact_emails"] = ["ops@example.com"]
    rule["docu_url"] = "https://docs.example/rule"
    rule["match_hosts"] = ["web01"]
    rule["bulk"] = ("always", AlwaysBulkParameters(interval=60, count=10, groupby=["host"]))
    return rule


def _nobody_rule() -> EventRule:
    rule = mail_rule("cancelling rule", parameter_id=None)
    rule["contact_object"] = False
    return rule


def _global_rule_rows(load_config: Config, test_edition: Edition) -> list[TableRow]:
    _save_rules([_detailed_rule(), _nobody_rule()])
    page = render_page(
        ModeAnalyzeNotifications(test_edition, page_context(load_config)), load_config
    )
    return table_rows(page, "Global notification rules")


@pytest.mark.usefixtures("automations")
def test_analysis_rule_table_lists_the_contacts(load_config: Config, test_edition: Edition) -> None:
    rows = _global_rule_rows(load_config, test_edition)

    assert [
        [li.get_text() for li in row["Contacts"].select("li")]
        or [row["Contacts"].get_text(strip=True)]
        for row in rows
    ] == [
        [
            "all contacts of the notified object",
            "all users",
            "all users with an email address",
            "users: ghost",
            "contact groups: admins",
            "email addresses: ops@example.com",
        ],
        ["(no one)"],
    ]


@pytest.mark.usefixtures("automations")
def test_analysis_rule_table_warns_about_an_unknown_contact_user(
    load_config: Config, test_edition: Edition
) -> None:
    rows = _global_rule_rows(load_config, test_edition)

    assert icon_titles(rows[0]["Contacts"]) == ["User ghost does not exist."]


@pytest.mark.usefixtures("automations")
def test_analysis_rule_table_shows_the_effect(load_config: Config, test_edition: Edition) -> None:
    rows = _global_rule_rows(load_config, test_edition)

    assert [icon_titles(row["Effect"]) for row in rows] == [
        ["Create a notification"],
        ["Cancel notifications for this plug-in type"],
    ]


@pytest.mark.usefixtures("automations")
def test_analysis_rule_table_marks_bulk_rules(load_config: Config, test_edition: Edition) -> None:
    rows = _global_rule_rows(load_config, test_edition)

    assert [icon_titles(row["Bulk"]) for row in rows] == [
        ["This rule configures bulk notifications."],
        [],
    ]


@pytest.mark.usefixtures("automations")
def test_analysis_rule_table_counts_the_conditions(
    load_config: Config, test_edition: Edition
) -> None:
    rows = _global_rule_rows(load_config, test_edition)

    folded_conditions = rows[0]["Conditions"].select_one(".foldable_header")
    assert folded_conditions is not None
    assert (
        folded_conditions.get_text(strip=True),
        rows[1]["Conditions"].get_text(strip=True),
    ) == ("1 conditions", "(no conditions)")


@pytest.mark.usefixtures("automations")
def test_analysis_rule_table_edits_rules_in_the_quick_setup(
    load_config: Config, test_edition: Edition
) -> None:
    rows = _global_rule_rows(load_config, test_edition)

    assert link_vars(rows[0]["Actions"])["mode"] == "notification_rule_quick_setup"


@pytest.mark.usefixtures("automations")
def test_showing_user_rules_lists_them_below_the_global_rules(
    load_config: Config,
    test_edition: Edition,
    with_admin_login: UserId,
) -> None:
    _save_user_rules(with_admin_login, [mail_rule("personal rule")])
    submit(_show_user="1")
    ModeAnalyzeNotifications(test_edition, page_context(load_config)).action(load_config)
    request.del_var("_show_user")

    page = render_page(
        ModeAnalyzeNotifications(test_edition, page_context(load_config)), load_config
    )

    rows = table_rows(page, f"Notification rules of user {with_admin_login}")
    assert [row["Description"].get_text(strip=True) for row in rows] == ["personal rule"]


def test_deleting_a_rule_removes_it(load_config: Config, test_edition: Edition) -> None:
    _save_rules([mail_rule("first"), mail_rule("second")])
    submit(_delete="0")

    result = ModeNotifications(test_edition, page_context(load_config)).action(load_config)

    assert _rule_descriptions() == ["second"]
    assert redirect_vars(result)["mode"] == "notifications"


def test_moving_a_rule_reorders_the_rules(load_config: Config, test_edition: Edition) -> None:
    _save_rules([mail_rule("first"), mail_rule("second")])
    submit(_move="0", _index="1")

    ModeNotifications(test_edition, page_context(load_config)).action(load_config)

    assert _rule_descriptions() == ["second", "first"]


def test_rule_list_action_keeps_the_search(load_config: Config, test_edition: Edition) -> None:
    _save_rules([mail_rule("first")])
    submit(_move="0", _index="0", search="first")

    result = ModeNotifications(test_edition, page_context(load_config)).action(load_config)

    assert redirect_vars(result) == {"mode": "notifications", "search": "first"}


def test_rule_list_action_returns_to_the_calling_mode(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rules([mail_rule("first")])
    submit(_move="0", _index="0", back_mode="test_notifications", user="", search="first")

    result = ModeNotifications(test_edition, page_context(load_config)).action(load_config)

    assert redirect_vars(result) == {"mode": "test_notifications", "search": "first"}


_BACKLOG = [
    {
        "MICROTIME": "1700000000000000",
        "NOTIFICATIONTYPE": "PROBLEM",
        "HOSTNAME": "web01",
        "SERVICEDESC": "CPU load",
        "SERVICESTATE": "CRITICAL",
        "SERVICESTATEID": "2",
        "SERVICEOUTPUT": "load too high",
    },
    {
        "SHORTDATETIME": "2026-10-07 10:00:00",
        "NOTIFICATIONTYPE": "PROBLEM",
        "HOSTNAME": "db01",
        "HOSTSTATE": "DOWN",
        "HOSTSTATEID": "1",
        "HOSTOUTPUT": "host unreachable",
    },
    {"NOTIFICATIONTYPE": "DOWNTIMESTART", "HOSTNAME": "web02"},
    {"NOTIFICATIONTYPE": "ACKNOWLEDGEMENT", "HOSTNAME": "web03"},
    {"NOTIFICATIONTYPE": "FLAPPINGSTART", "HOSTNAME": "web04"},
    {"NOTIFICATIONTYPE": "CUSTOM", "HOSTNAME": "web05"},
]


@pytest.mark.usefixtures("automations")
def test_analysis_lists_the_recent_notifications(
    load_config: Config, test_edition: Edition
) -> None:
    _save_backlog(_BACKLOG)

    page = render_page(
        ModeAnalyzeNotifications(test_edition, page_context(load_config)), load_config
    )

    rows = table_rows(page, "Analysis: recent notifications")
    assert [
        (
            row["Time"].get_text(strip=True),
            row["State"].get_text(strip=True) or icon_titles(row["State"]),
            row["Plug-in output"].get_text(strip=True),
        )
        for row in rows[1:]
    ] == [
        ("2026-10-07 10:00:00", "DOWN", "host unreachable"),
        ("Unknown date", ["Downtime"], ""),
        ("Unknown date", ["Acknowledgment"], ""),
        ("Unknown date", ["Flapping"], ""),
        ("Unknown date", [], ""),
    ]


@pytest.mark.usefixtures("automations")
def test_analysis_shows_the_service_state_of_a_service_notification(
    load_config: Config, test_edition: Edition
) -> None:
    _save_backlog(_BACKLOG)

    page = render_page(
        ModeAnalyzeNotifications(test_edition, page_context(load_config)), load_config
    )

    [service_row, *_] = table_rows(page, "Analysis: recent notifications")
    assert (
        service_row["Service"].get_text(strip=True),
        service_row["State"].get_text(strip=True),
        service_row["Plug-in output"].get_text(strip=True),
    ) == ("CPU load", "CRIT", "load too high")


def _analysis(rules: list[EventRule]) -> NotifyAnalysisInfo:
    return (
        [("match", rules[0], ""), ("miss", rules[1], "wrong host")],
        [
            ("admin", "mail", {}, None),
            (
                "mailto:a@example.com,b@example.com",
                "mail",
                {},
                AlwaysBulkParameters(interval=60, count=10, groupby=["host"]),
            ),
        ],
    )


def _analysed_page(automations: _Automations, load_config: Config, test_edition: Edition) -> str:
    rules = [mail_rule("matching"), mail_rule("missing"), mail_rule("unsynced")]
    _save_rules(rules)
    _save_backlog(_BACKLOG)
    automations.results["notification-analyse"] = NotificationAnalyseResult(result=_analysis(rules))
    set_request_vars(analyse="0")
    return render_page(
        ModeAnalyzeNotifications(test_edition, page_context(load_config)), load_config
    )


def test_analysing_a_notification_asks_the_core_for_the_analysis(
    automations: _Automations, load_config: Config, test_edition: Edition
) -> None:
    _analysed_page(automations, load_config, test_edition)

    assert ("notification-analyse", ("0",)) in automations.calls


def test_analysing_a_notification_marks_it_in_the_backlog(
    automations: _Automations, load_config: Config, test_edition: Edition
) -> None:
    page = _analysed_page(automations, load_config, test_edition)

    [analysed, *others] = table_rows(page, "Analysis: recent notifications")
    assert "You are analysing this notification" in icon_titles(analysed[""])
    assert not any("You are analysing this notification" in icon_titles(row[""]) for row in others)


def test_analysing_a_notification_shows_the_result_per_rule(
    automations: _Automations, load_config: Config, test_edition: Edition
) -> None:
    page = _analysed_page(automations, load_config, test_edition)

    assert [
        title
        for title in icon_titles(data_table(page, "Global notification rules"))
        if title.startswith("This rule")
    ] == [
        "This rule matches",
        "This rule does not match: wrong host",
        (
            "This rule is not yet known on the target site. Activate pending changes or complete "
            "the user profile replication to synchronize it."
        ),
    ]


def test_analysing_a_notification_warns_about_unsynchronized_rules(
    automations: _Automations, load_config: Config, test_edition: Edition
) -> None:
    page = _analysed_page(automations, load_config, test_edition)

    assert "The target site does not know about all notification rules" in page


def test_analysing_a_notification_predicts_the_notifications(
    automations: _Automations, load_config: Config, test_edition: Edition
) -> None:
    page = _analysed_page(automations, load_config, test_edition)

    assert [
        (
            row["Recipient"].get_text(strip=True),
            "Maximum count: 10" in row["Building bulks"].get_text(),
        )
        for row in table_rows(page, "Predicted notifications")
    ] == [("admin", False), ("a@example.com, b@example.com", True)]


_OVERDUE_BULKS: NotifyBulks = [
    (
        "/omd/sites/NO_SITE/var/check_mk/notify/bulk/admin/mail/host_web01",
        120.0,
        60,
        "24X7",
        2,
        [(1.0, "uuid1"), (2.0, "uuid2")],
        "admin,mail,web01",
    )
]


def test_overdue_bulks_are_highlighted(
    automations: _Automations, load_config: Config, test_edition: Edition
) -> None:
    automations.results["notification-get-bulks"] = NotificationGetBulksResult(
        result=_OVERDUE_BULKS
    )

    page = render_page(
        ModeAnalyzeNotifications(test_edition, page_context(load_config)), load_config
    )

    assert ("notification-get-bulks", ("1",)) in automations.calls
    assert "Overdue bulk notifications!" in page
    assert "Age of oldest notification is over maximum age" in page
    assert "Number of notifications exceeds maximum allowed number" in page


def test_showing_all_bulks_reports_when_none_are_pending(
    automations: _Automations, load_config: Config, test_edition: Edition
) -> None:
    submit(_show_bulks="1")
    ModeAnalyzeNotifications(test_edition, page_context(load_config)).action(load_config)
    request.del_var("_show_bulks")

    page = render_page(
        ModeAnalyzeNotifications(test_edition, page_context(load_config)), load_config
    )

    assert ("notification-get-bulks", ("0",)) in automations.calls
    assert "Currently there are no unsent bulk notifications pending." in page


def test_failing_bulk_lookup_is_reported(
    automations: _Automations, load_config: Config, test_edition: Edition
) -> None:
    automations.failing.add("notification-get-bulks")

    page = render_page(
        ModeAnalyzeNotifications(test_edition, page_context(load_config)), load_config
    )

    assert "Could not retrieve bulk notifications" in page


def test_replaying_a_notification_triggers_the_automation(
    automations: _Automations, load_config: Config, test_edition: Edition
) -> None:
    automations.results["notification-replay"] = NotificationReplayResult()
    submit(_replay="3")

    result = ModeAnalyzeNotifications(test_edition, page_context(load_config)).action(load_config)

    assert result is None
    assert ("notification-replay", ("3",)) in automations.calls


def test_changing_the_rule_list_display_returns_to_the_list(
    load_config: Config, test_edition: Edition
) -> None:
    submit(_show_user="1")

    result = ModeNotifications(test_edition, page_context(load_config)).action(load_config)

    assert redirect_vars(result) == {"mode": "notifications"}


def test_test_form_offers_the_simulation_options(
    load_config: Config, test_edition: Edition
) -> None:
    page = render_page(ModeTestNotifications(test_edition, page_context(load_config)), load_config)

    assert "Test notifications on" in page
    assert "Advanced condition simulation" in page
    assert "Trigger notification for a specific method" in page


def _submitted_test(
    load_config: Config, test_edition: Edition, button: str, **overrides: str
) -> dict[str, str]:
    form = form_values(
        render_page(ModeTestNotifications(test_edition, page_context(load_config)), load_config),
        "test_notifications",
    )
    # The date and time pickers are Vue components, their inputs only exist in the browser.
    browser_only = {
        "advanced_opts_p_date_and_time_0": "2026-10-07",
        "advanced_opts_p_date_and_time_1": "10:00",
    }
    submit(**{**form, **browser_only, button: "1", **overrides})
    return redirect_vars(
        ModeTestNotifications(test_edition, page_context(load_config)).action(load_config)
    )


def _follow_redirect(redirect: dict[str, str]) -> None:
    request.del_vars("_")
    set_request_vars(**redirect)


def test_testing_a_host_builds_a_host_context(load_config: Config, test_edition: Edition) -> None:
    redirect = _submitted_test(
        load_config,
        test_edition,
        "_test_host_notifications",
        general_opts_p_on_hostname_hint="web01",
        general_opts_p_plugin_output="host test output",
    )

    context = json.loads(redirect["test_context"])
    assert redirect["test_type"] == "host_test"
    assert context["HOSTNAME"] == "web01"
    assert context["WHAT"] == "HOST"
    assert context["NOTIFICATIONTYPE"] == "PROBLEM"
    assert context["HOSTOUTPUT"] == "host test output"


def test_testing_a_service_builds_a_service_context(
    load_config: Config, test_edition: Edition
) -> None:
    redirect = _submitted_test(
        load_config,
        test_edition,
        "_test_service_notifications",
        general_opts_p_on_hostname_hint="web01",
        general_opts_p_on_service_hint="CPU load",
        general_opts_p_plugin_output="service test output",
    )

    context = json.loads(redirect["test_context"])
    assert redirect["test_type"] == "svc_test"
    assert context["WHAT"] == "SERVICE"
    assert context["SERVICEDESC"] == "CPU load"
    assert context["SERVICEOUTPUT"] == "service test output"


def test_testing_without_a_host_is_rejected(load_config: Config, test_edition: Edition) -> None:
    with pytest.raises(MKUserError, match="Please provide a host name"):
        _submitted_test(
            load_config,
            test_edition,
            "_test_host_notifications",
            general_opts_p_on_hostname_hint="",
        )


@pytest.fixture(name="monitored_web01")
def fixture_monitored_web01(mock_livestatus: MockLiveStatusConnection) -> MockLiveStatusConnection:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table(
        "hosts",
        [
            {
                "name": "web01",
                "custom_variable_names": ["EC_SL", "OWNER"],
                "custom_variable_values": ["10", "ops"],
                "groups": ["web"],
                "contact_groups": ["admins"],
                "labels": {"os": "linux"},
                "alias": "Web server",
                "address": "10.0.0.1",
                "contacts": ["admin"],
                "notes_url": "",
                "tags": {"criticality": "prod"},
            }
        ],
    )
    mock_livestatus.add_table(
        "services",
        [
            {
                "host_name": "web01",
                "description": "CPU load",
                "custom_variable_names": ["EC_SL"],
                "custom_variable_values": ["20"],
                "groups": ["cpu"],
                "contact_groups": ["admins"],
                "check_command": "check_mk-cpu_loads",
                "labels": {"team": "ops"},
                "contacts": ["admin"],
                "display_name": "CPU load",
                "notes_url": "",
            }
        ],
    )
    return mock_livestatus


def _tested_service_page(
    automations: _Automations,
    monitored_web01: MockLiveStatusConnection,
    load_config: Config,
    test_edition: Edition,
) -> str:
    rules = [mail_rule("matching"), mail_rule("missing")]
    _save_rules(rules)
    automations.results["notification-test"] = NotificationTestResult(result=_analysis(rules))
    _follow_redirect(
        _submitted_test(
            load_config,
            test_edition,
            "_test_service_notifications",
            general_opts_p_on_hostname_hint="web01",
            general_opts_p_on_service_hint="CPU load",
        )
    )
    monitored_web01.expect_query(["GET hosts"], match_type="loose")
    monitored_web01.expect_query(["GET services"], match_type="loose")

    with monitored_web01:
        return render_page(
            ModeTestNotifications(test_edition, page_context(load_config)), load_config
        )


def test_testing_a_notification_sends_the_monitored_context(
    automations: _Automations,
    monitored_web01: MockLiveStatusConnection,
    load_config: Config,
    test_edition: Edition,
) -> None:
    _tested_service_page(automations, monitored_web01, load_config, test_edition)

    [(context_arg, _dispatch)] = [
        args for command, args in automations.calls if command == "notification-test"
    ]
    sent_context = json.loads(context_arg)
    assert {
        key: sent_context[key]
        for key in ("SITEOFHOST", "HOST_SL", "SVC_SL", "HOSTTAG_criticality", "SERVICELABEL_team")
    } == {
        "SITEOFHOST": "NO_SITE",
        "HOST_SL": "10",
        "SVC_SL": "20",
        "HOSTTAG_criticality": "prod",
        "SERVICELABEL_team": "ops",
    }


def test_test_result_summarizes_the_matching_rules(
    automations: _Automations,
    monitored_web01: MockLiveStatusConnection,
    load_config: Config,
    test_edition: Edition,
) -> None:
    page = _tested_service_page(automations, monitored_web01, load_config, test_edition)

    assert "1 notification rule matches (1 global rule, 0 user rules)" in page


def test_test_result_marks_the_tested_notification_as_matching(
    automations: _Automations,
    monitored_web01: MockLiveStatusConnection,
    load_config: Config,
    test_edition: Edition,
) -> None:
    page = _tested_service_page(automations, monitored_web01, load_config, test_edition)

    assert "This notification matches" in icon_titles(
        data_table(page, "Analysis: test notifications")
    )


def test_test_result_predicts_the_notifications(
    automations: _Automations,
    monitored_web01: MockLiveStatusConnection,
    load_config: Config,
    test_edition: Edition,
) -> None:
    page = _tested_service_page(automations, monitored_web01, load_config, test_edition)

    assert [
        row["Recipient"].get_text(strip=True) for row in table_rows(page, "Predicted notifications")
    ] == ["admin", "a@example.com, b@example.com"]


@pytest.mark.usefixtures("automations")
def test_testing_an_unmonitored_host_is_rejected(
    monitored_web01: MockLiveStatusConnection,
    load_config: Config,
    test_edition: Edition,
) -> None:
    _follow_redirect(
        _submitted_test(
            load_config,
            test_edition,
            "_test_host_notifications",
            general_opts_p_on_hostname_hint="unknown",
        )
    )
    monitored_web01.expect_query(["GET hosts"], match_type="loose")

    with (
        monitored_web01,
        pytest.raises(MKUserError, match="is not known in the activated monitoring"),
    ):
        render_page(ModeTestNotifications(test_edition, page_context(load_config)), load_config)


def test_user_rule_table_links_to_the_user_rule_editor(
    load_config: Config, test_edition: Edition, with_admin_login: UserId
) -> None:
    _save_user_rules(with_admin_login, [mail_rule("personal rule")])
    set_request_vars(user=with_admin_login)

    page = render_page(ModeUserNotifications(test_edition, page_context(load_config)), load_config)

    [row] = table_rows(page)
    assert (row["Description"].get_text(strip=True), link_vars(row["Actions"])["mode"]) == (
        "personal rule",
        "user_notification_rule",
    )


def test_personal_rule_table_links_to_the_personal_rule_editor(
    load_config: Config, test_edition: Edition, with_admin_login: UserId
) -> None:
    _save_user_rules(with_admin_login, [mail_rule("personal rule")])

    page = render_page(
        ModePersonalUserNotifications(test_edition, page_context(load_config)), load_config
    )

    [row] = table_rows(page)
    assert (row["Description"].get_text(strip=True), link_vars(row["Actions"])["mode"]) == (
        "personal rule",
        "notification_rule_p",
    )


def test_rule_table_of_unknown_user_is_rejected(load_config: Config, test_edition: Edition) -> None:
    set_request_vars(user="unknown")

    with pytest.raises(MKUserError, match="The requested user does not exist"):
        ModeUserNotifications(test_edition, page_context(load_config))


def test_deleting_a_user_rule_removes_it(
    load_config: Config, test_edition: Edition, with_admin_login: UserId
) -> None:
    _save_user_rules(with_admin_login, [mail_rule("first"), mail_rule("second")])
    submit(user=with_admin_login, _delete="1")

    result = ModeUserNotifications(test_edition, page_context(load_config)).action(load_config)

    assert _user_rule_descriptions(with_admin_login) == ["first"]
    assert redirect_vars(result) == {"mode": "user_notifications", "user": with_admin_login}


def test_moving_a_user_rule_reorders_the_rules(
    load_config: Config, test_edition: Edition, with_admin_login: UserId
) -> None:
    _save_user_rules(with_admin_login, [mail_rule("first"), mail_rule("second")])
    submit(user=with_admin_login, _move="1", _index="0", search="first")

    result = ModeUserNotifications(test_edition, page_context(load_config)).action(load_config)

    assert _user_rule_descriptions(with_admin_login) == ["second", "first"]
    assert redirect_vars(result)["search"] == "first"


def test_saving_the_rule_form_adds_a_user_rule(
    load_config: Config, test_edition: Edition, with_admin_login: UserId
) -> None:
    set_request_vars(user=with_admin_login)
    form = form_values(
        render_page(
            ModeEditUserNotificationRule(test_edition, page_context(load_config)), load_config
        ),
        "rule",
    )
    submit(**{**form, "rule_p_description": "created via form"})

    result = ModeEditUserNotificationRule(test_edition, page_context(load_config)).action(
        load_config
    )

    assert _user_rule_descriptions(with_admin_login) == ["created via form"]
    assert userdb.load_users()[with_admin_login]["notification_rules"][0]["contact_users"] == [
        with_admin_login
    ]
    assert redirect_vars(result) == {"mode": "user_notifications", "user": with_admin_login}


def test_cloning_a_user_rule_prefills_the_copy(
    load_config: Config, test_edition: Edition, with_admin_login: UserId
) -> None:
    _save_user_rules(with_admin_login, [mail_rule("original")])
    set_request_vars(user=with_admin_login, clone="0")

    page = render_page(
        ModeEditUserNotificationRule(test_edition, page_context(load_config)), load_config
    )

    assert form_values(page, "rule")["rule_p_description"] == "original"


def test_cloning_a_user_rule_is_titled_as_adding(
    load_config: Config, test_edition: Edition, with_admin_login: UserId
) -> None:
    _save_user_rules(with_admin_login, [mail_rule("original")])
    set_request_vars(user=with_admin_login, clone="0")

    mode = ModeEditUserNotificationRule(test_edition, page_context(load_config))

    assert mode.title() == f"Add notification rule for user {with_admin_login}"


def test_editing_a_missing_user_rule_is_rejected(
    load_config: Config, test_edition: Edition, with_admin_login: UserId
) -> None:
    set_request_vars(user=with_admin_login, edit="5")

    with pytest.raises(MKUserError, match="This notification rule does not exist."):
        ModeEditUserNotificationRule(test_edition, page_context(load_config))


def test_parameter_overview_filters_methods_by_search(
    load_config: Config, test_edition: Edition
) -> None:
    _save_parameters("mail", ["first"])
    set_request_vars(search="html")

    page = render_page(
        ModeNotificationParametersOverview(test_edition, page_context(load_config)), load_config
    )

    overview_tag = BeautifulSoup(page, "html.parser").select_one(
        "cmk-notification-parameters-overview"
    )
    assert overview_tag is not None
    rules = json.loads(str(overview_tag["data"]))["parameters"][0]["topics"][0]["rules"]
    assert [(rule["i18n"], rule["count"]) for rule in rules] == [("Email (HTML)", "1")]


def test_parameter_list_shows_the_parameters_matching_the_search(
    load_config: Config, test_edition: Edition
) -> None:
    _save_parameters("mail", ["first", "second"])
    set_request_vars(method="mail", search="first")

    page = render_page(
        ModeNotificationParameters(test_edition, page_context(load_config)), load_config
    )

    assert [row["Description"].get_text(strip=True) for row in table_rows(page, "Parameters")] == [
        "first"
    ]


def test_parameter_list_edit_link_keeps_the_search(
    load_config: Config, test_edition: Edition
) -> None:
    _save_parameters("mail", ["first"])
    set_request_vars(method="mail", search="first")

    page = render_page(
        ModeNotificationParameters(test_edition, page_context(load_config)), load_config
    )

    [row] = table_rows(page, "Parameters")
    edit_vars = link_vars(row["Actions"])
    assert (edit_vars["mode"], edit_vars["search"]) == ("edit_notification_parameter", "first")


def test_parameter_list_without_parameters_says_so(
    load_config: Config, test_edition: Edition
) -> None:
    set_request_vars(method="mail")

    page = render_page(
        ModeNotificationParameters(test_edition, page_context(load_config)), load_config
    )

    assert "You have not created any parameters for this notification method yet." in page


def test_parameter_list_of_unknown_method_is_rejected(
    load_config: Config, test_edition: Edition
) -> None:
    set_request_vars(method="no_such_method")

    with pytest.raises(MKUserError, match="Notification method 'no_such_method' does not exist"):
        render_page(
            ModeNotificationParameters(test_edition, page_context(load_config)), load_config
        )


def test_parameter_list_names_the_rules_that_block_a_deletion(
    load_config: Config, test_edition: Edition
) -> None:
    [parameter_id] = _save_parameters("mail", ["used"])
    _save_rules(
        [
            mail_rule("uses it", parameter_id=parameter_id),
            mail_rule("", parameter_id=parameter_id, rule_id="nondescript"),
        ]
    )
    set_request_vars(method="mail", _parameter_id_with_related_rules=parameter_id)

    page = render_page(
        ModeNotificationParameters(test_edition, page_context(load_config)), load_config
    )

    assert "This notification parameter is used by the following notification rule(s):" in page
    assert "uses it" in page
    assert "1 notification rule(s)" in page
    assert "without a description were found" in page


def test_deleting_an_unused_parameter_removes_it(
    load_config: Config, test_edition: Edition
) -> None:
    unused, _ = _save_parameters("mail", ["unused", "kept"])
    submit(method="mail", _delete=unused)

    result = ModeNotificationParameters(test_edition, page_context(load_config)).action(load_config)

    assert _parameter_descriptions("mail") == ["kept"]
    assert redirect_vars(result) == {"mode": "notification_parameters", "method": "mail"}


def test_deleting_a_used_parameter_is_refused(load_config: Config, test_edition: Edition) -> None:
    [used] = _save_parameters("mail", ["used"])
    _save_rules([mail_rule("uses it", parameter_id=used)])
    submit(method="mail", _delete=used)

    result = ModeNotificationParameters(test_edition, page_context(load_config)).action(load_config)

    assert _parameter_descriptions("mail") == ["used"]
    assert redirect_vars(result)["_parameter_id_with_related_rules"] == used


def test_moving_a_parameter_reorders_them(load_config: Config, test_edition: Edition) -> None:
    _save_parameters("mail", ["first", "second"])
    submit(method="mail", _move="0", _index="1", back_mode="notification_parameters_overview")

    result = ModeNotificationParameters(test_edition, page_context(load_config)).action(load_config)

    assert _parameter_descriptions("mail") == ["second", "first"]
    assert redirect_vars(result)["mode"] == "notification_parameters_overview"


def test_parameter_action_for_method_without_parameters_only_redirects(
    load_config: Config, test_edition: Edition
) -> None:
    submit(method="mail", _delete="anything")

    result = ModeNotificationParameters(test_edition, page_context(load_config)).action(load_config)

    assert redirect_vars(result) == {"mode": "notification_parameters", "method": "mail"}


# fmt: off
@pytest.mark.parametrize(
    "variables, expected_title",
    [
        pytest.param({}, "Add Email (HTML) notification parameter", id="new"),
        pytest.param({"clone": "param_0"}, "Clone Email (HTML) notification parameter", id="clone"),
        pytest.param({"parameter": "param_0", "edit": "0"}, "Edit Email (HTML) notification parameter #0", id="edit"),
    ],
)
# fmt: on
def test_parameter_editor_renders_the_form(
    variables: dict[str, str], expected_title: str, load_config: Config, test_edition: Edition
) -> None:
    _save_parameters("mail", ["existing"])
    set_request_vars(method="mail", **variables)

    mode = ModeEditNotificationParameter(test_edition, page_context(load_config))
    page = render_page(mode, load_config)

    assert mode.title() == expected_title
    assert "_vue_edit_notification_parameter" in page


def test_cloning_a_missing_parameter_is_rejected(
    load_config: Config, test_edition: Edition
) -> None:
    _save_parameters("mail", ["existing"])
    set_request_vars(method="mail", clone="missing")

    with pytest.raises(MKUserError, match="This notification parameter does not exist."):
        ModeEditNotificationParameter(test_edition, page_context(load_config))
