#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Autocompleter infrastructure: registry, AJAX handler, and page registration."""

# mypy: disable-error-code="type-arg"

from collections.abc import Callable
from typing import override

from cmk.ccc.plugin_registry import Registry
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.pages import AjaxPage, PageContext, PageEndpoint, PageRegistry, PageResult
from cmk.gui.type_defs import Choices

AutocompleterFunc = Callable[[Config, str, dict[str, object]], Choices]


class AutocompleterRegistry(Registry[AutocompleterFunc]):
    def plugin_name(self, instance: AutocompleterFunc) -> str:
        return instance._ident  # type: ignore[attr-defined, no-any-return]

    def register_autocompleter(self, ident: str, func: AutocompleterFunc) -> None:
        if not callable(func):
            raise TypeError()
        func._ident = ident  # type: ignore[attr-defined]
        self.register(func)


autocompleter_registry = AutocompleterRegistry()


class AutocompleterBackendWarning(Exception):
    """Warning from an autocompleter backend that allows user to continue with input.

    Used when a backend service is unavailable but user input should still be allowed.
    The exception carries both a warning message and the fallback choices to display.
    """

    def __init__(self, message: str, choices: Choices) -> None:
        super().__init__(message)
        self.choices = choices


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("ajax_vs_autocomplete", PageVsAutocomplete()))


def validate_autocompleter_data(api_request: dict[str, object]) -> None:
    params = api_request.get("params")
    if params is None:
        raise MKUserError("params", _('You need to set the "%s" parameter.') % "params")

    value = api_request.get("value")
    if value is None:
        raise MKUserError("params", _('You need to set the "%s" parameter.') % "value")

    ident = api_request.get("ident")
    if ident is None:
        raise MKUserError("ident", _('You need to set the "%s" parameter.') % "ident")


class PageVsAutocomplete(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        api_request = ctx.request.get_request()
        validate_autocompleter_data(api_request)
        ident = api_request["ident"]

        completer = autocompleter_registry.get(ident)
        if completer is None:
            raise MKUserError("ident", _("Invalid ident: %s") % ident)

        result_data = completer(ctx.config, api_request["value"], api_request["params"])

        assert isinstance(result_data, list)
        if result_data:
            assert isinstance(result_data[0], list | tuple)
            assert len(result_data[0]) == 2

        return {"choices": result_data}
