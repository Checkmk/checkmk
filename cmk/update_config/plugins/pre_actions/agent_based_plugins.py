#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import importlib.util
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from typing import override

from cmk.checkengine.plugin_backend import load_all_plugins
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.gui.exceptions import MKUserError
from cmk.mkp_tool import Manifest, PackageID
from cmk.update_config.internal import (
    ConflictMode,
    continue_per_users_choice,
    ExpiryVersion,
    PreUpdateAction,
    Resume,
)
from cmk.update_config.plugins.pre_actions.utils import (
    AGENT_BASED_PLUGINS_PREACTION_SORT_INDEX,
    disable_incomp_mkp,
    get_installer_and_package_map,
    is_applicable_mkp,
    make_path_config,
    PACKAGE_STORE,
)
from cmk.update_config.registry import pre_update_action_registry
from cmk.utils.paths import local_agent_based_plugins_dir, local_root
from cmk.web.utils.doc_references import werk_reference_url, WerkReference


class PreUpdateAgentBasedPlugins(PreUpdateAction):
    """Make sure no inactive agent based plug-ins are left over and all plug-ins load."""

    def _get_files(self) -> Sequence[Path]:
        try:
            return list(local_agent_based_plugins_dir.rglob("*.py"))
        except FileNotFoundError:
            return ()

    @override
    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        # In this case we have no mkp plugins available so bail out early
        if (path_config := make_path_config()) is None:
            return
        installer, package_map = get_installer_and_package_map(path_config)
        # group the local_agent_based_plugins_dir files by package
        grouped_files: dict[PackageID, list[Path]] = {}
        manifests: dict[PackageID, Manifest] = {}
        inactive_files_not_in_package = []
        for path in self._get_files():
            if (manifest := package_map.get(path.resolve())) is not None:
                grouped_files.setdefault(manifest.id, []).append(path)
                manifests[manifest.id] = manifest
            else:
                inactive_files_not_in_package.append(path)

        if inactive_files_not_in_package:
            _log_error_message_obsolete_files(logger, inactive_files_not_in_package)
            logger.error(
                "The above file(s) are not associated with any MKP and can thus not be removed automatically. "
                "You must manually remove them in order to suppress future warnings."
            )
            if _continue_per_users_choice(conflict_mode).is_abort():
                raise MKUserError(None, "decommissioned file(s)")

        for package_id, paths in grouped_files.items():
            if not is_applicable_mkp(manifests[package_id]):
                logger.info(
                    "[%(package_name)s %(package_version)s]: Ignoring problems "
                    "(MKP will be disabled on target version)",
                    {"package_name": package_id.name, "package_version": package_id.version},
                )
                continue

            _log_error_message_obsolete_files(logger, paths)
            logger.error(
                "The above file(s) are part of the extension package "
                "%(package_name)s %(package_version)s.",
                {"package_name": package_id.name, "package_version": package_id.version},
            )
            if disable_incomp_mkp(conflict_mode, package_id, installer, PACKAGE_STORE, path_config):
                continue
            raise MKUserError(None, "incompatible extension package")

        report_plugin_problems(
            logger,
            conflict_mode,
            find_plugin_problems(
                load_all_plugins(raise_errors=False),
                _module_path,
                package_map,
                local_root.resolve(),
            ),
        )


@dataclass(frozen=True)
class PluginProblems:
    by_package: Mapping[PackageID, Sequence[str]]
    by_local: Mapping[str, Sequence[str]]
    """Problems of unpackaged customizations, by local file or module"""
    shipped: Sequence[str]
    outdated: Sequence[Manifest]
    """Packages that will be disabled on the target version: their problems are moot"""


@dataclass(frozen=True)
class _Origin:
    description: str
    location: str
    """The file, or the module if it can not be located"""
    manifest: Manifest | None
    is_local: bool
    is_outdated: bool = False


