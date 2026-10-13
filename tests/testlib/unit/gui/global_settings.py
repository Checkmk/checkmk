#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager

import pytest

from cmk.ccc.user import UserId
from cmk.gui import login
from cmk.gui.permissions import permission_registry
from cmk.gui.role_types import CustomUserRole
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_variable_group_registry,
    config_variable_registry,
    ConfigVariable,
    ConfigVariableGroup,
    ConfigVariableHint,
    GlobalSettingsContext,
)
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import FormSpec, Integer
from cmk.shared_typing import global_settings as shared
from cmk.web.utils.permission_verification import PermissionName


def patch_factory_defaults(monkeypatch: pytest.MonkeyPatch, defaults: Mapping[str, object]) -> None:
    """Give a factory default to the test variables only, which hides every real variable
    and with it every real group. The real lookup runs an automation that needs a site."""
    monkeypatch.setattr(
        ABCConfigDomain,
        "get_all_default_globals",
        classmethod(lambda cls: defaults),  # noqa: ARG005
    )


def _an_integer(_context: GlobalSettingsContext) -> Integer:
    return Integer(title=Title("Test"))


@contextmanager
def registered[ModelT](
    group: ConfigVariableGroup,
    *varnames: str,
    primary_domain: type[ABCConfigDomain] = ConfigDomainGUI,
    form_spec: Callable[[GlobalSettingsContext], FormSpec[ModelT]] | None = None,
    hints: Callable[[], Sequence[ConfigVariableHint]] = tuple,
) -> Iterator[None]:
    config_variable_group_registry.register(group)
    variables = [
        ConfigVariable(
            group=group,
            primary_domain=primary_domain,
            ident=varname,
            form_spec=_an_integer if form_spec is None else form_spec,
            hints=hints,
        )
        for varname in varnames
    ]
    shadowed = [
        config_variable_registry[varname]
        for varname in varnames
        if varname in config_variable_registry
    ]
    for variable in variables:
        config_variable_registry.register(variable)
    try:
        yield
    finally:
        for variable in variables:
            config_variable_registry.unregister(variable.ident())
        for variable in shadowed:
            config_variable_registry.register(variable)
        config_variable_group_registry.unregister(group.ident())


@contextmanager
def logged_in(user_id: UserId, *permissions: PermissionName) -> Iterator[None]:
    role = CustomUserRole(
        alias="Test role",
        permissions=dict.fromkeys(permissions, True),
        builtin=False,
        basedon="no_permissions",
    )
    with login.TransactionIdContext(
        user_id,
        UserPermissions({"test_role": role}, permission_registry, {user_id: ["test_role"]}, []),
    ):
        yield


def shown_variables(
    data: shared.GlobalSettingsApp,
) -> Mapping[str, shared.GlobalSettingsVariable]:
    return {variable.name: variable for topic in data.topics for variable in topic.variables}
