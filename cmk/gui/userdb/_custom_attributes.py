#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.gui.config import active_config
from cmk.gui.valuespec import TextInput, ValueSpec

from . import ldap_connector
from ._user_attribute import get_user_attributes, user_attribute_registry, UserAttribute


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

    def from_config(self) -> bool:
        return self._from_config

    def user_editable(self) -> bool:
        return self._user_editable

    def permission(self) -> None | str:
        return self._permission

    def show_in_table(self) -> bool:
        return self._show_in_table

    def add_custom_macro(self) -> bool:
        return self._add_custom_macro

    def domain(self) -> str:
        return self._domain

    @classmethod
    def is_custom(cls) -> bool:
        return False


def register_custom_user_attributes(attributes: list[dict[str, Any]]) -> None:
    for attr in attributes:
        if attr["type"] != "TextAscii":
            raise NotImplementedError()

        @user_attribute_registry.register
        class _LegacyUserAttribute(GenericUserAttribute):
            # Play safe: Grab all necessary data at class construction time,
            # it's highly unclear if the attr dict is mutated later or not.
            _name = attr["name"]
            _valuespec = TextInput(title=attr["title"], help=attr["help"])
            _topic = attr.get("topic", "personal")
            _user_editable = attr["user_editable"]
            _show_in_table = attr.get("show_in_table", False)
            _add_custom_macro = attr.get("add_custom_macro", False)

            @classmethod
            def name(cls) -> str:
                return cls._name

            def valuespec(self) -> ValueSpec:
                return self._valuespec

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

            @classmethod
            def is_custom(cls) -> bool:
                return True

    ldap_connector.register_user_attribute_sync_plugins()


def update_config_based_user_attributes() -> None:
    _clear_config_based_user_attributes()
    register_custom_user_attributes(active_config.wato_user_attrs)


def _clear_config_based_user_attributes() -> None:
    for _name, attr in get_user_attributes():
        if attr.from_config():
            user_attribute_registry.unregister(attr.name())
