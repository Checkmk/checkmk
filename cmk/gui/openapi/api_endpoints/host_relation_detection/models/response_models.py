#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.common_fields import AnnotatedHostName
from cmk.gui.watolib.host_relation_detection import LinkOutcome

_REASON_EXAMPLE: dict[str, object] = {"word": "ilo", "source": None, "name": None, "value": None}

_RELATION_EXAMPLE: dict[str, object] = {
    "key": "srv-01-ilo|management|srv-01",
    "finding": "word:ilo",
    "source_host": "srv-01-ilo",
    "target_host": "srv-01",
    "kind": "management",
    "relation": "management_parent",
    "folders": ["oob", "linux"],
    "evidence": 'The name is "srv-01" with "ilo" added.',
    "reason": _REASON_EXAMPLE,
    "outcome": "link",
    "detail": "",
}

_GROUP_EXAMPLE: dict[str, object] = {
    "key": "management|w-4711,w-4712",
    "finding": "label:cmdb/sn",
    "kind": "management",
    "relation": "management_parent",
    "members": ["w-4711", "w-4712"],
    "folders": ["cmdb"],
    "evidence": 'All of them carry the host label "cmdb/sn" with the value "S-1".',
    "reason": {"word": None, "source": "label", "name": "cmdb/sn", "value": "S-1"},
    "outcome": "undecided",
    "settled": None,
    "refusals": {},
}

_COUNTS_EXAMPLE = {
    "link": 371,
    "already_linked": 26,
    "stored_otherwise": 1,
    "not_writable": 15,
    "undecided": 2,
}


@api_model
class RelationReasonModel:
    """What a proposal was found by: a word in a host name, or a value both hosts carry."""

    word: str | None = api_field(
        description="The word one host name carries on top of the other, if the names are "
        "what found the pair.",
        example="ilo",
    )
    source: Literal["label", "attribute"] | None = api_field(
        description="Whether the shared value is a host label or a custom host attribute, if "
        "a shared value is what found the pair.",
        example=None,
    )
    name: str | None = api_field(description="The name of the label or attribute.", example=None)
    value: str | None = api_field(description="The value the hosts share.", example=None)


@api_model
class RelationRowModel:
    key: str = api_field(
        description="What identifies the relation when it is left out of a run.",
        example="srv-01-ilo|management|srv-01",
    )
    finding: str = api_field(description="The finding that proposed it.", example="word:ilo")
    source_host: AnnotatedHostName = api_field(
        description="The host the relation is stored on.", example="srv-01-ilo"
    )
    target_host: AnnotatedHostName = api_field(
        description="The host it is related to.", example="srv-01"
    )
    kind: str = api_field(description="The kind of relation.", example="management")
    relation: str = api_field(
        description="The relation, named by the end the source host sits at.",
        example="management_parent",
    )
    folders: list[str] = api_field(
        description="The folders of the source and the target host.", example=["oob", "linux"]
    )
    evidence: str = api_field(
        description="What speaks for these two hosts belonging together, in one sentence.",
        example='The name is "srv-01" with "ilo" added.',
    )
    reason: RelationReasonModel | None = api_field(
        description="What the sentence says, taken apart.", example=_REASON_EXAMPLE
    )
    outcome: LinkOutcome = api_field(
        description="What storing it does: 'link', or why it does nothing - "
        "'already_linked', 'stored_otherwise', 'not_writable'.",
        example="link",
    )
    detail: str = api_field(
        description="Why, for the outcomes that need a reason. Empty otherwise.", example=""
    )


@api_model
class RelationGroupModel:
    """Hosts that belong together, with nothing saying which of them sits where."""

    key: str = api_field(
        description="What identifies the group when it is answered.",
        example="management|w-4711,w-4712",
    )
    finding: str = api_field(
        description="The finding that found these hosts.", example="label:cmdb/sn"
    )
    kind: str = api_field(
        description="The kind of relation these hosts would get.", example="management"
    )
    relation: str = api_field(
        description="The relation the host that gets named would hold to all the others.",
        example="management_parent",
    )
    members: list[AnnotatedHostName] = api_field(
        description="The hosts carrying the same value.", example=["w-4711", "w-4712"]
    )
    folders: list[str] = api_field(description="The folders of the members.", example=["cmdb"])
    evidence: str = api_field(
        description="What speaks for these hosts belonging together, in one sentence.",
        example='All of them carry the host label "cmdb/sn" with the value "S-1".',
    )
    reason: RelationReasonModel = api_field(
        description="What the sentence says, taken apart.",
        example={"word": None, "source": "label", "name": "cmdb/sn", "value": "S-1"},
    )
    outcome: LinkOutcome = api_field(
        description="'undecided' while the question is open, 'already_linked' once one of "
        "the members holds this relation to all the others.",
        example="undecided",
    )
    settled: AnnotatedHostName | None = api_field(
        description="The member that already holds this relation to all the others.",
        example=None,
    )
    refusals: dict[str, str] = api_field(
        description="Per member that cannot be named, why - such a host cannot be written.",
        example={},
    )
    partners: dict[str, list[AnnotatedHostName]] = api_field(
        description="Per member, the hosts it is related to when it is named - the members "
        "that can be written, and, for a member outside the folder or site looked in, only "
        "those inside it.",
        example={"w-4711": ["w-4712"], "w-4712": ["w-4711"]},
    )


