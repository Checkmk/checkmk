#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.plugin_registry import Registry

from ._base import VisualInfo


class VisualInfoRegistry(Registry[type[VisualInfo]]):
    def plugin_name(self, instance):
        return instance().ident

    # At least painter <> info matching extracts the info name from the name of the painter by
    # splitting at first "_" and use the text before it as info name. See
    # cmk.gui.views.infos_needed_by_painter().
    def registration_hook(self, instance):
        ident = instance().ident
        if ident == "aggr_group":
            return  # TODO: Allow this broken thing for the moment
        if "_" in ident:
            raise MKGeneralException("Underscores must not be used in info names: %s" % ident)


visual_info_registry = VisualInfoRegistry()
