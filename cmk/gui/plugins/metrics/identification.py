#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from typing import Generic, MutableMapping, Optional, Type, TypeVar

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.metrics.utils import GraphRecipe
from cmk.gui.type_defs import ExplicitGraphSpec, GraphIdentifier

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
        self._types: MutableMapping[str, Type["GraphIdentification"]] = {}

    def register(self, type_cls: Type["GraphIdentification"]) -> None:
        assert issubclass(type_cls, GraphIdentification)
        self._types[type_cls.ident()] = type_cls

    def verify(self, type_ident: str) -> None:
        if type_ident not in self._types:
            raise MKUserError(None, _('Invalid graph specification type "%s" given') % type_ident)

    def create_graph_recipes(
        self,
        graph_identification: GraphIdentifier,
        destination: Optional[str] = None,
    ) -> list[GraphRecipe]:
        type_ident, spec_info = graph_identification
        type_cls = self._types[type_ident]
        return type_cls().create_graph_recipes(spec_info, destination=destination)


graph_identification_types = GraphIdentificationTypes()

T = TypeVar("T")


class GraphIdentification(Generic[T], abc.ABC):
    """Abstract base class for all graph identification classes"""

    @classmethod
    @abc.abstractmethod
    def ident(cls) -> str:
        ...

    @abc.abstractmethod
    def create_graph_recipes(
        self, ident_info: T, destination: Optional[str] = None
    ) -> list[GraphRecipe]:
        ...


class GraphIdentificationExplicit(GraphIdentification[ExplicitGraphSpec]):
    @classmethod
    def ident(cls):
        return "explicit"

    def create_graph_recipes(
        self, ident_info: ExplicitGraphSpec, destination: Optional[str] = None
    ) -> list[GraphRecipe]:
        graph_recipe = dict(ident_info)
        graph_recipe["specification"] = ("explicit", ident_info)
        return [graph_recipe]


graph_identification_types.register(GraphIdentificationExplicit)
