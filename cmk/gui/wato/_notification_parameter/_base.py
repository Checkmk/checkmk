#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod

from cmk.gui.form_specs.private.dictionary_extended import DictionaryExtended
from cmk.gui.valuespec import Dictionary as ValueSpecDictionary

from cmk.rulesets.v1.form_specs import Dictionary


class NotificationParameter(ABC):
    @property
    @abstractmethod
    def ident(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def spec(self) -> ValueSpecDictionary:
        raise NotImplementedError()

    def _form_spec(self) -> DictionaryExtended | Dictionary:
        raise NotImplementedError()
