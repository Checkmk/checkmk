#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory.transformation.tree_files import _compute_bundle_size


def test_the_bundle_spreads_all_trees_including_the_transformed_ones() -> None:
    assert _compute_bundle_size(0, 400, 600) == 5
