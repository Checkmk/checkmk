#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from annotated_types import MinLen

from cmk.ccc.site import SiteId
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.common_fields import AnnotatedFolder
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator


@api_model
class HostValueModel:
    source: Literal["label", "attribute"] = api_field(
        description="Whether the value is a host label or a custom host attribute.",
        example="label",
    )
    name: Annotated[str, MinLen(1)] = api_field(
        description="The name of the label or attribute.", example="cmdb/sn"
    )


@api_model
class ScopeModel:
    folder: AnnotatedFolder | ApiOmitted = api_field(
        description="Only relations with a host in this folder or one of its subfolders. The "
        "other host may sit in any folder.",
        example="/oob",
        default_factory=ApiOmitted,
    )
    site: Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_exist)] | ApiOmitted = (
        api_field(
            description="Only relations with a host monitored on this site. The other host may be "
            "on any site.",
            example="central",
            default_factory=ApiOmitted,
        )
    )


@api_model
class SuggestEvidenceRequestModel:
    words: list[str] = api_field(
        description="Words the user typed. Each of them is reported with what it finds, "
        "even if no host carries it.",
        example=["oob"],
        default_factory=list,
    )
    values: list[HostValueModel] = api_field(
        description="Labels and attributes the user added. Each of them is reported with "
        "what it finds, however widely its values are shared.",
        example=[{"source": "label", "name": "cmdb/sn"}],
        default_factory=list,
    )
    look_in: Annotated[list[Literal["names", "values"]], MinLen(1)] = api_field(
        description="Where to look: in the host names, in the labels and attributes hosts "
        "share, or both.",
        example=["names"],
        default_factory=lambda: ["names", "values"],
    )
    scope: ScopeModel | ApiOmitted = api_field(
        description="Where to look. Every host the user may see is still read as the other "
        "end of a relation. Omitted, it is all of Setup.",
        example={"folder": "/oob"},
        default_factory=ApiOmitted,
    )


@api_model
class MarkedValueModel:
    source: Literal["label", "attribute"] = api_field(
        description="Whether the value is a host label or a custom host attribute.",
        example="label",
    )
    name: Annotated[str, MinLen(1)] = api_field(
        description="The name of the label or attribute.", example="cmdb/kind"
    )
    value: Annotated[str, MinLen(1)] = api_field(
        description="The value it carries on the host at the deciding end.", example="board"
    )


@api_model
class FindingModel:
    id: Annotated[str, MinLen(1)] = api_field(
        description="What the page calls this finding. Every relation the scan proposes names "
        "the finding it came from by this id.",
        example="word:ilo",
    )
    kind: str = api_field(description="The kind of relation it stands for.", example="management")
    words: list[str] = api_field(
        description="Words in the host names that mark the host at the deciding end - "
        '"srv-01-ilo" next to "srv-01". Without \'paired_by\' they pair the two hosts as well.',
        example=["ilo"],
        default_factory=list,
    )
    marked_by: MarkedValueModel | ApiOmitted = api_field(
        description="Instead of words: a label or attribute value that marks the host at "
        "the deciding end. Needs 'paired_by' beside it.",
        example={"source": "label", "name": "cmdb/kind", "value": "board"},
        default_factory=ApiOmitted,
    )
    paired_by: HostValueModel | ApiOmitted = api_field(
        description="A label or attribute whose value the two hosts share, such as a serial "
        "number. Hosts sharing a value that nothing marks are asked about as a group.",
        example={"source": "label", "name": "cmdb/sn"},
        default_factory=ApiOmitted,
    )


@api_model
class ScanRequestModel:
    findings: Annotated[list[FindingModel], MinLen(1)] = api_field(
        description="What to look for, in the order the page lists it. Where two findings "
        "propose the same relation, it is the first one's.",
        example=[
            {"id": "word:ilo", "kind": "management", "words": ["ilo"]},
            {
                "id": "label:cmdb/sn",
                "kind": "management",
                "marked_by": {"source": "label", "name": "cmdb/kind", "value": "board"},
                "paired_by": {"source": "label", "name": "cmdb/sn"},
            },
        ],
    )
    scope: ScopeModel | ApiOmitted = api_field(
        description="Where to look. Every host the user may see is still read as the other "
        "end of a relation. Omitted, it is all of Setup.",
        example={"folder": "/oob"},
        default_factory=ApiOmitted,
    )


@api_model
class AcceptRequestModel:
    scan_id: str = api_field(description="The scan to store from.", example="relation_scan-8f2a1c")
    findings: list[str] = api_field(
        description="The findings whose relations are stored. The relations of the others are not.",
        example=["word:ilo"],
    )
    excluded: list[str] = api_field(
        description="Relations of those findings that are not stored, by key.",
        example=["srv-02-ilo|management|srv-02"],
        default_factory=list,
    )
    answers: dict[str, str] = api_field(
        description="Per group of hosts the scan could only ask about, by key, the host that "
        "is at the deciding end. It is related to every other host of the group.",
        example={"management|w-4711,w-4712": "w-4712"},
        default_factory=dict,
    )
    resolutions: dict[str, str] = api_field(
        description="Per pair of hosts the findings disagree about, by key, the claim to "
        "store, by its key. A conflict left out here stores nothing.",
        example={"srv-01|srv-01-ilo": "srv-01-ilo|management|srv-01"},
        default_factory=dict,
    )
