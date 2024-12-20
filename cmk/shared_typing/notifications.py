#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# This file is auto-generated via the cmk-shared-typing package.
# Do not edit manually.
#
# fmt: off


from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(kw_only=True)
class FallbackWarningI18n:
    title: str
    message: str
    setup_link_title: str
    do_not_show_again_title: str


@dataclass(kw_only=True)
class NotificationStatsI18n:
    sent_notifications: str
    failed_notifications: str
    sent_notifications_link_title: str
    failed_notifications_link_title: str


@dataclass(kw_only=True)
class CoreStatsI18n:
    title: str
    sites_column_title: str
    status_column_title: str
    ok_msg: str
    warning_msg: str
    disabled_msg: str


@dataclass(kw_only=True)
class Rule:
    i18n: str
    count: str
    link: str


@dataclass(kw_only=True)
class FallbackWarning:
    i18n: FallbackWarningI18n
    setup_link: str
    do_not_show_again_link: str


@dataclass(kw_only=True)
class NotificationStats:
    num_sent_notifications: int
    num_failed_notifications: int
    sent_notification_link: str
    failed_notification_link: str
    i18n: NotificationStatsI18n


@dataclass(kw_only=True)
class CoreStats:
    sites: list[str]
    i18n: CoreStatsI18n


@dataclass(kw_only=True)
class RuleTopic:
    rules: list[Rule]
    i18n: Optional[str] = None


@dataclass(kw_only=True)
class RuleSection:
    i18n: str
    topics: list[RuleTopic]


@dataclass(kw_only=True)
class Notifications:
    overview_title_i18n: str
    notification_stats: NotificationStats
    core_stats: CoreStats
    rule_sections: list[RuleSection]
    user_id: str
    fallback_warning: Optional[FallbackWarning] = None


@dataclass(kw_only=True)
class NotificationParametersOverview:
    parameters: list[RuleSection]
    i18n: dict[str, Any]


@dataclass(kw_only=True)
class NotificationTypeDefs:
    notifications: Optional[Notifications] = None
    notification_parameters_overview: Optional[NotificationParametersOverview] = None
