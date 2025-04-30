#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import override

from cmk.gui.type_defs import CustomUserAttrSpec
from cmk.gui.valuespec import TextInput, ValueSpec

from ._base import UserAttribute


class GenericUserAttribute(UserAttribute):
    def __init__(
        self,
        user_editable: bool,
        show_in_table: bool,
        add_custom_macro: bool,
        domain: str,
        permission: str | None,
        from_config: bool,
    ) -> None:
        super().__init__()
        self._user_editable = user_editable
        self._show_in_table = show_in_table
        self._add_custom_macro = add_custom_macro
        self._domain = domain
        self._permission = permission
        self._from_config = from_config

    @override
    def from_config(self) -> bool:
        return self._from_config

    @override
    def user_editable(self) -> bool:
        return self._user_editable

    @override
    def permission(self) -> None | str:
        return self._permission

    @override
    def show_in_table(self) -> bool:
        return self._show_in_table

    @override
    def add_custom_macro(self) -> bool:
        return self._add_custom_macro

    @override
    def domain(self) -> str:
        return self._domain

    @override
    @classmethod
    def is_custom(cls) -> bool:
        return False


def config_based_custom_user_attributes(
    attributes: Sequence[CustomUserAttrSpec],
) -> list[tuple[str, type[GenericUserAttribute]]]:
    custom_attributes: list[tuple[str, type[GenericUserAttribute]]] = []
    for attr in attributes:
        if attr["type"] != "TextAscii":
            raise NotImplementedError()

        class CustomUserAttribute(GenericUserAttribute):
            # Play safe: Grab all necessary data at class construction time,
            # it's highly unclear if the attr dict is mutated later or not.
            _name = attr["name"]
            _valuespec = TextInput(title=attr["title"], help=attr["help"])
            _topic = attr.get("topic", "personal")
            _user_editable = attr["user_editable"] or False
            _show_in_table = attr.get("show_in_table") or False
            _add_custom_macro = attr.get("add_custom_macro") or False

            @override
            @classmethod
            def name(cls) -> str:
                return cls._name

            @override
            def valuespec(self) -> ValueSpec:
                return self._valuespec

            @override
            def topic(self) -> str:
                return self._topic

            def __init__(self) -> None:
                super().__init__(
                    user_editable=self._user_editable,
                    show_in_table=self._show_in_table,
                    add_custom_macro=self._add_custom_macro,
                    domain="multisite",
                    permission=None,
                    from_config=True,
                )

            @override
            @classmethod
            def is_custom(cls) -> bool:
                return True

        custom_attributes.append((str(attr["name"]), CustomUserAttribute))

    return custom_attributes
