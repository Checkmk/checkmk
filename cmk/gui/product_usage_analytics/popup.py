#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from dataclasses import asdict, dataclass
from typing import Final

from cmk.ccc.site import url_prefix
from cmk.gui.config import Config
from cmk.gui.form_specs.visitors.single_choice import SingleChoiceVisitor
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request, Response
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.site_config import (
    has_distributed_setup_remote_sites,
    is_distributed_setup_remote_site,
)
from cmk.gui.watolib import read_only
from cmk.gui.watolib.config_domain_name import config_variable_registry
from cmk.gui.watolib.global_settings import may_write
from cmk.product_usage.config import load_product_usage_config
from cmk.shared_typing.product_usage_analytics import (
    ProductUsageAnalyticsConfig,
    ReminderCookie,
)
from cmk.utils import paths
from cmk.web.utils.urls import makeuri, makeuri_contextless

from ._popup_cookie import (
    COOKIE_MAX_AGE_SECONDS,
    COOKIE_NAME,
    product_usage_analytics_popup_timestamp_cookie,
    REMINDER_INTERVAL_SECONDS,
    set_user_product_usage_analytics_popup_cookie,
)


@dataclass(frozen=True, kw_only=True)
class ProductUsageAnalyticsConfigTyped(ProductUsageAnalyticsConfig): ...


MANIFEST_URL: Final = "https://analytics.checkmk.com/manifest"

_VARNAME: Final = "product_usage_analytics"

# The frontend value of the global setting's choice to enable product usage analytics
ENABLED_CHOICE_ID: Final = SingleChoiceVisitor.option_id("enabled")

__popup_enabled = True


def disable_product_usage_analytics_popup() -> None:
    global __popup_enabled
    __popup_enabled = False


def render_product_usage_analytics_popup(
    active_config: Config, user: LoggedInUser, request: Request, response: Response
) -> None:
    # Show product usage analytics popup if the user may change the setting and the site is a central site (in case of
    # distributed setup) and has not decided about product usage analytics. We show the popup only
    # after 30 days have passed since the first login. After that, we keep showing the popup on
    # every page load until the user decides or defers the decision in the popup. Deferring resets
    # the cookie in the browser.

    is_not_distributed_setup = not has_distributed_setup_remote_sites(
        active_config.sites
    ) and not is_distributed_setup_remote_site(active_config.sites)
    is_central_site_in_distributed_setup = has_distributed_setup_remote_sites(
        active_config.sites
    ) and not is_distributed_setup_remote_site(active_config.sites)

    if not __popup_enabled:
        return

    if (
        _may_change_the_setting(active_config, user)
        and (is_not_distributed_setup or is_central_site_in_distributed_setup)
        and load_product_usage_config(paths.default_config_dir, logger).enabled == "not_decided"
    ):
        popup_timestamp_cookie = product_usage_analytics_popup_timestamp_cookie(request)

        if popup_timestamp_cookie is None:
            set_user_product_usage_analytics_popup_cookie(request, response)
        elif (
            datetime.datetime.now().timestamp() - popup_timestamp_cookie
            >= REMINDER_INTERVAL_SECONDS
        ):
            _show_popup(request)


def _show_popup(request: Request) -> None:
    html.vue_component(
        "cmk-product-usage-analytics",
        data=asdict(
            ProductUsageAnalyticsConfigTyped(
                global_settings_link=makeuri(
                    request,
                    addvars=[("varname", _VARNAME)],
                    filename="global_settings.py",
                ),
                manifest_link=MANIFEST_URL,
                enabled_choice_id=ENABLED_CHOICE_ID,
                activate_changes_link=makeuri_contextless(
                    request, [("mode", "changelog")], filename="wato.py"
                ),
                reminder_cookie=ReminderCookie(
                    name=COOKIE_NAME,
                    path=url_prefix(),
                    max_age_seconds=COOKIE_MAX_AGE_SECONDS,
                ),
            )
        ),
    )


def _may_change_the_setting(active_config: Config, user: LoggedInUser) -> bool:
    """The checks the global settings REST API does before it saves the setting

    Only users who pass them can decide, so only they are asked. The REST API also requires a
    provider site. That is covered by showing the pop-up on standalone and central sites only.
    """
    return (
        active_config.wato_enabled
        and not read_only.blocks_changes(active_config.wato_read_only)
        and user.may("wato.use")
        and may_write(config_variable_registry[_VARNAME], user)
    )
