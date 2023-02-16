#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
""" Pre update checks, executed before any configuration is changed. """

import enum
import sys
import traceback
from pathlib import Path
from typing import Mapping

from cmk.utils import paths
from cmk.utils.packaging import disable, Installer, PackageID, PathConfig

# It's OK to import centralized config load logic
import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from cmk.gui import main_modules
from cmk.gui.exceptions import MKUserError
from cmk.gui.session import SuperUserContext
from cmk.gui.utils import get_failed_plugins, remove_failed_plugin
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.hosts_and_folders import disable_redis
from cmk.gui.watolib.rulesets import RulesetCollection
from cmk.gui.wsgi.blueprints.global_vars import set_global_vars

from cmk.update_config.plugins.actions.rulesets import AllRulesets


class ConflictMode(enum.StrEnum):
    ASK = "ask"
    INSTALL = "install"
    KEEP_OLD = "keepold"
    ABORT = "abort"


_PATH_CONFIG = PathConfig(
    local_root=paths.local_root,
    mkp_rule_pack_dir=ec.mkp_rule_pack_dir(),
    agent_based_plugins_dir=paths.local_agent_based_plugins_dir,
    checks_dir=paths.local_checks_dir,
    inventory_dir=paths.local_inventory_dir,
    check_manpages_dir=paths.local_check_manpages_dir,
    agents_dir=paths.local_agents_dir,
    notifications_dir=paths.local_notifications_dir,
    gui_plugins_dir=paths.local_gui_plugins_dir,
    web_dir=paths.local_web_dir,
    pnp_templates_dir=paths.local_pnp_templates_dir,
    doc_dir=paths.local_doc_dir,
    locale_dir=paths.local_locale_dir,
    bin_dir=paths.local_bin_dir,
    lib_dir=paths.local_lib_dir,
    mib_dir=paths.local_mib_dir,
    alert_handlers_dir=paths.local_alert_handlers_dir,
)


def passed_pre_checks(
    conflict_mode: ConflictMode,
) -> bool:
    return _all_ui_extensions_compatible(conflict_mode) and _all_rulesets_compatible(conflict_mode)


def _all_rulesets_compatible(
    conflict_mode: ConflictMode,
) -> bool:
    try:
        with disable_redis(), gui_context(), SuperUserContext():
            set_global_vars()
            rulesets = AllRulesets.load_all_rulesets()
    except Exception:
        if conflict_mode in (ConflictMode.INSTALL, ConflictMode.KEEP_OLD) or (
            conflict_mode is ConflictMode.ASK
            and input(
                "Unknown exception while trying to load rulesets.\n"
                "Error: %s\n\n"
                "You can abort the update process (A) and try to fix "
                "the incompatibilities or try to continue the update (c).\n"
                "Abort update? [A/c]\n" % traceback.format_exc()
            ).lower()
            in ["c", "continue"]
        ):
            return True
        return False

    with disable_redis(), gui_context(), SuperUserContext():
        set_global_vars()
        result = _validate_rule_values(rulesets, conflict_mode)

    return result


def _validate_rule_values(
    all_rulesets: RulesetCollection,
    conflict_mode: ConflictMode,
) -> bool:
    rulesets_skip = {
        # the valid choices for this ruleset are user-dependent (SLAs) and not even an admin can
        # see all of them
        "extra_service_conf:_sla_config",
    }

    for ruleset in all_rulesets.get_rulesets().values():
        if ruleset.name in rulesets_skip:
            continue

        for folder, index, rule in ruleset.get_rules():
            try:
                ruleset.rulespec.valuespec.validate_value(
                    rule.value,
                    "",
                )
            except MKUserError as excpt:
                if conflict_mode in (ConflictMode.INSTALL, ConflictMode.KEEP_OLD) or (
                    conflict_mode is ConflictMode.ASK
                    and input(
                        "WARNING: Invalid rule configuration detected\n"
                        "Ruleset: %s\n"
                        "Title: %s\n"
                        "Folder: %s\n"
                        "Rule nr: %s\n"
                        "Exception: %s\n\n"
                        "You can abort the update process (A) and "
                        "try to fix the incompatibilities with a downgrade "
                        "to the version you came from or continue (c) the update.\n\n"
                        "Abort update? [A/c]\n"
                        % (
                            ruleset.name,
                            ruleset.title(),
                            folder.path() if folder.path() else "main",
                            index + 1,
                            excpt,
                        )
                    ).lower()
                    in ["c", "continue"]
                ):
                    return True
                return False
    return True


