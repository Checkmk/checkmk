#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

from cmk.ccc.version import Edition
from cmk.gui.background_job.job import BackgroundJobRegistry
from cmk.gui.main_menu import MainMenuRegistry
from cmk.gui.pages import PageRegistry
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib import profile_replication
from cmk.shared_typing.main_menu import (
    NavItemTopic,
)

from . import (
    change_password,
    edit_profile,
    main_menu,
    replicate,
    two_factor,
)


def register(
    edition: Edition,
    page_registry: PageRegistry,
    main_menu_registry: MainMenuRegistry,
    user_menu_topics: Callable[[UserPermissions], list[NavItemTopic]],
    job_registry: BackgroundJobRegistry,
) -> None:
    main_menu.register(page_registry, main_menu_registry, user_menu_topics)
    two_factor.register(edition, page_registry)
    edit_profile.register(edition, page_registry)
    change_password.register(edition, page_registry)
    replicate.register(page_registry)
    profile_replication.register(job_registry)
