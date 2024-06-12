#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Final

from typing_extensions import assert_never

from cmk.utils.i18n import _

from ._mkp import PackagePart


@dataclass(frozen=True)
class PathConfig:
    local_root: Path
    mkp_rule_pack_dir: Path
    agent_based_plugins_dir: Path
    checks_dir: Path
    inventory_dir: Path
    check_manpages_dir: Path
    agents_dir: Path
    notifications_dir: Path
    gui_plugins_dir: Path
    web_dir: Path
    pnp_templates_dir: Path
    doc_dir: Path
    locale_dir: Path
    bin_dir: Path
    lib_dir: Path
    mib_dir: Path
    alert_handlers_dir: Path

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
            case PackagePart.CMK_PLUGINS:
                # this is ignored in 2.2, but we must be able to resolve the path
                return self.lib_dir / "cmk23_cmk_plugins"
            case PackagePart.CMK_ADDONS_PLUGINS:
                # this is ignored in 2.2, but we must be able to resolve the path
                return self.lib_dir / "cmk23_cmk_addons_plugins"
        return assert_never(part)

    @cached_property
    def resolved_paths(self) -> Mapping[PackagePart, Path]:
        return {part: self.get_path(part).resolve() for part in PackagePart}

    def get_part(self, full_file_path: Path) -> PackagePart | None:
        """Determine the part for a given file (or return None if there is none)"""
        # deal with parts containing each other by checking more specific ones first!
        ffpr = full_file_path.resolve()
        return next(
            (
                part
                for part in self._parts_by_depth
                if ffpr.is_relative_to(self.resolved_paths[part])
            ),
            None,
        )

    @cached_property
    def _parts_by_depth(self) -> Sequence[PackagePart]:
        def _depth(part: PackagePart) -> int:
            return len(self.resolved_paths[part].parts)

        return sorted(PackagePart, key=_depth, reverse=True)


def ui_title(part: PackagePart) -> str:
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
        case PackagePart.CMK_PLUGINS:
            return _("Shipped Checkmk plug-ins (for Checkmk 2.3)")
        case PackagePart.CMK_ADDONS_PLUGINS:
            return _("Additional Checkmk plug-ins by third parties (for Checkmk 2.3)")

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
        case PackagePart.CMK_PLUGINS:
            return 0o644
        case PackagePart.CMK_ADDONS_PLUGINS:
            return 0o644
    return assert_never(part)


CONFIG_PARTS: Final = (PackagePart.EC_RULE_PACKS,)
