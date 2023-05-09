#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Text,
    Tuple,
    TypedDict,
    Union,
)

from cmk.gui.exceptions import FinalizeRequest
from cmk.utils.type_defs import UserId

HTTPVariables = List[Tuple[str, Union[None, int, str]]]
LivestatusQuery = str
PermissionName = str
RoleName = str
CSSSpec = Union[None, str, List[str], List[Optional[str]], str]
ChoiceText = str
ChoiceId = Optional[str]
Choice = Tuple[ChoiceId, ChoiceText]
Choices = List[Choice]
ChoiceGroup = NamedTuple("ChoiceGroup", [
    ("title", Text),
    ("choices", Choices),
])
GroupedChoices = List[ChoiceGroup]

# Visual specific
FilterName = str
FilterHTTPVariables = Dict[str, str]
Visual = Dict[str, Any]
VisualName = str
VisualTypeName = str
VisualContext = Dict[FilterName, Union[str, FilterHTTPVariables]]
InfoName = str
SingleInfos = List[InfoName]
VisualLinkSpec = NamedTuple("VisualLinkSpec", [
    ("type_name", VisualTypeName),
    ("name", VisualName),
])

# View specific
Row = Dict[str, Any]  # TODO: Improve this type
Rows = List[Row]
PainterName = str
SorterName = str
ViewName = str
ColumnName = str
PainterParameters = Dict  # TODO: Improve this type
PainterNameSpec = Union[PainterName, Tuple[PainterName, PainterParameters]]


class PainterSpec(
        NamedTuple('PainterSpec', [
            ('painter_name', PainterNameSpec),
            ('link_spec', Optional[VisualLinkSpec]),
            ('tooltip', Optional[ColumnName]),
            ('join_index', Optional[ColumnName]),
            ('column_title', Optional[str]),
        ])):
    def __new__(cls, *value):
        # Some legacy views have optional fields like "tooltip" set to "" instead of None
        # in their definitions. Consolidate this case to None.
        value = (value[0],) + tuple(p or None for p in value[1:]) + (None,) * (5 - len(value))

        # With Checkmk 2.0 we introduced the option to link to dashboards. Now the link_view is not
        # only a string (view_name) anymore, but a tuple of two elemets: ('<visual_type_name>',
        # '<visual_name>'). Transform the old value to the new format.
        if isinstance(value[1], str):
            value = (value[0], VisualLinkSpec("views", value[1])) + value[2:]
        elif isinstance(value[1], tuple):
            value = (value[0], VisualLinkSpec(*value[1])) + value[2:]

        return super(PainterSpec, cls).__new__(cls, *value)

    def __repr__(self):
        return str((self.painter_name, tuple(self.link_spec) if self.link_spec else None) +
                   tuple(self)[2:])


ViewSpec = Dict[str, Any]
AllViewSpecs = Dict[Tuple[UserId, ViewName], ViewSpec]
PermittedViewSpecs = Dict[ViewName, ViewSpec]
SorterFunction = Callable[[ColumnName, Row, Row], int]
FilterHeaders = str

# Configuration related
ConfigDomainName = str


class SetOnceDict(dict):
    """A subclass of `dict` on which every key can only ever be set once.

    Apart from preventing keys to be set again, and the fact that keys can't be removed it works
    just like a regular dict.

    Examples:

        >>> d = SetOnceDict()
        >>> d['foo'] = 'bar'
        >>> d['foo'] = 'bar'
        Traceback (most recent call last):
        ...
        ValueError: key 'foo' already set

    """
    def __setitem__(self, key, value):
        if key in self:
            raise ValueError("key %r already set" % (key,))
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        raise NotImplementedError("Deleting items are not supported.")


class ABCMegaMenuSearch(ABC):
    """Abstract base class for search fields in mega menus"""
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def onopen(self) -> str:
        return 'cmk.popup_menu.focus_search_field("mk_side_search_field_%s");' % self.name

    @abstractmethod
    def show_search_field(self) -> None:
        ...


class _Icon(TypedDict):
    icon: str
    emblem: Optional[str]


Icon = Union[str, _Icon]


class TopicMenuItem(NamedTuple):
    name: str
    title: str
    sort_index: int
    url: str
    target: str = "main"
    is_show_more: bool = False
    icon: Optional[Icon] = None
    button_title: Optional[str] = None


class TopicMenuTopic(NamedTuple):
    name: "str"
    title: "str"
    items: List[TopicMenuItem]
    max_entries: int = 10
    icon: Optional[Icon] = None
    hide: bool = False


class MegaMenu(NamedTuple):
    name: str
    title: str
    icon: Icon
    sort_index: int
    topics: Callable[[], List[TopicMenuTopic]]
    search: Optional[ABCMegaMenuSearch] = None
    info_line: Optional[Callable[[], str]] = None


SearchQuery = str


@dataclass
class SearchResult:
    """Representation of a single result"""
    title: str
    url: str
    context: str = ""


SearchResultsByTopic = Iterable[Tuple[str, Iterable[SearchResult]]]

# Metric & graph specific
GraphIdentifier = Tuple[str, Any]
RenderingExpression = Tuple[Any, ...]


class RenderableRecipe(NamedTuple):
    title: str
    expression: RenderingExpression
    color: str
    line_type: str
    visible: bool


ActionResult = Optional[FinalizeRequest]

CustomAttr = typing.TypedDict(
    'CustomAttr',
    {
        'title': str,
        'help': str,
        'name': str,
        'topic': str,
        'type': str,
        'add_custom_macro': bool,
        'show_in_table': bool,
    },
    total=True,
)
