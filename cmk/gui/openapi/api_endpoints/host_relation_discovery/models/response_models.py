#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.common_fields import AnnotatedHostName


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
        description="The hosts sharing it.", example=["w-4711", "w-4712"]
    )


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
    hosts_scanned: int = api_field(description="How many hosts of Setup were read.", example=812)
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
                "examples": [{"value": "S-1", "hosts": ["w-4711", "w-4712"]}],
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
