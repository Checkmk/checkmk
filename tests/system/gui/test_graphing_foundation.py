#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Smoke tests for the graph E2E foundation wiring (no site or browser needed)."""

import importlib

from tests.system.gui.testlib.playwright.pom.graphing.graph_surfaces import (
    GRAPH_SURFACES,
    surfaces_for_edition,
)
from tests.testlib.graphing import service_rrd_path
from tests.testlib.version import CMKEdition


def test_surface_page_objects_resolve() -> None:
    """Every surface's ``page_object`` pointer imports to a real class."""
    for surface in GRAPH_SURFACES:
        module_path, _, class_name = surface.page_object.partition(":")
        module = importlib.import_module(module_path)
        assert isinstance(getattr(module, class_name, None), type), (
            f"{surface.key}: '{surface.page_object}' does not resolve to a class"
        )


def test_surfaces_for_edition_excludes_pro_in_community() -> None:
    """Community sees only the non-pro surfaces; pro additionally sees the pro ones."""
    community = {s.key for s in surfaces_for_edition(CMKEdition(CMKEdition.COMMUNITY))}
    pro = {s.key for s in surfaces_for_edition(CMKEdition(CMKEdition.PRO))}
    assert community < pro
    assert "service_detail_graph" in community  # requires_pro=False
    assert "combined_graphs" not in community  # requires_pro=True
    assert "combined_graphs" in pro


def test_service_rrd_path_quotes_like_the_core() -> None:
    """Host and service names are pnp_cleanup-quoted into the per-service path."""
    assert service_rrd_path("myhost", "CPU load") == "var/check_mk/rrd/myhost/CPU_load.rrd"
