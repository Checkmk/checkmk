#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from functools import cached_property
from pathlib import Path
from typing import Final

from typing_extensions import assert_never

import cmk.utils.paths
from cmk.utils.i18n import _

# It's OK to import centralized config load logic
import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

PartName = str
PartFiles = list[str]


@enum.unique
class PackagePart(str, enum.Enum):
    EC_RULE_PACKS = "ec_rule_packs"
    AGENT_BASED = "agent_based"
    CHECKS = "checks"
    HASI = "inventory"
    CHECKMAN = "checkman"
    AGENTS = "agents"
    NOTIFICATIONS = "notifications"
    GUI = "gui"
    WEB = "web"
    PNP_TEMPLATES = "pnp-templates"
    DOC = "doc"
    LOCALES = "locales"
    BIN = "bin"
    LIB = "lib"
    MIBS = "mibs"
    ALERT_HANDLERS = "alert_handlers"

    @property
    def ident(self) -> PartName:
        return self.value

    @property
    def ui_title(self) -> str:  # don't mix up with str.title
        return self._derived_properties[0]

    @property
    def path(self) -> Path:
        return self._derived_properties[1]

    @cached_property
    def _derived_properties(self) -> tuple[str, Path]:
        match self:
            case PackagePart.EC_RULE_PACKS:
                return _("Event Console rule packs"), ec.mkp_rule_pack_dir()
            case PackagePart.AGENT_BASED:
                return (
                    _("Agent based plugins (Checks, Inventory),"),
                    cmk.utils.paths.local_agent_based_plugins_dir,
                )
            case PackagePart.CHECKS:
                return _("Legacy check plugins"), cmk.utils.paths.local_checks_dir
            case PackagePart.HASI:
                return _("Legacy inventory plugins"), cmk.utils.paths.local_inventory_dir
            case PackagePart.CHECKMAN:
                return _("Checks' man pages"), cmk.utils.paths.local_check_manpages_dir
            case PackagePart.AGENTS:
                return _("Agents"), cmk.utils.paths.local_agents_dir
            case PackagePart.NOTIFICATIONS:
                return _("Notification scripts"), cmk.utils.paths.local_notifications_dir
            case PackagePart.GUI:
                return _("GUI extensions"), cmk.utils.paths.local_gui_plugins_dir
            case PackagePart.WEB:
                return _("Legacy GUI extensions"), cmk.utils.paths.local_web_dir
            case PackagePart.PNP_TEMPLATES:
                return (
                    _("PNP4Nagios templates (deprecated)"),
                    cmk.utils.paths.local_pnp_templates_dir,
                )
            case PackagePart.DOC:
                return _("Documentation files"), cmk.utils.paths.local_doc_dir
            case PackagePart.LOCALES:
                return _("Localizations"), cmk.utils.paths.local_locale_dir
            case PackagePart.BIN:
                return _("Binaries"), cmk.utils.paths.local_bin_dir
            case PackagePart.LIB:
                return _("Libraries"), cmk.utils.paths.local_lib_dir
            case PackagePart.MIBS:
                return _("SNMP MIBs"), cmk.utils.paths.local_mib_dir
            case PackagePart.ALERT_HANDLERS:
                return _("Alert handlers"), cmk.utils.paths.local_share_dir / "alert_handlers"

        return assert_never(self)


CONFIG_PARTS: Final = (PackagePart.EC_RULE_PACKS,)


PACKAGE_PARTS: Final = (
    PackagePart.AGENT_BASED,
    PackagePart.CHECKS,
    PackagePart.HASI,
    PackagePart.CHECKMAN,
    PackagePart.AGENTS,
    PackagePart.NOTIFICATIONS,
    PackagePart.GUI,
    PackagePart.WEB,
    PackagePart.PNP_TEMPLATES,
    PackagePart.DOC,
    PackagePart.LOCALES,
    PackagePart.BIN,
    PackagePart.LIB,
    PackagePart.MIBS,
    PackagePart.ALERT_HANDLERS,
)
