#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.astrein.checker_localization import LocalizationChecker
from cmk.astrein.checker_module_layers import ModuleLayersChecker
from cmk.astrein.framework import ASTVisitorChecker


def all_checkers() -> dict[str, type[ASTVisitorChecker]]:
    return {
        "localization": LocalizationChecker,
        "module-layers": ModuleLayersChecker,
    }
