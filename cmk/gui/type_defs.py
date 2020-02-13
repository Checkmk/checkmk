#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Union, List, Tuple, Text, Any, Optional

HTTPVariables = List[Tuple[str, Union[None, int, str, Text]]]
LivestatusQuery = Union[Text, str]

# View specific
Row = Dict[str, Any]  # TODO: Improve this type
Rows = List[Row]
PainterName = str
SorterName = str
ViewName = str
ColumnName = str
PainterSpec = Union[  #
    PainterName,  #
    Tuple[PainterName, Optional[ViewName], Optional[PainterName], Optional[ColumnName], Text],  #
    Tuple[PainterName, Optional[ViewName], Optional[PainterName], Optional[ColumnName]],  #
    Tuple[PainterName, Optional[ViewName], Optional[PainterName]],  #
    Tuple[PainterName, Optional[ViewName]],  #
]  #
ViewSpec = Dict[str, Any]

# Visual specific
FilterName = str
VisualContext = Dict[FilterName, Union[str, Dict[str, str]]]
SingleInfos = List[str]
