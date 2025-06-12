#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from datamodel_code_generator.format import CustomCodeFormatter

from .postprocess import postprocess


class CodeFormatter(CustomCodeFormatter):
    def apply(self, code: str) -> str:
        code = postprocess(code)
        return code
