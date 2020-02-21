#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Union, List, Tuple, Text, Any, Optional, Callable
from cmk.utils.type_defs import UserId

HTTPVariables = List[Tuple[str, Union[None, int, str, Text]]]
LivestatusQuery = Union[Text, str]
PermissionName = str

# View specific
Row = Dict[str, Any]  # TODO: Improve this type
Rows = List[Row]
PainterName = str
SorterName = str
ViewName = str
ColumnName = str
PainterParameters = Dict  # TODO: Improve this type
PainterNameSpec = Union[PainterName, Tuple[PainterName, PainterParameters]]
PainterSpec = Union[  #
    Tuple[PainterNameSpec, Optional[ViewName], Optional[PainterName], Optional[ColumnName],
          Text],  #
    Tuple[PainterNameSpec, Optional[ViewName], Optional[PainterName], Optional[ColumnName]],  #
    Tuple[PainterNameSpec, Optional[ViewName], Optional[PainterName]],  #
    Tuple[PainterNameSpec, Optional[ViewName]],  #
]  #
ViewSpec = Dict[str, Any]
AllViewSpecs = Dict[Tuple[UserId, ViewName], ViewSpec]
PermittedViewSpecs = Dict[ViewName, ViewSpec]
SorterFunction = Callable[[ColumnName, Row, Row], int]

# Visual specific
FilterName = str
FilterHTTPVariables = Dict[str, Union[Text, str]]
Visual = Dict[str, Any]
VisualTypeName = str
VisualContext = Dict[FilterName, Union[Union[Text, str], FilterHTTPVariables]]
InfoName = str
SingleInfos = List[InfoName]