@api_model
class RelationConflictModel:
    """Two hosts the findings say different things about."""

    key: str = api_field(
        description="What identifies the conflict when it is resolved.",
        example="srv-01|srv-01-ilo",
    )
    hosts: list[AnnotatedHostName] = api_field(
        description="The two hosts.", example=["srv-01", "srv-01-ilo"]
    )
    claims: list[RelationRowModel] = api_field(
        description="What each finding says about them.", example=[_RELATION_EXAMPLE]
    )


@api_model
class RowsPageModel:
    total: int = api_field(description="How many rows match, on all pages.", example=1204)
    relations: list[RelationRowModel] = api_field(
        description="The relations on this page, if relations were asked for.",
        example=[_RELATION_EXAMPLE],
    )
    groups: list[RelationGroupModel] = api_field(
        description="The groups on this page, if groups were asked for.", example=[]
    )
    conflicts: list[RelationConflictModel] = api_field(
        description="The conflicts on this page, if conflicts were asked for.", example=[]
    )
    keys: list[str] = api_field(
        description="The key of every relation that matches and can be stored, on all pages, "
        "if asked for.",
        example=[],
    )


@api_model
class WordExampleModel:
    named: AnnotatedHostName = api_field(
        description="The host whose name carries the word.", example="srv-01-ilo"
    )
    base: AnnotatedHostName = api_field(
        description="The host whose name it is with the word taken out.", example="srv-01"
    )


@api_model
class WordFindingModel:
    word: str = api_field(description="The word, in lower case.", example="ilo")
    pairs: int = api_field(
        description="How many hosts are named like another host plus this word.", example=12
    )
    examples: list[WordExampleModel] = api_field(
        description="A few of these pairs.",
        example=[{"named": "srv-01-ilo", "base": "srv-01"}],
    )
    kind: str | None = api_field(
        description="The kind of relation whose vendors use this word, or null for a word "
        "no kind declares.",
        example="management",
    )


@api_model
class ValueExampleModel:
    value: str = api_field(description="The value the hosts share.", example="S-1")
    hosts: list[AnnotatedHostName] = api_field(
        description="The first few of the hosts sharing it, by name.", example=["w-4711", "w-4712"]
    )
    size: int = api_field(description="How many hosts share it.", example=2)


@api_model
class ValueCountModel:
    value: str = api_field(description="A value of the label or attribute.", example="board")
    groups: int = api_field(
        description="In how many groups exactly one host carries it.", example=40
    )


@api_model
class ToldApartModel:
    """What says which host of each group is which, as far as the hosts give it away."""

    by: Literal["names", "value"] = api_field(
        description="Whether a word in one host name tells them apart, or a value of a label "
        "or attribute only one host of the group carries.",
        example="value",
    )
    kind: str | None = api_field(
        description="For words: the kind of relation whose vendors use them.", example=None
    )
    words: list[str] = api_field(
        description="For words: the words, the most frequent first.", example=[]
    )
    groups: int = api_field(
        description="For words: in how many groups exactly one host carries one.", example=0
    )
    source: Literal["label", "attribute"] | None = api_field(
        description="For a value: whether it is a host label or a custom host attribute.",
        example="label",
    )
    name: str | None = api_field(
        description="For a value: the name of the label or attribute.", example="cmdb/kind"
    )
    values: list[ValueCountModel] = api_field(
        description="For a value: each value that stands alone in its group.",
        example=[{"value": "board", "groups": 40}, {"value": "server", "groups": 40}],
    )
    suggested: str | None = api_field(
        description="For a value: the one that reads like the deciding end, if any does.",
        example=None,
    )


