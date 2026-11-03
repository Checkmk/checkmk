#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Literal

import pytest
import time_machine

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.type_defs import Row, Rows
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.views.command import commands
from cmk.gui.views.command.base import Command, CommandSpec
from cmk.gui.views.command.commands import (
    _acknowledgement_needs_removal,
    _query_downtime_ids_for_leaf,
    CommandAcknowledge,
    CommandAddComment,
    CommandClearModifiedAttributes,
    CommandCustomNotification,
    CommandFakeCheckResult,
    CommandNotifications,
    CommandRemoveAcknowledgments,
    CommandRemoveComments,
    CommandRemoveDowntimesDowntimesTable,
    CommandReschedule,
    CommandScheduleDowntimes,
    CommandScheduleDowntimesForm,
    CommandToggleActiveChecks,
    CommandTogglePassiveChecks,
    NoRecurringDowntimes,
    time_interval_end,
)
from cmk.gui.views.command.form import core_command
from cmk.livestatus_client import (
    AcknowledgeHostProblem,
    Acknowledgement,
    AcknowledgeServiceProblem,
    AddHostComment,
    AddServiceComment,
    ChangeHostModifiedAttributes,
    ChangeServiceModifiedAttributes,
    DeleteHostComment,
    DeleteHostDowntime,
    DeleteServiceComment,
    DeleteServiceDowntime,
    DisableHostNotifications,
    DisablePassiveServiceChecks,
    DisableServiceCheck,
    EnableHostCheck,
    EnablePassiveHostChecks,
    EnableServiceNotifications,
    NotificationOption,
    ProcessHostCheckResult,
    ProcessServiceCheckResult,
    RemoveHostAcknowledgement,
    RemoveServiceAcknowledgement,
    ScheduleForcedHostCheck,
    ScheduleForcedServiceCheck,
    ScheduleHostDowntime,
    ScheduleServiceDowntime,
    SendCustomServiceNotification,
)
from cmk.livestatus_client import Command as LivestatusCommand
from cmk.livestatus_client.testing import MockLiveStatusConnection
from cmk.utils.servicename import ServiceName
from cmk.web.utils.html import HTML
from tests.testlib.unit.gui.global_settings import logged_in
from tests.testlib.unit.gui.web_test_app import SetConfig
from tests.unit.cmk.gui.helpers.setup_mode_test_helper import set_request_vars

COMMENT_TABLE = [
    # Host comments
    {"comment_id": 11, "entry_type": 4, "is_service": 0},
    {"comment_id": 12, "entry_type": 4, "is_service": 0},
    {"comment_id": 13, "entry_type": 0, "is_service": 0},
    # Service comments
    {"comment_id": 21, "entry_type": 4, "is_service": 1},
    {"comment_id": 22, "entry_type": 4, "is_service": 1},
    {"comment_id": 23, "entry_type": 0, "is_service": 1},
]


