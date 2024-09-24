#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import contextmanager

from cmk.utils.labels import LabelGroups as _LabelGroups
from cmk.utils.user import UserId

from cmk.gui import visuals
from cmk.gui.type_defs import VisualTypeName
from cmk.gui.valuespec import LabelGroups


def update_visuals(
    visual_type: VisualTypeName,
    all_visuals: dict[tuple[UserId, str], visuals.TVisual],
) -> None:
    with _save_user_visuals(visual_type, all_visuals) as affected_user:
        # skip builtins, only users
        affected_user.update(owner for owner, _name in all_visuals if owner)

        # Add migration code here
        _set_key_megamenu_search_terms(all_visuals)


@contextmanager
def _save_user_visuals(
    visual_type: VisualTypeName,
    all_visuals: dict[tuple[UserId, str], visuals.TVisual],
) -> Iterator[set[UserId]]:
    modified_user_instances: set[UserId] = set()
    try:
        yield modified_user_instances
    finally:
        # Now persist all modified instances
        for user_id in modified_user_instances:
            visuals.save(visual_type, all_visuals, user_id)


def _set_key_megamenu_search_terms(
    all_visuals: dict[tuple[UserId, str], visuals.TVisual],
) -> None:
    """2.3 introduced the mandatory key "megamenu_search_terms". Update old visuals"""
    for (owner, _name), config in all_visuals.items():
        if not owner:
            continue
        if "megamenu_search_terms" in config:
            continue
        config["megamenu_search_terms"] = []
