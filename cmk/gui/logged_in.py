#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Manage the currently logged in user"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Container, Sequence
from typing import Any, Final

from livestatus import SiteConfigurations, SiteId

from cmk.ccc import store
from cmk.ccc.version import __version__, Edition, edition, Version

import cmk.utils.paths
from cmk.utils.user import UserId

from cmk.gui import hooks, permissions, site_config
from cmk.gui.config import active_config
from cmk.gui.ctx_stack import session_attr
from cmk.gui.exceptions import MKAuthException
from cmk.gui.i18n import _
from cmk.gui.utils.permission_verification import BasePerm
from cmk.gui.utils.roles import may_with_roles, roles_of_user
from cmk.gui.utils.transaction_manager import TransactionManager

_logger = logging.getLogger(__name__)
_ContactgroupName = str


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
        self._attributes = self._load_attributes(self.id, self.role_ids)
        self.alias = self._attributes.get("alias", self.id)
        self.email = self._attributes.get("email", self.id)

        self.explicitly_given_permissions: Final = explicitly_given_permissions
        self._siteconf = self.load_file("siteconfig", {})
        self._button_counts: dict[str, float] = {}
        self._stars: set[str] = set()
        self._tree_states: dict = {}
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

    def _load_attributes(self, user_id: UserId | None, role_ids: list[str]) -> Any:
        if user_id is None:
            return {"roles": role_ids}
        attributes = self.load_file("cached_profile", None)
        if attributes is None:
            attributes = active_config.multisite_users.get(
                user_id,
                {
                    "roles": role_ids,
                },
            )
        return attributes

    def get_attribute(self, key: str, deflt: Any = None) -> Any:
        return self._attributes.get(key, deflt)

    def _set_attribute(self, key: str, value: Any) -> None:
        self._attributes[key] = value

    def _unset_attribute(self, key: str) -> None:
        try:
            del self._attributes[key]
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
    def show_help(self) -> bool:
        return self.load_file("help", False)

    @show_help.setter
    def show_help(self, value: bool) -> None:
        self.save_file("help", value)

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

    def get_rowselection(self, selection_id: str, identifier: str) -> list[str]:
        vo = self.load_file("rowselection/%s" % selection_id, {})
        return vo.get(identifier, [])

    def set_rowselection(
        self, selection_id: str, identifier: str, rows: list[str], action: str
    ) -> None:
        vo = self.load_file("rowselection/%s" % selection_id, {}, lock=True)

        if action == "set":
            vo[identifier] = rows

        elif action == "add":
            vo[identifier] = list(set(vo.get(identifier, [])).union(rows))

        elif action == "del":
            vo[identifier] = list(set(vo.get(identifier, [])) - set(rows))

        elif action == "unset":
            del vo[identifier]

        self.save_file("rowselection/%s" % selection_id, vo)

    def cleanup_old_selections(self) -> None:
        # Delete all selection files older than the defined livetime.
        if self.confdir is None:
            return

        path = self.confdir + "/rowselection"
        try:
            for f in os.listdir(path):
                if f[1] != "." and f.endswith(".mk"):
                    p = path + "/" + f
                    if time.time() - os.stat(p).st_mtime > active_config.selection_livetime:
                        os.unlink(p)
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

    def authorized_login_sites(self) -> SiteConfigurations:
        login_site_ids = site_config.get_login_slave_sites()
        return self.authorized_sites(
            SiteConfigurations(
                {
                    site_id: s
                    for site_id, s in site_config.enabled_sites().items()
                    if site_id in login_site_ids  #
                }
            )
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

    def load_file(self, name: str, deflt: Any, lock: bool = False) -> Any:
        if self.confdir is None:
            return deflt

        path = self.confdir + "/" + name + ".mk"

        # The user files we load with this function are mostly some kind of persisted states.  In
        # case a file is corrupted for some reason we rather start over with the default instead of
        # failing at some random places.
        try:
            return store.load_object_from_file(path, default=deflt, lock=lock)
        except (ValueError, SyntaxError):
            return deflt

    def save_file(self, name: str, content: Any) -> None:
        assert self.id is not None
        save_user_file(name, content, self.id)

    def file_modified(self, name: str) -> float:
        if self.confdir is None:
            return 0

        try:
            return os.stat(self.confdir + "/" + name + ".mk").st_mtime
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


def _confdir_for_user_id(user_id: UserId | None) -> str | None:
    if user_id is None:
        return None

    confdir = cmk.utils.paths.profile_dir / user_id
    store.mkdir(confdir)
    return str(confdir)


def save_user_file(name: str, data: Any, user_id: UserId) -> None:
    path = cmk.utils.paths.profile_dir.joinpath(user_id, name + ".mk")
    store.mkdir(path.parent)
    store.save_object_to_file(path, data)


user: LoggedInUser = session_attr("user", LoggedInUser)
