#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import dataclasses
import importlib
import pkgutil
from collections.abc import Iterable, Mapping, Sequence

from .v0_unstable import LegacyCheckDefinition

_LEGACY_CHECKS_NAMESPACE = "cmk.legacy_checks"


def find_legacy_check_modules() -> tuple[str, ...]:
    try:
        namespace = importlib.import_module(_LEGACY_CHECKS_NAMESPACE)
    except ModuleNotFoundError:
        # happens in tests. When happens in prod, we can nuke `cmk.agent_based.legacy`.
        return ()
    return tuple(
        f"{_LEGACY_CHECKS_NAMESPACE}.{mod.name}" for mod in pkgutil.iter_modules(namespace.__path__)
    )


@dataclasses.dataclass
class DiscoveredLegacyChecks:
    ignored_plugins_errors: Sequence[str]
    sane_check_info: Sequence[LegacyCheckDefinition]
    plugin_files: Mapping[str, str]


def discover_legacy_checks(
    module_names: Iterable[str],
    *,
    raise_errors: bool,
) -> DiscoveredLegacyChecks:
    ignored_plugins_errors = []
    sane_check_info = []
    legacy_check_plugin_files: dict[str, str] = {}

    for f in module_names:
        try:
            check_context = importlib.import_module(f)
            if not isinstance(defined_checks := check_context.check_info, dict):
                raise TypeError(defined_checks)
        except AttributeError:
            continue  # no check_info, happens during migration.
        except Exception as e:
            if raise_errors:
                raise
            ignored_plugins_errors.append(
                f"Ignoring outdated plug-in file {f}: {e} -- this API is deprecated!"
            )
            continue

        for plugin in defined_checks.values():
            if isinstance(plugin, LegacyCheckDefinition):  # contains Any
                sane_check_info.append(plugin)
                legacy_check_plugin_files[plugin.name] = f
            else:
                # Now just drop everything we don't like; this is not a supported API anymore.
                # Users affected by this will see a CRIT in their "Analyse Configuration" page.
                ignored_plugins_errors.append(
                    f"Ignoring outdated plug-in in {f!r}: Format no longer supported"
                    " -- this API is deprecated!"
                )

    return DiscoveredLegacyChecks(
        ignored_plugins_errors, sane_check_info, legacy_check_plugin_files
    )
