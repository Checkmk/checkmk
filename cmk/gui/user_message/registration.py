#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.pages import PageEndpoint, PageRegistry

from .user_message import ajax_acknowledge_user_message, ajax_delete_user_message, PageUserMessage


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("user_message", PageUserMessage))
    page_registry.register(PageEndpoint("ajax_delete_user_message", ajax_delete_user_message))
    page_registry.register(
        PageEndpoint("ajax_acknowledge_user_message", ajax_acknowledge_user_message)
    )