def find_plugin_problems(
    plugins: AgentBasedPlugins,
    module_path: Callable[[str], Path | None],
    package_map: Mapping[Path, Manifest],
    local_root: Path,
) -> PluginProblems:
    """Group the problems of the loaded plug-ins by whoever is responsible for them

    Files below `local_root` are customizations, either packaged or not.
    So are modules we can not locate: shipped modules can always be located.
    Everything else is shipped.
    A name conflict concerns every customization involved, whichever plug-in is used.
    Packages that will be disabled on the target version are not responsible for
    anything, and a name conflict with them will be gone.
    """
    by_package: dict[PackageID, list[str]] = {}
    outdated: dict[PackageID, Manifest] = {}
    by_local: dict[str, list[str]] = {}
    shipped: list[str] = []

    def origin(module: str) -> _Origin:
        if (path := module_path(module)) is None:
            return _Origin(f"module {module}", module, None, is_local=True)
        if (manifest := package_map.get(path)) is not None:
            return _Origin(
                f"extension package {manifest.name} {manifest.version} ({path})",
                str(path),
                manifest,
                is_local=False,
                is_outdated=not is_applicable_mkp(manifest),
            )
        if path.is_relative_to(local_root):
            return _Origin(f"local file {path}", str(path), None, is_local=True)
        return _Origin(f"shipped file {path}", str(path), None, is_local=False)

    def add(origins: Sequence[_Origin], message: str) -> None:
        if moot := [o.manifest for o in origins if o.manifest is not None and o.is_outdated]:
            outdated.update((m.id, m) for m in moot)
            return
        # Both sides of a conflict may belong to the same culprit: report it only once.
        packages = {o.manifest.id for o in origins if o.manifest is not None}
        locals_ = {o.description for o in origins if o.manifest is None and o.is_local}
        for package_id in packages:
            by_package.setdefault(package_id, []).append(message)
        for culprit in locals_:
            by_local.setdefault(culprit, []).append(message)
        if not (packages or locals_):
            shipped.append(message)

    for conflict in plugins.conflicts:
        used, ignored = origin(conflict.used.module), origin(conflict.ignored.module)
        add(
            (used, ignored),
            f"Name conflict for '{conflict.name}': "
            f"Ignoring '{conflict.ignored}' of {ignored.description} "
            f"in favor of '{conflict.used}' of {used.description}",
        )

    for module, errors in plugins.errors_by_module.items():
        module_origin = origin(module)
        for error in errors:
            add((module_origin,), f"{error} ({module_origin.location})")

    return PluginProblems(
        by_package=by_package,
        by_local=by_local,
        shipped=shipped,
        outdated=list(outdated.values()),
    )


def report_plugin_problems(
    logger: Logger, conflict_mode: ConflictMode, problems: PluginProblems
) -> None:
    """Report all problems at once and let the user decide whether to continue

    Continuing is not harmful: the site will load the plug-ins just like this.
    """
    for manifest in problems.outdated:
        logger.info(
            "[%(package_name)s %(package_version)s]: Ignoring problems "
            "(MKP will be disabled on target version)",
            {"package_name": manifest.name, "package_version": manifest.version},
        )

    # Nothing the user can fix: don't block the update.
    if problems.shipped:
        _log_problems(logger, logging.WARNING, "Checkmk", problems.shipped)

    if not (problems.by_package or problems.by_local):
        return

    for package_id, messages in problems.by_package.items():
        _log_problems(
            logger,
            logging.ERROR,
            f"extension package '{package_id.name} {package_id.version}'",
            messages,
        )
    for culprit, messages in problems.by_local.items():
        _log_problems(logger, logging.ERROR, culprit, messages)

    logger.error(
        "If you continue, plug-ins with errors will not be loaded, and for each name "
        "conflict only the plug-in shown as used above will be loaded. To avoid this, "
        "abort the update and fix or disable the affected extension packages and local files."
    )
    if _continue_per_users_choice(conflict_mode).is_abort():
        raise MKUserError(None, "incompatible agent based plug-ins")


def _log_problems(logger: Logger, level: int, culprit: str, messages: Sequence[str]) -> None:
    logger.log(
        level, "Problems with the agent based plug-ins of %(culprit)s:", {"culprit": culprit}
    )
    for message in messages:
        logger.log(level, "    %(message)s", {"message": message})


def _module_path(module: str) -> Path | None:
    try:
        spec = importlib.util.find_spec(module)
    except Exception:
        return None
    if spec is None or spec.origin is None:
        return None
    return Path(spec.origin).resolve()


def _continue_per_users_choice(conflict_mode: ConflictMode) -> Resume:
    match conflict_mode:
        case ConflictMode.FORCE:
            return Resume.UPDATE
        case ConflictMode.ABORT:
            return Resume.ABORT
        case ConflictMode.ASK:
            return continue_per_users_choice(
                "You can abort the update process (A) or continue the update (c).\n"
                "Abort the update process? [A/c] \n",
            )


def _log_error_message_obsolete_files(logger: Logger, paths: Sequence[Path]) -> None:
    for path in paths:
        logger.error("Obsolete file: '%(path)s'", {"path": path})
    logger.error(
        "The file(s) residing in `local/lib/python3/cmk/plugins/agent_based` will no longer be loaded in Checkmk 2.4. "
    )
    logger.error("See: %(url)s", {"url": werk_reference_url(WerkReference.DECOMMISSION_V1_API)})


pre_update_action_registry.register(
    PreUpdateAgentBasedPlugins(
        name="agent_based_plugins",
        title="Agent based plugins",
        sort_index=AGENT_BASED_PLUGINS_PREACTION_SORT_INDEX,
        expiry_version=ExpiryVersion.NEVER,
    )
)
