#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore  # CMK-23620

from datamodel_code_generator.format import CustomCodeFormatter
from source.vue_formspec.postprocess import postprocess_vue_formspec_components


class CodeFormatter(CustomCodeFormatter):
    def apply(self, code: str) -> str:
        code = postprocess_vue_formspec_components(code)
        return code
