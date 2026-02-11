#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc

from cmk.gui.config import Config, default_authorized_builtin_role_ids
from cmk.gui.logged_in import user
from cmk.gui.pages import PageHandler
from cmk.gui.type_defs import PermissionName, RoleName
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.valuespec import ValueSpec

PageHandlers = dict[str, PageHandler]


# TODO: Transform methods to class methods
class SidebarSnapin(abc.ABC):
    """Abstract base class for all sidebar snap-ins"""

    @classmethod
    @abc.abstractmethod
    def type_name(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def title(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def description(cls) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def show(self, config: Config) -> None:
        raise NotImplementedError()

    @classmethod
    def has_show_more_items(cls) -> bool:
        return False

    @classmethod
    def refresh_regularly(cls) -> bool:
        return False

    @classmethod
    def refresh_on_restart(cls) -> bool:
        return False

    @classmethod
    def is_custom_snapin(cls) -> bool:
        """Whether or not a snap-in type is a customized snap-in"""
        return False

    @classmethod
    def permission_name(cls) -> PermissionName:
        return "sidesnap.%s" % cls.type_name()

    @classmethod
    def allowed_roles(cls) -> list[RoleName]:
        return default_authorized_builtin_role_ids

    @classmethod
    def may_see(cls, user_permissions: UserPermissions) -> bool:
        return user.may(cls.permission_name())

    @classmethod
    def included_in_default_sidebar(cls) -> bool:
        """Determine if this snapin should be included in the default sidebar configuration.

        This method allows snapins to control whether they appear in the default sidebar
        for users who don't have a saved configuration. Most snapins should return True
        (always included by default), but specific snapins can override this to implement
        custom logic based on user attributes or other conditions.

        Returns:
            True if the snapin should be included in default sidebar, False otherwise.
        """
        return True

    def styles(self) -> str | None:
        return None

    def page_handlers(self) -> PageHandlers:
        return {}


class CustomizableSidebarSnapin(SidebarSnapin, abc.ABC):
    """Parent for all user configurable sidebar snap-ins

    Subclass this class in case you want to implement a sidebar snap-in type that can
    be customized by the user"""

    @classmethod
    @abc.abstractmethod
    def vs_parameters(cls) -> list[tuple[str, ValueSpec[object]]]:
        """The Dictionary() elements to be used for configuring the parameters"""
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def parameters(cls) -> object:
        """Default set of parameters to be used for the uncustomized snap-in"""
        raise NotImplementedError()
