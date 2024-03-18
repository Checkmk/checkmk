#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc

from cmk.gui.valuespec import ValueSpec


class UserAttribute(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def name(cls) -> str: ...

    @classmethod
    def is_custom(cls) -> bool:
        return False

    @abc.abstractmethod
    def topic(self) -> str: ...

    @abc.abstractmethod
    def valuespec(self) -> ValueSpec: ...

    def from_config(self) -> bool:
        return False

    def user_editable(self) -> bool:
        return True

    def permission(self) -> None | str:
        return None

    def show_in_table(self) -> bool:
        return False

    def add_custom_macro(self) -> bool:
        return False

    def domain(self) -> str:
        return "multisite"
