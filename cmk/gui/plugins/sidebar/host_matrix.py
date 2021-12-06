#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.visuals as visuals
from cmk.gui.i18n import _
from cmk.gui.matrix_visualization import HostMatrixVisualization
from cmk.gui.plugins.sidebar.utils import CustomizableSidebarSnapin, snapin_registry, snapin_width


@snapin_registry.register
class HostMatrixSnapin(CustomizableSidebarSnapin):
    @staticmethod
    def type_name():
        return "hostmatrix"

    @classmethod
    def title(cls):
        return _("Host matrix")

    @classmethod
    def description(cls):
        return _("A matrix showing a colored square for each host")

    @classmethod
    def refresh_regularly(cls):
        return True

    @classmethod
    def vs_parameters(cls):
        return [
            (
                "context",
                visuals.VisualFilterList(
                    title=_("Filters"),
                    info_list=["host"],
                ),
            ),
        ]

    @classmethod
    def parameters(cls):
        return {
            "context": {},
        }

    def show(self):
        HostMatrixVisualization().show(snapin_width, self.parameters()["context"])

    @classmethod
    def allowed_roles(cls):
        return ["user", "admin", "guest"]
