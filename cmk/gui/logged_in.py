#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disable-error-code="explicit-override, no-any-return, no-untyped-call, no-untyped-def"

"""Manage the currently logged in user"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Container, Sequence
from pathlib import Path
from typing import Any, Final, Literal, NewType, TypedDict

from livestatus import SiteConfigurations

from cmk.ccc import store
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.ccc.version import __version__, Edition, edition, Version

import cmk.utils.paths

from cmk.gui import hooks, permissions, site_config
from cmk.gui.config import active_config
from cmk.gui.ctx_stack import session_attr
from cmk.gui.exceptions import MKAuthException
from cmk.gui.i18n import _
from cmk.gui.type_defs import DismissableWarning, UserSpec
from cmk.gui.utils.permission_verification import BasePerm
from cmk.gui.utils.roles import may_with_roles, roles_of_user
from cmk.gui.utils.selection_id import SelectionId
from cmk.gui.utils.transaction_manager import TransactionManager

from cmk.shared_typing.user_frontend_config import UserFrontendConfig

_logger = logging.getLogger(__name__)
_ContactgroupName = str
UserFileName = Literal[
    "acknowledged_notifications",
    "analyze_notification_display_options",
    "automation_user",
    "avoptions",
    "bi_assumptions",
    "bi_treestate",
    "cached_profile",
    "customer_settings",
    "discovery_checkboxes",
    "discovery_show_discovered_labels",
    "discovery_show_plugin_names",
    "favorites",
    "foldertree",
    "graph_pin",
    "graph_size",
    "help",
    "notification_display_options",
    "parameter_column",
    "parentscan",
    "reporting_timerange",
    "sidebar",
    "sidebar_sites",
    "simulated_event",
    "siteconfig",
    "start_url",
    "tableoptions",
    "test_notification_display_options",
    "transids",
    "treestates",
    "unittest",  # for testing only
    "ui_config",
    "viewoptions",
    "virtual_host_tree",
    "wato_folders_show_labels",
    "wato_folders_show_tags",
]

# a str consisting of `rowselection/` and a SelectionId (uuid)
_RowSelection = NewType("_RowSelection", str)

# a str that is supposed to be "path safe"
UserGraphDataRangeFileName = NewType("UserGraphDataRangeFileName", str)


class UserUIConfig(TypedDict, total=False):
    dismissed_warnings: set[DismissableWarning]


class LoggedInUser:
    """Manage the currently logged-in user

    This objects intention is currently only to handle the currently logged-in user after
    authentication.
    """

    def __init__(
        self,
        user_id: UserId | None,
        *,
        explicitly_given_permissions: Container[str] = frozenset(),
    ) -> None:
        self.id = user_id
        self.transactions = TransactionManager(user_id, self.transids, self.save_transids)

        self.confdir = _confdir_for_user_id(self.id)
        self.role_ids = self._gather_roles(self.id)
        self.attributes: UserSpec = self._load_attributes(self.id, self.role_ids)
        self.alias = self.attributes.get("alias", self.id)
        self.email = self.attributes.get("email", self.id)

        self.explicitly_given_permissions: Final = explicitly_given_permissions
        self._siteconf = self.load_file("siteconfig", {})
        self._button_counts: dict[str, float] = {}
        self._stars: set[str] = set()
        self._tree_states: dict = {}
        self._ui_config: UserUIConfig = self.load_file("ui_config", {})
        self._bi_assumptions: dict[tuple[str, str] | tuple[str, str, str], int] = {}
        self._tableoptions: dict[str, dict[str, Any]] = {}

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.id!r}>"

    @property
    def ident(self) -> UserId:
        """Return the user ID or crash

        Raises:
            ValueError: whenever there is no user_id.
        """
        if self.id is None:
            raise AttributeError("No user_id on this instance.")
        return self.id

    def _gather_roles(self, user_id: UserId | None) -> list[str]:
        return roles_of_user(user_id)

    def _load_attributes(self, user_id: UserId | None, role_ids: list[str]) -> UserSpec:
        if user_id is None:
            return {"roles": role_ids}
        attributes: UserSpec | None = self.load_file("cached_profile", None)
        if attributes is None:
            attributes = active_config.multisite_users.get(
                user_id,
                {
                    "roles": role_ids,
                },
            )

        return attributes

    def get_attribute(self, key: str, deflt: Any = None) -> Any:
        return self.attributes.get(key, deflt)

    def _set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value  # type: ignore[literal-required]

    def _unset_attribute(self, key: str) -> None:
        try:
            del self.attributes[key]  # type: ignore[misc]
        except KeyError:
            pass

    @property
    def language(self) -> str:
        return self.get_attribute("language", active_config.default_language)

    @language.setter
    def language(self, value: str) -> None:
        self._set_attribute("language", value)

    def reset_language(self) -> None:
        self._unset_attribute("language")

    @property
    def automation_user(self) -> bool:
        return self.load_file("automation_user", False)

    @automation_user.setter
    def automation_user(self, value: bool) -> None:
        self.save_file("automation_user", value)

    @property
    def show_mode(self) -> str:
        return self.get_attribute("show_mode") or active_config.show_mode

    @property
    def show_more_mode(self) -> bool:
        return "show_more" in self.show_mode

    @property
    def customer_id(self) -> str | None:
        return self.get_attribute("customer")

    @property
    def contact_groups(self) -> Sequence[_ContactgroupName]:
        return [_ContactgroupName(raw) for raw in self.get_attribute("contactgroups", [])]

    @property
    def start_url(self) -> str | None:
        return self.load_file("start_url", None)

    @property
    def inline_help_as_text(self) -> bool:
        return self.load_file("help", False)

    @inline_help_as_text.setter
    def inline_help_as_text(self, value: bool) -> None:
        self.save_file("help", value)

    @property
    def frontend_config(self) -> UserFrontendConfig:
        warnings = self.dismissed_warnings
        return UserFrontendConfig(
            hide_contextual_help_icon=(
                self.get_attribute("contextual_help_icon") == "hide_icon" or None
            ),
            dismissed_warnings=[str(w) for w in warnings] if warnings else None,
        )

    @property
    def dismissed_warnings(self) -> set[DismissableWarning] | None:
        return self._ui_config.get("dismissed_warnings", set())

    @dismissed_warnings.setter
    def dismissed_warnings(self, values: set[DismissableWarning] | None) -> None:
        if not values:
            if "dismissed_warnings" in self._ui_config:
                del self._ui_config["dismissed_warnings"]
            if len(self._ui_config.keys()) == 0:
                self.remove_file("ui_config")
        else:
            self._ui_config["dismissed_warnings"] = values
            self.save_file("ui_config", self._ui_config)

    @property
    def acknowledged_notifications(self) -> int:
        return self.load_file("acknowledged_notifications", 0)

    @acknowledged_notifications.setter
    def acknowledged_notifications(self, value: int) -> None:
        self.save_file("acknowledged_notifications", value)

    @property
    def discovery_checkboxes(self) -> bool:
        return self.load_file("discovery_checkboxes", False)

    @discovery_checkboxes.setter
    def discovery_checkboxes(self, value: bool) -> None:
        self.save_file("discovery_checkboxes", value)

    @property
    def parameter_column(self) -> bool:
        return self.load_file("parameter_column", False)

    @parameter_column.setter
    def parameter_column(self, value: bool) -> None:
        self.save_file("parameter_column", value)

    @property
    def discovery_show_discovered_labels(self) -> bool:
        return self.load_file("discovery_show_discovered_labels", False)

    @discovery_show_discovered_labels.setter
    def discovery_show_discovered_labels(self, value: bool) -> None:
        self.save_file("discovery_show_discovered_labels", value)

    @property
    def discovery_show_plugin_names(self) -> bool:
        return self.load_file("discovery_show_plugin_names", False)

    @discovery_show_plugin_names.setter
    def discovery_show_plugin_names(self, value: bool) -> None:
        self.save_file("discovery_show_plugin_names", value)

    @property
    def wato_folders_show_tags(self) -> bool:
        return self.load_file("wato_folders_show_tags", False)

    @wato_folders_show_tags.setter
    def wato_folders_show_tags(self, value: bool) -> None:
        self.save_file("wato_folders_show_tags", value)

    @property
    def wato_folders_show_labels(self) -> bool:
        return self.load_file("wato_folders_show_labels", False)

    @wato_folders_show_labels.setter
    def wato_folders_show_labels(self, value: bool) -> None:
        self.save_file("wato_folders_show_labels", value)

    @property
    def bi_expansion_level(self) -> int:
        return self.load_file("bi_treestate", (0,))[0]

    @bi_expansion_level.setter
    def bi_expansion_level(self, value: int) -> None:
        self.save_file("bi_treestate", (value,))

    @property
    def stars(self) -> set[str]:
        if not self._stars:
            self._stars = set(self.load_file("favorites", []))
        return self._stars

    def save_stars(self) -> None:
        self.save_file("favorites", list(self._stars))

    @property
    def tree_states(self) -> dict:
        if not self._tree_states:
            self._tree_states = self.load_file("treestates", {})
        return self._tree_states

    def get_tree_states(self, tree):
        return self.tree_states.get(tree, {})

    def get_tree_state(self, treename: str, id_: str, isopen: bool) -> bool:
        # try to get persisted state of tree
        tree_state = self.get_tree_states(treename)

        if id_ in tree_state:
            isopen = tree_state[id_] == "on"
        return isopen

    def set_tree_state(self, tree, key, val):
        if tree not in self.tree_states:
            self.tree_states[tree] = {}

        self.tree_states[tree][key] = val

    def set_tree_states(self, tree, val):
        self.tree_states[tree] = val

    def save_tree_states(self) -> None:
        self.save_file("treestates", self._tree_states)

    def get_show_more_setting(self, more_id: str) -> bool:
        if self.show_mode == "enforce_show_more":
            return True

        return self.get_tree_state(
            treename="more_buttons",
            id_=more_id,
            isopen=self.show_mode == "default_show_more",
        )

    @property
    def bi_assumptions(self):
        if not self._bi_assumptions:
            self._bi_assumptions = self.load_file("bi_assumptions", {})
        return self._bi_assumptions

    def save_bi_assumptions(self):
        self.save_file("bi_assumptions", self._bi_assumptions)

    @property
    def tableoptions(self) -> dict[str, dict[str, Any]]:
        if not self._tableoptions:
            self._tableoptions = self.load_file("tableoptions", {})
        return self._tableoptions

    def save_tableoptions(self) -> None:
        self.save_file("tableoptions", self._tableoptions)

    def get_rowselection(self, selection_id: SelectionId, identifier: str) -> list[str]:
        vo = self.load_file(_RowSelection(f"rowselection/{selection_id}"), {})
        return vo.get(identifier, [])

    def set_rowselection(
        self, selection_id: SelectionId, identifier: str, rows: list[str], action: str
    ) -> None:
        row_selection = _RowSelection(f"rowselection/{selection_id}")
        vo = self.load_file(row_selection, {}, lock=True)

        if action == "set":
            vo[identifier] = rows

        elif action == "add":
            vo[identifier] = list(set(vo.get(identifier, [])).union(rows))

        elif action == "del":
            vo[identifier] = list(set(vo.get(identifier, [])) - set(rows))

        elif action == "unset":
            del vo[identifier]

        self.save_file(row_selection, vo)

    def cleanup_old_selections(self) -> None:
        # Delete all selection files older than the defined livetime.
        if self.confdir is None:
            return

        path = self.confdir / "rowselection"
        try:
            for f in os.listdir(path):
                if f[1] != "." and f.endswith(".mk"):
                    p = path / f
                    if time.time() - p.stat().st_mtime > active_config.selection_livetime:
                        p.unlink()
        except OSError:
            pass  # no directory -> no cleanup

    def get_sidebar_configuration(self, default: dict[str, Any]) -> dict[str, Any]:
        return self.load_file("sidebar", default)

    def set_sidebar_configuration(self, configuration: dict[str, Any]) -> None:
        self.save_file("sidebar", configuration)

    def is_site_disabled(self, site_id: SiteId) -> bool:
        return self._siteconf.get(site_id, {}).get("disabled", False)

    def disable_site(self, site_id: SiteId) -> None:
        self._siteconf.setdefault(site_id, {})["disabled"] = True

    def enable_site(self, site_id: SiteId) -> None:
        self._siteconf.setdefault(site_id, {}).pop("disabled", None)

    def save_site_config(self) -> None:
        self.save_file("siteconfig", self._siteconf)

    def transids(self, lock: bool = False) -> list[str]:
        return self.load_file("transids", [], lock=lock)

    def save_transids(self, transids: list[str]) -> None:
        if self.id:
            self.save_file("transids", transids)

    def authorized_sites(
        self, unfiltered_sites: SiteConfigurations | None = None
    ) -> SiteConfigurations:
        if unfiltered_sites is None:
            unfiltered_sites = site_config.enabled_sites()

        authorized_sites = self.get_attribute("authorized_sites")
        if authorized_sites is None:
            return SiteConfigurations(dict(unfiltered_sites))

        return SiteConfigurations(
            {
                site_id: s
                for site_id, s in unfiltered_sites.items()
                if site_id in authorized_sites  #
            }
        )

    def may(self, pname: str) -> bool:
        they_may = (pname in self.explicitly_given_permissions) or may_with_roles(
            self.role_ids, pname
        )
        hooks.call("permission-checked", pname)
        return they_may

    def need_permission(self, permission: str | BasePerm) -> None:
        if isinstance(permission, BasePerm):
            for p in permission.iter_perms():
                self.need_permission(p.name)
            return

        if not self.may(permission):
            perm = permissions.permission_registry[permission]
            raise MKAuthException(
                _(
                    "We are sorry, but you lack the permission "
                    "for this operation. If you do not like this "
                    "then please ask your administrator to provide you with "
                    "the following permission: '<b>%s</b>'."
                )
                % perm.title
            )

    def load_file(
        self,
        name: UserFileName | _RowSelection | UserGraphDataRangeFileName,
        deflt: Any,
        lock: bool = False,
    ) -> Any:
        if self.confdir is None:
            return deflt

        path = self.confdir / (name + ".mk")

        # The user files we load with this function are mostly some kind of persisted states.  In
        # case a file is corrupted for some reason we rather start over with the default instead of
        # failing at some random places.
        try:
            return store.load_object_from_file(path, default=deflt, lock=lock)
        except (ValueError, SyntaxError):
            return deflt

    def save_file(
        self, name: UserFileName | _RowSelection | UserGraphDataRangeFileName, content: object
    ) -> None:
        assert self.id is not None
        save_user_file(name, content, self.id)

    def remove_file(self, name: UserFileName) -> None:
        assert self.id is not None
        path = cmk.utils.paths.profile_dir.joinpath(self.id, name + ".mk")
        path.unlink(missing_ok=True)

    def file_modified(self, name: str) -> float:
        if self.confdir is None:
            return 0

        try:
            return (self.confdir / (name + ".mk")).stat().st_mtime
        except FileNotFoundError:
            return 0

    def get_docs_base_url(self) -> str:
        version = (
            "saas"
            if edition(cmk.utils.paths.omd_root) == Edition.CSE
            else Version.from_str(__version__).version_base or "master"
        )
        language = "de" if self.language == "de" else "en"
        return f"https://docs.checkmk.com/{version}/{language}"


# Login a user that has all permissions. This is needed for making
# Livestatus queries from unauthentiated page handlers
# TODO: Can we somehow get rid of this?
class LoggedInSuperUser(LoggedInUser):
    def __init__(self) -> None:
        super().__init__(None)
        self.alias = "Superuser for internal use"
        self.email = "admin"

    def _gather_roles(self, _user_id: UserId | None) -> list[str]:
        return ["admin"]

    def save_file(self, name: str, content: Any) -> None:
        raise TypeError("The profiles of LoggedInSuperUser cannot be saved")


class LoggedInRemoteSite(LoggedInUser):
    def __init__(self, *, site_name: str) -> None:
        super().__init__(None)
        self.alias = f"Remote site {site_name}"
        self.email = "?"
        self.site_name = site_name

    def _gather_roles(self, _user_id: UserId | None) -> list[str]:
        return ["no_permissions"]

    def save_file(self, name: str, content: Any) -> None:
        raise TypeError("The profiles of LoggedInRemoteSite cannot be saved")


class LoggedInNobody(LoggedInUser):
    def __init__(self) -> None:
        super().__init__(None)
        self.alias = "Unauthenticated user"
        self.email = "nobody"

    def _gather_roles(self, _user_id: UserId | None) -> list[str]:
        return []

    def save_file(self, name: str, content: Any) -> None:
        raise TypeError("The profiles of LoggedInNobody cannot be saved")


def _confdir_for_user_id(user_id: UserId | None) -> Path | None:
    if user_id is None:
        return None

    confdir = cmk.utils.paths.profile_dir / user_id
    confdir.mkdir(mode=0o770, exist_ok=True)
    return confdir


def save_user_file(name: str, data: Any, user_id: UserId) -> None:
    path = cmk.utils.paths.profile_dir / user_id / (name + ".mk")
    path.parent.mkdir(mode=0o770, exist_ok=True)
    store.save_object_to_file(path, data)


user: LoggedInUser = session_attr("user", LoggedInUser)
