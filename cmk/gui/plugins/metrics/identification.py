#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from collections.abc import MutableMapping, Sequence
from typing import Generic, TypeVar

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.metrics.utils import ExplicitGraphRecipe, GraphRecipe
from cmk.gui.type_defs import ExplicitGraphSpec, GraphIdentifier, GraphSpec

# .
#   .--Identification------------------------------------------------------.
#   |     ___    _            _   _  __ _           _   _                  |
#   |    |_ _|__| | ___ _ __ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __       |
#   |     | |/ _` |/ _ \ '_ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \      |
#   |     | | (_| |  __/ | | | |_| |  _| | (_| (_| | |_| | (_) | | | |     |
#   |    |___\__,_|\___|_| |_|\__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  A graph identification is some collection of information from that  |
#   |  one or more graph recipes can be computed. Currently there          |
#   |  exis two types of identifications: "template" and "custom".         |
#   |  Athird one will                                                     |
#   |  follow, which implements graphs derived from templates, showing     |
#   |  data from several services of the same type.                        |
#   |                                                                      |
#   |  A graph identification is a pair of (type, graph_ident..info),      |
#   |  where type is one of "template", "custom"                           |
#   '----------------------------------------------------------------------'


class GraphIdentificationTypes:
    """Container class for managing all known identification types"""

    def __init__(self) -> None:
        super().__init__()
        self._types: MutableMapping[str, type["GraphIdentification"]] = {}

    def register(self, type_cls: type["GraphIdentification"]) -> None:
        assert issubclass(type_cls, GraphIdentification)
        self._types[type_cls.ident()] = type_cls

    def verify(self, type_ident: str) -> None:
        if type_ident not in self._types:
            raise MKUserError(None, _('Invalid graph specification type "%s" given') % type_ident)

    def create_graph_recipes(
        self,
        graph_identification: GraphIdentifier,
        destination: str | None = None,
    ) -> Sequence[GraphRecipe]:
        type_ident, spec_info = graph_identification
        type_cls = self._types[type_ident]
        return type_cls().create_graph_recipes(spec_info, destination=destination)


graph_identification_types = GraphIdentificationTypes()

_TGraphSpec = TypeVar("_TGraphSpec", bound=GraphSpec | str)
_TGraphRecipe = TypeVar("_TGraphRecipe", bound=GraphRecipe)


class GraphIdentification(Generic[_TGraphSpec, _TGraphRecipe], abc.ABC):
    """Abstract base class for all graph identification classes"""

    @classmethod
    @abc.abstractmethod
    def ident(cls) -> str:
        ...

    @abc.abstractmethod
    def create_graph_recipes(
        self, ident_info: _TGraphSpec, destination: str | None = None
    ) -> Sequence[_TGraphRecipe]:
        ...


class GraphIdentificationExplicit(GraphIdentification[ExplicitGraphSpec, ExplicitGraphRecipe]):
    @classmethod
    def ident(cls):
        return "explicit"

    def create_graph_recipes(
        self, ident_info: ExplicitGraphSpec, destination: str | None = None
    ) -> list[ExplicitGraphRecipe]:
        return [
            {
                "title": ident_info["title"],
                "unit": ident_info["unit"],
                "consolidation_function": ident_info["consolidation_function"],
                "explicit_vertical_range": ident_info["explicit_vertical_range"],
                "omit_zero_metrics": ident_info["omit_zero_metrics"],
                "horizontal_rules": ident_info["horizontal_rules"],
                "context": ident_info["context"],
                "add_context_to_title": ident_info["add_context_to_title"],
                "metrics": ident_info["metrics"],
                "specification": ("explicit", ident_info),
            }
        ]


graph_identification_types.register(GraphIdentificationExplicit)
