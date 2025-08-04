#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=too-few-public-methods

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, KW_ONLY
from typing import Generic, TypeVar

from ._localize import Label, Title
from ._style import Alignment, BackgroundColor, LabelColor
from ._types import SupportsRichComparison
from ._unit import Unit


@dataclass(frozen=True)
class BoolField:
    """
    Args:
        title: A title
        render_true: Rendering of the value 'True'
        render_false: Rendering of the value 'False'
        style: A function which returns alignments, background or label colors
    """

    title: Title
    _: KW_ONLY
    render_true: Label | str = Label("Yes")
    render_false: Label | str = Label("No")
    style: Callable[
        [bool],
        Iterable[Alignment | BackgroundColor | LabelColor],
    ] = lambda _: ()

    def __post_init__(self) -> None:
        if not self.title.localize(lambda v: v):
            raise ValueError(self.title)


@dataclass(frozen=True)
class NumberField:
    """
    Args:
        title: A title
        render: Rendering of a numerical value
        style: A function which returns alignments, background or label colors
    """

    title: Title
    _: KW_ONLY
    render: Callable[[int | float], Label | str] | Unit = str
    style: Callable[
        [int | float],
        Iterable[Alignment | BackgroundColor | LabelColor],
    ] = lambda _: ()

    def __post_init__(self) -> None:
        if not self.title.localize(lambda v: v):
            raise ValueError(self.title)


@dataclass(frozen=True)
class TextField:
    """
    Args:
        title: A title
        render: Rendering of a string
        style: A function which returns alignments, background or label colors
        sort_key: Enables rich comparisons of strings, ie. lower, lower equal, greater, greater equal
    """

    title: Title
    _: KW_ONLY
    render: Callable[[str], Label | str] = lambda v: v
    style: Callable[
        [str],
        Iterable[Alignment | BackgroundColor | LabelColor],
    ] = lambda _: ()
    sort_key: Callable[[str], SupportsRichComparison] | None = None

    def __post_init__(self) -> None:
        if not self.title.localize(lambda v: v):
            raise ValueError(self.title)


T = TypeVar("T", int, float, str)
type OrderedMapping[T] = Mapping[T, Label | str]


@dataclass(frozen=True)
class ChoiceField(Generic[T]):
    """
    Args:
        title: A title
        mappings: Maps the original value to a readable label
        style: A function which returns alignments, background or label colors
    """

    title: Title
    _: KW_ONLY
    mapping: OrderedMapping[T]
    style: Callable[[T], Iterable[Alignment | BackgroundColor | LabelColor]] = lambda _: ()

    def __post_init__(self) -> None:
        if not self.title.localize(lambda v: v):
            raise ValueError(self.title)
        if not self.mapping:
            raise ValueError(self.mapping)


type OrderedAttributes = Mapping[
    str,
    BoolField | NumberField | TextField | ChoiceField[int] | ChoiceField[float] | ChoiceField[str],
]
type OrderedColumns = Mapping[
    str,
    BoolField | NumberField | TextField | ChoiceField[int] | ChoiceField[float] | ChoiceField[str],
]


@dataclass(frozen=True, kw_only=True)
class View:
    """
    Args:
        name: A unique name
        title: A title
        group: Groups several views below this title
    """

    name: str
    title: Title
    group: Title | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)
        if not self.title.localize(lambda v: v):
            raise ValueError(self.title)
        if self.group is not None and not self.group.localize(lambda v: v):
            raise ValueError(self.group)


@dataclass(frozen=True)
class Table:
    """
    Args:
        columns: Specifies fields for columns
        view: A view
    """

    columns: OrderedColumns = field(default_factory=dict)
    view: View | None = None

    def __post_init__(self) -> None:
        for column in self.columns:
            if not column:
                raise ValueError(column)


@dataclass(frozen=True, kw_only=True)
class Node:
    """
    Args:
        name: A unique name
        title: A title
        path: The path to the node
        attributes: Specifies fields for attributes
        table: A table
    """

    name: str
    title: Title
    path: Sequence[str]
    attributes: OrderedAttributes = field(default_factory=dict)
    table: Table = Table()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)
        if not self.title.localize(lambda v: v):
            raise ValueError(self.title)
        if not self.path:
            raise ValueError(self.path)
        for edge in self.path:
            if not edge:
                raise ValueError(edge)
        for key in self.attributes:
            if not key:
                raise ValueError(key)
