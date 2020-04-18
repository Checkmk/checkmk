#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
