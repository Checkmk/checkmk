#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=too-many-return-statements,too-many-instance-attributes

import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import assert_never, Final, Self

from ._mkp import PackagePart


@dataclass(frozen=True)
class PathConfig:
    # This is very confusing.
    # Those paths describe both where to put things when installing,
    # and where to look for things when packaging.
    # There are also paths that have different purposes :-(

    # paths for MKP content
    cmk_plugins_dir: Path
    cmk_addons_plugins_dir: Path
    agent_based_plugins_dir: Path
    agents_dir: Path
    alert_handlers_dir: Path
    bin_dir: Path
    check_manpages_dir: Path
    checks_dir: Path
    doc_dir: Path
    gui_plugins_dir: Path
    inventory_dir: Path
    lib_dir: Path
    locale_dir: Path
    mib_dir: Path
    mkp_rule_pack_dir: Path
    notifications_dir: Path
    pnp_templates_dir: Path
    web_dir: Path

    # other paths
    installed_packages_dir: Path
    local_root: Path
    packages_enabled_dir: Path
    packages_local_dir: Path
    packages_shipped_dir: Path
    tmp_dir: Path

    @classmethod
    def from_toml(cls, content: str) -> Self:
        raw = tomllib.loads(content)["paths"]
        return cls(
            cmk_plugins_dir=Path(raw["cmk_plugins_dir"]),
            cmk_addons_plugins_dir=Path(raw["cmk_addons_plugins_dir"]),
            agent_based_plugins_dir=Path(raw["agent_based_plugins_dir"]),
            agents_dir=Path(raw["agents_dir"]),
            alert_handlers_dir=Path(raw["alert_handlers_dir"]),
            bin_dir=Path(raw["bin_dir"]),
            check_manpages_dir=Path(raw["check_manpages_dir"]),
            checks_dir=Path(raw["checks_dir"]),
            doc_dir=Path(raw["doc_dir"]),
            gui_plugins_dir=Path(raw["gui_plugins_dir"]),
            inventory_dir=Path(raw["inventory_dir"]),
            lib_dir=Path(raw["lib_dir"]),
            locale_dir=Path(raw["locale_dir"]),
            mib_dir=Path(raw["mib_dir"]),
            mkp_rule_pack_dir=Path(raw["mkp_rule_pack_dir"]),
            notifications_dir=Path(raw["notifications_dir"]),
            pnp_templates_dir=Path(raw["pnp_templates_dir"]),
            web_dir=Path(raw["web_dir"]),
            installed_packages_dir=Path(raw["installed_packages_dir"]),
            local_root=Path(raw["local_root"]),
            packages_enabled_dir=Path(raw["packages_enabled_dir"]),
            packages_local_dir=Path(raw["packages_local_dir"]),
            packages_shipped_dir=Path(raw["packages_shipped_dir"]),
            tmp_dir=Path(raw["tmp_dir"]),
        )

    def get_path(self, part: PackagePart) -> Path:
        match part:
            case PackagePart.CMK_PLUGINS:
                return self.cmk_plugins_dir
            case PackagePart.CMK_ADDONS_PLUGINS:
                return self.cmk_addons_plugins_dir
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
            case unreachable:
                assert_never(unreachable)

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


def ui_title(part: PackagePart, _: Callable[[str], str]) -> str:
    match part:
        case PackagePart.CMK_PLUGINS:
            return _("Shipped Checkmk plugins")
        case PackagePart.CMK_ADDONS_PLUGINS:
            return _("Additional Checkmk plugins by third parties")
        case PackagePart.EC_RULE_PACKS:
            return _("Event Console rule packs")
        case PackagePart.AGENT_BASED:
            return _("Agent based plugins (deprecated)")
        case PackagePart.CHECKS:
            return _("Legacy check plugins (deprecated)")
        case PackagePart.HASI:
            return _("Legacy inventory plugins (deprecated)")
        case PackagePart.CHECKMAN:
            return _("Checks' man pages (deprecated)")
        case PackagePart.AGENTS:
            return _("Agents")
        case PackagePart.NOTIFICATIONS:
            return _("Notification scripts")
        case PackagePart.GUI:
            return _("GUI extensions (deprecated)")
        case PackagePart.WEB:
            return _("Legacy GUI extensions (deprecated)")
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
        case unreachable:
            assert_never(unreachable)


def permissions(part: PackagePart) -> int:
    match part:
        case PackagePart.CMK_PLUGINS:
            return 0o644
        case PackagePart.CMK_ADDONS_PLUGINS:
            return 0o644
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
        case unreachable:
            assert_never(unreachable)


CONFIG_PARTS: Final = (PackagePart.EC_RULE_PACKS,)


PackageOperationCallback = Callable[[Sequence[Path]], None]


@dataclass(frozen=True)
class PackageOperationCallbacks:
    # currently we don't need more. Add if needed.
    install: PackageOperationCallback = lambda _files: None
    uninstall: PackageOperationCallback = lambda _files: None
    release: PackageOperationCallback = lambda _files: None
