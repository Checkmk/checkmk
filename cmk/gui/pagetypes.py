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
from typing import cast, Generic, Literal, TypedDict, TypeVar

import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import UserId

import cmk.gui.pages
import cmk.gui.sites as sites
import cmk.gui.userdb as userdb
import cmk.gui.weblib as weblib
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_main_menu_breadcrumb
from cmk.gui.config import default_authorized_builtin_role_ids
from cmk.gui.default_name import unique_default_name_suggestion
from cmk.gui.default_permissions import PermissionSectionGeneral
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _l, _u
from cmk.gui.logged_in import save_user_file, user
from cmk.gui.main_menu import mega_menu_registry
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
    HTTPVariables,
    Icon,
    MegaMenu,
    PermissionName,
    TopicMenuItem,
    TopicMenuTopic,
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

SubPagesSpec = list[tuple[str, str, str]]
PagetypePhrase = Literal["title", "title_plural", "add_to", "clone", "create", "edit", "new"]
# Three possible modes:
# "create" -> create completely new page
# "clone"  -> like new, but prefill form with values from existing page
# "edit"   -> edit existing page
PageMode = Literal["create", "clone", "edit"]


class _BaseSpecMandatory(TypedDict):
    name: str
    title: str


class BaseSpec(_BaseSpecMandatory, total=False):
    description: str


class _OverridableSpecMandatory(BaseSpec):
    owner: UserId
    public: bool | tuple[Literal["contact_groups"], Sequence[str]]


class OverridableSpec(_OverridableSpecMandatory, total=False):
    # Seems it is not configurable through the UI. Is it OK?
    hidden: bool


ElementSpec = dict


class OverridableContainerSpec(OverridableSpec):
    # TODO: Specify element types. Can we make use of the generic typed dicts here?
    elements: list[ElementSpec]


class PageRendererSpec(OverridableContainerSpec):
    topic: str
    sort_index: int
    is_show_more: bool


class _PagetypeTopicSpecMandatory(OverridableSpec):
    icon_name: str
    sort_index: int


class PagetypeTopicSpec(_PagetypeTopicSpecMandatory, total=False):
    max_entries: int
    # Seems it is not configurable through the UI. Is it OK?
    hide: bool


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

_T_BaseSpec = TypeVar("_T_BaseSpec", bound=BaseSpec)


