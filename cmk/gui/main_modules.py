#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

# mypy: disable-error-code="redundant-expr"

import importlib
import sys
import traceback
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import assert_never

import cmk.ccc.version as cmk_version

# The following imports trigger loading of built-in main modules.
# Note: They are loaded once more in `_import_main_module_plugins()` and
# possibly a third time over the plug-in discovery mechanism.
import cmk.gui.plugins.main_modules  # pylint: disable=cmk-module-layer-violation
from cmk import trace
from cmk.ccc.version import Edition
from cmk.gui import utils
from cmk.gui.log import logger
from cmk.utils import paths
from cmk.utils.plugin_loader import load_plugins_with_exceptions

match edition := cmk_version.edition(paths.omd_root):
    case Edition.PRO:
        import cmk.gui.nonfree.pro.registration  # type: ignore[import-not-found, import-untyped, unused-ignore] # pylint: disable=cmk-module-layer-violation

        cmk.gui.nonfree.pro.registration.register(edition)

    case Edition.ULTIMATEMT:
        import cmk.gui.nonfree.ultimatemt.registration  # type: ignore[import-not-found, import-untyped, unused-ignore] # pylint: disable=cmk-module-layer-violation

        cmk.gui.nonfree.ultimatemt.registration.register(edition)

    case Edition.ULTIMATE:
        import cmk.gui.nonfree.ultimate.registration  # type: ignore[import-not-found, import-untyped, unused-ignore] # pylint: disable=cmk-module-layer-violation

        cmk.gui.nonfree.ultimate.registration.register(edition)

    case Edition.CLOUD:
        import cmk.gui.nonfree.cloud.registration  # type: ignore[import-not-found, import-untyped, unused-ignore]

        cmk.gui.nonfree.cloud.registration.register(edition)

    case Edition.COMMUNITY:
        import cmk.gui.community_registration

        cmk.gui.community_registration.register(edition)

    case _ as unreachable:
        assert_never(unreachable)


tracer = trace.get_tracer()


def _imports() -> Iterator[str]:
    """Returns a list of names of all currently imported python modules"""
    for val in globals().values():
        if isinstance(val, ModuleType):
            yield val.__name__


@tracer.instrument("main_modules.load_plugins")
def load_plugins() -> None:
    """Loads and initializes main modules and plug-ins into the application
    Only built-in main modules are already imported."""
    local_main_modules = _import_local_main_modules()
    main_modules = _cmk_gui_top_level_modules() + local_main_modules
    _import_main_module_plugins(main_modules)
    _call_load_plugins_hooks(main_modules)


def _import_local_main_modules() -> list[ModuleType]:
    """Imports all site local main modules

    We essentially load the site local pages plug-ins (`local/share/check_mk/web/plugins/pages`)
    which are expected to contain the actual imports of the main modules.

    Please note that the built-in main modules are already loaded by the imports of
    `cmk.gui.plugins.main_modules` above.

    Note: Once we have PEP 420 namespace support, we can deprecate this and leave it to the imports
    above. Until then we'll have to live with it.
    """
    module_names_prev = set(_imports())

    # Load all multisite pages which will also perform imports of the needed modules
    utils.load_web_plugins("pages", globals())

    return [sys.modules[m] for m in set(_imports()).difference(module_names_prev)]


def _import_main_module_plugins(main_modules: list[ModuleType]) -> None:
    logger.debug("Importing main module plugins")

    for module in main_modules:
        main_module_name = module.__name__.split(".")[-1]

        plugin_package_name = f"cmk.gui.plugins.{main_module_name}"
        if not _is_plugin_namespace(plugin_package_name):
            continue

        logger.debug("  Importing plug-ins from %s", plugin_package_name)
        for plugin_name, exc in load_plugins_with_exceptions(plugin_package_name):
            logger.error(
                "  Error in %s plug-in '%s'\n", main_module_name, plugin_name, exc_info=exc
            )
            utils.add_failed_plugin(
                Path(traceback.extract_tb(exc.__traceback__)[-1].filename),
                main_module_name,
                plugin_name,
                exc,
            )

    logger.debug("Main module plug-ins imported")


def _is_plugin_namespace(plugin_package_name: str) -> bool:
    # TODO: We should know this somehow by declarations without need to try this out
    try:
        importlib.import_module(plugin_package_name)
        return True
    except ModuleNotFoundError:
        return False


def _call_load_plugins_hooks(main_modules: list[ModuleType]) -> None:
    """Call the load_plugins() function in all main modules

    Have a look at our Wiki: /books/concepts/page/how-cmkgui-is-organised

    Each main module has the option to declare a `load_plugins` hook function to realize it's own
    logic that should be executed when initializing the main module.

    In previous versions this was executed with loaded configuration and localized during request
    processing, which resulted in several problems. Now this is executed during application
    initialization (at import time).

    1. During import of the application (e.g. web/app/index.wsgi) `init_modules` cares for the
       import of all main modules
    2. Then this function calls the function `load_plugins` hook of all main modules.
    3. The main module is doing it's initialization logic.
    """
    logger.debug("Executing load_plugin hooks")

    for module in main_modules:
        name = module.__name__

        if name == "cmk.gui.main_modules":
            continue  # Do not call ourselfs

        if not hasattr(module, "load_plugins"):
            continue  # has no load_plugins hook, nothing to do

        logger.debug("Executing load_plugins hook for %s", name)
        module.load_plugins()

    logger.debug("Finished executing load_plugin hooks")


def _cmk_gui_top_level_modules() -> list[ModuleType]:
    return [
        module
        for name, module in sys.modules.items()
        # None entries are only an import optimization of cPython and can be removed:
        # https://www.python.org/dev/peps/pep-0328/#relative-imports-and-indirection-entries-in-sys-modules
        if module is not None
        # top level modules only, please...
        if name.startswith("cmk.gui.") and len(name.split(".")) == 3
    ]
