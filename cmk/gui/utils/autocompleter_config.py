#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
AutocompleterConfig is used to transport data from python via html, javascript
and ajax back to python.
The main use case is AjaxDropdownChoice which will serialize the data returned
by the config property into a html attribute called "data-autocompleter" which
will be read by javascript and included in the ajax call to the autocompleters
endpoint.
"""

from typing import Collection, Literal, Mapping, Optional, Union

AutocompleterParams = Mapping[str, Union[str, int, float, bool, Collection[str]]]
AutocompleterConfigJson = Mapping[
    str, Union[str, int, float, bool, Collection[str], AutocompleterParams]
]
DynamicParamsCallbackName = Literal[
    # see dynamicParamsCallbacks object in web/htdocs/js/modules/valuespecs.js
    "nop",
    "tag_group_options_autocompleter",
    "host_and_service_hinted_autocompleter",
    "host_hinted_autocompleter",
]


class AutocompleterConfig:
    def __init__(
        self,
        *,
        ident: str,
        # TODO: rename ident to endpoint!
        strict: bool = False,
        dynamic_params_callback_name: Optional[DynamicParamsCallbackName] = None,
    ):
        self._ident = ident
        self._strict = strict
        self._dynamic_params_callback_name = dynamic_params_callback_name

    @property
    def ident(self) -> str:
        return self._ident

    @property
    def params(self) -> AutocompleterParams:
        return {"strict": self._strict}

    @property
    def config(self) -> AutocompleterConfigJson:
        config = {"ident": self.ident, "params": self.params}
        if self._dynamic_params_callback_name is not None:
            config["dynamic_params_callback_name"] = self._dynamic_params_callback_name
        return config


class ContextAutocompleterConfig(AutocompleterConfig):
    """
    The javascript side of the corresponding autocompleter finds certain
    neighbor fields and sends those values as context to the autocompleter
    python function. With this it's possible to limit the number of choices of
    the main dropdown (for example the graph dropdown in the performance graph
    dashlet) based on other dropdowns (the service and host dropdowns).
    Depending on the use case it might be necessary to only show elements of the
    main dropdown, if the other dropdowns are already defined. This can be
    influenced with the show_independent_of_context option: If true the main
    dropdown will show all possible values while the other dropdowns have no
    values set. If false the main dropdown will show no values if the context
    is not yet chosen (this is the case in the custom graph graph designer: the
    metric can only be chosen if both host and service is chosen).
    """

    def __init__(
        self,
        *,
        ident: str,
        strict: bool = True,
        show_independent_of_context=False,
        dynamic_params_callback_name: Optional[DynamicParamsCallbackName] = None,
    ) -> None:
        super().__init__(
            ident=ident,
            dynamic_params_callback_name=dynamic_params_callback_name,
            strict=strict,
        )
        self._show_independent_of_context = show_independent_of_context

    @property
    def params(self) -> AutocompleterParams:
        return {"show_independent_of_context": self._show_independent_of_context, **super().params}


class GroupAutocompleterConfig(AutocompleterConfig):
    def __init__(
        self,
        *,
        ident: str,
        group_type: Literal["host", "service", "contact"],
        strict: bool = True,
        dynamic_params_callback_name: Optional[DynamicParamsCallbackName] = None,
    ) -> None:
        super().__init__(
            ident=ident, strict=strict, dynamic_params_callback_name=dynamic_params_callback_name
        )
        self._group_type = group_type

    @property
    def params(self) -> AutocompleterParams:
        return {"group_type": self._group_type, **super().params}
