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


@dataclass(kw_only=True)
class I18n:
    popup_title: str
    why_need_title: str
    why_need_description: str
    what_collect_title: str
    we_collect_label: str
    we_collect_details: str
    we_do_not_collect_label: str
    we_do_not_collect_details: str
    mkp_warning_title: str
    mkp_warning_description: str
    global_settings_hint_title: str
    global_settings_hint_description: str
    ask_later_button: str
    enable_settings_button: str


@dataclass(kw_only=True)
class ProductUsageAnalyticsConfig:
    global_settings_link: str
    i18n: I18n
