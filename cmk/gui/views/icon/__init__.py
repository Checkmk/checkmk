#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable

from cmk.gui.permissions import PermissionSectionRegistry

from ..painter.v0.base import PainterRegistry
from .base import Icon
from .builtin import (
    AcknowledgeIcon,
    ActionMenuIcon,
    ActiveChecksIcon,
    AggregationIcon,
    AggregationsIcon,
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
    RobotmkErrorIcon,
    RobotmkIcon,
    RuleEditorIcon,
    ServicePeriodIcon,
    StalenessIcon,
    StarsIcon,
)
from .config_icons import update_icons_from_configuration
from .inventory import InventoryIcon
from .page_ajax_popup_action_menu import ajax_popup_action_menu
from .painter import PainterHostIcons, PainterServiceIcons
from .permission_section import PermissionSectionIconsAndActions
from .registry import icon_and_action_registry, IconRegistry
from .topology import ShowParentChildTopology


def register(
    icon_registry: IconRegistry,
    painter_registry: PainterRegistry,
    permission_section_registry: PermissionSectionRegistry,
    register_post_config_load_hook: Callable[[Callable[[], None]], None],
) -> None:
    permission_section_registry.register(PermissionSectionIconsAndActions)
    register_post_config_load_hook(update_icons_from_configuration)
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
    icon_registry.register(AggregationsIcon)
    icon_registry.register(StarsIcon)
    icon_registry.register(AggregationIcon)
    icon_registry.register(CrashdumpsIcon)
    icon_registry.register(CheckPeriodIcon)
    # Better move these implementations & registrations to the feature related modules
    icon_registry.register(InventoryIcon)
    icon_registry.register(RobotmkIcon)
    icon_registry.register(RobotmkErrorIcon)


__all__ = [
    "icon_and_action_registry",
    "IconRegistry",
    "Icon",
    "update_icons_from_configuration",
    "ajax_popup_action_menu",
]
