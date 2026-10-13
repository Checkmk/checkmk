#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import logging
import threading
from contextlib import nullcontext
from pathlib import Path

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.background_job.job import BackgroundJobDefines, BackgroundProcessInterface
from cmk.gui.config import Config
from cmk.gui.utils.roles import UserPermissionSerializableConfig
from cmk.gui.watolib.host_relation_detection import LinkOutcome
from cmk.gui.watolib.host_relation_scan import (
    accepted_pairs,
    AcceptedScan,
    conflicts_page,
    failed,
    finding_summaries,
    found_folders,
    FoundConflict,
    FoundGroup,
    FoundReason,
    FoundRelation,
    groups_page,
    RelationDetectionBackgroundJob,
    relations_page,
    RowFilter,
    run_counts,
    RunResult,
    SAMPLE_SIZE,
    ScanResult,
)
from cmk.gui.watolib.hosts_and_folders import make_folder_tree
from cmk.livestatus_client import SiteConfigurations


def _relation(
    source: str,
    target: str,
    *,
    finding: str = "word:ilo",
    outcome: LinkOutcome = LinkOutcome.LINK,
    direction: str = "parent",
    folders: tuple[str, str] = ("", ""),
) -> FoundRelation:
    return FoundRelation.model_validate(
        {
            "finding": finding,
            "source": source,
            "target": target,
            "kind_id": "management",
            "source_direction": direction,
            "folders": folders,
            "outcome": outcome,
        }
    )


def _group(
    *members: str,
    finding: str = "label:cmdb/sn",
    refusals: dict[str, str] | None = None,
    outside: list[str] | None = None,
) -> FoundGroup:
    return FoundGroup(
        finding=finding,
        kind_id="management",
        direction="parent",
        members=[HostName(member) for member in members],
        folders=[""],
        evidence="",
        reason=FoundReason(source="label", name="cmdb/sn", value="S-1"),
        settled=None,
        refusals=refusals or {},
        outside=outside or [],
    )


def _scan(
    relations: list[FoundRelation],
    *,
    groups: list[FoundGroup] | None = None,
    conflicts: list[FoundConflict] | None = None,
    findings: list[str] | None = None,
) -> ScanResult:
    return ScanResult(
        hosts_scanned=0,
        findings=findings or ["word:ilo", "label:cmdb/sn"],
        relations=relations,
        groups=groups or [],
        conflicts=conflicts or [],
    )


def _stored(result: ScanResult, accepted: AcceptedScan) -> list[tuple[str, str, str]]:
    return [
        (finding, str(pair.source), str(pair.target))
        for finding, pair in accepted_pairs(result, accepted)
    ]


def test_everything_a_finding_found_is_stored_however_much_it_is() -> None:
    """A fleet is not a table of five hundred rows: accepting a finding accepts all of it."""
    result = _scan([_relation(f"srv-{index:04}-ilo", f"srv-{index:04}") for index in range(1200)])

    assert len(accepted_pairs(result, AcceptedScan(scan_id="s", findings=["word:ilo"]))) == 1200


def test_a_finding_that_is_not_accepted_stores_nothing() -> None:
    result = _scan([_relation("a-ilo", "a"), _relation("w-1", "w-2", finding="label:cmdb/sn")])

    assert _stored(result, AcceptedScan(scan_id="s", findings=["word:ilo"])) == [
        ("word:ilo", "a-ilo", "a")
    ]


def test_a_finding_the_scan_did_not_read_is_refused() -> None:
    """Storing nothing for it would pass for a finding without relations; the client is told."""
    result = _scan([_relation("a-ilo", "a")])

    with pytest.raises(ValueError, match="word:nope"):
        accepted_pairs(result, AcceptedScan(scan_id="s", findings=["word:ilo", "word:nope"]))


def test_a_relation_taken_out_is_not_stored() -> None:
    result = _scan([_relation("a-ilo", "a"), _relation("b-ilo", "b")])

    assert _stored(
        result,
        AcceptedScan(scan_id="s", findings=["word:ilo"], excluded=["b-ilo|management|b"]),
    ) == [("word:ilo", "a-ilo", "a")]


def test_only_what_can_be_stored_is_stored() -> None:
    result = _scan(
        [
            _relation("a-ilo", "a", outcome=LinkOutcome.ALREADY_LINKED),
            _relation("b-ilo", "b", outcome=LinkOutcome.NOT_WRITABLE),
            _relation("c-ilo", "c", outcome=LinkOutcome.STORED_OTHERWISE),
        ]
    )

    assert _stored(result, AcceptedScan(scan_id="s", findings=["word:ilo"])) == []


