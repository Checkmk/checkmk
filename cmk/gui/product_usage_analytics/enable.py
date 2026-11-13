#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Enable product usage analytics from the pop-up

The pop-up saves the global setting the same way the global settings page does: it becomes a
pending change with an audit log entry. It does not activate the changes, because that would also
activate the pending changes of other users.
"""

from typing import Final, override

from cmk.ccc import store
from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.global_config import get_global_config
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInUser, user
from cmk.gui.pages import AjaxPage, PageContext, PageEndpoint, PageRegistry, PageResult
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.watolib import read_only
from cmk.gui.watolib.config_domain_name import config_variable_registry
from cmk.gui.watolib.global_settings import (
    add_global_settings_change,
    load_configuration_settings,
    save_global_settings,
)
from cmk.utils.paths import configuration_lockfile

VARNAME: Final = "product_usage_analytics"


def register(page_registry: PageRegistry) -> None:
    page_registry.register(
        PageEndpoint("ajax_enable_product_usage_analytics", AjaxEnableProductUsageAnalytics())
    )


def may_change_the_setting(config: Config, acting_user: LoggedInUser) -> bool:
    """The checks the global settings page does before it saves the setting

    Only users who pass them can decide, so only they are asked.
    """
    return (
        config.wato_enabled
        and not (
            read_only.is_enabled(config.wato_read_only)
            and not read_only.may_override(config.wato_read_only)
        )
        and acting_user.may("wato.use")
        and acting_user.may("wato.edit")
        and acting_user.may("wato.global")
        and get_global_config().global_settings.is_activated(VARNAME)
    )


def enable_product_usage_analytics(*, user_id: UserId | None, use_git: bool) -> None:
    """Set the global setting to "enabled" and keep its other parts, like the proxy"""
    config_variable = config_variable_registry[VARNAME]
    settings = dict(load_configuration_settings())
    current: dict[str, object] = dict(
        settings[VARNAME]
        if VARNAME in settings
        else config_variable.primary_domain().default_globals()[VARNAME]
    )
    settings[VARNAME] = {**current, "enabled": "enabled"}
    save_global_settings(settings)
    add_global_settings_change(
        config_variable,
        user_id=user_id,
        text=_("Enabled product usage analytics"),
        sites=None,
        use_git=use_git,
    )


class AjaxEnableProductUsageAnalytics(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        check_csrf_token()
        if not may_change_the_setting(ctx.config, user):
            raise MKAuthException(_("You are not permitted to enable product usage analytics."))
        if is_distributed_setup_remote_site(ctx.config.sites):
            raise MKUserError(
                None, _("Product usage analytics can only be enabled on the central site.")
            )
        with store.lock_checkmk_configuration(configuration_lockfile):
            enable_product_usage_analytics(user_id=user.id, use_git=ctx.config.wato_use_git)
        return {}
