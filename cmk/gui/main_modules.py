#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from typing import assert_never

from cmk.ccc.version import Edition
from cmk.discover_plugins import discover_plugins_from_modules
from cmk.gui.autocompleters import autocompleter_registry
from cmk.gui.legacy_plugins import get_failed_plugins as get_failed_plugins
from cmk.gui.main_navigation import main_navigation_renderer_registry, MainNavigation
from cmk.gui.openapi import endpoint_family_registry, versioned_endpoint_registry
from cmk.gui.sidebar import SidebarRenderer, snapin_registry
from cmk.gui.watolib.config_domain_name import config_domain_registry, config_variable_registry
from cmk.gui.watolib.config_sync import replication_path_registry
from cmk.gui_plugins.internal.feature_registration import GuiFeaturePlugin, RegistrationContext
from cmk.licensing.basics.options import get_license_options, LicenseOptions
from cmk.utils import paths


def _render_main_navigation(title: str | None, nav: MainNavigation) -> None:
    SidebarRenderer().render_main_navigation_with_open_content_area(title=title, nav=nav)


main_navigation_renderer_registry.register(_render_main_navigation)


def _build_context(edition: Edition, features: LicenseOptions) -> RegistrationContext:
    return RegistrationContext(
        edition=edition,
        features=features,
        autocompleter_registry=autocompleter_registry,
        config_domain_registry=config_domain_registry,
        config_variable_registry=config_variable_registry,
        endpoint_family_registry=endpoint_family_registry,
        replication_path_registry=replication_path_registry,
        snapin_registry=snapin_registry,
        versioned_endpoint_registry=versioned_endpoint_registry,
    )


def load_feature_plugins(module_paths: Iterable[str], ctx: RegistrationContext) -> None:
    for plugin in discover_plugins_from_modules(
        {GuiFeaturePlugin: "feature_plugin_"},
        module_paths,
        skip_wrong_types=False,
        raise_errors=True,
    ).plugins.values():
        if plugin.enabled(ctx):
            plugin.register(ctx)


# TODO: flatten this into Sequence[str]. For this we need to block the imports first
_FEATURE_PLUGIN_MODULES: Mapping[Edition, Sequence[str]] = {
    Edition.ULTIMATE: ["cmk.metric_backend.gui._registration_ultimate"],
    Edition.ULTIMATEMT: ["cmk.metric_backend.gui._registration_ultimate"],
    Edition.CLOUD: ["cmk.metric_backend.gui._registration_cloud"],
}
_registered_edition: Edition | None = None


def register(edition: Edition) -> None:
    global _registered_edition
    if _registered_edition is not None:
        if _registered_edition is not edition:
            raise RuntimeError(
                f"main_modules.register() called with {edition!r}, "
                f"but was already registered with {_registered_edition!r}"
            )
        return
    _registered_edition = edition

    features = get_license_options(paths.omd_root, edition)
    ctx = _build_context(edition, features)

    match edition:
        case Edition.PRO:
            import cmk.gui.nonfree.pro.registration  # type: ignore[import-not-found, import-untyped, unused-ignore]

            cmk.gui.nonfree.pro.registration.register(ctx)

        case Edition.ULTIMATEMT:
            import cmk.gui.nonfree.ultimatemt.registration  # type: ignore[import-not-found, import-untyped, unused-ignore]

            cmk.gui.nonfree.ultimatemt.registration.register(ctx)

        case Edition.ULTIMATE:
            import cmk.gui.nonfree.ultimate.registration  # type: ignore[import-not-found, import-untyped, unused-ignore]

            cmk.gui.nonfree.ultimate.registration.register(ctx)

        case Edition.CLOUD:
            import cmk.gui.nonfree.cloud.registration  # type: ignore[import-not-found, import-untyped, unused-ignore]

            cmk.gui.nonfree.cloud.registration.register(ctx)

        case Edition.COMMUNITY:
            import cmk.gui.community_registration

            cmk.gui.community_registration.register(ctx)

        case _ as unreachable:
            assert_never(unreachable)

    load_feature_plugins(_FEATURE_PLUGIN_MODULES.get(edition, []), ctx)