def test_an_answered_group_relates_the_host_named_to_every_other_one() -> None:
    group = _group("blade-1", "blade-2", "oa", refusals={"blade-2": "No permission."})
    result = _scan([], groups=[group])

    assert _stored(
        result,
        AcceptedScan(scan_id="s", findings=["label:cmdb/sn"], answers={group.key: "oa"}),
    ) == [("label:cmdb/sn", "oa", "blade-1")]


def test_an_answer_from_outside_the_scope_relates_only_to_the_members_inside() -> None:
    group = _group("blade-1", "blade-2", "oa", outside=["blade-2", "oa"])
    result = _scan([], groups=[group])

    assert _stored(
        result,
        AcceptedScan(scan_id="s", findings=["label:cmdb/sn"], answers={group.key: "oa"}),
    ) == [("label:cmdb/sn", "oa", "blade-1")]


@pytest.mark.parametrize(
    "answers",
    [
        pytest.param({"management|x,y": "x"}, id="a group the scan did not find"),
        pytest.param({"management|blade-1,oa": "blade-9"}, id="a host that is no member"),
        pytest.param({"management|blade-1,oa": "oa"}, id="a member that cannot be written"),
    ],
)
def test_an_answer_the_scan_did_not_ask_for_is_refused(answers: dict[str, str]) -> None:
    result = _scan([], groups=[_group("blade-1", "oa", refusals={"oa": "No permission."})])

    with pytest.raises(ValueError):
        accepted_pairs(
            result, AcceptedScan(scan_id="s", findings=["label:cmdb/sn"], answers=answers)
        )


def test_a_resolved_conflict_stores_the_claim_picked() -> None:
    board = _relation("srv-01-ilo", "srv-01")
    reverse = _relation("srv-01", "srv-01-ilo", finding="label:cmdb/sn")
    conflict = FoundConflict(
        hosts=(HostName("srv-01"), HostName("srv-01-ilo")), claims=[board, reverse]
    )
    result = _scan([], conflicts=[conflict])

    assert _stored(
        result, AcceptedScan(scan_id="s", findings=[], resolutions={conflict.key: board.key})
    ) == [("word:ilo", "srv-01-ilo", "srv-01")]
    assert _stored(result, AcceptedScan(scan_id="s", findings=["word:ilo"])) == []


def test_a_finding_shows_samples_from_all_of_its_relations() -> None:
    result = _scan([_relation(f"srv-{index:02}-ilo", f"srv-{index:02}") for index in range(50)])

    (ilo, _serial) = finding_summaries(result)

    assert [row.source for row in ilo.samples] == [
        "srv-00-ilo",
        "srv-12-ilo",
        "srv-24-ilo",
        "srv-36-ilo",
        "srv-49-ilo",
    ]
    assert len(ilo.samples) == SAMPLE_SIZE


def test_a_finding_samples_what_it_would_store_rather_than_what_is_stored_already() -> None:
    result = _scan(
        [
            _relation("a-ilo", "a", outcome=LinkOutcome.ALREADY_LINKED),
            _relation("b-ilo", "b"),
        ]
    )

    (ilo, _serial) = finding_summaries(result)

    assert [row.source for row in ilo.samples] == ["b-ilo"]


def test_a_finding_counts_its_relations_and_its_questions() -> None:
    result = _scan(
        [
            _relation("a-ilo", "a"),
            _relation("b-ilo", "b", outcome=LinkOutcome.NOT_WRITABLE),
            _relation("w-1", "w-2", finding="label:cmdb/sn"),
        ],
        groups=[_group("w-3", "w-4")],
    )

    ilo, serial = finding_summaries(result)

    assert (ilo.counts[LinkOutcome.LINK], ilo.counts[LinkOutcome.NOT_WRITABLE]) == (1, 1)
    assert (serial.counts[LinkOutcome.LINK], serial.questions) == (1, 1)


def test_a_group_is_not_counted_as_a_relation() -> None:
    """A group answered already is not a row of the finding's relations to show."""
    answered = _group("w-3", "w-4").model_copy(update={"settled": "w-3"})
    result = _scan([], groups=[answered])

    (_ilo, serial) = finding_summaries(result)

    assert (sum(serial.counts.values()), serial.settled_groups) == (0, 1)


def test_a_finding_says_how_many_of_its_pairs_are_in_a_conflict() -> None:
    conflict = FoundConflict(
        hosts=(HostName("a"), HostName("a-ilo")),
        claims=[_relation("a-ilo", "a"), _relation("a", "a-ilo", finding="label:cmdb/sn")],
    )

    ilo, serial = finding_summaries(_scan([], conflicts=[conflict]))

    assert (ilo.conflicts, serial.conflicts) == (1, 1)


