#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

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
