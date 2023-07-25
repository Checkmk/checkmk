#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import assert_never, Final

from ._mkp import PackagePart


@dataclass(frozen=True)
class PathConfig:
    agent_based_plugins_dir: Path
    agents_dir: Path
    alert_handlers_dir: Path
    bin_dir: Path
    check_manpages_dir: Path
    checks_dir: Path
    doc_dir: Path
    gui_plugins_dir: Path
    installed_packages_dir: Path
    inventory_dir: Path
    lib_dir: Path
    locale_dir: Path
    local_root: Path
    mib_dir: Path
    mkp_rule_pack_dir: Path
    notifications_dir: Path
    packages_enabled_dir: Path
    packages_local_dir: Path
    packages_shipped_dir: Path
    pnp_templates_dir: Path
    tmp_dir: Path
    web_dir: Path

    def get_path(self, part: PackagePart) -> Path:
        match part:
            case PackagePart.EC_RULE_PACKS:
                return self.mkp_rule_pack_dir
            case PackagePart.AGENT_BASED:
                return self.agent_based_plugins_dir
            case PackagePart.CHECKS:
                return self.checks_dir
            case PackagePart.HASI:
                return self.inventory_dir
            case PackagePart.CHECKMAN:
                return self.check_manpages_dir
            case PackagePart.AGENTS:
                return self.agents_dir
            case PackagePart.NOTIFICATIONS:
                return self.notifications_dir
            case PackagePart.GUI:
                return self.gui_plugins_dir
            case PackagePart.WEB:
                return self.web_dir
            case PackagePart.PNP_TEMPLATES:
                return self.pnp_templates_dir
            case PackagePart.DOC:
                return self.doc_dir
            case PackagePart.LOCALES:
                return self.locale_dir
            case PackagePart.BIN:
                return self.bin_dir
            case PackagePart.LIB:
                return self.lib_dir
            case PackagePart.MIBS:
                return self.mib_dir
            case PackagePart.ALERT_HANDLERS:
                return self.alert_handlers_dir
        return assert_never(part)

    def get_part(self, full_file_path: Path) -> PackagePart | None:
        """Determine the part for a given file (or return None if there is none)"""

        # deal with parts containing each other by checking more specific ones first!
        def _part_depth(part: PackagePart) -> int:
            return len(Path(self.get_path(part)).resolve().parts)

        return next(
            (
                part
                for part in sorted(PackagePart, key=_part_depth, reverse=True)
                if full_file_path.resolve().is_relative_to(self.get_path(part).resolve())
            ),
            None,
        )


def ui_title(part: PackagePart, _: Callable[[str], str]) -> str:
    match part:
        case PackagePart.EC_RULE_PACKS:
            return _("Event Console rule packs")
        case PackagePart.AGENT_BASED:
            return _("Agent based plugins (Checks, Inventory)")
        case PackagePart.CHECKS:
            return _("Legacy check plugins")
        case PackagePart.HASI:
            return _("Legacy inventory plugins")
        case PackagePart.CHECKMAN:
            return _("Checks' man pages")
        case PackagePart.AGENTS:
            return _("Agents")
        case PackagePart.NOTIFICATIONS:
            return _("Notification scripts")
        case PackagePart.GUI:
            return _("GUI extensions")
        case PackagePart.WEB:
            return _("Legacy GUI extensions")
        case PackagePart.PNP_TEMPLATES:
            return _("PNP4Nagios templates (deprecated)")
        case PackagePart.DOC:
            return _("Documentation files")
        case PackagePart.LOCALES:
            return _("Localizations")
        case PackagePart.BIN:
            return _("Binaries")
        case PackagePart.LIB:
            return _("Libraries")
        case PackagePart.MIBS:
            return _("SNMP MIBs")
        case PackagePart.ALERT_HANDLERS:
            return _("Alert handlers")

    return assert_never(part)


def permissions(part: PackagePart) -> int:
    match part:
        case PackagePart.EC_RULE_PACKS:
            return 0o644
        case PackagePart.AGENT_BASED:
            return 0o644
        case PackagePart.CHECKS:
            return 0o644
        case PackagePart.HASI:
            return 0o644
        case PackagePart.CHECKMAN:
            return 0o644
        case PackagePart.AGENTS:
            return 0o755
        case PackagePart.NOTIFICATIONS:
            return 0o755
        case PackagePart.GUI:
            return 0o644
        case PackagePart.WEB:
            return 0o644
        case PackagePart.PNP_TEMPLATES:
            return 0o644
        case PackagePart.DOC:
            return 0o644
        case PackagePart.LOCALES:
            return 0o644
        case PackagePart.BIN:
            return 0o755
        case PackagePart.LIB:
            return 0o644
        case PackagePart.MIBS:
            return 0o644
        case PackagePart.ALERT_HANDLERS:
            return 0o755
    return assert_never(part)


CONFIG_PARTS: Final = (PackagePart.EC_RULE_PACKS,)


PackageOperationCallback = Callable[[Sequence[Path]], None]


@dataclass(frozen=True)
class PackageOperationCallbacks:
    # currently we don't need more. Add if needed.
    install: PackageOperationCallback = lambda _files: None
    uninstall: PackageOperationCallback = lambda _files: None
    release: PackageOperationCallback = lambda _files: None
