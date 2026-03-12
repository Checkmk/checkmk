#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.gui.exceptions import HTTPRedirect, MKAuthException, MKUserError
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import Page, PageContext, PageEndpoint, PageRegistry
from cmk.gui.watolib.profile_replication import start_profile_replication_job


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("user_profile_replicate", UserProfileReplicate()))


class UserProfileReplicate(Page):
    @override
    def page(self, ctx: PageContext) -> None:
        if not user.id:
            raise MKUserError(None, _("Not logged in."))

        if not user.may("general.change_password") and not user.may("general.edit_profile"):
            raise MKAuthException(_("You are not allowed to edit your user profile."))

        if not ctx.config.wato_enabled:
            raise MKAuthException(_("User profiles cannot be edited (Setup is disabled)."))

        back_url = ctx.request.get_url_input("back", "user_profile.py")
        start_profile_replication_job(back_url=back_url, config=ctx.config)
        raise HTTPRedirect(back_url)
