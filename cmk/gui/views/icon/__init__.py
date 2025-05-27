#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import active_config
from cmk.gui.painter.v0 import PainterRegistry
from cmk.gui.permissions import (
    declare_dynamic_permissions,
    PermissionSectionRegistry,
)

from .base import Icon
from .builtin import (
    AcknowledgeIcon,
    ActionMenuIcon,
    ActiveChecksIcon,
    CheckPeriodIcon,
    CommentsIcon,
    CrashdumpsIcon,
    CustomActionIcon,
    DowntimesIcon,
    FlappingIcon,
    IconImageIcon,
    LogwatchIcon,
    ManpageIcon,
    NotesIcon,
    NotificationPeriodIcon,
    NotificationsIcon,
    PassiveChecksIcon,
    PerfgraphIcon,
    PredictionIcon,
    RescheduleIcon,
    RuleEditorIcon,
    ServicePeriodIcon,
    StalenessIcon,
    StarsIcon,
)
from .config_icons import declare_icons_and_actions_perm
from .page_ajax_popup_action_menu import ajax_popup_action_menu
from .painter import PainterHostIcons, PainterServiceIcons
from .permission_section import (
    PERMISSION_SECTION_ICONS_AND_ACTIONS,
)
from .registry import icon_and_action_registry, IconRegistry
from .topology import ShowParentChildTopology


def register(
    icon_registry: IconRegistry,
    painter_registry: PainterRegistry,
    permission_section_registry: PermissionSectionRegistry,
) -> None:
    permission_section_registry.register(PERMISSION_SECTION_ICONS_AND_ACTIONS)
    painter_registry.register(PainterHostIcons)
    painter_registry.register(PainterServiceIcons)
    icon_registry.register(ShowParentChildTopology)
    icon_registry.register(ActionMenuIcon)
    icon_registry.register(IconImageIcon)
    icon_registry.register(RescheduleIcon)
    icon_registry.register(RuleEditorIcon)
    icon_registry.register(ManpageIcon)
    icon_registry.register(AcknowledgeIcon)
    icon_registry.register(PerfgraphIcon)
    icon_registry.register(PredictionIcon)
    icon_registry.register(CustomActionIcon)
    icon_registry.register(LogwatchIcon)
    icon_registry.register(NotesIcon)
    icon_registry.register(DowntimesIcon)
    icon_registry.register(CommentsIcon)
    icon_registry.register(NotificationsIcon)
    icon_registry.register(FlappingIcon)
    icon_registry.register(StalenessIcon)
    icon_registry.register(ActiveChecksIcon)
    icon_registry.register(PassiveChecksIcon)
    icon_registry.register(NotificationPeriodIcon)
    icon_registry.register(ServicePeriodIcon)
    icon_registry.register(StarsIcon)
    icon_registry.register(CrashdumpsIcon)
    icon_registry.register(CheckPeriodIcon)

    # also declare permissions for custom icons
    declare_dynamic_permissions(
        lambda: declare_icons_and_actions_perm(active_config.user_icons_and_actions)
    )


__all__ = [
    "icon_and_action_registry",
    "IconRegistry",
    "Icon",
    "ajax_popup_action_menu",
]