class Base(abc.ABC, Generic[_T_BaseSpec]):
    def __init__(self, d: _T_BaseSpec) -> None:
        super().__init__()

        # The dictionary with the name _ holds all information about
        # the page in question - as a dictionary that can be loaded
        # and saved to files using repr().
        self._ = d

    def internal_representation(self) -> _T_BaseSpec:
        return self._

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
                _("General Properties"),
                [
                    (
                        1.1,
                        "name",
                        ID(
                            title=_("Unique ID"),
                            help=_(
                                "The ID will be used do identify this page in URLs. If this page has the "
                                "same ID as a builtin page of the type <i>%s</i> then it will shadow the builtin one."
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
        return self._["name"]

    def title(self) -> str:
        return self._["title"]

    def description(self) -> str:
        try:
            return self._["description"]
        except KeyError:
            return ""

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
    def type_name(cls) -> str:
        ...

    @classmethod
    @abc.abstractmethod
    def type_icon(cls) -> Icon:
        ...


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

_T_OverridableSpec = TypeVar("_T_OverridableSpec", bound=OverridableSpec)
# TODO: May be replaced with Self once we are with Python 3.11
_Self = TypeVar("_Self", bound="Overridable")
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
                elif page.is_builtin():
                    builtin = page
                else:
                    foreign = page

        if mine:
            return mine
        if forced:
            return forced
        if builtin:
            return builtin
        if foreign:
            return foreign
        return None

    def pages(self) -> list[_T]:
        """Return all pages visible to the user, implements shadowing etc."""
        pages = {}

        # Builtin pages
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


class Overridable(Base[_T_OverridableSpec], Generic[_T_OverridableSpec, _Self]):
    # Default values for the creation dialog can be overridden by the
    # sub class.
    @classmethod
    def default_name(cls: type[_Self], instances: OverridableInstances[_Self]) -> str:
        return unique_default_name_suggestion(
            cls.type_name(),
            (instance.name() for instance in instances.instances()),
        )

    def __init__(self, d: _T_OverridableSpec) -> None:
        if "public" not in d:
            d["public"] = False
        super().__init__(d)

    @classmethod
    def parameters(cls, mode: PageMode) -> list[tuple[str, list[tuple[float, str, ValueSpec]]]]:
        parameters = super().parameters(mode)

        if is_user_with_publish_permissions("pagetype", user.id, cls.type_name()):
            vs_visibility: ValueSpec = Optional(
                title=_("Visibility"),
                label=_("Make this %s available for other users") % cls.phrase("title"),
                none_label=_("Don't publish to other users"),
                valuespec=PublishTo(
                    publish_all=cls.has_overriding_permission("publish"),
                    publish_groups=cls.has_overriding_permission("publish_to_groups"),
                    publish_sites=cls.has_overriding_permission("publish_to_sites"),
                    title="",
                    type_title=cls.phrase("title"),
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
                _("General Properties"),
                [
                    (2.2, "public", vs_visibility),
                ],
            ),
        ]

    @classmethod
    def page_handlers(cls: type[_Self]) -> dict[str, cmk.gui.pages.PageHandlerFunc]:
        handlers = super().page_handlers()
        handlers.update(
            {
                "%ss" % cls.type_name(): lambda: ListPage[_Self](cls).page(),
                "edit_%s"
                % cls.type_name(): lambda: EditPage[_T_OverridableSpec, _Self](cls).page(),
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
        if self._["public"] is False:
            return False

        return self.publish_is_allowed()

    def publish_is_allowed(self) -> bool:
        """Whether publishing an element to other users is allowed by the owner"""
        return not self.owner() or user_may(self.owner(), "general.publish_" + self.type_name())

    def is_public_forced(self) -> bool:
        """Whether the user is allowed to override builtin pagetypes"""
        return self.is_public() and user_may(self.owner(), "general.force_" + self.type_name())

    def is_published_to_me(self) -> bool:
        """Whether the page is published to the currently active user"""
        if not user.may("general.see_user_%s" % self.type_name()):
            return False

        if self._["public"] is True:
            return self.publish_is_allowed()

        if isinstance(self._["public"], tuple) and self._["public"][0] == "contact_groups":
            if set(user.contact_groups).intersection(self._["public"][1]):
                return self.publish_is_allowed()

        return False

    def is_hidden(self) -> bool:
        try:
            return self._["hidden"]
        except KeyError:
            return False

    def is_builtin(self) -> bool:
        return not self.owner()

    def is_mine(self) -> bool:
        return self.owner() == user.id

    def is_mine_and_may_have_own(self) -> bool:
        return self.is_mine() and user.may("general.edit_" + self.type_name())

    def render_title(self, instances: OverridableInstances[_Self]) -> str | HTML:
        return _u(self.title())

    def _can_be_linked(self, instances: OverridableInstances[_Self]) -> bool:
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
        return UserId(self._["owner"])

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
        return (self.is_mine() and self.may_see()) or (
            not self.is_mine() and self.is_published_to_me() and self.may_see()
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
                description=_l("Allows to create own %s, customize builtin %s and use them.")
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
                title=_l("Modify builtin %s") % title_lower,
                description=_l("Make own published %s override builtin %s for all users.")
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
    def need_overriding_permission(cls) -> None:
        if not cls.has_overriding_permission("edit"):
            raise MKAuthException(
                _("Sorry, you lack the permission. Operation: %s, table: %s")
                % ("edit", cls.phrase("title_plural"))
            )

    @classmethod
    def builtin_pages(cls) -> Mapping[str, _T_OverridableSpec]:
        return {}

    @classmethod
    def load(cls: type[_Self]) -> OverridableInstances[_Self]:
        instances = OverridableInstances[_Self]()

        # First load builtin pages. Set username to ''
        for name, page_dict in cls.builtin_pages().items():
            page_dict = cls._transform_old_spec(page_dict)
            new_page = cls(page_dict)
            instances.add_instance((page_dict["owner"], name), new_page)

        # Now scan users subdirs for files "user_$type_name.mk"
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

                    user_pages = store.try_load_file_from_pickle_cache(path, default={})
                    for name, page_dict in user_pages.items():
                        page_dict["owner"] = user_id
                        page_dict["name"] = name
                        page_dict = cls._transform_old_spec(page_dict)

                        instances.add_instance((user_id, name), cls(page_dict))

                except SyntaxError as e:
                    raise MKGeneralException(
                        _("Cannot load %s from %s: %s") % (cls.type_name(), path, e)
                    )

        cls._load(instances)
        cls._declare_instance_permissions(instances)
        return instances

    # TODO: Clean this up
    @classmethod
    def _load(cls, instances: OverridableInstances[_Self]) -> None:
        """Custom method to load e.g. old configs
        after performing the loading of the regular files."""

    @classmethod
    def _transform_old_spec(cls, spec: dict) -> dict:
        """May be used to transform old persisted data structures"""
        return spec

    @classmethod
    def _declare_instance_permissions(cls, instances: OverridableInstances[_Self]) -> None:
        for instance in instances.instances():
            if instance.is_public():
                cls.declare_permission(instance)

    @classmethod
    def save_user_instances(
        cls, instances: OverridableInstances[_Self], owner: UserId | None = None
    ) -> None:
        if not owner:
            owner = user.id
        assert owner is not None

        save_dict = {}
        for page in instances.instances():
            if page.owner() == owner:
                save_dict[page.name()] = page.internal_representation()

        save_user_file("user_%ss" % cls.type_name(), save_dict, owner)

    def clone(self: _Self) -> _Self:
        page_dict = self._.copy()
        page_dict["owner"] = str(user.id) if user.id else ""
        new_page = self.__class__(page_dict)
        return new_page

    @classmethod
    def declare_permission(cls, page: _Self) -> None:
        permname = f"{cls.type_name()}.{page.name()}"
        if page.is_public() and permname not in permission_registry:
            permission_registry.register(
                Permission(
                    section=permission_section_registry[cls.type_name()],
                    name=page.name(),
                    title=page.title(),
                    description=page.description(),
                    defaults=default_authorized_builtin_role_ids,
                )
            )

    @classmethod
    def custom_list_buttons(cls, instance: _Self) -> None:
        pass

    # Override this in order to display additional columns of an instance
    # in the table of all instances.
    def render_extra_columns(self, table: Table) -> None:
        pass

    @classmethod
    def reserved_unique_ids(cls) -> list[str]:
        """Used to exclude names from choosing as unique ID, e.g. builtin names
        in sidebar snapins"""
        return []


class ListPage(Page, Generic[_Self]):
    def __init__(self, pagetype: type[_Self]) -> None:
        self._type = pagetype

    def page(self) -> None:
        instances = self._type.load()
        self._type.need_overriding_permission()

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
                html.reload_whole_page()
            except MKUserError as e:
                html.user_error(e)

            flash(_("Your %s has been deleted.") % pagetype_title)
            html.reload_whole_page(self._type.list_url())

        elif request.var("_bulk_delete") and transactions.check_transaction():
            self._bulk_delete_after_confirm(instances)

        my_instances, foreign_instances, builtin_instances = self._partition_instances(instances)
        for what, title, scope_instances in [
            ("my", _("Customized"), my_instances),
            ("foreign", _("Owned by other users"), foreign_instances),
            ("builtin", _("Builtin"), builtin_instances),
        ]:
            if scope_instances:
                self._show_table(instances, what, title, scope_instances)

        html.footer()

    @classmethod
    def _partition_instances(
        cls,
        instances: OverridableInstances[_Self],
    ) -> tuple[list[_Self], list[_Self], list[_Self]]:
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

    def _bulk_delete_after_confirm(self, instances: OverridableInstances[_Self]) -> None:
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

        flash(_("The selected %s have been deleted.") % self._type.phrase("title_plural"))
        html.reload_whole_page(self._type.list_url())

    def _show_table(
        self,
        instances: OverridableInstances[_Self],
        what: str,
        title: str,
        scope_instances: Sequence[Overridable],
    ) -> None:
        html.h3(title, class_="table")

        if what != "builtin":
            html.begin_form("bulk_delete", method="POST")

        with table_element(limit=None) as table:
            for instance in scope_instances:
                table.row()

                if what != "builtin" and instance.may_delete():
                    table.cell(
                        html.render_input(
                            "_toggle_group",
                            type_="button",
                            class_="checkgroup",
                            onclick="cmk.selection.toggle_all_rows(this.form);",
                            value="X",
                        ),
                        sortable=False,
                        css=["checkbox"],
                    )
                    html.checkbox(f"_c_{instance.owner()}+{instance.name()}")

                # Actions
                table.cell(_("Actions"), css=["buttons visuals"])

                # View
                if isinstance(instance, PageRenderer):
                    html.icon_button(instance.page_url(), _("View"), self._type.type_name())

                # Clone / Customize
                html.icon_button(instance.clone_url(), _("Create a private copy of this"), "clone")

                # Delete
                if instance.may_delete():
                    html.icon_button(instance.delete_url(), _("Delete!"), "delete")

                # Edit
                if instance.may_edit():
                    html.icon_button(instance.edit_url(), _("Edit"), "edit")

                self._type.custom_list_buttons(instance)

                # Internal ID of instance (we call that 'name')
                table.cell(_("ID"), instance.name(), css=["narrow"])

                # Title
                table.cell(_("Title"))
                html.write_text(instance.render_title(instances))
                html.help(_u(instance.description()))

                # Custom columns specific to that page type
                instance.render_extra_columns(table)

                # Owner
                table.cell(
                    _("Owner"),
                    HTMLWriter.render_i(_("builtin"))
                    if instance.is_builtin()
                    else instance.owner(),
                )
                table.cell(_("Public"), _("yes") if instance.is_public() else _("no"))
                table.cell(_("Hidden"), _("yes") if instance.is_hidden() else _("no"))

        if what != "builtin":
            html.hidden_field("selection_id", weblib.selection_id())
            html.hidden_fields()
            html.end_form()
            init_rowselect(self._type.type_name())


class EditPage(Page, Generic[_T_OverridableSpec, _Self]):
    def __init__(self, pagetype: type[_Self]) -> None:
        self._type = pagetype

    def page(self) -> None:  # pylint: disable=too-many-branches
        """Page for editing an existing page, or creating a new one"""
        back_url = request.get_url_input("back", self._type.list_url())

        instances = self._type.load()
        self._type.need_overriding_permission()

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
            page_dict = {
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

            page_dict = page.internal_representation()
            if mode == "edit":
                if not page.may_edit():
                    raise MKAuthException(
                        _("You do not have the permissions to edit this %s")
                        % self._type.phrase("title")
                    )
            else:  # clone
                page_dict = copy.deepcopy(page_dict)
                page_dict["name"] += "_clone"
                assert user.id is not None
                page_dict["owner"] = str(user.id)
                owner_id = user.id

        breadcrumb = make_breadcrumb(title, mode, self._type.list_url())
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
            title=_("General Properties"),
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
            else:
                page_dict = new_page_dict
                page_dict["owner"] = str(user.id)  # because is not in vs elements

            # Since we have no way to parse the raw dictionary and Dictionary is also not typable,
            # we need to hope here that page_dict fits with _T_OverridableSpec. On the mission to at
            # least add some typing to `self._`, we take this shortcut for now. There are way bigger
            # problems in this class hierarchy than the edit dialog we should solve first.
            # TODO: Find a way to clean it up.
            new_page = self._type(cast(_T_OverridableSpec, page_dict))

            if not user_errors:
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
                # of type PageRenderer but has a dedicated sidebar snapin. Maybe
                # the best option would be to make a dedicated method to decide whether
                # or not to reload the sidebar.
                html.reload_whole_page(redirect_url)

        else:
            html.show_localization_hint()

        html.show_user_errors()

        html.begin_form("edit", method="POST")
        html.help(vs.help())
        vs.render_input(varprefix, page_dict)
        # Should be ignored by hidden_fields, but I do not dare to change it there
        request.del_var("filled_in")
        html.hidden_fields()
        html.end_form()
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


def make_breadcrumb(title: str, page_name: str, list_url: str) -> Breadcrumb:
    breadcrumb = make_main_menu_breadcrumb(mega_menu_registry.menu_customize())

    breadcrumb.append(BreadcrumbItem(title=title, url=list_url))

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
                title=other_pagetype.phrase("title_plural").title(),
                icon_name=other_type_name,
                item=make_simple_link("%ss.py" % other_type_name),
            )


def _has_reporting() -> bool:
    return not cmk_version.is_raw_edition()


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
    title: str | None = None,
    type_title: str | None = None,
    with_foreign_groups: bool = True,
) -> CascadingDropdown:
    if title is None:
        title = _("Make this %s available for other users") % type_title

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
                title=type_title.title(),
                topics=[
                    PageMenuTopic(
                        title=_("Save this %s and go to") % type_title,
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
        title=_("List of %s") % type_title_plural,
        icon_name="save",
        item=make_form_submit_link(form_name, "_save"),
        is_list_entry=True,
        is_shortcut=True,
        is_suggested=True,
        shortcut_title=_("Save & go to list"),
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
        is_list_entry=False,
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
        contact_group_choices = sites.all_groups("contact")
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

_T_OverridableContainerSpec = TypeVar("_T_OverridableContainerSpec", bound=OverridableContainerSpec)


class OverridableContainer(Overridable[_T_OverridableContainerSpec, _Self]):
    @classmethod
    @abc.abstractmethod
    def may_contain(cls, element_type_name: str) -> bool:
        ...

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
    def _page_menu_add_to_entries(cls, pages: list[_Self]) -> Iterator[PageMenuEntry]:
        for page in pages:
            yield PageMenuEntry(
                title=page.title(),
                icon_name=cls.type_name(),
                item=make_javascript_link(
                    "cmk.popup_menu.pagetype_add_to_container(%s, %s);"
                    % (json.dumps(cls.type_name()), json.dumps(page.name()))
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
            html.write_text(target_page)
        html.write_text("\n%s" % ("true" if need_sidebar_reload else "false"))

    # Default implementation for generic containers - used e.g. by GraphCollection
    @classmethod
    def add_element_via_popup(
        cls: type[_Self], page_name: str, element_type: str, create_info: ElementSpec
    ) -> tuple[str | None, bool]:
        cls.need_overriding_permission()

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

    def __init__(self, d: _T_OverridableContainerSpec) -> None:
        if "elements" not in d:
            d["elements"] = []
        super().__init__(d)

    def elements(self) -> Sequence[ElementSpec]:
        return self._["elements"]

    def remove_element(self, nr: int) -> None:
        del self._["elements"][nr]

    def add_element(self, element: ElementSpec) -> None:
        self._["elements"].append(element)

    def move_element(self, nr: int, whither: int) -> None:
        el = self._["elements"][nr]
        del self._["elements"][nr]
        self._["elements"][whither:whither] = [el]

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
#   |  an HTML page. And that can be added to the sidebar snapin of all    |
#   |  pages.
#   '----------------------------------------------------------------------'

_T_PageRendererSpec = TypeVar("_T_PageRendererSpec", bound=PageRendererSpec)
_SelfPageRenderer = TypeVar("_SelfPageRenderer", bound="PageRenderer")


class PageRenderer(OverridableContainer[_T_PageRendererSpec, _SelfPageRenderer]):
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
    def _transform_old_spec(cls, spec: dict) -> dict:
        spec.setdefault("sort_index", 99)
        spec.setdefault("is_show_more", False)

        spec.setdefault("context", {})
        spec.setdefault("add_context_to_title", False)

        return spec

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
    def page_show(cls) -> None:
        ...

    @classmethod
    def requested_page(
        cls, instances: OverridableInstances[_SelfPageRenderer]
    ) -> _SelfPageRenderer:
        name = request.get_ascii_input_mandatory(cls.ident_attr(), "")
        page = instances.find_page(name)
        if not page:
            raise MKGeneralException(
                _("Cannot find %s with the name %s") % (cls.phrase("title"), name)
            )
        return page

    def topic(self) -> str:
        try:
            return self._["topic"]
        except KeyError:
            return "other"

    def sort_index(self) -> int:
        try:
            return self._["sort_index"]
        except KeyError:
            return 99

    def is_show_more(self) -> bool:
        try:
            return self._["is_show_more"]
        except KeyError:
            return False

    # Helper functions for page handlers and render function
    def page_header(self) -> str:
        return self.phrase("title") + " - " + self.title()

    def page_url(self) -> str:
        return makeuri_contextless(
            request,
            [(self.ident_attr(), self.name())],
            filename="%s.py" % self.type_name(),
        )

    def render_title(self, instances: OverridableInstances[_SelfPageRenderer]) -> str | HTML:
        if self._can_be_linked(instances):
            return HTMLWriter.render_a(self.title(), href=self.page_url())
        return super().render_title(instances)


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


class PagetypeTopics(Overridable[PagetypeTopicSpec, "PagetypeTopics"]):
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
        table.cell(_("Icon"), html.render_icon(self._["icon_name"]))
        table.cell(_("Nr. of items"), str(self.max_entries()))
        table.cell(_("Sort index"), str(self._["sort_index"]))

    @classmethod
    def builtin_pages(cls) -> Mapping[str, PagetypeTopicSpec]:
        return {
            "overview": {
                "name": "overview",
                "title": _("Overview"),
                "icon_name": "topic_overview",
                "description": "",
                "public": True,
                "sort_index": 20,
                "owner": UserId.builtin(),
            },
            "monitoring": {
                "name": "monitoring",
                "title": _("Monitoring"),
                "icon_name": "topic_monitoring",
                "description": "",
                "public": True,
                "sort_index": 30,
                "owner": UserId.builtin(),
            },
            "problems": {
                "name": "problems",
                "title": _("Problems"),
                "icon_name": "topic_problems",
                "description": "",
                "public": True,
                "sort_index": 40,
                "owner": UserId.builtin(),
            },
            "history": {
                "name": "history",
                "title": _("History"),
                "icon_name": "topic_history",
                "description": "",
                "public": True,
                "sort_index": 50,
                "owner": UserId.builtin(),
            },
            "analyze": {
                "name": "analyze",
                "title": _("System"),
                "icon_name": "topic_checkmk",
                "description": "",
                "public": True,
                "sort_index": 60,
                "owner": UserId.builtin(),
            },
            "events": {
                "name": "events",
                "title": _("Event Console"),
                "icon_name": "topic_events",
                "description": "",
                "public": True,
                "sort_index": 70,
                "owner": UserId.builtin(),
            },
            "cloud": {
                "name": "cloud",
                "title": _("Cloud"),
                "icon_name": "plugins_cloud",
                "description": "",
                "public": True,
                "sort_index": 75,
                "owner": UserId.builtin(),
            },
            "bi": {
                "name": "bi",
                "title": _("Business Intelligence"),
                "icon_name": "topic_bi",
                "description": "",
                "sort_index": 80,
                "public": True,
                "hide": _no_bi_aggregate_active(),
                "owner": UserId.builtin(),
            },
            "applications": {
                "name": "applications",
                "title": _("Applications"),
                "icon_name": "topic_applications",
                "description": "",
                "public": True,
                "sort_index": 85,
                "owner": UserId.builtin(),
            },
            "inventory": {
                "name": "inventory",
                "title": _("Inventory"),
                "icon_name": "topic_inventory",
                "description": "",
                "public": True,
                "sort_index": 90,
                "owner": UserId.builtin(),
            },
            "network_statistics": {
                "name": "network_statistics",
                "title": _("Network statistics"),
                "icon_name": "topic_network_statistics",
                "description": "",
                "sort_index": 95,
                "public": True,
                "hide": not is_ntop_configured(),
                "owner": UserId.builtin(),
            },
            "it_efficiency": {
                "name": "it_efficiency",
                "title": _("IT infrastructure efficiency"),
                "icon_name": "topic_analyze",
                "description": _("Analyze the utilization of your IT infrastructure data center."),
                "public": True,
                "sort_index": 100,
                "owner": UserId.builtin(),
            },
            "my_workplace": {
                "name": "my_workplace",
                "title": _("Workplace"),
                "icon_name": "topic_my_workplace",
                "description": "",
                "public": True,
                "sort_index": 105,
                "owner": UserId.builtin(),
            },
            # Only fallback for items without topic
            "other": {
                "name": "other",
                "title": _("Other"),
                "icon_name": "topic_other",
                "description": "",
                "public": True,
                "sort_index": 110,
                "owner": UserId.builtin(),
            },
        }

    def max_entries(self) -> int:
        return self._.get("max_entries", 10)

    def sort_index(self) -> int:
        return self._["sort_index"]

    def icon_name(self) -> str:
        return self._["icon_name"]

    def hide(self) -> bool:
        return self._.get("hide", False)

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        instances = cls.load()
        return [
            (p.name(), p.title())
            for p in sorted(instances.instances(), key=lambda p: p.sort_index())
        ]

    @classmethod
    def get_topic(cls, topic_id: str) -> PagetypeTopics:
        """Returns either the requested topic or fallback to "other"."""
        instances = PagetypeTopics.load()
        other_page = instances.find_page("other")
        assert other_page is not None
        return instances.find_page(topic_id) or other_page


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
    monitoring_items = [
        TopicMenuItem(
            name="views",
            title=_("Views"),
            url="edit_views.py",
            sort_index=10,
            is_show_more=False,
            icon="view",
        ),
        TopicMenuItem(
            name="dashboards",
            title=_("Dashboards"),
            url="edit_dashboards.py",
            sort_index=20,
            is_show_more=False,
            icon="dashboard",
        ),
    ]
    graph_items = []
    business_reporting_items = [
        TopicMenuItem(
            name="reports",
            title=_("Reports"),
            url="edit_reports.py",
            sort_index=10,
            is_show_more=True,
            icon="report",
        )
    ]

    for index, page_type_ in enumerate(all_page_types().values()):
        item = TopicMenuItem(
            name=page_type_.type_name(),
            title=page_type_.phrase("title_plural"),
            url="%ss.py" % page_type_.type_name(),
            sort_index=40 + (index * 10),
            is_show_more=page_type_.type_is_show_more(),
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


mega_menu_registry.register(
    MegaMenu(
        name="customize",
        title=_l("Customize"),
        icon="main_customize",
        sort_index=10,
        topics=_customize_menu_topics,
    )
)

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
