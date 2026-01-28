#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disallow-untyped-defs
# mypy: disallow-incomplete-defs
# mypy: disallow-untyped-decorators

# TODO:
# - The classes here mix two things:
#   a) Manager/Container classes
#   b) The object classes
#   This is done by a lot of classmethods where some have even have a
#   comment "don't override this". It would be much clearer to split
#   this into separate classes.
# - The classes are more used as namespaces (lot of classmethods).
#   It would be easier to understand what's happening here when we
#   used real instances. We could - for example - add a single instance
#   per type to the page_types dictionary. Or add some management object
#   for this

from __future__ import annotations

import abc
import copy
import json
import os
from collections.abc import Iterator, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, replace
from typing import Generic, Literal, Self, TypeVar

from pydantic import BaseModel as PydanticBaseModel

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.version import Edition, edition

import cmk.utils.paths
from cmk.utils.user import UserId

import cmk.gui.pages
from cmk.gui import userdb, weblib
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_main_menu_breadcrumb
from cmk.gui.config import default_authorized_builtin_role_ids
from cmk.gui.default_name import unique_default_name_suggestion
from cmk.gui.default_permissions import PermissionSectionGeneral
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _, _l, _u
from cmk.gui.logged_in import LoggedInUser, save_user_file, user
from cmk.gui.main_menu import mega_menu_registry, MegaMenuRegistry
from cmk.gui.page_menu import (
    doc_reference_to_page_menu,
    make_confirmed_form_submit_link,
    make_external_link,
    make_form_submit_link,
    make_javascript_link,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuLink,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.pages import Page
from cmk.gui.permissions import (
    declare_dynamic_permissions,
    declare_permission_section,
    Permission,
    permission_registry,
    permission_section_registry,
)
from cmk.gui.table import init_rowselect, Table, table_element
from cmk.gui.type_defs import (
    AnnotatedUserId,
    HTTPVariables,
    Icon,
    MegaMenu,
    PermissionName,
    TopicMenuItem,
    TopicMenuTopic,
    Visual,
)
from cmk.gui.user_sites import get_configured_site_choices
from cmk.gui.utils.flashed_messages import flash, get_flashed_messages
from cmk.gui.utils.html import HTML
from cmk.gui.utils.ntop import is_ntop_configured
from cmk.gui.utils.roles import is_user_with_publish_permissions, user_may
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link, makeactionuri, makeuri, makeuri_contextless
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.validate import validate_id
from cmk.gui.valuespec import (
    CascadingDropdown,
    CascadingDropdownChoice,
    Checkbox,
    Dictionary,
    DropdownChoice,
    DualListChoice,
    FixedValue,
    IconSelector,
    ID,
    Integer,
    Optional,
    TextAreaUnicode,
    TextInput,
    ValueSpec,
)
from cmk.gui.watolib.groups_io import all_groups

SubPagesSpec = list[tuple[str, str, str]]
PagetypePhrase = Literal["title", "title_plural", "add_to", "clone", "create", "edit", "new"]
# Three possible modes:
# "create" -> create completely new page
# "clone"  -> like new, but prefill form with values from existing page
# "edit"   -> edit existing page
PageMode = Literal["create", "clone", "edit"]


class BaseModel(PydanticBaseModel):
    name: str
    title: str
    description: str = ""


@dataclass(kw_only=True)
class BaseConfig:
    name: str
    title: str
    description: str = ""


class OverridableModel(BaseModel):
    owner: AnnotatedUserId
    public: bool | tuple[Literal["contact_groups", "sites"], Sequence[str]] | None
    hidden: bool = False  # TODO: Seems it is not configurable through the UI. Is it OK?


@dataclass(kw_only=True)
class OverridableConfig(BaseConfig):
    owner: UserId
    public: bool | tuple[Literal["contact_groups", "sites"], Sequence[str]] | None
    hidden: bool = False  # TODO: Seems it is not configurable through the UI. Is it OK?


ElementSpec = dict


class OverridableContainerModel(OverridableModel):
    # TODO: Specify element types. Can we make use of the generic typed dicts here?
    elements: list[ElementSpec] = []


@dataclass(kw_only=True)
class OverridableContainerConfig(OverridableConfig):
    # TODO: Specify element types. Can we make use of the generic typed dicts here?
    elements: list[ElementSpec]


class PageRendererModel(OverridableContainerModel):
    topic: str
    sort_index: int
    is_show_more: bool


@dataclass(kw_only=True)
class PageRendererConfig(OverridableContainerConfig):
    topic: str
    sort_index: int
    is_show_more: bool


class PagetypeTopicModel(OverridableModel):
    icon_name: str
    sort_index: int
    max_entries: int = 10
    hide: bool = False  # TODO: Seems it is not configurable through the UI. Is it OK?


@dataclass(kw_only=True)
class PagetypeTopicConfig(OverridableConfig):
    icon_name: str
    sort_index: int
    max_entries: int = 10
    hide: bool = False  # TODO: Seems it is not configurable through the UI. Is it OK?


def register(mega_menu_registry_: MegaMenuRegistry) -> None:
    mega_menu_registry_.register(
        MegaMenu(
            name="customize",
            title=_l("Customize"),
            icon="main_customize",
            sort_index=10,
            topics=_customize_menu_topics,
            hide=hide_customize_menu,
        )
    )


#   .--Base----------------------------------------------------------------.
#   |                        ____                                          |
#   |                       | __ )  __ _ ___  ___                          |
#   |                       |  _ \ / _` / __|/ _ \                         |
#   |                       | |_) | (_| \__ \  __/                         |
#   |                       |____/ \__,_|___/\___|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Base class of all things that are UserOverridable, ElementContainer |
#   |  or PageRenderer.                                                    |
#   '----------------------------------------------------------------------'

_T_BaseConfig = TypeVar("_T_BaseConfig", bound=BaseConfig)


class Base(abc.ABC, Generic[_T_BaseConfig]):
    def __init__(self, config: _T_BaseConfig) -> None:
        self.config = config

    @classmethod
    @abc.abstractmethod
    def deserialize(cls, page_dict: Mapping[str, object]) -> Self: ...

    @abc.abstractmethod
    def serialize(self) -> dict[str, object]: ...

    # You always must override the following method. Not all phrases
    # might be necessary depending on the type of you page.
    # Possible phrases:
    # "title"        : Title of one instance
    # "title_plural" : Title in plural
    # "add_to"       : Text like "Add to foo bar..."
    # TODO: Refactor this to different indepentent class methods. For example
    # the "add_to" phrase is not relevant for non container elements. In the
    # moment we use dedicated methods, wrong usage will be found by pylint.
    @classmethod
    def phrase(cls, phrase: PagetypePhrase) -> str:
        return _("MISSING '%s'") % phrase

    @classmethod
    def parameters(cls, mode: PageMode) -> list[tuple[str, list[tuple[float, str, ValueSpec]]]]:
        """Defines the parameter to be configurable by the user when editing this object

        Implement this function in a subclass in order to add parameters to be editable by
        the user when editing the details of such page type.
        """
        return [
            (
                _("General properties"),
                [
                    (
                        1.1,
                        "name",
                        ID(
                            title=_("Unique ID"),
                            help=_(
                                "The ID will be used do identify this page in URLs. If this page has the "
                                "same ID as a built-in page of the type <i>%s</i> then it will shadow the built-in one."
                            )
                            % cls.phrase("title"),
                            allow_empty=False,
                        ),
                    ),
                    (
                        1.2,
                        "title",
                        TextInput(
                            title=_("Title") + "<sup>*</sup>",
                            size=50,
                            allow_empty=False,
                        ),
                    ),
                    (
                        1.3,
                        "description",
                        TextAreaUnicode(
                            title=_("Description") + "<sup>*</sup>",
                            help=_(
                                "The description is optional and can be used for explanations or documentation"
                            ),
                            rows=4,
                            cols=50,
                        ),
                    ),
                ],
            )
        ]

    # Define page handlers for the necessary pages. This is being called (indirectly)
    # in index.py. That way we do not need to hard code page handlers for all types of
    # PageTypes in plugins/pages. It is simply sufficient to register a PageType and
    # all page handlers will exist :-)
    @classmethod
    def page_handlers(cls) -> dict[str, cmk.gui.pages.PageHandlerFunc]:
        return {}

    # Object methods that *can* be overridden - for cases where
    # that pages in question of a dictionary format that is not
    # compatible.
    def name(self) -> str:
        return self.config.name

    def title(self) -> str:
        return self.config.title

    def description(self) -> str:
        return self.config.description

    def is_hidden(self) -> bool:
        return False

    def is_empty(self) -> bool:
        return False

    def _show_in_sidebar(self) -> bool:
        return not self.is_empty() and not self.is_hidden()

    @classmethod
    def default_topic(cls) -> str:
        return "other"

    @classmethod
    def type_is_show_more(cls) -> bool:
        """Whether or not this page type should be treated as element in the
        navigation only shown on show more button"""
        return False

    @classmethod
    @abc.abstractmethod
    def type_name(cls) -> str: ...

    @classmethod
    @abc.abstractmethod
    def type_icon(cls) -> Icon: ...


# .
#   .--Overridable---------------------------------------------------------.
#   |         ___                      _     _       _     _               |
#   |        / _ \__   _____ _ __ _ __(_) __| | __ _| |__ | | ___          |
#   |       | | | \ \ / / _ \ '__| '__| |/ _` |/ _` | '_ \| |/ _ \         |
#   |       | |_| |\ V /  __/ |  | |  | | (_| | (_| | |_) | |  __/         |
#   |        \___/  \_/ \___|_|  |_|  |_|\__,_|\__,_|_.__/|_|\___|         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Base class for things that the user can override by cloning and     |
#   |  editing and where the user might also create complete new types.    |
#   |  Examples: views, dashboards, graphs collections                     |
#   '----------------------------------------------------------------------'

_T_OverridableConfig = TypeVar("_T_OverridableConfig", bound=OverridableConfig)
_T = TypeVar("_T", bound="Overridable")

InstanceId = tuple[UserId, str]


class OverridableInstances(Generic[_T]):
    def __init__(self) -> None:
        self.__instances: dict[InstanceId, _T] = {}

    def clear_instances(self) -> None:
        self.__instances = {}

    def add_instance(self, key: InstanceId, instance: _T) -> None:
        self.__instances[key] = instance

    def remove_instance(self, key: InstanceId) -> None:
        del self.__instances[key]

    def instances(self) -> list[_T]:
        """Return a list of all instances of this type"""
        return list(self.__instances.values())

    def instance(self, key: InstanceId) -> _T:
        return self.__instances[key]

    def has_instance(self, key: InstanceId) -> bool:
        return key in self.__instances

    def instances_dict(self) -> dict[InstanceId, _T]:
        return self.__instances

    def instances_sorted(self) -> list[_T]:
        return sorted(self.__instances.values(), key=lambda x: x.title())

    def permitted_instances_sorted(self) -> list[_T]:
        return [i for i in self.instances_sorted() if i.is_permitted()]

    def add_page(self, new_page: _T) -> None:
        self.add_instance((new_page.owner(), new_page.name()), new_page)

    @request_memoize(maxsize=4096)
    def find_page(self, name: str) -> _T | None:
        """Find a page by name, implements shadowing and publishing und overriding by admins"""
        mine = None
        forced = None
        builtin = None
        foreign = None

        for page in self.instances():
            if page.name() != name:
                continue

            if page.is_mine_and_may_have_own():
                mine = page

            elif page.is_published_to_me() and page.may_see():
                if page.is_public_forced():
                    forced = page
                else:
                    foreign = page
            elif page.is_builtin():
                builtin = page

        if mine:
            return mine
        if forced:
            return forced
        if builtin:
            return builtin
        if foreign:
            return foreign
        return None

    def find_foreign_page(self, owner: UserId, name: str) -> _T | None:
        try:
            return self.instance((UserId(owner), name))
        except KeyError:
            return None

    def pages(self) -> list[_T]:
        """Return all pages visible to the user, implements shadowing etc."""
        pages = {}

        # Built-in pages
        for page in self.instances():
            if page.is_published_to_me() and page.may_see() and page.is_builtin():
                pages[page.name()] = page

        # Public pages by normal other users
        for page in self.instances():
            if page.is_published_to_me() and page.may_see():
                pages[page.name()] = page

        # Public pages by admin users, forcing their versions over others
        for page in self.instances():
            if page.is_published_to_me() and page.may_see() and page.is_public_forced():
                pages[page.name()] = page

        # My own pages
        for page in self.instances():
            if page.is_mine_and_may_have_own():
                pages[page.name()] = page

        return sorted(pages.values(), key=lambda x: x.title())

    def page_choices(self) -> list[tuple[str, str]]:
        return [(page.name(), page.title()) for page in self.pages()]


class Overridable(Base[_T_OverridableConfig]):
    # Default values for the creation dialog can be overridden by the
    # sub class.
    @classmethod
    def default_name(cls, instances: OverridableInstances[Self]) -> str:
        return unique_default_name_suggestion(
            cls.type_name(),
            (instance.name() for instance in instances.instances()),
        )

    @classmethod
    def parameters(cls, mode: PageMode) -> list[tuple[str, list[tuple[float, str, ValueSpec]]]]:
        parameters = super().parameters(mode)

        if is_user_with_publish_permissions("pagetype", user.id, cls.type_name()):
            vs_visibility: ValueSpec = Optional(
                title=_("Visibility"),
                label=_("Make this %s available for other users") % cls.phrase("title").lower(),
                none_label=_("Don't publish to other users"),
                valuespec=PublishTo(
                    publish_all=cls.has_overriding_permission("publish"),
                    publish_groups=cls.has_overriding_permission("publish_to_groups"),
                    publish_sites=cls.has_overriding_permission("publish_to_sites"),
                    type_title=cls.phrase("title"),
                    title="",
                    with_foreign_groups=cls.has_overriding_permission("publish_to_foreign_groups"),
                ),
            )
        else:
            vs_visibility = vs_no_permission_to_publish(
                type_title=cls.phrase("title"),
                title=_("Visibility"),
            )

        return parameters + [
            (
                _("General properties"),
                [
                    (2.2, "public", vs_visibility),
                ],
            ),
        ]

    @classmethod
    def page_handlers(cls) -> dict[str, cmk.gui.pages.PageHandlerFunc]:
        handlers = super().page_handlers()
        handlers.update(
            {
                "%ss" % cls.type_name(): lambda: ListPage(cls).page(),
                "edit_%s" % cls.type_name(): lambda: EditPage(cls).page(),
            }
        )
        return handlers

    def page_header(self) -> str:
        header = self.phrase("title") + " - " + self.title()
        if not self.is_mine():
            header += " (%s)" % self.owner()
        return header

    def is_public(self) -> bool:
        """Checks whether a page is visible to other users than the owner.

        This does not only need a flag in the page itself, but also the
        permission from its owner to publish it."""
        return False if not self.config.public else self.publish_is_allowed()

    def publish_is_allowed(self) -> bool:
        """Whether publishing an element to other users is allowed by the owner"""
        return not self.owner() or is_user_with_publish_permissions(
            "pagetype", self.owner(), self.type_name()
        )

    def is_public_forced(self) -> bool:
        """Whether the user is allowed to override built-in pagetypes"""
        return self.is_public() and user_may(self.owner(), "general.force_" + self.type_name())

    def is_published_to_me(self) -> bool:
        """Whether the page is published to the currently active user"""
        if not user.may("general.see_user_%s" % self.type_name()):
            return False

        if self.config.public is True:
            return self.publish_is_allowed()

        if isinstance(self.config.public, tuple):
            if set(user.contact_groups).intersection(self.config.public[1]):
                return self.publish_is_allowed()

        return False

    def is_hidden(self) -> bool:
        return self.config.hidden

    def is_builtin(self) -> bool:
        return not self.owner()

    def is_mine(self) -> bool:
        return self.owner() == user.id

    def is_mine_and_may_have_own(self) -> bool:
        return self.is_mine() and user.may("general.edit_" + self.type_name())

    def render_title(self, instances: OverridableInstances[Self]) -> str | HTML:
        return _u(self.title())

    def _can_be_linked(self, instances: OverridableInstances[Self]) -> bool:
        """Whether or not the thing can be linked to"""
        if self.is_mine():
            return True

        # Is this the visual which would be shown to the user in case the user
        # requests a visual with the current name?
        page = instances.find_page(self.name())
        if page and page.owner() != self.owner():
            return False

        return self.is_published_to_me()

    @classmethod
    def _delete_permission(cls) -> PermissionName:
        return "general.edit_" + cls.type_name()

    def owner(self) -> UserId:
        return self.config.owner

    # Checks if the current user is allowed to see a certain page
    # TODO: Wie is die Semantik hier genau? Umsetzung vervollständigen!
    def may_see(self) -> bool:
        perm_name = f"{self.type_name()}.{self.name()}"
        if perm_name in permission_registry and not user.may(perm_name):
            return False

        # if self.owner() == "" and not user.may(perm_name):
        #    return False

        return True
        #    continue # not allowed to see this view

        # TODO: Permissions
        # ## visual = visuals[(owner, visual_name)]
        # ## if owner == user.id or \
        # ##    (visual["public"] and owner != '' and user_may(owner, "general.publish_" + what)):
        # ##     custom.append((owner, visual_name, visual))
        # ## elif visual["public"] and owner == "":
        # ##     builtin.append((owner, visual_name, visual))

    # TODO: Shouldn't this be `may_see` and `may_see` should be some internal helper to be used
    # together with `is_mine`?
    def is_permitted(self) -> bool:
        """Whether or not a user is allowed to see an instance

        Same logic as `permitted_instances_sorted`."""
        return (
            (self.is_builtin() and self.may_see())
            or (self.is_mine() and self.may_see())
            or (not self.is_mine() and self.is_published_to_me() and self.may_see())
        )

    def may_delete(self) -> bool:
        if self.is_builtin():
            return False
        if self.is_mine() and user.may(self._delete_permission()):
            return True
        return user.may("general.delete_foreign_%s" % self.type_name())

    def may_edit(self) -> bool:
        if self.is_builtin():
            return False
        if self.is_mine() and user.may("general.edit_%s" % self.type_name()):
            return True
        return user.may("general.edit_foreign_%s" % self.type_name())

    def edit_url(self) -> str:
        http_vars: HTTPVariables = [("load_name", self.name())]
        if not self.is_mine():
            http_vars.append(("owner", self.owner()))

        return makeuri_contextless(request, http_vars, filename="edit_%s.py" % self.type_name())

    def clone_url(self) -> str:
        return makeuri_contextless(
            request,
            [
                ("owner", self.owner()),
                ("load_name", self.name()),
                ("mode", "clone"),
                ("back", makeuri_contextless(request, [])),
            ],
            filename="edit_%s.py" % self.type_name(),
        )

    def delete_url(self) -> str:
        add_vars: HTTPVariables = [("_delete", self.name())]
        if not self.is_mine():
            add_vars.append(("_owner", self.owner()))

        assert user.id is not None

        confirm_message = _("ID: %s") % self.name()
        if not self.is_mine():
            confirm_message += "<br>" + _("Owner: %s") % self.owner()

        return make_confirm_delete_link(
            url=makeactionuri(request, transactions, add_vars),
            title=_("Delete %s") % self.phrase("title").lower(),
            suffix=self.title(),
            message=confirm_message,
        )

    @classmethod
    def create_url(cls) -> str:
        return "edit_%s.py?mode=create" % cls.type_name()

    @classmethod
    def list_url(cls) -> str:
        return "%ss.py" % cls.type_name()

    def after_create_url(self) -> str | None:
        return None  # where redirect after a create should go

    @classmethod
    def page_menu_entry_list(cls) -> Iterator[PageMenuEntry]:
        yield PageMenuEntry(
            title=cls.phrase("title_plural"),
            icon_name=cls.type_name(),
            item=make_simple_link(cls.list_url()),
        )

    def page_menu_entry_edit(self) -> Iterator[PageMenuEntry]:
        if not self.may_edit():
            return

        yield PageMenuEntry(
            title=_("Edit properties"),
            icon_name="edit",
            item=make_simple_link(self.edit_url()),
        )

    @classmethod
    def declare_overriding_permissions(cls) -> None:
        declare_permission_section(cls.type_name(), cls.phrase("title_plural"), do_sort=True)

        title_lower = cls.phrase("title_plural").lower()

        permission_registry.register(
            Permission(
                section=PermissionSectionGeneral,
                name="edit_" + cls.type_name(),
                title=_l("Customize and use %s") % title_lower,
                description=_l("Allows to create own %s, customize built-in %s and use them.")
                % (title_lower, title_lower),
                defaults=["admin", "user"],
            )
        )

        permission_registry.register(
            Permission(
                section=PermissionSectionGeneral,
                name="publish_" + cls.type_name(),
                title=_l("Publish %s") % title_lower,
                description=_l("Make %s visible and usable for all users.") % title_lower,
                defaults=["admin", "user"],
            )
        )

        permission_registry.register(
            Permission(
                section=PermissionSectionGeneral,
                name="publish_to_groups_" + cls.type_name(),
                title=_l("Publish %s to allowed contact groups") % title_lower,
                description=_l(
                    "Make %s visible and usable for users of contact groups the publishing user is a member of."
                )
                % title_lower,
                defaults=["admin", "user"],
            )
        )

        permission_registry.register(
            Permission(
                section=PermissionSectionGeneral,
                name="publish_to_foreign_groups_" + cls.type_name(),
                title=_l("Publish %s to foreign contact groups") % title_lower,
                description=_l(
                    "Make %s visible and usable for users of contact groups the publishing user is not a member of."
                )
                % title_lower,
                defaults=["admin"],
            )
        )

        permission_registry.register(
            Permission(
                section=PermissionSectionGeneral,
                name="publish_to_sites_" + cls.type_name(),
                title=_l("Publish %s to users of selected sites") % title_lower,
                description=_l(
                    "Make %s visible and usable for users of sites the "
                    "publishing user has selected."
                )
                % title_lower,
                defaults=["admin"],
            )
        )

        # TODO: Bug: This permission does not seem to be used
        permission_registry.register(
            Permission(
                section=PermissionSectionGeneral,
                name="see_user_" + cls.type_name(),
                title=_l("See user %s") % title_lower,
                description=_l("Is needed for seeing %s that other users have created.")
                % title_lower,
                defaults=default_authorized_builtin_role_ids,
            )
        )

        permission_registry.register(
            Permission(
                section=PermissionSectionGeneral,
                name="force_" + cls.type_name(),
                title=_l("Modify built-in %s") % title_lower,
                description=_l("Make own published %s override built-in %s for all users.")
                % (title_lower, title_lower),
                defaults=["admin"],
            )
        )

        permission_registry.register(
            Permission(
                section=PermissionSectionGeneral,
                name="edit_foreign_" + cls.type_name(),
                title=_l("Edit foreign %s") % title_lower,
                description=_("Allows to view and edit %s created by other users.") % title_lower,
                defaults=["admin"],
            )
        )

        permission_registry.register(
            Permission(
                section=PermissionSectionGeneral,
                name="delete_foreign_" + cls.type_name(),
                title=_l("Delete foreign %s") % title_lower,
                description=_l("Allows to delete %s created by other users.") % title_lower,
                defaults=["admin"],
            )
        )

    @classmethod
    def has_overriding_permission(cls, how: str) -> bool:
        return user.may(f"general.{how}_{cls.type_name()}")

    @classmethod
    def need_overriding_permission(cls, permission_name: Literal["edit", "see_user"]) -> None:
        if not cls.has_overriding_permission(permission_name):
            raise MKAuthException(
                _("Sorry, you lack the permission. Operation: %s, table: %s")
                % (permission_name, cls.phrase("title_plural"))
            )

    @classmethod
    def builtin_pages(cls) -> Mapping[str, _T_OverridableConfig]:
        return {}

    @classmethod
    def load_raw(cls) -> Mapping[InstanceId, dict[str, object]]:
        # For (config) updates we need the raw data.
        # We use 'dict' for the (inner) page_dict in order to allow in-place modifications
        # for simplicity.
        page_dicts_by_instance_id: dict[InstanceId, dict[str, object]] = {}

        with suppress(FileNotFoundError):
            for profile_path in cmk.utils.paths.profile_dir.iterdir():
                try:
                    user_id = UserId(profile_path.name)
                except ValueError:
                    # skip paths that aren't valid UserIds
                    continue

                try:
                    path = profile_path.joinpath("user_%ss.mk" % cls.type_name())
                    if not path.exists():
                        continue

                    if not userdb.user_exists(user_id):
                        continue

                    user_pages = store.try_load_file_from_pickle_cache(
                        path,
                        default={},
                        temp_dir=cmk.utils.paths.tmp_dir,
                        root_dir=cmk.utils.paths.omd_root,
                    )
                    for name, page_dict in user_pages.items():
                        page_dict["owner"] = user_id
                        page_dict["name"] = name
                        page_dicts_by_instance_id[(user_id, name)] = page_dict

                except SyntaxError as e:
                    raise MKGeneralException(
                        _("Cannot load %s from %s: %s") % (cls.type_name(), path, e)
                    )

        return page_dicts_by_instance_id

    @classmethod
    def load(cls) -> OverridableInstances[Self]:
        instances = OverridableInstances[Self]()

        # First load built-in pages. Set username to ''
        for name, page_config in cls.builtin_pages().items():
            new_page = cls(page_config)
            instances.add_instance((page_config.owner, name), new_page)

        # Now scan users subdirs for files "user_$type_name.mk"
        for (user_id, name), raw_page_dict in cls.load_raw().items():
            instances.add_instance((user_id, name), cls.deserialize(raw_page_dict))

        cls._declare_instance_permissions(instances)
        return instances

    @classmethod
    def _declare_instance_permissions(cls, instances: OverridableInstances[Self]) -> None:
        for instance in instances.instances():
            # Skip the permission declaration for the fallback topic.
            # Otherwise, users can disable it leading to a crashed GUI
            if instance.name() == cls.default_topic():
                continue
            if instance.is_public():
                cls.declare_permission(instance)

    @classmethod
    def save_user_instances(
        cls, instances: OverridableInstances[Self], owner: UserId | None = None
    ) -> None:
        if not owner:
            owner = user.id
        assert owner is not None

        save_dict = {}
        save_dict_by_owner: dict[UserId, dict[str, object]] = {}
        for page in instances.instances():
            if (page_owner := page.owner()) == owner:
                save_dict[page.name()] = page.serialize()
            elif LoggedInUser(owner).may("general.edit_foreign_%s" % cls.type_name()):
                save_dict_by_owner.setdefault(page_owner, {}).setdefault(
                    page.name(), page.serialize()
                )

        save_user_file("user_%ss" % cls.type_name(), save_dict, owner)
        for page_owner, save_dict_of_owner in save_dict_by_owner.items():
            save_user_file("user_%ss" % cls.type_name(), save_dict_of_owner, page_owner)

    def clone(self) -> Self:
        page_config = replace(self.config)
        page_config.owner = user.id if user.id else UserId("")
        new_page = self.__class__(page_config)
        return new_page

    @classmethod
    def declare_permission(cls, page: Self) -> None:
        permname = f"{cls.type_name()}.{page.name()}"
        if page.is_public() and permname not in permission_registry:
            permission_registry.register(
                Permission(
                    section=permission_section_registry[cls.type_name()],
                    name=page.name(),
                    title=f"{page.title()} ({page.name()})",
                    description=page.description(),
                    defaults=default_authorized_builtin_role_ids,
                )
            )

    @classmethod
    def custom_list_buttons(cls, instance: Self) -> None:
        pass

    # Override this in order to display additional columns of an instance
    # in the table of all instances.
    def render_extra_columns(self, table: Table) -> None:
        pass

    @classmethod
    def reserved_unique_ids(cls) -> list[str]:
        """Used to exclude names from choosing as unique ID, e.g. built-in names
        in sidebar snap-ins"""
        return []


class ListPage(Page, Generic[_T]):
    def __init__(self, pagetype: type[_T]) -> None:
        self._type = pagetype

    def page(self) -> None:
        instances = self._type.load()
        self._type.need_overriding_permission("edit")

        title_plural = self._type.phrase("title_plural")
        breadcrumb = make_breadcrumb(title_plural, "list", self._type.list_url())

        current_type_dropdown = PageMenuDropdown(
            name=self._type.type_name(),
            title=title_plural,
            topics=[
                PageMenuTopic(
                    title=title_plural,
                    entries=[
                        PageMenuEntry(
                            title=self._type.phrase("new"),
                            icon_name="new",
                            item=make_simple_link(self._type.create_url()),
                            is_shortcut=True,
                            is_suggested=True,
                        ),
                        PageMenuEntry(
                            title=_("Delete selected"),
                            name="delete",
                            icon_name="delete",
                            item=make_confirmed_form_submit_link(
                                form_name="bulk_delete",
                                button_name="_bulk_delete",
                                title=_("Delete selected %s") % title_plural.lower(),
                            ),
                            is_shortcut=True,
                            is_suggested=True,
                        ),
                    ],
                ),
            ],
        )

        page_menu = customize_page_menu(
            breadcrumb,
            current_type_dropdown,
            self._type.type_name(),
        )
        doc_reference_to_page_menu(
            page_menu, self._type.type_name(), self._type.phrase("title_plural")
        )
        make_header(html, title_plural, breadcrumb, page_menu)

        for message in get_flashed_messages():
            html.show_message(message.msg)

        # Deletion
        delname = request.var("_delete")
        if delname and transactions.check_transaction():
            owner = request.get_validated_type_input_mandatory(UserId, "_owner", user.id)
            pagetype_title = self._type.phrase("title")

            try:
                instance = instances.instance((owner, delname))
            except KeyError:
                raise MKUserError(
                    "_delete",
                    _("The %s you are trying to delete does not exist.") % pagetype_title,
                )

            if not instance.may_delete():
                raise MKUserError("_delete", _("You are not permitted to perform this action."))

            try:
                instances.remove_instance((owner, delname))
                self._type.save_user_instances(instances, owner)
                flash(_("Your %s has been deleted.") % pagetype_title)
                html.reload_whole_page()
            except MKUserError as e:
                html.user_error(e)

        elif request.var("_bulk_delete") and transactions.check_transaction():
            self._bulk_delete_after_confirm(instances)

        my_instances, foreign_instances, builtin_instances = self._partition_instances(instances)
        for what, title, scope_instances in [
            ("my", _("Customized"), my_instances),
            ("foreign", _("Owned by other users"), foreign_instances),
            ("builtin", _("Built-in"), builtin_instances),
        ]:
            if scope_instances:
                html.h3(title, class_="table")

                if what != "builtin":
                    with html.form_context("bulk_delete", method="POST"):
                        self._show_table(instances, scope_instances, deletable=True)
                        html.hidden_field("selection_id", weblib.selection_id())
                        html.hidden_fields()
                        init_rowselect(self._type.type_name())
                else:
                    self._show_table(instances, scope_instances)

        html.javascript("cmk.page_menu.check_menu_entry_by_checkboxes('delete')")
        html.footer()

    @classmethod
    def _partition_instances(
        cls,
        instances: OverridableInstances[_T],
    ) -> tuple[list[_T], list[_T], list[_T]]:
        my_instances, foreign_instances, builtin_instances = [], [], []

        for instance in instances.instances_sorted():
            if instance.may_see():
                if instance.is_builtin():
                    builtin_instances.append(instance)
                elif instance.is_mine():
                    my_instances.append(instance)
                elif instance.is_published_to_me() or instance.may_delete() or instance.may_edit():
                    foreign_instances.append(instance)

        return my_instances, foreign_instances, builtin_instances

    def _bulk_delete_after_confirm(self, instances: OverridableInstances[_T]) -> None:
        to_delete: list[tuple[UserId, str]] = []
        for varname, _value in request.itervars(prefix="_c_"):
            if html.get_checkbox(varname):
                raw_user, name = varname[3:].split("+")
                to_delete.append((UserId(raw_user), name))

        if not to_delete:
            return

        for owner, instance_id in to_delete:
            instances.remove_instance((owner, instance_id))

        for owner in {e[0] for e in to_delete}:
            self._type.save_user_instances(instances, owner)

        if len(to_delete) > 1:
            flash(_("Selected %s have been deleted.") % self._type.phrase("title_plural").lower())
        elif len(to_delete) == 1:
            flash(_("%s has been deleted.") % self._type.phrase("title"))

        html.reload_whole_page()

    def _show_table(
        self,
        instances: OverridableInstances[_T],
        scope_instances: Sequence[_T],
        deletable: bool = False,
    ) -> None:
        with table_element(limit=None) as table:
            for instance in scope_instances:
                table.row()

                if deletable and instance.may_delete():
                    table.cell(
                        html.render_input(
                            "_toggle_group",
                            type_="button",
                            class_="checkgroup",
                            onclick="cmk.selection.toggle_all_rows(this.form);"
                            "cmk.page_menu.check_menu_entry_by_checkboxes('delete')",
                            value="X",
                        ),
                        sortable=False,
                        css=["checkbox"],
                    )
                    html.checkbox(
                        f"_c_{instance.owner()}+{instance.name()}",
                        onclick="cmk.page_menu.check_menu_entry_by_checkboxes('delete')",
                        class_="page_checkbox",
                    )

                # Actions
                table.cell(_("Actions"), css=["buttons visuals"])

                # View
                if isinstance(instance, PageRenderer):
                    html.icon_button(instance.view_url(), _("View"), self._type.type_name())

                # Edit
                if instance.may_edit():
                    html.icon_button(instance.edit_url(), _("Edit"), "edit")

                self._type.custom_list_buttons(instance)

                # Clone / Customize
                html.icon_button(instance.clone_url(), _("Create a private copy of this"), "clone")

                # Delete
                if instance.may_delete():
                    html.icon_button(instance.delete_url(), _("Delete"), "delete")

                # Internal ID of instance (we call that 'name')
                table.cell(_("ID"), instance.name(), css=["narrow"])

                # Title
                table.cell(_("Title"))
                html.write_text_permissive(instance.render_title(instances))
                html.help(_u(instance.description()))

                # Custom columns specific to that page type
                instance.render_extra_columns(table)

                # Owner
                table.cell(
                    _("Owner"),
                    (
                        HTMLWriter.render_i(_("built-in"))
                        if instance.is_builtin()
                        else instance.owner()
                    ),
                )
                table.cell(_("Public"), _("yes") if instance.is_public() else _("no"))
                table.cell(_("Hidden"), _("yes") if instance.is_hidden() else _("no"))


class EditPage(Page, Generic[_T_OverridableConfig, _T]):
    def __init__(self, pagetype: type[_T]) -> None:
        self._type = pagetype

    def page(self) -> None:  # pylint: disable=too-many-branches
        """Page for editing an existing page, or creating a new one"""
        back_url = request.get_url_input("back", self._type.list_url())

        instances = self._type.load()
        self._type.need_overriding_permission("edit")

        raw_mode = request.get_ascii_input_mandatory("mode", "edit")
        mode: PageMode
        if raw_mode == "create":
            mode = "create"
        elif raw_mode == "edit":
            mode = "edit"
        elif raw_mode == "clone":
            mode = "clone"
        else:
            raise MKUserError("mode", "Invalid mode")

        owner_id = request.get_validated_type_input_mandatory(UserId, "owner", user.id)
        title = self._type.phrase(mode)
        if mode == "create":
            page_name = ""
            page_dict: dict[str, object] = {
                "name": self._type.default_name(instances),
                "topic": self._type.default_topic(),
            }
        else:
            page_name = request.get_str_input_mandatory("load_name")
            try:
                page = instances.instance((owner_id, page_name))
            except KeyError:
                raise MKUserError(
                    None, _("The requested %s does not exist") % self._type.phrase("title")
                )

            page_dict = page.serialize()
            if mode == "edit":
                if not page.may_edit():
                    raise MKAuthException(
                        _("You do not have the permissions to edit this %s")
                        % self._type.phrase("title")
                    )
            else:  # clone
                page_dict = copy.deepcopy(page_dict)
                page_dict["name"] = f"{page_dict['name']}_clone"
                assert user.id is not None
                page_dict["owner"] = str(user.id)
                owner_id = user.id
        breadcrumb = make_breadcrumb(title, mode, self._type.list_url(), self._type.phrase("title"))
        page_menu = make_edit_form_page_menu(
            breadcrumb,
            dropdown_name=self._type.type_name(),
            mode=mode,
            type_title=self._type.phrase("title"),
            type_title_plural=self._type.phrase("title_plural"),
            ident_attr_name="name",
            sub_pages=[],
            form_name="edit",
            visualname=page_name,
        )

        make_header(html, title, breadcrumb, page_menu)

        parameters, keys_by_topic = self._collect_parameters(mode)

        vs = Dictionary(
            title=_("General properties"),
            render="form",
            optional_keys=False,
            elements=parameters,
            headers=keys_by_topic,
            validate=validate_id(
                mode,
                {p.name(): p for p in instances.permitted_instances_sorted() if p.is_mine()},
                self._type.reserved_unique_ids(),
            ),
        )

        varprefix = ""
        if request.get_ascii_input("filled_in") == "edit" and transactions.check_transaction():
            try:
                new_page_dict = vs.from_html_vars(varprefix)
                vs.validate_value(new_page_dict, varprefix)
            except MKUserError as e:
                user_errors.add(e)
                new_page_dict = {}

            # Take over keys from previous value that are specific to the page type
            # and not edited here.
            if mode in ("edit", "clone"):
                page_dict.update(new_page_dict)
                # TODO this is done in a similar way with visuals but there the
                # VS is a Dictionary. Maybe we should change the format to
                # dict for both cases. But this would need a big adjustement of
                # the publish logic.
                #
                # This is needed because the Optional VS will be checked if value
                # is False (see the other way around in the form underneath)
                if page_dict["public"] is None:
                    page_dict["public"] = False
            else:
                page_dict = new_page_dict
                page_dict["owner"] = str(user.id)  # because is not in vs elements

            if not user_errors:
                new_page = self._type.deserialize(page_dict)

                instances.add_page(new_page)
                self._type.save_user_instances(instances, owner_id)
                if request.var("save_and_view"):
                    redirect_url = new_page.after_create_url() or makeuri_contextless(
                        request,
                        [("name", new_page.name())],
                        filename="%s.py" % self._type.type_name(),
                    )
                else:
                    redirect_url = back_url
                    flash(_("Your changes have been saved."))

                # Reload sidebar.TODO: This code logically belongs to PageRenderer. How
                # can we simply move it there?
                # TODO: This is not true for all cases. e.g. the BookmarkList is not
                # of type PageRenderer but has a dedicated sidebar snap-in. Maybe
                # the best option would be to make a dedicated method to decide whether
                # or not to reload the sidebar.
                html.reload_whole_page(redirect_url)

        else:
            html.show_localization_hint()

        html.show_user_errors()

        with html.form_context("edit", method="POST"):
            html.help(vs.help())
            # This is needed because the Optional VS will be checked if value
            # is False (see the other way around in the save phase above)
            if page_dict.get("public", False) is False:
                page_dict["public"] = None
            vs.render_input(varprefix, page_dict)
            # Should be ignored by hidden_fields, but I do not dare to change it there
            request.del_var("filled_in")
            html.hidden_fields()
        html.footer()

    def _collect_parameters(
        self, mode: PageMode
    ) -> tuple[list[tuple[str, ValueSpec]], list[tuple[str, list[str]]]]:
        topics: dict[str, list[tuple[float, str, ValueSpec]]] = {}
        for topic, elements in self._type.parameters(mode):
            el = topics.setdefault(topic, [])
            el += elements

        # Sort elements of each topic
        for topic_elements in topics.values():
            topic_elements.sort()

        # Now remove order numbers and produce the structures for the Dictionary VS
        parameters, keys_by_topic = [], []
        for topic, elements in sorted(topics.items(), key=lambda x: x[1][0]):
            topic_keys = []

            for _unused_order, key, vs in elements:
                parameters.append((key, vs))
                topic_keys.append(key)

            keys_by_topic.append((topic, topic_keys))

        return parameters, keys_by_topic


def make_breadcrumb(
    title: str, page_name: str, list_url: str, parent_title: str | None = None
) -> Breadcrumb:
    breadcrumb = make_main_menu_breadcrumb(mega_menu_registry.menu_customize())

    breadcrumb.append(BreadcrumbItem(title=parent_title or title, url=list_url))

    if page_name == "list":  # The list is the parent of all others
        return breadcrumb

    breadcrumb.append(BreadcrumbItem(title=title, url=makeuri(request, [])))
    return breadcrumb


def customize_page_menu(
    breadcrumb: Breadcrumb,
    current_type_dropdown: PageMenuDropdown,
    current_type_name: str,
) -> PageMenu:
    return PageMenu(
        dropdowns=[
            current_type_dropdown,
            PageMenuDropdown(
                name="related",
                title=_("Related"),
                topics=[
                    PageMenuTopic(
                        title=_("Customize"),
                        entries=list(_page_menu_entries_related(current_type_name)),
                    ),
                ],
            ),
        ],
        breadcrumb=breadcrumb,
        inpage_search=PageMenuSearch(),
    )


def _page_menu_entries_related(current_type_name: str) -> Iterator[PageMenuEntry]:
    if current_type_name != "views":
        yield PageMenuEntry(
            title=_("Views"),
            icon_name="view",
            item=make_simple_link("edit_views.py"),
        )

    if current_type_name != "dashboards":
        yield PageMenuEntry(
            title=_("Dashboards"),
            icon_name="dashboard",
            item=make_simple_link("edit_dashboards.py"),
        )

    if _has_reporting() and current_type_name != "reports":
        yield PageMenuEntry(
            title=_("Reports"),
            icon_name="report",
            item=make_simple_link("edit_reports.py"),
        )

    for other_type_name, other_pagetype in page_types.items():
        if current_type_name != other_type_name:
            yield PageMenuEntry(
                title=other_pagetype.phrase("title_plural"),
                icon_name=other_type_name,
                item=make_simple_link("%ss.py" % other_type_name),
            )


def _has_reporting() -> bool:
    return edition(cmk.utils.paths.omd_root) is not Edition.CRE


def vs_no_permission_to_publish(type_title: str, title: str) -> FixedValue:
    return FixedValue(
        value=False,
        title=title,
        totext=_("The %s is only visible to you because you don't have the permission to share it.")
        % type_title.lower(),
    )


def PublishTo(
    publish_all: bool,
    publish_groups: bool,
    publish_sites: bool,
    type_title: str,
    title: str | None = None,
    with_foreign_groups: bool = True,
) -> CascadingDropdown:
    if title is None:
        title = _("Make this %s available for other users") % type_title.lower()

    choices: list[CascadingDropdownChoice] = []
    if publish_all:
        choices.append((True, _("Publish to all users")))

    if publish_groups or with_foreign_groups:
        choices.append(
            (
                "contact_groups",
                _("Publish to members of contact groups"),
                ContactGroupChoice(with_foreign_groups=with_foreign_groups),
            )
        )

    if publish_sites:
        choices.append(
            (
                "sites",
                _("Publish to users of sites"),
                DualListChoice(
                    choices=get_configured_site_choices(),
                    title=_("Publish to all users of sites"),
                    rows=15,
                    size=80,
                    help=_(
                        "Select sites the %s should be avalable on. It will "
                        "become available for all users of that sites on the "
                        "next activation of changes for the selected sites."
                    )
                    % type_title,
                ),
            )
        )

    return CascadingDropdown(title=title, choices=choices)


def make_edit_form_page_menu(
    breadcrumb: Breadcrumb,
    dropdown_name: str,
    mode: str,
    type_title: str,
    type_title_plural: str,
    ident_attr_name: str,
    sub_pages: SubPagesSpec,
    form_name: str,
    visualname: str,
) -> PageMenu:
    return PageMenu(
        dropdowns=[
            PageMenuDropdown(
                name=dropdown_name,
                title=type_title.capitalize(),
                topics=[
                    PageMenuTopic(
                        title=_("Actions"),
                        entries=list(
                            _page_menu_entries_save(
                                breadcrumb,
                                sub_pages,
                                dropdown_name,
                                type_title,
                                type_title_plural,
                                form_name=form_name,
                            )
                        ),
                    ),
                    PageMenuTopic(
                        title=_("For this %s") % type_title,
                        entries=list(
                            _page_menu_entries_sub_pages(
                                mode, sub_pages, ident_attr_name, visualname
                            )
                        ),
                    ),
                ],
            ),
        ],
        breadcrumb=breadcrumb,
    )


_save_pagetype_icons: dict[str, Icon] = {
    "custom_graph": {
        "icon": "save_graph",
        "emblem": "add",
    },
    "dashboard": "save_dashboard",
    "forecast_graph": {
        "icon": "save_graph",
        "emblem": "time",
    },
    "graph_collection": "save_graph",
    "view": "save_view",
}


def _page_menu_entries_save(
    breadcrumb: Breadcrumb,
    sub_pages: SubPagesSpec,
    dropdown_name: str,
    type_title: str,
    type_title_plural: str,
    form_name: str,
) -> Iterator[PageMenuEntry]:
    """Provide the different "save" buttons"""
    yield PageMenuEntry(
        title=_("Save & view list"),
        icon_name="save",
        item=make_form_submit_link(form_name, "_save"),
        is_list_entry=True,
        is_shortcut=True,
        is_suggested=True,
        shortcut_title=_("Save & view list"),
        css_classes=["submit"],
    )

    if dropdown_name in _save_pagetype_icons:
        yield PageMenuEntry(
            title=type_title.title(),
            icon_name=_save_pagetype_icons[dropdown_name],
            item=make_form_submit_link(form_name, "save_and_view"),
            is_list_entry=True,
            is_shortcut=True,
            is_suggested=True,
            shortcut_title=_("Save & go to %s") % type_title,
        )

    parent_item = breadcrumb[-2]

    yield PageMenuEntry(
        title=_("Cancel"),
        icon_name="cancel",
        item=make_simple_link(parent_item.url),
        is_list_entry=True,
        is_shortcut=True,
        is_suggested=True,
    )

    for nr, (title, _pagename, _icon) in enumerate(sub_pages):
        yield PageMenuEntry(
            title=title,
            icon_name="save",
            item=make_form_submit_link(form_name, "save%d" % nr),
        )


def _page_menu_entries_sub_pages(
    mode: str, sub_pages: SubPagesSpec, ident_attr_name: str, visualname: str
) -> Iterator[PageMenuEntry]:
    """Extra links to sub modules

    These are used for things to edit about this visual that are more complex to be done in one
    value spec."""
    if mode != "edit":
        return

    for title, pagename, icon in sub_pages:
        uri: str = makeuri_contextless(
            request,
            [(ident_attr_name, visualname)],
            filename=pagename + ".py",
        )
        link: PageMenuLink = (
            make_external_link(uri) if pagename == "report" else make_simple_link(uri)
        )
        yield PageMenuEntry(title=title, icon_name=icon, item=link)


def ContactGroupChoice(with_foreign_groups: bool) -> DualListChoice:
    def _load_groups() -> list[tuple[str, str]]:
        contact_group_choices = all_groups("contact")
        return [
            (group_id, alias)
            for (group_id, alias) in contact_group_choices
            if with_foreign_groups or group_id in user.contact_groups
        ]

    return DualListChoice(
        choices=_load_groups,
        title=_("Publish to members of contact groups"),
        rows=15,
        size=80,
    )


# .
#   .--Container-----------------------------------------------------------.
#   |              ____            _        _                              |
#   |             / ___|___  _ __ | |_ __ _(_)_ __   ___ _ __              |
#   |            | |   / _ \| '_ \| __/ _` | | '_ \ / _ \ '__|             |
#   |            | |__| (_) | | | | || (_| | | | | |  __/ |                |
#   |             \____\___/|_| |_|\__\__,_|_|_| |_|\___|_|                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Base class for element containers - things that contain elements.   |
#   |  Examples: dashboards contain dashlets, graph collections contain    |
#   |  graphs.                                                             |
#   '----------------------------------------------------------------------'

_T_OverridableContainerConfig = TypeVar(
    "_T_OverridableContainerConfig", bound=OverridableContainerConfig
)


class OverridableContainer(Overridable[_T_OverridableContainerConfig]):
    @classmethod
    @abc.abstractmethod
    def may_contain(cls, element_type_name: str) -> bool: ...

    @classmethod
    def page_menu_add_to_topics(cls, added_type: str) -> list[PageMenuTopic]:
        if not cls.may_contain(added_type):
            return []

        pages = cls.load().pages()
        if not pages:
            return []

        return [
            PageMenuTopic(
                title=cls.phrase("add_to"),
                entries=list(cls._page_menu_add_to_entries(pages)),
            )
        ]

    @classmethod
    def _page_menu_add_to_entries(cls, pages: list[Self]) -> Iterator[PageMenuEntry]:
        for page in pages:
            yield PageMenuEntry(
                title=page.title(),
                icon_name=cls.type_name(),
                item=make_javascript_link(
                    f"cmk.popup_menu.pagetype_add_to_container({json.dumps(cls.type_name())}, {json.dumps(page.name())});"
                ),
            )

    @classmethod
    def page_handlers(cls) -> dict[str, cmk.gui.pages.PageHandlerFunc]:
        handlers = super().page_handlers()
        handlers.update(
            {
                # Ajax handler for adding elements to a container
                "ajax_pagetype_add_element": cls.ajax_add_element
            }
        )
        return handlers

    # Callback for the Javascript function cmk.popup_menu.pagetype_add_to_container(). The
    # create_info will contain a dictionary that is known to the underlying
    # element. Note: this is being called with the base class object Container,
    # not with any actual subclass like GraphCollection. We need to find that
    # class by the URL variable page_type.
    @classmethod
    def ajax_add_element(cls) -> None:
        page_type_name = request.get_ascii_input_mandatory("page_type")
        page_name = request.get_ascii_input_mandatory("page_name")
        element_type = request.get_ascii_input_mandatory("element_type")
        create_info = json.loads(request.get_str_input_mandatory("create_info"))

        page_ty = page_types[page_type_name]
        assert issubclass(page_ty, OverridableContainer)
        target_page, need_sidebar_reload = page_ty.add_element_via_popup(
            page_name, element_type, create_info
        )
        # Redirect user to tha page this displays the thing we just added to
        if target_page:
            if not isinstance(target_page, str):
                target_page = target_page.page_url()

        response.set_content_type("text/plain")
        response.set_data(f"{target_page or ""}\n{"true" if need_sidebar_reload else "false"}")

    # Default implementation for generic containers - used e.g. by GraphCollection
    @classmethod
    def add_element_via_popup(
        cls, page_name: str, element_type: str, create_info: ElementSpec
    ) -> tuple[str | None, bool]:
        cls.need_overriding_permission("edit")

        need_sidebar_reload = False
        instances = cls.load()
        page = instances.find_page(page_name)
        if page is None:
            raise MKGeneralException(
                _("Cannot find %s with the name %s") % (cls.phrase("title"), page_name)
            )
        if not page.is_mine():
            page = page.clone()
            instances.add_page(page)
            if isinstance(page, PageRenderer) and not page.is_hidden():
                need_sidebar_reload = True

        page.add_element(create_info)  # can be overridden
        cls.save_user_instances(instances)
        return None, need_sidebar_reload
        # With a redirect directly to the page afterwards do it like this:
        # return page, need_sidebar_reload

    def elements(self) -> Sequence[ElementSpec]:
        return self.config.elements

    def remove_element(self, nr: int) -> None:
        del self.config.elements[nr]

    def add_element(self, element: ElementSpec) -> None:
        self.config.elements.append(element)

    def move_element(self, nr: int, whither: int) -> None:
        el = self.config.elements[nr]
        del self.config.elements[nr]
        self.config.elements[whither:whither] = [el]

    def is_empty(self) -> bool:
        return not self.elements()


#   .--PageRenderer--------------------------------------------------------.
#   |   ____                  ____                _                        |
#   |  |  _ \ __ _  __ _  ___|  _ \ ___ _ __   __| | ___ _ __ ___ _ __     |
#   |  | |_) / _` |/ _` |/ _ \ |_) / _ \ '_ \ / _` |/ _ \ '__/ _ \ '__|    |
#   |  |  __/ (_| | (_| |  __/  _ <  __/ | | | (_| |  __/ | |  __/ |       |
#   |  |_|   \__,_|\__, |\___|_| \_\___|_| |_|\__,_|\___|_|  \___|_|       |
#   |              |___/                                                   |
#   +----------------------------------------------------------------------+
#   |  Base class for all things that have an URL and can be rendered as   |
#   |  an HTML page. And that can be added to the sidebar snap-in of all   |
#   |  pages.                                                              |
#   '----------------------------------------------------------------------'

_T_PageRendererConfig = TypeVar("_T_PageRendererConfig", bound=PageRendererConfig)


class PageRenderer(OverridableContainer[_T_PageRendererConfig]):
    # Stuff to be overridden by the implementation of actual page types

    # Attribute for identifying that page when building an URL to
    # the page. This is always "name", but
    # in the views it's for historic reasons "view_name". We might
    # change this in near future.
    # TODO: Change that. In views.py we could simply accept *both*.
    # First look for "name" and then for "view_name" if "name" is
    # missing.
    @classmethod
    def ident_attr(cls) -> str:
        return "name"

    # Parameters special for page renderers. These can be added to the sidebar,
    # so we need a topic and a checkbox for the visibility
    @classmethod
    def parameters(cls, mode: PageMode) -> list[tuple[str, list[tuple[float, str, ValueSpec]]]]:
        parameters = super().parameters(mode)

        parameters += [
            (
                _("Navigation"),
                [
                    (
                        1.4,
                        "topic",
                        DropdownChoice(
                            title=_("Topic"),
                            choices=PagetypeTopics.choices(),
                        ),
                    ),
                    (
                        1.5,
                        "sort_index",
                        Integer(
                            title=_("Sort index"),
                            default_value=99,
                            minvalue=1,
                            maxvalue=65535,
                            help=_(
                                "You can customize the order of the %s by changing "
                                "this number. Lower numbers will be sorted first. "
                                "Topics with the same number will be sorted alphabetically."
                            )
                            % cls.phrase("title_plural"),
                        ),
                    ),
                    (
                        1.6,
                        "is_show_more",
                        Checkbox(
                            title=_("Show more"),
                            label=_("Only show the %s if show more is active")
                            % cls.phrase("title_plural"),
                            default_value=False,
                            help=_(
                                "The navigation allows to hide items based on a show "
                                "less / show more toggle. You can specify here whether or "
                                "not this %s should only be shown with show more %s."
                            )
                            % (cls.phrase("title_plural"), cls.phrase("title_plural")),
                        ),
                    ),
                    (
                        2.0,
                        "hidden",
                        Checkbox(
                            title=_("Sidebar integration"),
                            label=_(
                                "Do not add a link to this page in sidebar and in monitor menu."
                            ),
                        ),
                    ),
                ],
            )
        ]

        return parameters

    @classmethod
    def page_handlers(cls) -> dict[str, cmk.gui.pages.PageHandlerFunc]:
        handlers = super().page_handlers()
        handlers.update(
            {
                cls.type_name(): cls.page_show,
            }
        )
        return handlers

    @classmethod
    @abc.abstractmethod
    def page_show(cls) -> None: ...

    @classmethod
    def requested_page(cls, instances: OverridableInstances[Self]) -> Self:
        return cls.requested_page_by_name(
            instances,
            request.get_ascii_input_mandatory(cls.ident_attr(), ""),
        )

    @classmethod
    def requested_page_by_name(cls, instances: OverridableInstances[Self], name: str) -> Self:
        if owner := request.get_validated_type_input(UserId, "owner"):
            if owner != user.id:
                cls.need_overriding_permission("see_user")
            if foreign := instances.find_foreign_page(owner, name):
                return foreign

        page = instances.find_page(name)
        if not page:
            raise MKGeneralException(
                _("Cannot find %s with the name %s") % (cls.phrase("title"), name)
            )
        return page

    def topic(self) -> str:
        return self.config.topic

    def sort_index(self) -> int:
        return self.config.sort_index

    def is_show_more(self) -> bool:
        return self.config.is_show_more

    # Helper functions for page handlers and render function
    def page_header(self) -> str:
        return self.phrase("title") + " - " + self.title()

    def page_url(self) -> str:
        return makeuri_contextless(
            request,
            [(self.ident_attr(), self.name())],
            filename="%s.py" % self.type_name(),
        )

    def view_url(self) -> str:
        http_vars: HTTPVariables = [(self.ident_attr(), self.name())]
        if not self.is_mine():
            http_vars.append(("owner", self.owner()))
        return makeuri_contextless(request, http_vars, filename="%s.py" % self.type_name())

    def render_title(self, instances: OverridableInstances[Self]) -> str | HTML:
        if self._can_be_linked(instances):
            return HTMLWriter.render_a(self.title(), href=self.page_url())
        return super().render_title(instances)

    def to_visual(self) -> Visual:
        return {
            "owner": self.config.owner,
            "name": self.config.name,
            "context": {},
            "single_infos": [],
            "add_context_to_title": False,
            "title": self.config.title,
            "description": self.config.description,
            "topic": self.config.topic,
            "sort_index": self.config.sort_index,
            "is_show_more": self.config.is_show_more,
            "icon": None,
            "hidden": self.config.hidden,
            "hidebutton": False,
            "public": False if self.config.public is None else self.config.public,
            "packaged": False,
            "link_from": {},
            "megamenu_search_terms": [],
        }


# .
#   .--globals-------------------------------------------------------------.
#   |                         _       _           _                        |
#   |                    __ _| | ___ | |__   __ _| |___                    |
#   |                   / _` | |/ _ \| '_ \ / _` | / __|                   |
#   |                  | (_| | | (_) | |_) | (_| | \__ \                   |
#   |                   \__, |_|\___/|_.__/ \__,_|_|___/                   |
#   |                   |___/                                              |
#   +----------------------------------------------------------------------+
#   |  Global methods for the integration of PageTypes into Multisite      |
#   '----------------------------------------------------------------------'

# Global dict of all page types
page_types: dict[str, type[Overridable]] = {}


def declare(page_ty: type[Overridable]) -> None:
    page_ty.declare_overriding_permissions()
    page_types[page_ty.type_name()] = page_ty

    for path, page_func in page_ty.page_handlers().items():
        cmk.gui.pages.page_registry.register_page_handler(path, page_func)


def page_type(page_type_name: str) -> type[Overridable]:
    return page_types[page_type_name]


def has_page_type(page_type_name: str) -> bool:
    return page_type_name in page_types


def all_page_types() -> Mapping[str, type[Overridable]]:
    return page_types


# Global module functions for the integration into the rest of the code


def page_menu_add_to_topics(added_type: str) -> list[PageMenuTopic]:
    topics = []
    for page_ty in page_types.values():
        if issubclass(page_ty, OverridableContainer):
            topics += page_ty.page_menu_add_to_topics(added_type)
    return topics


#   .--Topics--------------------------------------------------------------.
#   |                     _____           _                                |
#   |                    |_   _|__  _ __ (_) ___ ___                       |
#   |                      | |/ _ \| '_ \| |/ __/ __|                      |
#   |                      | | (_) | |_) | | (__\__ \                      |
#   |                      |_|\___/| .__/|_|\___|___/                      |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   | Each visuals / pagetype can have one topic. These topics are also    |
#   | managed in form of pagetypes to be customizable.                     |
#   '----------------------------------------------------------------------'


class PagetypeTopics(Overridable[PagetypeTopicConfig]):
    @classmethod
    def deserialize(cls, page_dict: Mapping[str, object]) -> Self:
        deserialized = PagetypeTopicModel.model_validate(page_dict)
        return cls(
            PagetypeTopicConfig(
                name=deserialized.name,
                title=deserialized.title,
                description=deserialized.description,
                owner=deserialized.owner,
                public=deserialized.public,
                hidden=deserialized.hidden,
                icon_name=deserialized.icon_name,
                sort_index=deserialized.sort_index,
                max_entries=deserialized.max_entries,
                hide=deserialized.hide,
            )
        )

    def serialize(self) -> dict[str, object]:
        return PagetypeTopicModel(
            name=self.config.name,
            title=self.config.title,
            description=self.config.description,
            owner=self.config.owner,
            public=self.config.public,
            hidden=self.config.hidden,
            icon_name=self.config.icon_name,
            sort_index=self.config.sort_index,
            max_entries=self.config.max_entries,
            hide=self.config.hide,
        ).model_dump()

    @classmethod
    def type_name(cls) -> str:
        return "pagetype_topic"

    @classmethod
    def type_icon(cls) -> Icon:
        return "pagetype_topic"

    @classmethod
    def phrase(cls, phrase: PagetypePhrase) -> str:
        return {
            "title": _("Topic"),
            "title_plural": _("Topics"),
            "clone": _("Clone topic"),
            "create": _("Create topic"),
            "edit": _("Edit topic"),
            "new": _("Add topic"),
        }.get(phrase, Base.phrase(phrase))

    @classmethod
    def parameters(cls, mode: PageMode) -> list[tuple[str, list[tuple[float, str, ValueSpec]]]]:
        parameters = super().parameters(mode)

        parameters += [
            (
                _("Topic"),
                [
                    # sort-index, key, valuespec
                    (
                        2.5,
                        "icon_name",
                        IconSelector(
                            title=_("Icon"),
                            allow_empty=False,
                            with_emblem=False,
                        ),
                    ),
                    (
                        2.5,
                        "max_entries",
                        Integer(
                            title=_("Number of items"),
                            help=_(
                                "You can define how much items this topic "
                                "should show. The remaining items will be "
                                "visible with the 'Show all' option, available "
                                "under the last item of the topic."
                            ),
                            default_value=10,
                        ),
                    ),
                    (
                        2.5,
                        "sort_index",
                        Integer(
                            title=_("Sort index"),
                            help=_(
                                "You can customize the order of the topics by changing "
                                "this number. Lower numbers will be sorted first. "
                                "Topics with the same number will be sorted alphabetically."
                            ),
                        ),
                    ),
                ],
            ),
        ]

        return parameters

    def render_extra_columns(self, table: Table) -> None:
        """Show some specific useful columns in the list view"""
        table.cell(_("Icon"), html.render_icon(self.config.icon_name))
        table.cell(_("Nr. of items"), str(self.max_entries()))
        table.cell(_("Sort index"), str(self.config.sort_index))

    @classmethod
    def builtin_pages(cls) -> Mapping[str, PagetypeTopicConfig]:
        topics: dict[str, PagetypeTopicConfig] = {
            "overview": PagetypeTopicConfig(
                name="overview",
                title=_("Overview"),
                icon_name="topic_overview",
                public=True,
                sort_index=20,
                owner=UserId.builtin(),
            ),
            "monitoring": PagetypeTopicConfig(
                name="monitoring",
                title=_("Monitoring"),
                icon_name="topic_monitoring",
                public=True,
                sort_index=30,
                owner=UserId.builtin(),
            ),
            "problems": PagetypeTopicConfig(
                name="problems",
                title=_("Problems"),
                icon_name="topic_problems",
                public=True,
                sort_index=40,
                owner=UserId.builtin(),
            ),
            "history": PagetypeTopicConfig(
                name="history",
                title=_("History"),
                icon_name="topic_history",
                public=True,
                sort_index=50,
                owner=UserId.builtin(),
            ),
            "analyze": PagetypeTopicConfig(
                name="analyze",
                title=_("System"),
                icon_name="topic_checkmk",
                public=True,
                sort_index=60,
                owner=UserId.builtin(),
            ),
            "cloud": PagetypeTopicConfig(
                name="cloud",
                title=_("Cloud"),
                icon_name="plugins_cloud",
                public=True,
                sort_index=75,
                owner=UserId.builtin(),
            ),
            "bi": PagetypeTopicConfig(
                name="bi",
                title=_("Business Intelligence"),
                icon_name="topic_bi",
                sort_index=80,
                public=True,
                hide=_no_bi_aggregate_active(),
                owner=UserId.builtin(),
            ),
            "applications": PagetypeTopicConfig(
                name="applications",
                title=_("Applications"),
                icon_name="topic_applications",
                public=True,
                sort_index=85,
                owner=UserId.builtin(),
            ),
            "inventory": PagetypeTopicConfig(
                name="inventory",
                title=_("HW/SW Inventory"),
                icon_name="topic_inventory",
                public=True,
                sort_index=90,
                owner=UserId.builtin(),
            ),
            "network_statistics": PagetypeTopicConfig(
                name="network_statistics",
                title=_("Network statistics"),
                icon_name="topic_network",
                sort_index=95,
                public=True,
                hide=not is_ntop_configured(),
                owner=UserId.builtin(),
            ),
            "it_efficiency": PagetypeTopicConfig(
                name="it_efficiency",
                title=_("IT infrastructure efficiency"),
                icon_name="topic_analyze",
                description=_("Analyze the utilization of your IT infrastructure data center."),
                public=True,
                sort_index=100,
                owner=UserId.builtin(),
            ),
            "synthetic_monitoring": PagetypeTopicConfig(
                name="synthetic_monitoring",
                title=_("Synthetic Monitoring"),
                icon_name="synthetic_monitoring_topic",
                public=True,
                sort_index=105,
                owner=UserId.builtin(),
            ),
            "my_workplace": PagetypeTopicConfig(
                name="my_workplace",
                title=_("Workplace"),
                icon_name="topic_my_workplace",
                public=True,
                sort_index=110,
                owner=UserId.builtin(),
            ),
            # Only fallback for items without topic
            "other": PagetypeTopicConfig(
                name="other",
                title=_("Other"),
                icon_name="topic_other",
                public=True,
                sort_index=115,
                owner=UserId.builtin(),
            ),
        }
        if edition(cmk.utils.paths.omd_root) is not Edition.CSE:  # disabled in CSE
            topics.update(
                {
                    "events": PagetypeTopicConfig(
                        name="events",
                        title=_("Event Console"),
                        icon_name="topic_events",
                        public=True,
                        sort_index=70,
                        owner=UserId.builtin(),
                    )
                }
            )

        return topics

    def max_entries(self) -> int:
        return self.config.max_entries

    def sort_index(self) -> int:
        return self.config.sort_index

    def icon_name(self) -> str:
        return self.config.icon_name

    def hide(self) -> bool:
        return self.config.hide

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        instances = cls.load()
        return [
            (p.name(), p.title())
            for p in sorted(instances.instances(), key=lambda p: p.sort_index())
            if p.is_permitted()
        ]

    @classmethod
    def get_topic(cls, topic_id: str) -> PagetypeTopics:
        """Returns either the requested topic or fallback to "other"."""
        instances = PagetypeTopics.load()
        other_page = instances.find_page("other")
        # should never happen
        if not other_page:
            raise MKGeneralException(_("Cannot find fallback topic 'Other'"))
        return instances.find_page(topic_id) or other_page

    @classmethod
    def reserved_unique_ids(cls) -> list[str]:
        return [cls.default_topic()]


declare(PagetypeTopics)


def _no_bi_aggregate_active() -> bool:
    enabled_info_file = "%s/num_enabled_aggregations" % os.path.join(
        cmk.utils.paths.var_dir, "wato"
    )
    return bool(not store.load_object_from_file(enabled_info_file, default=None))


#   .--Main menu-----------------------------------------------------------.
#   |          __  __       _                                              |
#   |         |  \/  | __ _(_)_ __    _ __ ___   ___ _ __  _   _           |
#   |         | |\/| |/ _` | | '_ \  | '_ ` _ \ / _ \ '_ \| | | |          |
#   |         | |  | | (_| | | | | | | | | | | |  __/ | | | |_| |          |
#   |         |_|  |_|\__,_|_|_| |_| |_| |_| |_|\___|_| |_|\__,_|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Register all pagetypes in the main menu                              |
#   '----------------------------------------------------------------------'
# .


def _customize_menu_topics() -> list[TopicMenuTopic]:
    general_items = []
    monitoring_items = []
    graph_items = []
    business_reporting_items = []

    if user.may("general.edit_views"):
        monitoring_items.append(
            TopicMenuItem(
                name="views",
                title=_("Views"),
                url="edit_views.py",
                sort_index=10,
                is_show_more=False,
                icon="view",
            ),
        )

    if user.may("general.edit_dashboards"):
        monitoring_items.append(
            TopicMenuItem(
                name="dashboards",
                title=_("Dashboards"),
                url="edit_dashboards.py",
                sort_index=20,
                is_show_more=False,
                icon="dashboard",
            ),
        )

    if user.may("general.edit_reports"):
        business_reporting_items.append(
            TopicMenuItem(
                name="reports",
                title=_("Reports"),
                url="edit_reports.py",
                sort_index=10,
                is_show_more=False,
                icon="report",
            )
        )

    for index, page_type_ in enumerate(all_page_types().values()):
        if not user.may(f"general.edit_{page_type_.type_name()}"):
            continue

        item = TopicMenuItem(
            name=page_type_.type_name(),
            title=page_type_.phrase("title_plural"),
            url="%ss.py" % page_type_.type_name(),
            sort_index=40 + (index * 10),
            is_show_more=False,
            icon=page_type_.type_icon(),
        )

        if page_type_.type_name() in ("pagetype_topic", "bookmark_list", "custom_snapin"):
            general_items.append(item)
        elif page_type_.type_name() == "sla_configuration":
            business_reporting_items.append(item)
        elif "graph" in page_type_.type_name():
            graph_items.append(item)
        else:
            monitoring_items.append(item)

    topics = [
        TopicMenuTopic(
            name="general",
            title=_("General"),
            icon="topic_general",
            items=general_items,
        ),
        TopicMenuTopic(
            name="visualization",
            title=_("Visualization"),
            icon="topic_visualization",
            items=monitoring_items,
        ),
        TopicMenuTopic(
            name="graphs",
            title=_("Graphs"),
            icon="topic_graphs",
            items=graph_items,
        ),
    ]

    if _has_reporting():
        topics.append(
            TopicMenuTopic(
                name="business_reporting",
                title=_("Business reporting"),
                icon="topic_reporting",
                items=business_reporting_items,
            )
        )

    return topics


def hide_customize_menu() -> bool:
    permissions = [
        "general.edit_pagetype_topic",
        "general.edit_bookmark_list",
        "general.edit_custom_snapin",
        "general.edit_graph_collection",
        "general.edit_graph_tuning",
        "general.edit_custom_graph",
        "general.edit_forecast_graph",
        "general.edit_sla_configuration",
        "general.edit_views",
        "general.edit_dashboards",
        "general.edit_reports",
    ]

    return not any(user.may(perm) for perm in permissions)


#   .--Permissions---------------------------------------------------------.
#   |        ____                     _         _                          |
#   |       |  _ \ ___ _ __ _ __ ___ (_)___ ___(_) ___  _ __  ___          |
#   |       | |_) / _ \ '__| '_ ` _ \| / __/ __| |/ _ \| '_ \/ __|         |
#   |       |  __/  __/ |  | | | | | | \__ \__ \ | (_) | | | \__ \         |
#   |       |_|   \___|_|  |_| |_| |_|_|___/___/_|\___/|_| |_|___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Declare all pagetype permissions as dynamic permissions              |
#   '----------------------------------------------------------------------'


def _load_pagetype_permissions() -> None:
    for pagetype in all_page_types().values():
        pagetype.load()


declare_dynamic_permissions(_load_pagetype_permissions)
