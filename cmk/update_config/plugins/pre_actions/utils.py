#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import sys
from collections.abc import Callable, Sequence
from logging import Logger
from pathlib import Path
from termios import tcflush, TCIFLUSH
from typing import Final

from cmk.utils import paths
from cmk.utils.setup_search_index import request_index_rebuild
from cmk.utils.visuals import invalidate_visuals_cache

# It's OK to import centralized config load logic
import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from cmk.discover_plugins import addons_plugins_local_path, plugins_local_path
from cmk.mkp_tool import (
    disable,
    Installer,
    make_post_package_change_actions,
    Manifest,
    PackageID,
    PackageStore,
    PathConfig,
    reload_apache,
)

AGENT_BASED_PLUGINS_PREACTION_SORT_INDEX = 30
GUI_PLUGINS_PREACTION_SORT_INDEX = 20

AUTOCHECK_REWRITE_PREACTION_SORT_INDEX = (  # autocheck rewrite *must* run after these two!
    max(AGENT_BASED_PLUGINS_PREACTION_SORT_INDEX, GUI_PLUGINS_PREACTION_SORT_INDEX) + 10
)


def prompt(message: str) -> str:
    tcflush(sys.stdin, TCIFLUSH)
    return input(message)


def get_path_config() -> PathConfig:
    return PathConfig(
        cmk_plugins_dir=plugins_local_path(),
        cmk_addons_plugins_dir=addons_plugins_local_path(),
        agent_based_plugins_dir=paths.local_agent_based_plugins_dir,
        agents_dir=paths.local_agents_dir,
        alert_handlers_dir=paths.local_alert_handlers_dir,
        bin_dir=paths.local_bin_dir,
        check_manpages_dir=paths.local_legacy_check_manpages_dir,
        checks_dir=paths.local_checks_dir,
        doc_dir=paths.local_doc_dir,
        gui_plugins_dir=paths.local_gui_plugins_dir,
        installed_packages_dir=paths.installed_packages_dir,
        inventory_dir=paths.local_inventory_dir,
        lib_dir=paths.local_lib_dir,
        locale_dir=paths.local_locale_dir,
        local_root=paths.local_root,
        mib_dir=paths.local_mib_dir,
        mkp_rule_pack_dir=ec.mkp_rule_pack_dir(),
        notifications_dir=paths.local_notifications_dir,
        pnp_templates_dir=paths.local_pnp_templates_dir,
        manifests_dir=paths.tmp_dir,
        web_dir=paths.local_web_dir,
    )


_CALLBACKS: Final = ec.mkp_callbacks()

PACKAGE_STORE = PackageStore(
    enabled_dir=paths.local_enabled_packages_dir,
    local_dir=paths.local_optional_packages_dir,
    shipped_dir=paths.optional_packages_dir,
)


class ConflictMode(enum.StrEnum):
    ASK = "ask"
    INSTALL = "install"
    KEEP_OLD = "keepold"
    ABORT = "abort"


USER_INPUT_CONTINUE: Final[Sequence] = ["c", "continue"]
USER_INPUT_DISABLE: Final[Sequence] = ["d", "disable"]


def disable_incomp_mkp(
    logger: Logger,
    conflict_mode: ConflictMode,
    module_name: str,
    error: BaseException,
    package_id: PackageID,
    installer: Installer,
    package_store: PackageStore,
    path_config: PathConfig,
    path: Path,
) -> bool:
    logger.error(error_message_incomp_package(path, package_id, error))
    if conflict_mode in (ConflictMode.INSTALL, ConflictMode.KEEP_OLD) or (
        conflict_mode is ConflictMode.ASK
        and _request_user_input_on_incompatible_file().lower() in USER_INPUT_DISABLE
    ):
        if (
            disabled := disable(
                installer,
                package_store,
                path_config,
                _CALLBACKS,
                package_id,
            )
        ) is not None:  # should not be None in this case.
            _make_post_change_actions()([disabled])

        sys.stdout.write(f"Disabled extension package: {package_id.name} {package_id.version}\n")
        return True
    return False


def _request_user_input_on_incompatible_file() -> str:
    return prompt(
        "You can abort the update process (A) or disable the "
        "extension package (d) and continue the update process.\n"
        "Abort the update process? [A/d] \n"
    )


def error_message_incomp_package(path: Path, package_id: PackageID, error: BaseException) -> str:
    return (
        f"Incompatible file '{path}' of extension package '{package_id.name} "
        f"{package_id.version}'\nError: {error}\n\n"
    )


def _make_post_change_actions() -> Callable[[Sequence[Manifest]], None]:
    return make_post_package_change_actions(
        on_any_change=(reload_apache, invalidate_visuals_cache, request_index_rebuild)
    )


def continue_on_incomp_local_file(conflict_mode: ConflictMode) -> bool:
    return continue_per_users_choice(
        conflict_mode,
        "You can abort the update process (A) and try to fix "
        "the incompatibilities or continue the update (c).\n\n"
        "Abort the update process? [A/c] \n",
    )


def error_message_incomp_local_file(path: Path, error: BaseException) -> str:
    return f"Incompatible local file '{path}'.\nError: {error}\n\n"


def continue_per_users_choice(conflict_mode: ConflictMode, propt_text: str) -> bool:
    if conflict_mode is ConflictMode.ASK:
        return prompt(propt_text).lower() in USER_INPUT_CONTINUE
    return False


def get_installer_and_package_map(
    path_config: PathConfig,
) -> tuple[Installer, dict[Path, PackageID]]:
    installer = Installer(paths.installed_packages_dir)
    installed_files_package_map = {
        Path(path_config.get_path(part)).resolve() / file: manifest.id
        for manifest in installer.get_installed_manifests()
        for part, files in manifest.files.items()
        for file in files
    }
    return installer, installed_files_package_map
