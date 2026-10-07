#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.search.matchers import match_item_generator_registry
from cmk.gui.search.permissions import (
    category_permissions_handler_registry,
    search_permissions_handler_registry,
)


def test_all_categorized_providers_have_a_permissions_handler() -> None:
    """Every provider with registered match items must supply a permissions handler.

    Otherwise `CompositePermissionsHandler` (search/routing.py) fails closed for that provider's
    categories, silently hiding all of its search results with no indication anything is wrong.
    """
    categorized_providers = {
        match_item_generator_registry.provider_for(category)
        for category in match_item_generator_registry
    }
    assert categorized_providers <= set(search_permissions_handler_registry)


def test_all_category_permission_handlers_refer_to_known_categories() -> None:
    assert set(category_permissions_handler_registry) <= set(match_item_generator_registry)
