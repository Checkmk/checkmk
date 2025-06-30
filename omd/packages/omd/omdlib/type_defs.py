#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod

import cmk.ccc.resulttype as result

Config = dict[str, str]
Replacements = dict[str, str]
CommandOptions = dict[str, str | None]


class ConfigChoiceHasError(ABC):
    @abstractmethod
    def __call__(self, value: str) -> result.Result[None, str]:
        raise NotImplementedError
