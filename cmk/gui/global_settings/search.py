#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from typing import Final, override

from cmk.ccc.site import omd_site
from cmk.ccc.version import edition
from cmk.gui.config import active_config
from cmk.gui.form_specs import localize
from cmk.gui.form_specs.unstable.legacy_converter import resolve_title
from cmk.gui.global_config import get_global_config
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.search.matchers import ABCMatchItemGenerator, MatchItem, MatchItems
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_variable_group_registry,
    ConfigVariable,
    GlobalSettingsContext,
)
from cmk.gui.watolib.global_settings import (
    is_available_in_global_settings,
    make_global_settings_context,
)
from cmk.utils import paths
from cmk.web.utils.urls import makeuri_contextless


class MatchItemGeneratorSettings(ABCMatchItemGenerator):
    def __init__(
        self,
        name: str,
        topic: str,
        *,
        filename: str,
        shows: Callable[[ConfigVariable], bool],
    ) -> None:
        super().__init__(name, provider="setup")
        self._topic: Final[str] = topic
        self._filename: Final[str] = filename
        self._shows: Final = shows

    @override
    def generate_match_items(self, user_permissions: UserPermissions) -> MatchItems:
        # The index serves all users, so it holds every available setting and the
        # permission check happens when a user queries it.
        context = make_global_settings_context(
            edition(paths.omd_root),
            omd_site(),
            sites=active_config.sites,
            graph_timeranges=active_config.graph_timeranges,
        )
        default_values = ABCConfigDomain.get_all_default_globals()
        is_activated = get_global_config().global_settings.is_activated
        for group in sorted(config_variable_group_registry.values(), key=lambda g: g.sort_index()):
            for config_variable in group.config_variables():
                if not self._shows(config_variable):
                    continue
                if not is_available_in_global_settings(
                    config_variable, default_values=default_values, is_activated=is_activated
                ):
                    continue
                yield self._match_item(config_variable, context)

    def _match_item(
        self, config_variable: ConfigVariable, context: GlobalSettingsContext
    ) -> MatchItem:
        title = localize(resolve_title(config_variable.value_model(context))) or _(
            "Untitled setting"
        )
        ident = config_variable.ident()
        return MatchItem(
            title=title,
            topic=self._topic,
            url=makeuri_contextless(request, [("varname", ident)], filename=self._filename),
            match_texts=[title, ident],
        )

    @staticmethod
    @override
    def is_affected_by_change(_change_action_name: str) -> bool:
        return False

    @property
    @override
    def is_localization_dependent(self) -> bool:
        return True
