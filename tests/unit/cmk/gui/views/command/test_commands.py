#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.htmllib.html import html
from cmk.gui.views.command import commands
from cmk.gui.views.command.commands import (
    _acknowledgement_needs_removal,
    _query_downtime_ids_for_leaf,
    CommandScheduleDowntimes,
    CommandScheduleDowntimesForm,
    NoRecurringDowntimes,
)
from cmk.livestatus_client import DeleteServiceDowntime
from cmk.livestatus_client.testing import MockLiveStatusConnection
from cmk.utils.servicename import ServiceName
from cmk.web.utils.html import HTML
from tests.testlib.gui.web_test_app import SetConfig

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
def test_acknowledgement_needs_removal(
    request_context: None,
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

    def test_service_row_without_the_downtimes_column(
        self,
        request_context: None,
        with_admin_login: UserId,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        queried_for: list[tuple[str | None, str, str | None]] = []

        def _fake_query(
            site: SiteId | None, host: HostName, service: ServiceName | None
        ) -> list[int]:
            queried_for.append((site, host, service))
            return [7]

        monkeypatch.setattr(commands, "_query_downtime_ids_for_leaf", _fake_query)

        result = commands._rm_downtime_from_hst_or_svc_datasource(
            commands.CommandRemoveDowntimesHostServicesTable,
            "SVC",
            {"site": "heute", "host_name": "heute", "service_description": "CPU"},
            [],
        )

        assert result is not None
        downtime_commands, _dialog = result
        assert list(downtime_commands) == [DeleteServiceDowntime(7)]
        assert queried_for == [("heute", "heute", "CPU")]

    def test_service_row_with_the_downtimes_column_does_not_query(
        self,
        request_context: None,
        with_admin_login: UserId,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _must_not_query(*_args: object) -> list[int]:
            raise AssertionError("the downtime ids are already in the row")

        monkeypatch.setattr(commands, "_query_downtime_ids_for_leaf", _must_not_query)

        result = commands._rm_downtime_from_hst_or_svc_datasource(
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

    def test_renders_a_button_for_a_usable_preset(
        self,
        request_context: None,
        set_config: SetConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        form = self._form(monkeypatch)

        with set_config(user_downtime_timeranges=[{"title": "2 hours", "end": 7200}]):
            assert "_downrange__7200" in str(form._get_duration_options())

    def test_skips_a_preset_whose_end_is_not_representable(
        self,
        request_context: None,
        set_config: SetConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        form = self._form(monkeypatch)

        with set_config(user_downtime_timeranges=[{"title": "far future", "end": 10**18}]):
            assert form._get_duration_options() == HTML.empty()

    def test_activates_the_first_preset_it_can_render(
        self,
        request_context: None,
        set_config: SetConfig,
        monkeypatch: pytest.MonkeyPatch,
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
            duration_options = str(form._get_duration_options())

        assert 'id="_downrange__7200"' in duration_options
        assert 'class="button duration active"' in duration_options
        assert "date__down_to_date" in html.final_javascript_code()
        assert "time__down_to_time" in html.final_javascript_code()
