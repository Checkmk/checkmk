#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from livestatus import SiteId

from cmk.utils.hostaddress import HostName
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from cmk.utils.servicename import ServiceName
from cmk.utils.user import UserId

from cmk.gui.views.command import commands
from cmk.gui.views.command.commands import _acknowledgement_needs_removal

ACK_COMMENT_TABLE = [
    {"host_name": "myhost", "service_description": "", "id": 11, "entry_type": 4},
    {"host_name": "myhost", "service_description": "", "id": 13, "entry_type": 1},
    {"host_name": "otherhost", "service_description": "", "id": 14, "entry_type": 4},
    {"host_name": "myhost", "service_description": "CPU load", "id": 21, "entry_type": 4},
    {"host_name": "myhost", "service_description": "CPU load", "id": 22, "entry_type": 4},
    {"host_name": "myhost", "service_description": "CPU load", "id": 23, "entry_type": 1},
    {"host_name": "myhost", "service_description": "Memory", "id": 24, "entry_type": 4},
]
REMOTE_ACK_COMMENT_TABLE = [
    {"host_name": "myhost", "service_description": "", "id": 31, "entry_type": 4},
    {"host_name": "myhost", "service_description": "CPU load", "id": 32, "entry_type": 4},
]


@pytest.mark.parametrize(
    "service_description, comment_ids, removal_expected",
    [
        pytest.param("CPU load", [21, 22], True, id="all ack comments of a service"),
        pytest.param("", [11], True, id="all ack comments of a host"),
        pytest.param("CPU load", [21], False, id="one of several ack comments"),
    ],
)
def test_acknowledgement_needs_removal(
    request_context: None,
    mock_livestatus: MockLiveStatusConnection,
    service_description: str,
    comment_ids: list[int],
    removal_expected: bool,
) -> None:
    rows = [
        {
            "site": "local",
            "host_name": "myhost",
            "service_description": service_description,
            "comment_id": comment_id,
        }
        for comment_id in comment_ids
    ]
    mock_livestatus.add_table("comments", ACK_COMMENT_TABLE, site="local")
    mock_livestatus.add_table("comments", REMOTE_ACK_COMMENT_TABLE, site="remote")
    mock_livestatus.expect_query(
        [
            "GET comments",
            "Columns: host_name service_description id",
            "Filter: entry_type = 4",
        ],
        match_type="ellipsis",
    )

    with mock_livestatus():
        assert _acknowledgement_needs_removal(rows[0], rows) == removal_expected


class TestRemoveDowntimeFromHostOrServiceDatasource:
    """A view whose painters do not fetch the downtime column.

    The rows of a user-defined host/service view only carry the columns its painters
    ask for, so ``service_downtimes`` / ``host_downtimes`` can be absent entirely.
    The ids are then looked up from the downtimes table instead.
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

        monkeypatch.setattr(commands, "_query_downtime_ids_for_leaf", _fake_query, raising=False)

        result = commands._rm_downtime_from_hst_or_svc_datasource(
            commands.CommandRemoveDowntimesHostServicesTable,
            "SVC",
            {"site": "heute", "host_name": "heute", "service_description": "CPU"},
            [],
        )

        assert result is not None
        downtime_commands, _dialog = result
        assert list(downtime_commands) == ["DEL_SVC_DOWNTIME;7\n"]
        assert queried_for == [("heute", "heute", "CPU")]
