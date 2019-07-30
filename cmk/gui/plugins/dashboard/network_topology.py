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

import cmk.gui.config as config
from cmk.gui.i18n import _

from cmk.gui.plugins.dashboard import (
    IFrameDashlet,
    dashlet_registry,
)


@dashlet_registry.register
class NetworkTopologyDashlet(IFrameDashlet):
    """Dashlet that displays a NagVis automap"""
    @classmethod
    def type_name(cls):
        return "network_topology"

    @classmethod
    def title(cls):
        return _("Network topology")

    @classmethod
    def description(cls):
        return _("Uses the parent relationships of your hosts to display a hierarchical map.")

    @classmethod
    def sort_index(cls):
        return 90

    @classmethod
    def initial_size(cls):
        return (30, 10)

    def reload_on_resize(self):
        return True

    def display_title(self):
        return _("Network topology of site %s") % self._site_id()

    def update(self):
        pass  # Not called at all. This dashlet always opens configured pages (see below)

    def _site_id(self):
        return self._dashlet_spec["context"].get("site", {"site": config.omd_site()})["site"]

    def _get_iframe_url(self):
        return ('../nagvis/frontend/nagvis-js/index.php?mod=Map&header_template=on-demand-filter'
                '&header_menu=1&label_show=1&sources=automap&act=view&backend_id=%s'
                '&render_mode=undirected&url_target=main&filter_group=%s' %
                (self._site_id(), config.topology_default_filter_group or ''))
