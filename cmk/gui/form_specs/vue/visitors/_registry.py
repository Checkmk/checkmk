#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable
from typing import Any

from cmk.gui.form_specs.private import UnknownFormSpec
from cmk.gui.form_specs.vue.visitors._base import FormSpecVisitor
from cmk.gui.form_specs.vue.visitors._type_defs import VisitorOptions

from cmk.rulesets.v1.form_specs import FormSpec
from cmk.rulesets.v1.form_specs._base import ModelT

RecomposerFunction = Callable[[FormSpec[Any]], FormSpec[Any]]
form_spec_visitor_registry: dict[
    type[FormSpec[Any]], type[FormSpecVisitor[FormSpec[Any], Any]]
] = {}

form_spec_recomposer_registry: dict[type[FormSpec[Any]], RecomposerFunction] = {}


def register_visitor_class(
    form_spec_class: type[FormSpec[ModelT]], visitor_class: type[FormSpecVisitor[Any, ModelT]]
) -> None:
    form_spec_visitor_registry[form_spec_class] = visitor_class


def register_recomposer_function(
    form_spec_class: type[FormSpec[ModelT]], recomposer_function: RecomposerFunction
) -> None:
    form_spec_recomposer_registry[form_spec_class] = recomposer_function


def get_visitor(
    form_spec: FormSpec[ModelT], options: VisitorOptions
) -> FormSpecVisitor[FormSpec[ModelT], ModelT]:
    if recompose_function := form_spec_recomposer_registry.get(form_spec.__class__):
        return get_visitor(recompose_function(form_spec), options)

    if visitor_class := form_spec_visitor_registry.get(form_spec.__class__):
        return visitor_class(form_spec, options)

    # If the form spec is not known to any registry, convert it to the legacy valuespec visitor
    unknown_recomposer = form_spec_recomposer_registry[UnknownFormSpec]
    assert unknown_recomposer is not None
    return get_visitor(unknown_recomposer(form_spec), options)
