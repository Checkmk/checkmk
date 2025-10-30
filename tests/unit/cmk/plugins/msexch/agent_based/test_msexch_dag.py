#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.msexch.agent_based.msexch_dag import (
    check_msexch_dag_contentindex,
    check_msexch_dag_copyqueue,
    check_msexch_dag_dbcopy,
    DEPRECATED_CONTENTINDEX_MESSAGE,
    discover_msexch_dag_contentindex,
    discover_msexch_dag_copyqueue,
    discover_msexch_dag_dbcopy,
    parse_msexch_dag,
)

# Test data fixtures
SINGLE_DATABASE_DATA = [
    ["RunspaceId", "d58353f4-f868-43b2-8404-25875841a47b"],
    ["Identity", "Mailbox Database 1\\S0141KL"],
    ["Name", "Mailbox Database 1\\S0141KL"],
    ["DatabaseName", "Mailbox Database 1"],
    ["Status", "Mounted"],
    ["MailboxServer", "S0141KL"],
    ["ActiveDatabaseCopy", "s0141kl"],
    ["ActivationSuspended", "False"],
    ["ContentIndexState", "Healthy"],
    ["CopyQueueLength", "0"],
    ["ReplayQueueLength", "0"],
    ["ActiveCopy", "True"],
]

MULTIPLE_DATABASE_DATA = [
    ["RunspaceId", "    d58353f4-f868-43b2-8404-25875841a47b"],
    ["Identity", "  Mailbox Database 1\\S0141KL"],
    ["Name", "    Mailbox Database 1\\S0141KL"],
    ["DatabaseName", "    Mailbox Database 1"],
    ["Status", "    Mounted"],
    ["MailboxServer", "    S0141KL"],
    ["ContentIndexState", "    Healthy"],
    ["CopyQueueLength", "    0"],
    ["ActiveCopy", "    True"],
    ["RunspaceId", "d58353f4-f868-43b2-8404-25875841a47b"],
    ["Identity", "Mailbox Database 2\\S0141KL"],
    ["Name", "Mailbox Database 2\\S0141KL"],
    ["DatabaseName", "Mailbox Database 2"],
    ["Status", "Healthy"],
    ["MailboxServer", "S0141KL"],
    ["ContentIndexState", "NotApplicable"],
    ["CopyQueueLength", "5"],
    ["ActiveCopy", "False"],
]

MALFORMED_DATA = [
    ["RunspaceId", "d58353f4-f868-43b2-8404-25875841a47b"],
    ["DatabaseName", "Test DB"],
    ["Status"],
    ["CopyQueueLength", "10"],
    ["ExtraField", ""],
]

EMPTY_DATA: StringTable = []


class TestParseMsexchDag:
    def test_parse_single_database(self) -> None:
        result = parse_msexch_dag(SINGLE_DATABASE_DATA)

        assert len(result) == 1

        db = result["Mailbox Database 1"]
        assert db["Status"] == "Mounted"
        assert db["MailboxServer"] == "S0141KL"
        assert db["ContentIndexState"] == "Healthy"
        assert db["CopyQueueLength"] == "0"
        assert db["ActiveCopy"] == "True"

    def test_parse_multiple_databases(self) -> None:
        result = parse_msexch_dag(MULTIPLE_DATABASE_DATA)

        assert len(result) == 2

        db1 = result["Mailbox Database 1"]
        assert db1["Status"] == "Mounted"
        assert db1["ContentIndexState"] == "Healthy"
        assert db1["CopyQueueLength"] == "0"

        db2 = result["Mailbox Database 2"]
        assert db2["Status"] == "Healthy"
        assert db2["ContentIndexState"] == "NotApplicable"
        assert db2["CopyQueueLength"] == "5"

    def test_parse_malformed_data(self) -> None:
        result = parse_msexch_dag(MALFORMED_DATA)

        assert result == {
            "Test DB": {
                "RunspaceId": "d58353f4-f868-43b2-8404-25875841a47b",
                "CopyQueueLength": "10",
                "ExtraField": "",
            }
        }

    def test_parse_no_database_name(self) -> None:
        data = [
            ["RunspaceId", "test-id"],
            ["Status", "Mounted"],
            ["CopyQueueLength", "0"],
        ]
        result = parse_msexch_dag(data)
        # Without DatabaseName, no databases are recorded
        assert result == {}


class TestDiscoverMsexchDagDbcopy:
    def test_discover_multiple_databases(self) -> None:
        section = {
            "Mailbox Database 1": {"Status": "Mounted"},
            "Mailbox Database 2": {"Status": "Healthy"},
        }

        services = list(discover_msexch_dag_dbcopy(section))

        assert services == [
            Service(
                item="Mailbox Database 1", parameters={"inv_key": "Status", "inv_val": "Mounted"}
            ),
            Service(
                item="Mailbox Database 2", parameters={"inv_key": "Status", "inv_val": "Healthy"}
            ),
        ]

    def test_discover_missing_status(self) -> None:
        section = {
            "Mailbox Database 1": {"MailboxServer": "S0141KL"},
            "Mailbox Database 2": {"Status": "Healthy"},
        }

        services = list(discover_msexch_dag_dbcopy(section))

        assert services == [
            Service(
                item="Mailbox Database 2", parameters={"inv_key": "Status", "inv_val": "Healthy"}
            )
        ]


