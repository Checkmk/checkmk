#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Union, List, Tuple, Any, Optional, Callable, NamedTuple
from cmk.utils.type_defs import UserId

HTTPVariables = List[Tuple[str, Union[None, int, str]]]
LivestatusQuery = str
PermissionName = str
RoleName = str

CSSSpec = Union[None, str, List[str], List[Optional[str]], str]

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
            ('link_view', Optional[ViewName]),
            ('tooltip', Optional[ColumnName]),
            ('join_index', Optional[ColumnName]),
            ('column_title', Optional[str]),
        ])):
    def __new__(cls, *value):
        value = value + (None,) * (5 - len(value))
        return super(PainterSpec, cls).__new__(cls, *value)

    def __repr__(self):
        return str(tuple(self))


ViewSpec = Dict[str, Any]
AllViewSpecs = Dict[Tuple[UserId, ViewName], ViewSpec]
PermittedViewSpecs = Dict[ViewName, ViewSpec]
SorterFunction = Callable[[ColumnName, Row, Row], int]
FilterHeaders = str

# Visual specific
FilterName = str
FilterHTTPVariables = Dict[str, str]
Visual = Dict[str, Any]
VisualTypeName = str
VisualContext = Dict[FilterName, Union[str, FilterHTTPVariables]]
InfoName = str
SingleInfos = List[InfoName]

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


TopicMenuItem = NamedTuple("TopicMenuItem", [
    ("name", str),
    ("title", str),
    ("url", str),
    ("sort_index", int),
    ("is_advanced", bool),
    ("icon_name", Optional[str]),
    ("emblem", Optional[str]),
])

TopicMenuTopic = NamedTuple("TopicMenuTopic", [
    ("name", "str"),
    ("title", "str"),
    ("items", List[TopicMenuItem]),
    ("icon_name", Optional[str]),
])

MegaMenu = NamedTuple("MegaMenu", [
    ("name", str),
    ("title", str),
    ("icon_name", str),
    ("sort_index", int),
    ("topics", Callable[[], List[TopicMenuTopic]]),
])
