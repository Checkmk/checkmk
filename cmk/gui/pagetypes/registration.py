#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.main_menu import MainMenuRegistry
from cmk.gui.main_menu_match_items import MatchItemGeneratorMainMenu
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry
from cmk.gui.search.matchers import MatchItemGeneratorRegistry
from cmk.gui.search.permissions import (
    search_permissions_handler_registry,
    SearchPermissionsHandlerFactory,
)
from cmk.shared_typing.unified_search import ProviderName

from ._core import (
    _customize_menu_topics,
    BuiltinPagetypeTopicRegistry,
    CustomizePermissionsHandler,
    declare,
    PagetypeTopics,
)
from ._core import register as _register_core
from ._openapi._registration import register as register_openapi_endpoints


def register(
    main_menu_registry: MainMenuRegistry,
    builtin_pagetype_topic_registry: BuiltinPagetypeTopicRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
    match_item_generator_registry: MatchItemGeneratorRegistry,
) -> None:
    _register_core(main_menu_registry, builtin_pagetype_topic_registry)
    match_item_generator_registry.register(
        MatchItemGeneratorMainMenu(
            "customize",
            provider="customize",
            topic_generator=_customize_menu_topics,
        )
    )
    search_permissions_handler_registry.register(
        SearchPermissionsHandlerFactory(
            provider=ProviderName.customize,
            build=CustomizePermissionsHandler.build,
        )
    )
    declare(PagetypeTopics)
    register_openapi_endpoints(
        endpoint_family_registry=endpoint_family_registry,
        versioned_endpoint_registry=versioned_endpoint_registry,
    )
