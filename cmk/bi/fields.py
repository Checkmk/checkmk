#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from functools import partial

from cmk.fields import Boolean, Constant, Dict, Integer, List, Nested, String

ReqList = partial(List, required=True)
ReqDict = partial(Dict, required=True)
ReqConstant = partial(Constant, required=True)
ReqInteger = partial(Integer, required=True)
ReqString = partial(String, required=True)
ReqNested = partial(Nested, required=True)
ReqBoolean = partial(Boolean, required=True)
