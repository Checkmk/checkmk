#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from functools import lru_cache
from pathlib import Path
from typing import Final

from typing_extensions import assert_never

import cmk.utils.paths
from cmk.utils.i18n import _

# It's OK to import centralized config load logic
import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from ._mkp import PackagePart


def ui_title(part: PackagePart) -> str:
    return _derived_properties(part)[0]


def site_path(part: PackagePart) -> Path:
    return _derived_properties(part)[1]


def permissions(part: PackagePart) -> int:
    return _derived_properties(part)[2]


@lru_cache
def _derived_properties(part: PackagePart) -> tuple[str, Path, int]:
    match part:
        case PackagePart.EC_RULE_PACKS:
            return _("Event Console rule packs"), ec.mkp_rule_pack_dir(), 0o644
        case PackagePart.AGENT_BASED:
            return (
                _("Agent based plugins (Checks, Inventory)"),
                cmk.utils.paths.local_agent_based_plugins_dir,
                0o644,
            )

        case PackagePart.CHECKS:
            return _("Legacy check plugins"), cmk.utils.paths.local_checks_dir, 0o644
        case PackagePart.HASI:
            return _("Legacy inventory plugins"), cmk.utils.paths.local_inventory_dir, 0o644
        case PackagePart.CHECKMAN:
            return _("Checks' man pages"), cmk.utils.paths.local_check_manpages_dir, 0o644
        case PackagePart.AGENTS:
            return _("Agents"), cmk.utils.paths.local_agents_dir, 0o755
        case PackagePart.NOTIFICATIONS:
            return _("Notification scripts"), cmk.utils.paths.local_notifications_dir, 0o755
        case PackagePart.GUI:
            return _("GUI extensions"), cmk.utils.paths.local_gui_plugins_dir, 0o644
        case PackagePart.WEB:
            return _("Legacy GUI extensions"), cmk.utils.paths.local_web_dir, 0o644
        case PackagePart.PNP_TEMPLATES:
            return (
                _("PNP4Nagios templates (deprecated)"),
                cmk.utils.paths.local_pnp_templates_dir,
                0o644,
            )

        case PackagePart.DOC:
            return _("Documentation files"), cmk.utils.paths.local_doc_dir, 0o644
        case PackagePart.LOCALES:
            return _("Localizations"), cmk.utils.paths.local_locale_dir, 0o644
        case PackagePart.BIN:
            return _("Binaries"), cmk.utils.paths.local_bin_dir, 0o755
        case PackagePart.LIB:
            return _("Libraries"), cmk.utils.paths.local_lib_dir, 0o644
        case PackagePart.MIBS:
            return _("SNMP MIBs"), cmk.utils.paths.local_mib_dir, 0o644
        case PackagePart.ALERT_HANDLERS:
            return _("Alert handlers"), cmk.utils.paths.local_alert_handlers_dir, 0o755

    return assert_never(part)


CONFIG_PARTS: Final = (PackagePart.EC_RULE_PACKS,)


def _part_depth(part: PackagePart) -> int:
    return len(Path(site_path(part)).resolve().parts)


def get_package_part(full_file_path: Path) -> PackagePart | None:
    """Determine the part for a given file (or return None if there is none)"""
    # deal with parts containing each other by checking more specific ones first!
    return next(
        (
            part
            for part in sorted(PackagePart, key=_part_depth, reverse=True)
            if full_file_path.resolve().is_relative_to(site_path(part).resolve())
        ),
        None,
    )
