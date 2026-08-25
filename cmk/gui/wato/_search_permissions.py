#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.version import Edition, edition
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.global_config import get_global_config
from cmk.gui.logged_in import user
from cmk.gui.pages import get_page_handler, PageContext
from cmk.gui.search.permissions import VisibilityCheck
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.watolib.mode import mode_registry
from cmk.gui.watolib.rulesets import may_edit_ruleset
from cmk.utils import paths
from cmk.web.utils.urls import file_name_and_query_vars_from_url


class SetupPermissionsHandler:
    def __init__(self, edition: Edition, ctx: PageContext) -> None:
        self._edition = edition
        self._ctx = ctx
        self._config = ctx.config
        self._request = ctx.request
        self._category_permissions = {
            "global_settings": user.may("wato.global") or user.may("wato.seeall"),
            "folders": user.may("wato.hosts"),
            "hosts": user.may("wato.hosts"),
            "event_console": user.may("mkeventd.edit") or user.may("wato.seeall"),
            "event_console_settings": user.may("mkeventd.config") or user.may("wato.seeall"),
            "logfile_pattern_analyzer": user.may("wato.pattern_editor") or user.may("wato.seeall"),
            "notification_parameter": user.may("wato.notifications") or user.may("wato.seeall"),
        }

    def may_see_category(self, category: str) -> bool:
        return user.may("wato.use") and self._category_permissions.get(category, True)

    def get_visibility_check(self, category: str) -> VisibilityCheck:
        return {
            "global_settings": self._check_global_setting_visibility,
            "rules": self._check_rule_visibility,
            "hosts": self._check_host_visibility,
            "setup": self._check_page_handler,
        }.get(category, lambda _: True)

    @staticmethod
    def _check_global_setting_visibility(url: str) -> bool:
        if edition(paths.omd_root) is not Edition.CLOUD:
            return True
        _, query_vars = file_name_and_query_vars_from_url(url)
        return get_global_config().global_settings.is_activated(query_vars["varname"][0])

    @staticmethod
    def _check_rule_visibility(url: str) -> bool:
        _, query_vars = file_name_and_query_vars_from_url(url)
        return may_edit_ruleset(query_vars["varname"][0])

    def _check_host_visibility(self, url: str) -> bool:
        perms_to_see_all_hosts = ("wato.all_folders", "wato.see_all_folders")
        can_see_all_hosts = any(user.may(perm) for perm in perms_to_see_all_hosts)
        return can_see_all_hosts or self._check_page_handler(url)

    def _check_page_handler(self, url: str) -> bool:
        file_name, query_vars = file_name_and_query_vars_from_url(url)

        for name, vals in query_vars.items():
            self._request.set_var(name, vals[0])

        mode = modes[0] if (modes := query_vars.get("mode", [])) else None

        try:
            if mode:
                mode_registry[mode](self._edition, self._ctx).ensure_permissions()
            else:
                self._check_if_handling_page_triggers_exception(file_name)
            return True
        except MKAuthException:
            return False
        except MKUserError:
            # In case a page initialization fails with a user error (invalid input) for some reason,
            # we don't want to show the search result.
            #
            # A possible scenario is (see also CMK-22600):
            #
            # 1. We are a non-admin user (which triggers this function)
            # 2. A host xyz exists, is in the search index and can be searched.
            # 3. The host is deleted in setup
            # 4. Before the search index is being rebuilt and the entry for the hosts edit mode is
            #    removed from the index, the search is used to find the host xyz.
            #
            # In this case the code above would create an instance of ModeEditHost, which would raise
            # a MKUserError because the host does not exist anymore.
            return False

    # TODO: see if there is a better way to check for permission than this.
    def _check_if_handling_page_triggers_exception(self, file_name: str) -> None:
        if (handler := get_page_handler(file_name)) is None:
            return

        # This context manager is needed to prevent HTML from being outputed to the response.
        # TODO: see if this is still relevant now that we are rendering from Vue.
        with output_funnel.plugged():
            handler(PageContext(config=self._config, request=self._request))
            output_funnel.drain()