@pytest.mark.parametrize(
    "cmdtag, comments_to_remove, removal_expected",
    [
        ("HOST", {"11"}, False),
        ("HOST", {"11", "12"}, True),
        ("HOST", {"11", "12", "13"}, True),
        ("SVC", {"21"}, False),
        ("SVC", {"21", "22"}, True),
        ("SVC", {"21", "22", "23"}, True),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_acknowledgement_needs_removal(
    mock_livestatus: MockLiveStatusConnection,
    cmdtag: Literal["HOST", "SVC"],
    comments_to_remove: set[str],
    removal_expected: bool,
) -> None:
    live = mock_livestatus
    live.add_table("comments", COMMENT_TABLE)
    live.expect_query(
        [
            "GET comments",
            "Columns: comment_id",
            "Filter: is_service = ...",
            "Filter: entry_type = 4",
            "ColumnHeaders: off",
        ],
        match_type="ellipsis",
    )
    with live():
        assert _acknowledgement_needs_removal(cmdtag, comments_to_remove) == removal_expected


@pytest.mark.usefixtures("request_context")
class TestRemoveDowntimesBI:
    def test_host(self, mock_livestatus: MockLiveStatusConnection) -> None:
        mock_livestatus.add_table(
            "downtimes",
            [
                {"id": 1, "host_name": "heute", "is_service": 0},
                {"id": 2, "host_name": "gestern", "is_service": 0},
                {"id": 3, "host_name": "zukunft", "is_service": 0},
            ],
        )
        mock_livestatus.expect_query(
            [
                "GET downtimes",
                "Columns: id",
                "Filter: host_name = heute",
                "Filter: is_service = 0",
                "And: 2",
            ],
        )
        with mock_livestatus():
            assert _query_downtime_ids_for_leaf(None, HostName("heute"), service=None) == [1]

    def test_host_and_service(self, mock_livestatus: MockLiveStatusConnection) -> None:
        mock_livestatus.add_table(
            "downtimes",
            [
                {"id": 1, "host_name": "heute", "service_description": "CPU", "is_service": 1},
                {"id": 2, "host_name": "gestern", "service_description": "CPU", "is_service": 1},
                {"id": 3, "host_name": "zukunft", "service_description": "CPU", "is_service": 1},
            ],
        )
        mock_livestatus.expect_query(
            [
                "GET downtimes",
                "Columns: id",
                "Filter: host_name = heute",
                "Filter: service_description = CPU",
                "Filter: is_service = 1",
                "And: 3",
            ],
        )
        with mock_livestatus():
            assert _query_downtime_ids_for_leaf(None, HostName("heute"), ServiceName("CPU")) == [1]

    def test_not_found(self, mock_livestatus: MockLiveStatusConnection) -> None:
        mock_livestatus.expect_query(
            [
                "GET downtimes",
                "Columns: id",
                "Filter: host_name = heute",
                "Filter: is_service = 0",
                "And: 2",
            ],
        )
        with mock_livestatus():
            assert not _query_downtime_ids_for_leaf(None, HostName("heute"), service=None)


class TestRemoveDowntimeFromHostOrServiceDatasource:
    """A view whose painters do not fetch the downtime column.

    The rows of a user-defined host/service view only carry the columns its painters
    ask for, so ``service_downtimes`` / ``host_downtimes`` can be absent entirely.
    The ids are then looked up from the downtimes table instead; that lookup itself is
    covered by TestQueryDowntimeIdsForLeaf.
    """

    @pytest.mark.usefixtures("request_context", "with_admin_login")
    def test_service_row_without_the_downtimes_column(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        queried_for: list[tuple[str | None, str, str | None]] = []

        def _fake_query(
            site: SiteId | None, host: HostName, service: ServiceName | None
        ) -> list[int]:
            queried_for.append((site, host, service))
            return [7]

        monkeypatch.setattr(commands, "_query_downtime_ids_for_leaf", _fake_query)

        result = commands._rm_downtime_from_hst_or_svc_datasource(  # noqa: SLF001
            commands.CommandRemoveDowntimesHostServicesTable,
            "SVC",
            {"site": "heute", "host_name": "heute", "service_description": "CPU"},
            [],
        )

        assert result is not None
        downtime_commands, _dialog = result
        assert list(downtime_commands) == [DeleteServiceDowntime(7)]
        assert queried_for == [("heute", "heute", "CPU")]

    @pytest.mark.usefixtures("request_context", "with_admin_login")
    def test_service_row_with_the_downtimes_column_does_not_query(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _must_not_query(*_args: object) -> list[int]:
            raise AssertionError("the downtime ids are already in the row")

        monkeypatch.setattr(commands, "_query_downtime_ids_for_leaf", _must_not_query)

        result = commands._rm_downtime_from_hst_or_svc_datasource(  # noqa: SLF001
            commands.CommandRemoveDowntimesHostServicesTable,
            "SVC",
            {"host_name": "heute", "service_description": "CPU", "service_downtimes": ["7", ""]},
            [],
        )

        assert result is not None
        downtime_commands, _dialog = result
        assert list(downtime_commands) == [DeleteServiceDowntime(7)]


def test_a_downtime_repeats_never_where_no_core_repeats_it() -> None:
    assert [
        (recurrence.recur, recurrence.title) for recurrence in NoRecurringDowntimes().recurrences()
    ] == [("fixed", "never")]


def test_a_named_interval_reads_the_way_the_classic_dropdown_reads() -> None:
    """The two views of one list, so neither can be added to without the other."""
    downtimes = NoRecurringDowntimes()

    assert [recurrence.title for recurrence in downtimes.recurrences()] == [
        title for _value, title in downtimes.choices()
    ]


def test_the_registered_command_hands_on_the_intervals_it_was_given() -> None:
    """What a page offers is read back off the command, so the two cannot part ways."""
    recurring_downtimes = NoRecurringDowntimes()

    command = CommandScheduleDowntimes(recurring_downtimes=recurring_downtimes)

    assert command.recurring_downtimes is recurring_downtimes


class TestDowntimeDurationPresets:
    """Downtime duration presets are admin configured, so their end can be absurd.

    ``user_downtime_timeranges`` entries carry a duration in seconds; a large enough
    one puts the resulting end timestamp outside the platform's time_t range.
    """

    @staticmethod
    def _form(monkeypatch: pytest.MonkeyPatch) -> CommandScheduleDowntimesForm:
        form = CommandScheduleDowntimesForm(NoRecurringDowntimes())
        monkeypatch.setattr(form, "_current_local_time", lambda: 0.0)
        return form

    @pytest.mark.usefixtures("request_context")
    def test_renders_a_button_for_a_usable_preset(
        self, set_config: SetConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        form = self._form(monkeypatch)

        with set_config(user_downtime_timeranges=[{"title": "2 hours", "end": 7200}]):
            assert "_downrange__7200" in str(form._get_duration_options())  # noqa: SLF001

    @pytest.mark.usefixtures("request_context")
    def test_skips_a_preset_whose_end_is_not_representable(
        self, set_config: SetConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        form = self._form(monkeypatch)

        with set_config(user_downtime_timeranges=[{"title": "far future", "end": 10**18}]):
            assert form._get_duration_options() == HTML.empty()  # noqa: SLF001

    @pytest.mark.usefixtures("request_context")
    def test_activates_the_first_preset_it_can_render(
        self, set_config: SetConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The active button is the one that pre-fills the form's date & time.

        A skipped preset must not consume that role, or the form opens with no button
        marked and the date & time fields left blank.
        """
        form = self._form(monkeypatch)

        with set_config(
            user_downtime_timeranges=[
                {"title": "far future", "end": 10**18},
                {"title": "2 hours", "end": 7200},
            ]
        ):
            duration_options = str(form._get_duration_options())  # noqa: SLF001

        assert 'id="_downrange__7200"' in duration_options
        assert 'class="button duration active"' in duration_options
        assert "date__down_to_date" in duration_options
        assert "time__down_to_time" in duration_options


class TestDowntimeSpecsForHosts:
    """Scheduling host downtime from a service view.

    ``action_rows`` are the rows of whichever view the user selected in, so they only
    carry the columns that view's painters ask for -- ``host_name`` can be absent.
    The rows are used to count the affected hosts; the commands themselves come from
    ``spec``, so a missing column must not take the page down.
    """

    @staticmethod
    def _specs(action_rows: list[dict[str, str]]) -> tuple[str, list[str], list[dict[str, str]]]:
        form = CommandScheduleDowntimesForm(NoRecurringDowntimes())
        request.set_var("_down_host", "1")
        return form._downtime_specs("SVC", {"site": "heute"}, action_rows, "myhost;CPU")  # noqa: SLF001

    @pytest.mark.usefixtures("request_context", "with_admin_login")
    def test_counts_one_row_per_affected_host(self) -> None:
        cmdtag, specs, action_rows = self._specs(
            [
                {"site": "heute", "host_name": "myhost"},
                {"site": "heute", "host_name": "myhost"},
                {"site": "heute", "host_name": "otherhost"},
            ]
        )

        assert cmdtag == "HOST"
        assert specs == ["myhost"]
        assert [r["host_name"] for r in action_rows] == ["myhost", "otherhost"]

    @pytest.mark.usefixtures("request_context", "with_admin_login")
    def test_tolerates_rows_without_the_host_name_column(self) -> None:
        cmdtag, specs, action_rows = self._specs([{"site": "heute"}, {"site": "heute"}])

        assert cmdtag == "HOST"
        assert specs == ["myhost"]
        assert len(action_rows) == 1


HOST_ROW: Row = {"site": "local", "host_name": "myhost"}
SERVICE_ROW: Row = {"site": "local", "host_name": "myhost", "service_description": "CPU load"}
AGGREGATION_ROW: Row = {
    "aggr_id": "Hosts",
    "aggr_tree": {
        "type": 2,
        "nodes": [
            {"type": 1, "host": ("local", "myhost")},
            {"type": 1, "host": ("remote", "otherhost"), "service": "CPU load"},
        ],
    },
}


def _issue(
    user_id: UserId,
    permissions: Sequence[str],
    what: str,
    row: Row,
    action_rows: Rows | None = None,
) -> list[CommandSpec]:
    with logged_in(user_id, *permissions):
        issued, _options, _dialog, _executor = core_command(what, row, 0, action_rows or [row])
    return list(issued)


def _render(command: Command, what: str) -> str:
    with output_funnel.plugged():
        command.render(what)
        return "".join(output_funnel.drain())


# fmt: off
@pytest.mark.parametrize(
    "permission, submit_var, what, row, expected",
    [
        pytest.param("action.notifications", "_enable_notifications", "service", SERVICE_ROW, EnableServiceNotifications(HostName("myhost"), "CPU load"), id="enable service notifications"),
        pytest.param("action.notifications", "_disable_notifications", "host", HOST_ROW, DisableHostNotifications(HostName("myhost")), id="disable host notifications"),
        pytest.param("action.enablechecks", "_enable_checks", "host", HOST_ROW, EnableHostCheck(HostName("myhost")), id="enable active host checks"),
        pytest.param("action.enablechecks", "_disable_checks", "service", SERVICE_ROW, DisableServiceCheck(HostName("myhost"), "CPU load"), id="disable active service checks"),
        pytest.param("action.enablechecks", "_enable_passive_checks", "host", HOST_ROW, EnablePassiveHostChecks(HostName("myhost")), id="enable passive host checks"),
        pytest.param("action.enablechecks", "_disable_passive_checks", "service", SERVICE_ROW, DisablePassiveServiceChecks(HostName("myhost"), "CPU load"), id="disable passive service checks"),
        pytest.param("action.clearmodattr", "_clear_modattr", "host", HOST_ROW, ChangeHostModifiedAttributes(HostName("myhost"), 0), id="reset host attributes"),
        pytest.param("action.clearmodattr", "_clear_modattr", "service", SERVICE_ROW, ChangeServiceModifiedAttributes(HostName("myhost"), 0, "CPU load"), id="reset service attributes"),
    ],
)
# fmt: on
@pytest.mark.usefixtures("request_context")
def test_a_toggle_issues_the_core_command_of_the_pressed_button(
    with_user: tuple[UserId, str],
    permission: str,
    submit_var: str,
    what: str,
    row: Row,
    expected: LivestatusCommand,
) -> None:
    set_request_vars(**{submit_var: "1"})

    assert _issue(with_user[0], [permission], what, row) == [expected]


# fmt: off
@pytest.mark.parametrize(
    "command, what, submit_button",
    [
        pytest.param(CommandReschedule, "service", "_resched_checks", id="reschedule"),
        pytest.param(CommandNotifications, "host", "_enable_notifications", id="notifications"),
        pytest.param(CommandToggleActiveChecks, "host", "_enable_checks", id="active checks"),
        pytest.param(CommandTogglePassiveChecks, "host", "_enable_passive_checks", id="passive checks"),
        pytest.param(CommandClearModifiedAttributes, "host", "_clear_modattr", id="modified attributes"),
        pytest.param(CommandFakeCheckResult, "host", "_fake_check_result", id="fake host check result"),
        pytest.param(CommandFakeCheckResult, "service", "_fake_check_result", id="fake service check result"),
        pytest.param(CommandCustomNotification, "host", "_customnotification", id="custom notification"),
        pytest.param(CommandAcknowledge, "service", "_acknowledge", id="acknowledge"),
        pytest.param(CommandAddComment, "host", "_add_comment", id="add comment"),
        pytest.param(CommandRemoveDowntimesDowntimesTable, "downtime", "_remove_downtimes", id="remove downtimes"),
        pytest.param(CommandRemoveComments, "comment", "_delete_comments", id="remove comments"),
        pytest.param(CommandScheduleDowntimes(NoRecurringDowntimes()), "service", "_down_host", id="schedule downtimes"),
    ],
)
# fmt: on
@pytest.mark.usefixtures("request_context", "with_admin_login", "patch_theme")
def test_a_command_form_offers_the_button_its_action_reacts_to(
    command: Command, what: str, submit_button: str
) -> None:
    assert f'name="{submit_button}"' in _render(command, what)


@pytest.mark.usefixtures("request_context", "with_admin_login", "patch_theme")
def test_the_ad_hoc_downtime_button_is_offered_once_configured(set_config: SetConfig) -> None:
    with set_config(adhoc_downtime={"duration": 60, "comment": "Ad hoc"}):
        rendered = _render(CommandScheduleDowntimes(NoRecurringDowntimes()), "host")

    assert 'name="_down_adhoc"' in rendered


@pytest.mark.usefixtures("request_context")
def test_rescheduling_spreads_the_checks_over_the_given_minutes(
    with_user: tuple[UserId, str],
) -> None:
    set_request_vars(_resched_checks="1", _resched_spread="10")

    with (
        time_machine.travel(1_900_000_000, tick=False),
        logged_in(with_user[0], "action.reschedule"),
    ):
        issued, _options, _dialog, _executor = core_command(
            "service", SERVICE_ROW, 1, [SERVICE_ROW, SERVICE_ROW]
        )

    assert list(issued) == [
        ScheduleForcedServiceCheck(
            HostName("myhost"), datetime.fromtimestamp(1_900_000_000 + 5 * 60), "CPU load"
        )
    ]


@pytest.mark.usefixtures("request_context")
def test_rescheduling_a_host_checks_it_right_away_without_spread(
    with_user: tuple[UserId, str],
) -> None:
    set_request_vars(_resched_checks="1", _resched_spread="0")

    with time_machine.travel(1_900_000_000, tick=False):
        issued = _issue(with_user[0], ["action.reschedule"], "host", HOST_ROW)

    assert issued == [
        ScheduleForcedHostCheck(HostName("myhost"), datetime.fromtimestamp(1_900_000_000))
    ]


@pytest.mark.usefixtures("request_context")
def test_rescheduling_rejects_a_negative_spread(with_user: tuple[UserId, str]) -> None:
    set_request_vars(_resched_checks="1", _resched_spread="-1")

    with pytest.raises(MKUserError):
        _issue(with_user[0], ["action.reschedule"], "host", HOST_ROW)


@pytest.mark.usefixtures("request_context")
def test_a_fake_check_result_without_output_names_state_and_user(
    with_user: tuple[UserId, str],
) -> None:
    set_request_vars(_fake_check_result="1", _state="1", _state_1="Down", _fake_output="")

    assert _issue(with_user[0], ["action.fakechecks"], "host", HOST_ROW) == [
        ProcessHostCheckResult(HostName("myhost"), 1, f"Manually set to Down by {with_user[0]}")
    ]


@pytest.mark.usefixtures("request_context")
def test_a_fake_check_result_carries_the_given_metrics(with_user: tuple[UserId, str]) -> None:
    set_request_vars(
        _fake_check_result="1",
        _state="2",
        _fake_output="disk full",
        _fake_perfdata="usage=100",
    )

    assert _issue(with_user[0], ["action.fakechecks"], "service", SERVICE_ROW) == [
        ProcessServiceCheckResult(HostName("myhost"), 2, "disk full|usage=100", "CPU load")
    ]


@pytest.mark.usefixtures("request_context")
def test_the_fake_check_result_confirmation_names_the_target_state() -> None:
    set_request_vars(_state="2", _state_2="Critical")

    assert "Critical" in CommandFakeCheckResult.confirm_title


@pytest.mark.usefixtures("request_context")
def test_a_forced_broadcast_notification_combines_both_options(
    with_user: tuple[UserId, str],
) -> None:
    set_request_vars(
        _customnotification="1",
        _cusnot_comment="test",
        _cusnot_broadcast="on",
        _cusnot_forced="on",
    )

    assert _issue(with_user[0], ["action.customnotification"], "service", SERVICE_ROW) == [
        SendCustomServiceNotification(
            HostName("myhost"), NotificationOption(3), with_user[0], "test", "CPU load"
        )
    ]


@pytest.mark.usefixtures("request_context")
def test_acknowledging_a_service_carries_the_chosen_options(
    with_user: tuple[UserId, str],
) -> None:
    set_request_vars(_acknowledge="1", _ack_comment="ticket 42", _ack_sticky="on", _ack_notify="on")

    assert _issue(with_user[0], ["action.acknowledge"], "service", SERVICE_ROW) == [
        AcknowledgeServiceProblem(
            HostName("myhost"),
            "CPU load",
            Acknowledgement.STICKY,
            True,
            False,
            with_user[0],
            "ticket 42",
            None,
        )
    ]


@pytest.mark.usefixtures("request_context")
def test_acknowledging_until_a_date_expires_then(with_user: tuple[UserId, str]) -> None:
    set_request_vars(
        _acknowledge="1",
        _ack_comment="ticket 42",
        _ack_expire="on",
        _ack_expire_date="2030-01-01",
        _ack_expire_time="10:00",
    )

    with time_machine.travel(datetime(2029, 1, 1), tick=False):
        issued = _issue(with_user[0], ["action.acknowledge"], "service", SERVICE_ROW)

    assert isinstance(issued[0], AcknowledgeServiceProblem)
    assert issued[0].expire_on == datetime(2030, 1, 1, 10, 0)


@pytest.mark.parametrize(
    "comment",
    [
        pytest.param("", id="missing comment"),
        pytest.param("a;b", id="semicolon in comment"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_acknowledging_rejects_an_invalid_comment(
    with_user: tuple[UserId, str], comment: str
) -> None:
    set_request_vars(_acknowledge="1", _ack_comment=comment)

    with pytest.raises(MKUserError):
        _issue(with_user[0], ["action.acknowledge"], "host", HOST_ROW)


@pytest.mark.usefixtures("request_context")
def test_acknowledging_rejects_an_expiry_in_the_past(with_user: tuple[UserId, str]) -> None:
    set_request_vars(
        _acknowledge="1",
        _ack_comment="ticket 42",
        _ack_expire="on",
        _ack_expire_date="2000-01-01",
        _ack_expire_time="10:00",
    )

    with pytest.raises(MKUserError):
        _issue(with_user[0], ["action.acknowledge"], "host", HOST_ROW)


@pytest.mark.usefixtures("request_context")
def test_acknowledging_an_aggregation_acknowledges_each_leaf_on_its_site(
    with_user: tuple[UserId, str],
) -> None:
    set_request_vars(_acknowledge="1", _ack_comment="ticket 42")

    assert _issue(with_user[0], ["action.acknowledge"], "aggr", AGGREGATION_ROW) == [
        (
            SiteId("local"),
            AcknowledgeHostProblem(
                HostName("myhost"),
                Acknowledgement.NONE,
                False,
                False,
                with_user[0],
                "ticket 42",
                None,
            ),
        ),
        (
            SiteId("remote"),
            AcknowledgeServiceProblem(
                HostName("otherhost"),
                "CPU load",
                Acknowledgement.NONE,
                False,
                False,
                with_user[0],
                "ticket 42",
                None,
            ),
        ),
    ]


@pytest.mark.usefixtures("request_context")
def test_the_acknowledge_confirmation_lists_the_expiry_conditions() -> None:
    set_request_vars(_ack_sticky="on", _ack_persistent="on")

    dialog = CommandAcknowledge.confirm_dialog_options("SVC", SERVICE_ROW, [SERVICE_ROW])

    assert "On recovery (OK/UP)" in str(dialog.additions)
    assert "Comment will be kept" in str(dialog.additions)


@pytest.mark.usefixtures("request_context")
def test_removing_acknowledgments_of_a_service(with_user: tuple[UserId, str]) -> None:
    set_request_vars(_remove_acknowledgments="1")

    assert _issue(with_user[0], ["action.acknowledge"], "service", SERVICE_ROW) == [
        RemoveServiceAcknowledgement(HostName("myhost"), "CPU load")
    ]


@pytest.mark.usefixtures("request_context")
def test_removing_acknowledgments_of_an_aggregation_covers_each_leaf(
    with_user: tuple[UserId, str],
) -> None:
    set_request_vars(_remove_acknowledgments="1")

    assert _issue(with_user[0], ["action.acknowledge"], "aggr", AGGREGATION_ROW) == [
        (SiteId("local"), RemoveHostAcknowledgement(HostName("myhost"))),
        (SiteId("remote"), RemoveServiceAcknowledgement(HostName("otherhost"), "CPU load")),
    ]


@pytest.mark.usefixtures("request_context")
def test_the_remove_acknowledgments_confirmation_counts_distinct_acknowledgments() -> None:
    rows: list[Row] = [
        {**HOST_ROW, "host_comments_with_extra_info": [[1, "alice", "x", 4, 100]]},
        {**HOST_ROW, "host_comments_with_extra_info": [[1, "alice", "x", 4, 100]]},
        {**HOST_ROW, "host_comments_with_extra_info": [[2, "bob", "y", 4, 200]]},
    ]

    dialog = CommandRemoveAcknowledgments.confirm_dialog_options("HOST", rows[0], rows)

    assert "Acknowledgments: 2" in str(dialog.additions)


@pytest.mark.usefixtures("request_context")
def test_a_comment_is_added_to_a_host(with_user: tuple[UserId, str]) -> None:
    set_request_vars(_add_comment="1", _comment="look here")

    assert _issue(with_user[0], ["action.addcomment"], "host", HOST_ROW) == [
        AddHostComment(HostName("myhost"), "look here", True, with_user[0])
    ]


@pytest.mark.usefixtures("request_context")
def test_a_comment_is_added_to_a_service(with_user: tuple[UserId, str]) -> None:
    set_request_vars(_add_comment="1", _comment="look here")

    assert _issue(with_user[0], ["action.addcomment"], "service", SERVICE_ROW) == [
        AddServiceComment(HostName("myhost"), "look here", True, with_user[0], "CPU load")
    ]


@pytest.mark.usefixtures("request_context")
def test_adding_an_empty_comment_is_rejected(with_user: tuple[UserId, str]) -> None:
    set_request_vars(_add_comment="1")

    with pytest.raises(MKUserError):
        _issue(with_user[0], ["action.addcomment"], "host", HOST_ROW)


@pytest.mark.usefixtures("request_context")
def test_removing_downtimes_of_an_aggregation_deletes_those_of_each_leaf(
    with_user: tuple[UserId, str], mock_livestatus: MockLiveStatusConnection
) -> None:
    set_request_vars(_remove_downtimes="1")
    mock_livestatus.add_table(
        "downtimes",
        [{"id": 1, "host_name": "myhost", "service_description": "", "is_service": 0}],
        site="local",
    )
    mock_livestatus.add_table(
        "downtimes",
        [{"id": 2, "host_name": "otherhost", "service_description": "CPU load", "is_service": 1}],
        site="remote",
    )
    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id",
            "Filter: host_name = myhost",
            "Filter: is_service = 0",
            "And: 2",
            "AuthUser: ...",
        ],
        match_type="ellipsis",
        sites=["local"],
    )
    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id",
            "Filter: host_name = otherhost",
            "Filter: service_description = CPU load",
            "Filter: is_service = 1",
            "And: 3",
            "AuthUser: ...",
        ],
        match_type="ellipsis",
        sites=["remote"],
    )

    with mock_livestatus():
        issued = _issue(
            with_user[0],
            ["action.downtimes", "action.remove_all_downtimes"],
            "aggr",
            AGGREGATION_ROW,
        )

    assert issued == [
        (SiteId("local"), DeleteHostDowntime(1)),
        (SiteId("remote"), DeleteServiceDowntime(2)),
    ]


@pytest.mark.usefixtures("request_context")
def test_removing_a_plain_comment_only_deletes_the_comment(with_user: tuple[UserId, str]) -> None:
    set_request_vars(_delete_comments="1")
    row: Row = {**HOST_ROW, "comment_id": 5, "comment_entry_type": 1, "comment_author": "alice"}

    assert _issue(with_user[0], ["action.addcomment"], "comment", row) == [DeleteHostComment(5)]


@pytest.mark.usefixtures("request_context")
def test_the_remove_comment_confirmation_names_the_author() -> None:
    row: Row = {**HOST_ROW, "comment_id": 5, "comment_entry_type": 1, "comment_author": "alice"}

    dialog = CommandRemoveComments.confirm_dialog_options("HOST", row, [row])

    assert "alice" in str(dialog.additions)


@pytest.mark.usefixtures("request_context")
def test_removing_the_last_acknowledgment_comment_also_removes_the_acknowledgment(
    with_user: tuple[UserId, str], mock_livestatus: MockLiveStatusConnection
) -> None:
    set_request_vars(_delete_comments="1")
    rows: list[Row] = [
        {**SERVICE_ROW, "comment_id": 21, "comment_entry_type": 4, "comment_author": "alice"},
        {**SERVICE_ROW, "comment_id": 22, "comment_entry_type": 4, "comment_author": "bob"},
    ]
    mock_livestatus.add_table("comments", COMMENT_TABLE)
    mock_livestatus.expect_query(
        [
            "GET comments",
            "Columns: comment_id",
            "Filter: is_service = 1",
            "Filter: entry_type = 4",
            "AuthUser: ...",
            "ColumnHeaders: off",
        ],
        match_type="ellipsis",
    )

    with mock_livestatus():
        issued = _issue(with_user[0], ["action.addcomment"], "comment", rows[0], rows)

    assert issued == [
        RemoveServiceAcknowledgement(HostName("myhost"), "CPU load"),
        DeleteServiceComment(21),
    ]


@pytest.mark.usefixtures("request_context")
def test_the_remove_comments_confirmation_counts_the_comments() -> None:
    rows: list[Row] = [
        {**SERVICE_ROW, "comment_id": 21, "comment_author": "alice"},
        {**SERVICE_ROW, "comment_id": 22, "comment_author": "bob"},
    ]

    dialog = CommandRemoveComments.confirm_dialog_options("SVC", rows[0], rows)

    assert "Total comments: 2" in str(dialog.additions)


class TestScheduleDowntimes:
    @staticmethod
    def _submit(button: str, **form: str) -> None:
        set_request_vars(
            **{
                button: "1",
                "_down_comment": "maintenance",
                "_down_from_date": "2030-01-01",
                "_down_from_time": "10:00",
                "_down_to_date": "2030-01-01",
                "_down_to_time": "12:00",
            }
            | form
        )

    @staticmethod
    def _schedule(user_id: UserId, what: str, row: Row) -> list[CommandSpec]:
        with time_machine.travel(datetime(2029, 1, 1), tick=False):
            return _issue(user_id, ["action.downtimes", "general.see_all"], what, row)

    @pytest.mark.usefixtures("request_context")
    def test_a_service_downtime_spans_the_given_dates(self, with_user: tuple[UserId, str]) -> None:
        self._submit("_down_service")

        assert self._schedule(with_user[0], "service", SERVICE_ROW) == [
            ScheduleServiceDowntime(
                HostName("myhost"),
                datetime(2030, 1, 1, 10, 0),
                datetime(2030, 1, 1, 12, 0),
                1,
                0,
                0,
                with_user[0],
                f"Author ({with_user[0]}): maintenance",
                "CPU load",
            )
        ]

    @pytest.mark.usefixtures("request_context")
    def test_a_flexible_downtime_waits_for_a_problem(self, with_user: tuple[UserId, str]) -> None:
        self._submit(
            "_down_host",
            _down_duration_p__down_duration_USE="on",
            _down_duration_p__down_duration_hours="1",
        )

        assert self._schedule(with_user[0], "host", HOST_ROW) == [
            ScheduleHostDowntime(
                HostName("myhost"),
                datetime(2030, 1, 1, 10, 0),
                datetime(2030, 1, 1, 12, 0),
                0,
                0,
                3600,
                with_user[0],
                f"Author ({with_user[0]}): maintenance",
            )
        ]

    @pytest.mark.usefixtures("request_context")
    def test_an_ad_hoc_downtime_lasts_the_configured_minutes(
        self, with_user: tuple[UserId, str], set_config: SetConfig
    ) -> None:
        self._submit("_down_adhoc")

        with set_config(adhoc_downtime={"duration": 30, "comment": "Ad hoc"}):
            issued = self._schedule(with_user[0], "host", HOST_ROW)

        assert isinstance(issued[0], ScheduleHostDowntime)
        assert issued[0].end_time - issued[0].start_time == timedelta(minutes=30)
        assert issued[0].comment == f"Author ({with_user[0]}): Ad hoc"

    @pytest.mark.usefixtures("request_context")
    def test_an_aggregation_downtime_covers_each_leaf(self, with_user: tuple[UserId, str]) -> None:
        self._submit("_down_host")

        start, end = datetime(2030, 1, 1, 10, 0), datetime(2030, 1, 1, 12, 0)
        comment = f"Author ({with_user[0]}): maintenance"

        assert self._schedule(with_user[0], "aggr", AGGREGATION_ROW) == [
            (
                SiteId("local"),
                ScheduleHostDowntime(
                    HostName("myhost"), start, end, 1, 0, 0, with_user[0], comment
                ),
            ),
            (
                SiteId("remote"),
                ScheduleServiceDowntime(
                    HostName("otherhost"), start, end, 1, 0, 0, with_user[0], comment, "CPU load"
                ),
            ),
        ]

    @pytest.mark.usefixtures("request_context")
    def test_child_hosts_go_into_downtime_when_asked_for(
        self, with_user: tuple[UserId, str], mock_livestatus: MockLiveStatusConnection
    ) -> None:
        self._submit("_down_host", _include_children_p__include_children_USE="on")
        mock_livestatus.add_table(
            "hosts",
            [
                {"name": "myhost", "parents": []},
                {"name": "child", "parents": ["myhost"]},
            ],
            site="local",
        )
        mock_livestatus.expect_query(
            [
                "GET hosts",
                "Columns: name",
                "Filter: parents >= myhost",
                "Or: 1",
                "ColumnHeaders: off",
            ],
            sites=["local"],
        )

        with mock_livestatus():
            issued = self._schedule(with_user[0], "host", HOST_ROW)

        assert [cmd.host_name for cmd in issued if isinstance(cmd, ScheduleHostDowntime)] == [
            "myhost",
            "child",
        ]

    # fmt: off
    @pytest.mark.parametrize(
        "form",
        [
            pytest.param({"_down_comment": ""}, id="missing comment"),
            pytest.param({"_down_from_date": "2000-01-01", "_down_to_date": "2000-01-01"}, id="end in the past"),
            pytest.param({"_down_from_date": "2030-01-02"}, id="end before start"),
        ],
    )
    # fmt: on
    @pytest.mark.usefixtures("request_context")
    def test_an_invalid_downtime_form_is_rejected(
        self, with_user: tuple[UserId, str], form: dict[str, str]
    ) -> None:
        self._submit("_down_service", **form)

        with pytest.raises(MKUserError):
            self._schedule(with_user[0], "service", SERVICE_ROW)

    @pytest.mark.usefixtures("request_context")
    def test_the_confirmation_describes_a_flexible_host_downtime(self) -> None:
        self._submit(
            "_down_host",
            _down_duration_p__down_duration_USE="on",
            _down_duration_p__down_duration_minutes="90",
        )
        command = CommandScheduleDowntimes(NoRecurringDowntimes())

        additions = str(command.confirm_dialog_options("HOST", HOST_ROW, [HOST_ROW]).additions)

        assert "max. duration of 1 hours and 30 minutes" in additions
        assert "applies to all services of the host" in additions

    @pytest.mark.usefixtures("request_context")
    def test_a_service_downtime_can_be_confirmed_for_the_host_instead(self) -> None:
        command = CommandScheduleDowntimes(NoRecurringDowntimes())

        assert [var for _title, var in command.user_confirm_options(2, "SVC")] == [
            "_do_confirm_service_downtime",
            "_do_confirm_host_downtime",
        ]


# fmt: off
@pytest.mark.parametrize(
    "time_value, expected_end",
    [
        pytest.param(600, datetime(2030, 1, 15, 10, 10), id="seconds"),
        pytest.param("next_day", datetime(2030, 1, 16), id="next day"),
        pytest.param("next_week", datetime(2030, 1, 21), id="next week"),
        pytest.param("next_month", datetime(2030, 2, 1), id="next month"),
        pytest.param("next_year", datetime(2031, 1, 1), id="next year"),
    ],
)
# fmt: on
def test_a_downtime_preset_ends_at_the_start_of_the_next_period(
    time_value: int | Literal["next_day", "next_week", "next_month", "next_year"],
    expected_end: datetime,
) -> None:
    start = datetime(2030, 1, 15, 10, 0).timestamp()

    assert datetime.fromtimestamp(time_interval_end(time_value, start)) == expected_end


def test_a_downtime_preset_in_december_ends_in_the_next_year() -> None:
    start = datetime(2030, 12, 15, 10, 0).timestamp()

    assert datetime.fromtimestamp(time_interval_end("next_month", start)) == datetime(2031, 1, 1)