class TestCheckMsexchDagDbcopy:
    def test_check_status_unchanged(self) -> None:
        section = {"Mailbox Database 1": {"Status": "Mounted"}}
        params = {"inv_key": "Status", "inv_val": "Mounted"}

        results = list(check_msexch_dag_dbcopy("Mailbox Database 1", params, section))

        assert results == [Result(state=State.OK, summary="Status is Mounted")]

    def test_check_status_changed(self) -> None:
        section = {"Mailbox Database 1": {"Status": "Dismounted"}}
        params = {"inv_key": "Status", "inv_val": "Mounted"}

        results = list(check_msexch_dag_dbcopy("Mailbox Database 1", params, section))

        assert results == [
            Result(state=State.WARN, summary="Status changed from Mounted to Dismounted")
        ]

    def test_check_key_not_found(self) -> None:
        section = {"Mailbox Database 1": {"MailboxServer": "S0141KL"}}
        params = {"inv_key": "Status", "inv_val": "Mounted"}

        results = list(check_msexch_dag_dbcopy("Mailbox Database 1", params, section))
        assert results == []


class TestDiscoverMsexchDagContentindex:
    def test_discover_healthy_contentindex(self) -> None:
        section = {
            "Mailbox Database 1": {"ContentIndexState": "Healthy"},
            "Mailbox Database 2": {"ContentIndexState": "Failed"},
        }

        services = list(discover_msexch_dag_contentindex(section))

        assert services == [
            Service(item="Mailbox Database 1"),
            Service(item="Mailbox Database 2"),
        ]

    def test_discover_not_applicable_filtered(self) -> None:
        section = {
            "Mailbox Database 1": {"ContentIndexState": "Healthy"},
            "Mailbox Database 2": {"ContentIndexState": "NotApplicable"},
            "Mailbox Database 3": {"Status": "Mounted"},  # No ContentIndexState
        }

        services = list(discover_msexch_dag_contentindex(section))

        assert services == [Service(item="Mailbox Database 1")]


class TestCheckMsexchDagContentindex:
    def test_check_healthy_contentindex(self) -> None:
        section = {"Mailbox Database 1": {"ContentIndexState": "Healthy"}}

        results = list(check_msexch_dag_contentindex("Mailbox Database 1", section))

        assert results == [Result(state=State.OK, summary="Status: Healthy")]

    def test_check_failed_contentindex(self) -> None:
        section = {"Mailbox Database 1": {"ContentIndexState": "Failed"}}

        results = list(check_msexch_dag_contentindex("Mailbox Database 1", section))

        assert results == [Result(state=State.WARN, summary="Status: Failed")]

    def test_check_not_applicable_contentindex(self) -> None:
        section = {"Mailbox Database 1": {"ContentIndexState": "NotApplicable"}}

        results = list(check_msexch_dag_contentindex("Mailbox Database 1", section))

        assert results == [
            Result(
                state=State.OK,
                summary=DEPRECATED_CONTENTINDEX_MESSAGE,
            )
        ]


class TestDiscoverMsexchDagCopyqueue:
    def test_discover_all_databases(self) -> None:
        section = {
            "Mailbox Database 1": {"CopyQueueLength": "0"},
            "Mailbox Database 2": {"CopyQueueLength": "5"},
            "Mailbox Database 3": {"Status": "Mounted"},  # No CopyQueueLength
        }

        services = list(discover_msexch_dag_copyqueue(section))

        assert services == [
            Service(item="Mailbox Database 1"),
            Service(item="Mailbox Database 2"),
            Service(item="Mailbox Database 3"),
        ]


class TestCheckMsexchDagCopyqueue:
    def test_check_queue_length_ok(self) -> None:
        section = {"Mailbox Database 1": {"CopyQueueLength": "50"}}
        params = {"levels": (100, 200)}

        results = list(check_msexch_dag_copyqueue("Mailbox Database 1", params, section))

        # check_levels returns both Result and Metric objects
        assert results == [
            Result(state=State.OK, summary="Queue length: 50"),
            Metric("length", 50, levels=(100, 200), boundaries=(0, None)),
        ]

    def test_check_queue_length_warn(self) -> None:
        section = {"Mailbox Database 1": {"CopyQueueLength": "150"}}
        params = {"levels": (100, 200)}

        results = list(check_msexch_dag_copyqueue("Mailbox Database 1", params, section))

        assert results == [
            Result(state=State.WARN, summary="Queue length: 150 (warn/crit at 100/200)"),
            Metric("length", 150, levels=(100, 200), boundaries=(0, None)),
        ]

    def test_check_queue_length_crit(self) -> None:
        section = {"Mailbox Database 1": {"CopyQueueLength": "250"}}
        params = {"levels": (100, 200)}

        results = list(check_msexch_dag_copyqueue("Mailbox Database 1", params, section))

        assert results == [
            Result(state=State.CRIT, summary="Queue length: 250 (warn/crit at 100/200)"),
            Metric("length", 250, levels=(100, 200), boundaries=(0, None)),
        ]
