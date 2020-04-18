#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import six

from cmk.gui.i18n import _
from cmk.gui.exceptions import MKUserError

#.
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


class GraphIdentificationTypes(object):
    """Container class for managing all known identification types"""
    def __init__(self):
        super(GraphIdentificationTypes, self).__init__()
        self._types = {}

    def register(self, type_cls):
        assert issubclass(type_cls, GraphIdentification)
        self._types[type_cls.ident()] = type_cls

    def verify(self, type_ident):
        if type_ident not in self._types:
            raise MKUserError(None, _("Invalid graph specification type \"%s\" given") % type_ident)

    def create_graph_recipes(self, graph_identification, destination=None):
        type_ident, spec_info = graph_identification
        type_cls = self._types[type_ident]
        return type_cls().create_graph_recipes(spec_info, destination=destination)


graph_identification_types = GraphIdentificationTypes()


class GraphIdentification(six.with_metaclass(abc.ABCMeta, object)):
    """Abstract base class for all graph identification classes"""
    @classmethod
    def ident(cls):
        raise NotImplementedError()

    @abc.abstractmethod
    def create_graph_recipes(self, ident_info, destination=None):
        raise NotImplementedError()


class GraphIdentificationExplicit(GraphIdentification):
    @classmethod
    def ident(cls):
        return "explicit"

    def create_graph_recipes(self, ident_info, destination=None):
        graph_recipe = ident_info.copy()
        graph_recipe["specification"] = ("explicit", ident_info)
        return [graph_recipe]


graph_identification_types.register(GraphIdentificationExplicit)