def test_a_page_is_narrowed_down_to_a_host_a_folder_and_an_outcome() -> None:
    rows = [
        _relation("web-01-ilo", "web-01", folders=("oob", "linux/web")),
        _relation("db-01-ilo", "db-01", folders=("oob", "linux/db")),
        _relation(
            "web-02-ilo", "web-02", folders=("oob", "linux/web"), outcome=LinkOutcome.NOT_WRITABLE
        ),
    ]

    page = relations_page(
        rows,
        RowFilter(search="WEB", folder="linux", outcome=LinkOutcome.LINK),
        offset=0,
        limit=10,
    )

    assert (page.total, [row.source for row in page.items]) == (1, ["web-01-ilo"])


def test_a_folder_holds_its_subfolders_but_not_its_namesakes() -> None:
    rows = [
        _relation("a-ilo", "a", folders=("linux", "linux")),
        _relation("b-ilo", "b", folders=("linux/web", "linux/web")),
        _relation("c-ilo", "c", folders=("linux2", "linux2")),
    ]

    page = relations_page(rows, RowFilter(folder="linux"), offset=0, limit=10)

    assert [row.source for row in page.items] == ["a-ilo", "b-ilo"]


def test_a_page_holds_a_slice_and_says_how_many_there_are() -> None:
    rows = [_relation(f"srv-{index:02}-ilo", f"srv-{index:02}") for index in range(25)]

    page = relations_page(rows, RowFilter(), offset=20, limit=10)

    assert (page.total, [row.source for row in page.items]) == (
        25,
        [f"srv-{i}-ilo" for i in range(20, 25)],
    )


def test_groups_and_conflicts_are_read_a_page_at_a_time_too() -> None:
    groups = [_group("w-1", "w-2"), _group("w-3", "w-4", finding="label:other")]
    conflict = FoundConflict(
        hosts=(HostName("a"), HostName("a-ilo")),
        claims=[_relation("a-ilo", "a"), _relation("a", "a-ilo")],
    )

    assert groups_page(groups, RowFilter(finding="label:other"), offset=0, limit=10).total == 1
    assert conflicts_page([conflict], RowFilter(search="a-ilo"), offset=0, limit=10).total == 1


def test_the_folders_to_filter_by_are_the_ones_something_was_found_in() -> None:
    result = _scan(
        [_relation("a-ilo", "a", folders=("oob", "linux"))], groups=[_group("w-1", "w-2")]
    )

    assert found_folders(result) == ["", "linux", "oob"]


def test_a_run_counts_per_finding_and_lists_what_it_could_not_store() -> None:
    done = RunResult(
        findings=["word:ilo"],
        relations=[
            _relation("a-ilo", "a"),
            _relation("b-ilo", "b", outcome=LinkOutcome.STORED_OTHERWISE),
            _relation("c-ilo", "c", outcome=LinkOutcome.ALREADY_LINKED),
        ],
    )

    ((finding, counts),) = run_counts(done)

    assert (finding, counts[LinkOutcome.LINK], counts[LinkOutcome.STORED_OTHERWISE]) == (
        "word:ilo",
        1,
        1,
    )
    assert [row.source for row in failed(done)] == ["b-ilo"]


def test_a_relation_is_keyed_the_way_the_page_takes_it_out() -> None:
    assert _relation("srv-01-ilo", "srv-01").key == "srv-01-ilo|management|srv-01"


def test_a_run_on_a_scan_that_is_gone_says_so(tmp_path: Path) -> None:
    RelationDetectionBackgroundJob().do_execute(
        AcceptedScan(scan_id="relation_scan-gone", findings=["word:ilo"]),
        BackgroundProcessInterface(
            work_dir=str(tmp_path),
            job_id="relation_detection-test",
            logger=logging.getLogger(),
            stop_event=threading.Event(),
            gui_context=lambda _user_permissions: nullcontext(),
            progress_update=io.StringIO(),
        ),
        UserPermissionSerializableConfig(roles={}, user_roles={}, default_user_profile_roles=[]),
        tree=make_folder_tree(Config()),
        pprint_value=False,
        use_git=False,
        activation_site_configs=SiteConfigurations({}),
        local_site=SiteId("NO_SITE"),
        acting_user=None,
    )

    assert (tmp_path / BackgroundJobDefines.result_message_filename).read_text() == (
        "The scan is gone. Scan again.\n"
    )
