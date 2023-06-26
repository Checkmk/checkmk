#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Generic, Protocol, TypeVar

from cmk.utils.plugin_registry import Registry

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.utils.graph_specification import GraphSpecification

from .utils import GraphRecipe

_TGraphSpecification_contra = TypeVar(
    "_TGraphSpecification_contra",
    bound=GraphSpecification,
    contravariant=True,
)


class GraphRecipeBuilder(Protocol, Generic[_TGraphSpecification_contra]):
    @property
    def graph_type(self) -> str:
        ...

    def __call__(self, spec: _TGraphSpecification_contra) -> Sequence[GraphRecipe]:
        ...


class GraphRecipeBuilderRegistry(Registry[GraphRecipeBuilder]):
    def plugin_name(self, instance: GraphRecipeBuilder) -> str:
        return instance.graph_type


graph_recipe_builder_registry = GraphRecipeBuilderRegistry()


def build_graph_recipes(graph_specification: GraphSpecification) -> Sequence[GraphRecipe]:
    try:
        recipe_builder = graph_recipe_builder_registry[graph_specification.graph_type]
    except KeyError:
        raise MKUserError(None, _("Unknown graph type: %s") % graph_specification.graph_type)
    return recipe_builder(graph_specification)