def _all_ui_extensions_compatible(
    conflict_mode: ConflictMode,
) -> bool:
    main_modules.load_plugins()
    installer = Installer(paths.installed_packages_dir)
    installed_files_package_map = {
        _PATH_CONFIG.get_path(part) / file: manifest.id
        for manifest in installer.get_installed_manifests()
        for part, files in manifest.files.items()
        for file in files
    }

    disabled_packages: set[PackageID] = set()
    for gui_part, module_or_file, error in get_failed_plugins():

        if (
            path_and_id := _best_effort_guess_for_file_path(
                gui_part, module_or_file, installed_files_package_map
            )
        ) is None:
            # we know something is wrong, but have no idea which file to blame
            if conflict_mode in (ConflictMode.INSTALL, ConflictMode.KEEP_OLD) or (
                conflict_mode is ConflictMode.ASK
                and input(
                    "Incompatible plugin '%s'.\n"
                    "Error: %s\n\n"
                    "You can abort the update process (A) and try to fix "
                    "the incompatibilities or continue the update (c).\n\n"
                    "Abort the update process? [A/c] \n" % (module_or_file, error)
                ).lower()
                in ["c", "continue"]
            ):
                continue
            return False

        # file path is unused. We could offer to delete it in the dialog below?
        _file_path, package_id = path_and_id  # pylint: disable=unpacking-non-sequence

        # unpackaged files
        if package_id is None:
            if conflict_mode in (ConflictMode.INSTALL, ConflictMode.KEEP_OLD) or (
                conflict_mode is ConflictMode.ASK
                and input(
                    "Incompatible local file '%s'.\n"
                    "Error: %s\n\n"
                    "You can abort the update process (A) and try to fix "
                    "the incompatibilities or continue the update (c).\n\n"
                    "Abort the update process? [A/c] \n" % (module_or_file, error)
                ).lower()
                in ["c", "continue"]
            ):
                continue
            return False

        if package_id in disabled_packages:
            continue  # already dealt with

        if conflict_mode in (ConflictMode.INSTALL, ConflictMode.KEEP_OLD) or (
            conflict_mode is ConflictMode.ASK
            and input(
                "Incompatible file '%s' of extension package '%s %s'\n"
                "Error: %s\n\n"
                "You can abort the update process (A) or disable the "
                "extension package (d) and continue the update process.\n"
                "Abort the update process? [A/d] \n"
                % (module_or_file, package_id.name, package_id.version, error),
            ).lower()
            in ["d", "disable"]
        ):
            disable(
                installer,
                _PATH_CONFIG,
                package_id.name,
                package_id.version,
            )
            disabled_packages.add(package_id)
            remove_failed_plugin((gui_part, module_or_file))
            sys.stdout.write(
                "Disabled extension package: %s %s\n" % (package_id.name, package_id.version)
            )
        else:
            return False
    return True


def _best_effort_guess_for_file_path(
    gui_part: str, module_or_file: str, installed: Mapping[Path, PackageID]
) -> tuple[Path, PackageID | None] | None:
    "try to guess which file could create such an error"
    potential_sources = (
        (
            # the legacy case where we come from web dir
            _PATH_CONFIG.web_dir
            / gui_part
            / f"{module_or_file.rstrip('c')}",
        )
        if module_or_file.endswith((".py", ".pyc"))
        else (
            _PATH_CONFIG.gui_plugins_dir / gui_part / f"{module_or_file}.py",
            _PATH_CONFIG.gui_plugins_dir / gui_part / module_or_file / "__init__.py",
        )
    )

    installed_candidates = [
        (p, package) for p in potential_sources if ((package := installed.get(p)) is not None)
    ]
    match len(installed_candidates):
        case 0:
            pass
        case 1:
            return installed_candidates[0]
        case _more_than_one:
            return None  # refuse to guess

    unpackaged_candidates = [p for p in potential_sources if p.exists()]
    match len(unpackaged_candidates):
        case 0:
            return None  # how did that happen?
        case 1:
            return (unpackaged_candidates[0], None)
        case _more_than_one:
            return None  # refuse to guess