@api_model
class ValueFindingModel:
    source: Literal["label", "attribute"] = api_field(
        description="Whether the value is a host label or a custom host attribute.",
        example="label",
    )
    name: str = api_field(description="The name of the label or attribute.", example="cmdb/sn")
    groups: int = api_field(
        description="How many values are each shared by a handful of hosts.", example=40
    )
    largest_group: int = api_field(
        description="How many hosts the most widely shared of these values is shared by.",
        example=2,
    )
    examples: list[ValueExampleModel] = api_field(
        description="A few of these values, each with the hosts sharing it.",
        example=[{"value": "S-1", "hosts": ["w-4711", "w-4712"]}],
    )
    too_wide: int = api_field(
        description="How many values are shared by more hosts than one machine has. They pair "
        "nothing: a finding with only such values is a category rather than an identity.",
        example=0,
    )
    told_apart: ToldApartModel | None = api_field(
        description="What says which host of each group is which, or null where nothing does.",
        example=None,
    )


@api_model
class SuggestionsModel:
    hosts_scanned: int = api_field(
        description="How many hosts were looked at: those in scope, or every host of Setup the "
        "user may see.",
        example=812,
    )
    words: list[WordFindingModel] = api_field(
        description="Words that turn one host name into another, the ones a kind declares first.",
        example=[
            {
                "word": "ilo",
                "pairs": 12,
                "examples": [{"named": "srv-01-ilo", "base": "srv-01"}],
                "kind": "management",
            }
        ],
    )
    values: list[ValueFindingModel] = api_field(
        description="Labels and attributes whose values each look like one machine.",
        example=[
            {
                "source": "label",
                "name": "cmdb/sn",
                "groups": 40,
                "largest_group": 2,
                "examples": [{"value": "S-1", "hosts": ["w-4711", "w-4712"], "size": 2}],
                "too_wide": 0,
                "told_apart": None,
            }
        ],
    )
    label_names: list[str] = api_field(
        description="Every host label there is.", example=["cmdb/kind", "cmdb/sn"]
    )
    attribute_names: list[str] = api_field(
        description="Every custom host attribute there is.", example=["cmdb_serial"]
    )


@api_model
class RelationJobModel:
    job_id: str = api_field(
        description="The background job now scanning, respectively storing.",
        example="relation_scan-8f2a1c",
    )


@api_model
class FindingSummaryModel:
    id: str = api_field(description="The finding.", example="word:ilo")
    counts: dict[str, int] = api_field(
        description="How many of its relations fall to each outcome. A question about a group "
        "counts as one.",
        example=_COUNTS_EXAMPLE,
    )
    samples: list[RelationRowModel] = api_field(
        description="A few of its relations, spread over all of them.",
        example=[_RELATION_EXAMPLE],
    )
    questions: int = api_field(
        description="Its groups of hosts nothing tells apart, still to be answered.", example=0
    )
    settled_groups: int = api_field(description="Its groups of hosts answered already.", example=0)
    conflicts: int = api_field(
        description="The pairs of hosts it disagrees about with another finding. They are not "
        "in its counts.",
        example=0,
    )


@api_model
class ScanSummaryModel:
    hosts_scanned: int = api_field(
        description="How many hosts were looked at: those in scope, or every host of Setup the "
        "user may see.",
        example=812,
    )
    findings: list[FindingSummaryModel] = api_field(
        description="What each finding comes to, in the order they were asked for.",
        example=[
            {
                "id": "word:ilo",
                "counts": _COUNTS_EXAMPLE,
                "samples": [_RELATION_EXAMPLE],
                "questions": 0,
                "settled_groups": 0,
                "conflicts": 0,
            }
        ],
    )
    conflicts: int = api_field(
        description="How many pairs of hosts the findings disagree about.", example=0
    )
    folders: list[str] = api_field(
        description="The folders the hosts of what was found are in, by path, to filter by.",
        example=["", "oob", "linux"],
    )


@api_model
class RunSummaryModel:
    findings: list[FindingSummaryModel] = api_field(
        description="What came of the relations of each finding.",
        example=[
            {
                "id": "word:ilo",
                "counts": {"link": 371},
                "samples": [],
                "questions": 0,
                "settled_groups": 0,
                "conflicts": 0,
            }
        ],
    )
    failed: int = api_field(description="How many relations could not be stored.", example=15)


@api_model
class RelationJobStatusModel:
    running: bool = api_field(description="Whether the job is still running.", example=False)
    message: str = api_field(
        description="The most recent progress line of the job, for display while it runs.",
        example="[137/412] srv-137-ilo -> srv-137: stored",
    )
    summary: str = api_field(
        description="The job in one line, once it has finished. Empty while it runs.",
        example="371 stored, 26 already related",
    )
    scan: ScanSummaryModel | None = api_field(
        description="What a finished scan found. Null for a run, or while it runs.",
        example=None,
    )
    run: RunSummaryModel | None = api_field(
        description="What a finished run stored. Null for a scan, or while it runs.",
        example=None,
    )
