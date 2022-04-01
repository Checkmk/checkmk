#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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

import copy
import json
import os
from contextlib import suppress
from typing import Any, Dict, Iterator, List
from typing import Optional as _Optional
from typing import Tuple

import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.type_defs import UserId

import cmk.gui.pages
import cmk.gui.sites as sites
import cmk.gui.userdb as userdb
import cmk.gui.weblib as weblib
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_main_menu_breadcrumb
from cmk.gui.default_permissions import PermissionSectionGeneral
from cmk.gui.exceptions import MKAuthException, MKGeneralException, MKUserError
from cmk.gui.globals import html, request, transactions, user_errors
from cmk.gui.i18n import _, _l, _u
from cmk.gui.logged_in import save_user_file, user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.page_menu import (
    make_confirmed_form_submit_link,
    make_form_submit_link,
    make_javascript_link,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.permissions import (
    declare_permission_section,
    Permission,
    permission_registry,
    permission_section_registry,
)
from cmk.gui.table import init_rowselect, table_element
from cmk.gui.type_defs import HTTPVariables, Icon, MegaMenu, TopicMenuItem, TopicMenuTopic
from cmk.gui.utils import unique_default_name_suggestion, validate_id
from cmk.gui.utils.flashed_messages import flash, get_flashed_messages
from cmk.gui.utils.ntop import is_ntop_configured
from cmk.gui.utils.roles import is_user_with_publish_permissions, user_may
from cmk.gui.utils.urls import (
    make_confirm_link,
    makeactionuri,
    makeuri,
    makeuri_contextless,
    urlencode,
)
from cmk.gui.valuespec import (
    CascadingDropdown,
    CascadingDropdownChoice,
    Checkbox,
    Dictionary,
    DictionaryEntry,
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

SubPagesSpec = List[Tuple[str, str, str]]

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


class Base:
    def __init__(self, d: Dict[str, Any]) -> None:
        super().__init__()

        # The dictionary with the name _ holds all information about
        # the page in question - as a dictionary that can be loaded
        # and saved to files using repr().
        self._ = d

    def internal_representation(self) -> Dict[str, Any]:
        return self._

    # You always must override the following method. Not all phrases
    # might be neccessary depending on the type of you page.
    # Possible phrases:
    # "title"        : Title of one instance
    # "title_plural" : Title in plural
    # "add_to"       : Text like "Add to foo bar..."
    # TODO: Look at GraphCollection for the complete list of phrases to
    # be defined for each page type and explain that here.
    # TODO: Refactor this to different indepentent class methods. For example
    # the "add_to" phrase is not relevant for non container elements. In the
    # moment we use dedicated methods, wrong usage will be found by pylint.
    @classmethod
    def phrase(cls, phrase: str) -> str:
        return _("MISSING '%s'") % phrase

    # Implement this function in a subclass in order to add parameters
    # to be editable by the user when editing the details of such page
    # type.
    # Returns a list of entries.
    # Each entry is a pair of a topic and a list of elements.
    # Each element is a triple of order, key and valuespec
    # TODO: Add topic here
    @classmethod
    def parameters(cls, mode):
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

    # Define page handlers for the neccessary pages. This is being called (indirectly)
    # in index.py. That way we do not need to hard code page handlers for all types of
    # PageTypes in plugins/pages. It is simply sufficient to register a PageType and
    # all page handlers will exist :-)
    @classmethod
    def page_handlers(cls):
        return {}

    # Do *not* override this. It collects all editable parameters of our
    # page type by calling parameters() for each class
    @classmethod
    def _collect_parameters(cls, mode):
        topics: Dict[str, List[DictionaryEntry]] = {}
        for topic, elements in cls.parameters(mode):
            el = topics.setdefault(topic, [])
            el += elements

        # Sort elements of each topic
        for topic in topics.values():
            topic.sort()

        # Now remove order numbers and produce the structures for the Dictionary VS
        parameters, keys_by_topic = [], []
        for topic, elements in sorted(topics.items(), key=lambda x: x[1][0]):
            topic_keys = []

            for _unused_order, key, vs in elements:
                parameters.append((key, vs))
                topic_keys.append(key)

            keys_by_topic.append((topic, topic_keys))

        return parameters, keys_by_topic

    # Object methods that *can* be overridden - for cases where
    # that pages in question of a dictionary format that is not
    # compatible.
    def name(self) -> str:
        return self._["name"]

    def title(self) -> str:
        return self._["title"]

    def description(self) -> str:
        return self._.get("description", "")

    def is_hidden(self) -> bool:
        return False

    def _can_be_linked(self) -> bool:
        return True

    def render_title(self) -> str:
        return _u(self.title())

    def is_empty(self) -> bool:
        return False

    def _show_in_sidebar(self) -> bool:
        return not self.is_empty() and not self.is_hidden()

    # Default values for the creation dialog can be overridden by the
    # sub class.
    @classmethod
    def default_name(cls) -> str:
        return unique_default_name_suggestion(
            cls.type_name(),
            (instance.name() for instance in cls.__instances.values()),
        )

    @classmethod
    def default_topic(cls) -> str:
        return "other"

    @classmethod
    def type_is_show_more(cls) -> bool:
        """Whether or not this page type should be treated as element in the
        navigation only shown on show more button"""
        return False

    # Store for all instances of this page type. The key into
    # this dictionary????
    # TODO: Brauchen wir hier überhaupt ein dict??
    __instances: "Dict[Tuple[str, str], Base]" = {}

    @classmethod
    def clear_instances(cls):
        cls.__instances = {}

    @classmethod
    def add_instance(cls, key, instance):
        cls.__instances[key] = instance

    @classmethod
    def remove_instance(cls, key):
        del cls.__instances[key]

    # Return a list of all instances of this type
    @classmethod
    def instances(cls):
        return list(cls.__instances.values())

    @classmethod
    def instance(cls, key):
        return cls.__instances[key]

    @classmethod
    def has_instance(cls, key):
        return key in cls.__instances

    # Return a dict of all instances of this type
    @classmethod
    def instances_dict(cls):
        return cls.__instances

    # Return a list of pairs if instance key and instance, which
    # is sorted by the title of the instance
    @classmethod
    def instances_sorted(cls):
        return sorted(cls.__instances.values(), key=lambda x: x.title())

    # Stub function for the list of all pages. In case of Overridable
    # several instances might exist that overlay each other. This
    # function returns the final list of pages visible to the user
    @classmethod
    def pages(cls):
        for instance in cls.__instances.values():
            return instance
        return None

    # Stub function for finding a page by name. Overriden by
    # Overridable.
    @classmethod
    def find_page(cls, name):
        for instance in cls.__instances.values():
            if instance.name() == name:
                return instance
        return None

    @classmethod
    def type_name(cls) -> str:
        raise NotImplementedError()

    @classmethod
    def type_icon(cls) -> str:
        raise NotImplementedError()

    # Lädt alle Dinge vom aktuellen User-Homeverzeichnis und
    # mergt diese mit den übergebenen eingebauten
    @classmethod
    def load(cls):
        raise NotImplementedError()

    # Custom method to load e.g. old configs after performing the
    # loading of the regular files.
    @classmethod
    def _load(cls):
        pass


# .
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


class PageRenderer(Base):
    # Stuff to be overridden by the implementation of actual page types

    # TODO: Das von graphs.py rauspfluecken. Also alles, was man
    # überladen muss oder kann.

    # Attribute for identifying that page when building an URL to
    # the page. This is always "name", but
    # in the views it's for historic reasons "view_name". We might
    # change this in near future.
    # TODO: Change that. In views.py we could simply accept *both*.
    # First look for "name" and then for "view_name" if "name" is
    # missing.
    @classmethod
    def ident_attr(cls):
        return "name"

    # Parameters special for page renderers. These can be added to the sidebar,
    # so we need a topic and a checkbox for the visibility
    @classmethod
    def parameters(cls, mode):
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
                            label=_("Do not add a link to this page in sidebar"),
                        ),
                    ),
                ],
            )
        ]

        return parameters

    @classmethod
    def _transform_old_spec(cls, spec):
        spec.setdefault("sort_index", 99)
        spec.setdefault("is_show_more", False)

        spec.setdefault("context", {})
        spec.setdefault("add_context_to_title", False)

        return spec

    @classmethod
    def page_handlers(cls):
        handlers = super().page_handlers()
        handlers.update(
            {
                cls.type_name(): cls.page_show,
            }
        )
        return handlers

    # Most important: page for showing the page ;-)
    @classmethod
    def page_show(cls):
        page = cls.requested_page()
        page.render()

    @classmethod
    def requested_page(cls):
        name = request.var(cls.ident_attr())
        cls.load()
        page = cls.find_page(name)
        if not page:
            raise MKGeneralException(
                _("Cannot find %s with the name %s") % (cls.phrase("title"), name)
            )
        return page

    # Links for the sidebar
    @classmethod
    def sidebar_links(cls):
        for page in cls.pages():
            if page._show_in_sidebar():
                yield page.topic(), page.title(), page.page_url()

    def topic(self) -> str:
        return self._.get("topic", "other")

    def sort_index(self) -> int:
        return self._.get("sort_index", 99)

    def is_show_more(self) -> bool:
        return self._.get("is_show_more", False)

    # Helper functions for page handlers and render function
    def page_header(self):
        return self.phrase("title") + " - " + self.title()

    def page_url(self):
        return makeuri_contextless(
            request,
            [(self.ident_attr(), self.name())],
            filename="%s.py" % self.type_name(),
        )

    def render_title(self):
        if self._can_be_linked():
            return html.render_a(self.title(), href=self.page_url())
        return self.title()


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


class Overridable(Base):
    def __init__(self, d):
        super().__init__(d)
        self._.setdefault("public", False)

    @classmethod
    def parameters(cls, mode):
        parameters = super().parameters(mode)

        if is_user_with_publish_permissions("pagetype", user.id, cls.type_name()):
            vs_visibility: ValueSpec = Optional(
                title=_("Visibility"),
                label=_("Make this %s available for other users") % cls.phrase("title"),
                none_label=_("Don't publish to other users"),
                none_value=False,
                valuespec=PublishTo(
                    publish_all=cls.has_overriding_permission("publish"),
                    publish_groups=cls.has_overriding_permission("publish_to_groups"),
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
    def page_handlers(cls):
        handlers = super().page_handlers()
        handlers.update(
            {
                "%ss" % cls.type_name(): cls.page_list,
                "edit_%s" % cls.type_name(): cls.page_edit,
            }
        )
        return handlers

    def page_header(self):
        header = self.phrase("title") + " - " + self.title()
        if not self.is_mine():
            header += " (%s)" % self.owner()
        return header

    def is_public(self):
        """Checks whether a page is visible to other users than the owner.

        This does not only need a flag in the page itself, but also the
        permission from its owner to publish it."""
        if self._["public"] is False:
            return False

        return self.publish_is_allowed()

    def publish_is_allowed(self):
        """Whether or not not publishing an element to other users is allowed by the owner"""
        return not self.owner() or user_may(self.owner(), "general.publish_" + self.type_name())

    # Same, but checks if the owner has the permission to override builtin views
    def is_public_forced(self):
        return self.is_public() and user_may(self.owner(), "general.force_" + self.type_name())

    def is_published_to_me(self):
        """Whether or not the page is published to the currently active user"""
        if self._["public"] is True:
            return self.publish_is_allowed()

        if isinstance(self._["public"], tuple) and self._["public"][0] == "contact_groups":
            if set(user.contact_groups).intersection(self._["public"][1]):
                return self.publish_is_allowed()

        return False

    def is_hidden(self):
        return self._.get("hidden", False)

    # Derived method for conveniance
    def is_builtin(self):
        return not self.owner()

    def is_mine(self):
        return self.owner() == user.id

    def is_mine_and_may_have_own(self):
        return self.is_mine() and user.may("general.edit_" + self.type_name())

    def _can_be_linked(self):
        """Whether or not the thing can be linked to"""
        if self.is_hidden():
            return False  # don't link to hidden things

        if self.is_mine():
            return True

        # Is this the visual which would be shown to the user in case the user
        # requests a visual with the current name?
        page = self.find_page(self.name())
        if page and page.owner() != self.owner():
            return False

        return self.is_published_to_me()

    @classmethod
    def _delete_permission(cls):
        return "general.edit_" + cls.type_name()

    def owner(self) -> UserId:
        return self._["owner"]

    # Checks if the current user is allowed to see a certain page
    # TODO: Wie is die Semantik hier genau? Umsetzung vervollständigen!
    def may_see(self):
        perm_name = "%s.%s" % (self.type_name(), self.name())
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

    @classmethod
    def permitted_instances_sorted(cls):
        return [i for i in cls.instances_sorted() if i.is_permitted()]

    def may_delete(self):
        if self.is_builtin():
            return False
        if self.is_mine() and user.may(self._delete_permission()):
            return True
        return user.may("general.delete_foreign_%s" % self.type_name())

    def may_edit(self):
        if self.is_builtin():
            return False
        if self.is_mine() and user.may("general.edit_%s" % self.type_name()):
            return True
        return user.may("general.edit_foreign_%s" % self.type_name())

    def edit_url(self):
        http_vars: HTTPVariables = [("load_name", self.name())]
        if not self.is_mine():
            http_vars.append(("owner", self.owner()))

        return makeuri_contextless(request, http_vars, filename="edit_%s.py" % self.type_name())

    def clone_url(self):
        backurl = urlencode(makeuri(request, []))
        return makeuri_contextless(
            request,
            [
                ("owner", self.owner()),
                ("load_name", self.name()),
                ("mode", "clone"),
                ("back", backurl),
            ],
            filename="edit_%s.py" % self.type_name(),
        )

    def delete_url(self):
        add_vars: HTTPVariables = [("_delete", self.name())]
        if not self.is_mine():
            add_vars.append(("_owner", self.owner()))

        if not self.is_mine():
            owned_by = _(" (owned by %s)") % self.owner()
        else:
            owned_by = ""
        message = _('Please confirm the deletion of "%s"%s.') % (self.title(), owned_by)

        return make_confirm_link(
            url=makeactionuri(request, transactions, add_vars), message=message
        )

    @classmethod
    def create_url(cls):
        return "edit_%s.py?mode=create" % cls.type_name()

    @classmethod
    def list_url(cls):
        return "%ss.py" % cls.type_name()

    def after_create_url(self):
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
    def declare_overriding_permissions(cls):
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

        # TODO: Bug: This permission does not seem to be used
        permission_registry.register(
            Permission(
                section=PermissionSectionGeneral,
                name="see_user_" + cls.type_name(),
                title=_l("See user %s") % title_lower,
                description=_l("Is needed for seeing %s that other users have created.")
                % title_lower,
                defaults=["admin", "user", "guest"],
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
    def has_overriding_permission(cls, how):
        return user.may("general.%s_%s" % (how, cls.type_name()))

    @classmethod
    def need_overriding_permission(cls, how):
        if not cls.has_overriding_permission(how):
            raise MKAuthException(
                _("Sorry, you lack the permission. Operation: %s, table: %s")
                % (how, cls.phrase("title_plural"))
            )

    # Return all pages visible to the user, implements shadowing etc.
    @classmethod
    def pages(cls):
        cls.load()
        pages = {}

        # Builtin pages
        for page in cls.instances():
            if page.is_published_to_me() and page.may_see() and page.is_builtin():
                pages[page.name()] = page

        # Public pages by normal other users
        for page in cls.instances():
            if page.is_published_to_me() and page.may_see():
                pages[page.name()] = page

        # Public pages by admin users, forcing their versions over others
        for page in cls.instances():
            if page.is_published_to_me() and page.may_see() and page.is_public_forced():
                pages[page.name()] = page

        # My own pages
        for page in cls.instances():
            if page.is_mine_and_may_have_own():
                pages[page.name()] = page

        return sorted(pages.values(), key=lambda x: x.title())

    @classmethod
    def page_choices(cls):
        return [(page.name(), page.title()) for page in cls.pages()]

    # Find a page by name, implements shadowing and
    # publishing und overriding by admins
    @classmethod
    def find_page(cls, name):
        mine = None
        forced = None
        builtin = None
        foreign = None

        for page in cls.instances():
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

    @classmethod
    def find_my_page(cls, name):
        for page in cls.instances():
            if page.is_mine() and page.name() == name:
                return page

    @classmethod
    def find_foreign_page(cls, owner, name):
        try:
            return cls.instance((owner, name))
        except KeyError:
            return None

    @classmethod
    def builtin_pages(cls):
        return {}

    # Lädt alle Dinge vom aktuellen User-Homeverzeichnis und
    # mergt diese mit den übergebenen eingebauten
    @classmethod
    def load(cls):
        cls.clear_instances()

        # First load builtin pages. Set username to ''
        for name, page_dict in cls.builtin_pages().items():
            page_dict["owner"] = UserId("")  # might have been forgotten on copy action
            page_dict["public"] = True
            page_dict["name"] = name
            page_dict = cls._transform_old_spec(page_dict)

            new_page = cls(page_dict)
            cls.add_instance(("", name), new_page)

        # Now scan users subdirs for files "user_$type_name.mk"
        with suppress(FileNotFoundError):
            for profile_path in cmk.utils.paths.profile_dir.iterdir():
                user_id = UserId(profile_path.name)
                try:
                    path = profile_path.joinpath("user_%ss.mk" % cls.type_name())
                    if not path.exists():
                        continue

                    if not userdb.user_exists(user_id):
                        continue

                    user_pages = store.load_object_from_file(path, default={})
                    for name, page_dict in user_pages.items():
                        page_dict["owner"] = user_id
                        page_dict["name"] = name
                        page_dict = cls._transform_old_spec(page_dict)

                        cls.add_instance((user_id, name), cls(page_dict))

                except SyntaxError as e:
                    raise MKGeneralException(
                        _("Cannot load %s from %s: %s") % (cls.type_name(), path, e)
                    )

        cls._load()
        cls._declare_instance_permissions()

    @classmethod
    def _transform_old_spec(cls, spec: Dict) -> Dict:
        """May be used to transform old persisted data structures"""
        return spec

    @classmethod
    def _declare_instance_permissions(cls):
        for instance in cls.instances():
            if instance.is_public():
                cls.declare_permission(instance)

    @classmethod
    def save_user_instances(cls, owner: _Optional[UserId] = None) -> None:
        if not owner:
            owner = user.id
        assert owner is not None

        save_dict = {}
        for page in cls.instances():
            if page.owner() == owner:
                save_dict[page.name()] = page.internal_representation()

        save_user_file("user_%ss" % cls.type_name(), save_dict, owner)

    @classmethod
    def add_page(cls, new_page):
        cls.add_instance((new_page.owner(), new_page.name()), new_page)

    def clone(self):
        page_dict = {}
        page_dict.update(self._)
        page_dict["owner"] = user.id
        new_page = self.__class__(page_dict)
        self.add_page(new_page)
        return new_page

    @classmethod
    def declare_permission(cls, page):
        permname = "%s.%s" % (cls.type_name(), page.name())
        if page.is_public() and permname not in permission_registry:
            permission_registry.register(
                Permission(
                    section=permission_section_registry[cls.type_name()],
                    name=page.name(),
                    title=page.title(),
                    description=page.description(),
                    defaults=["admin", "user", "guest"],
                )
            )

    @classmethod
    def custom_list_buttons(cls, instance):
        pass

    @classmethod
    def breadcrumb(cls, title: str, page_name: str) -> Breadcrumb:
        breadcrumb = make_main_menu_breadcrumb(mega_menu_registry.menu_customize())

        breadcrumb.append(BreadcrumbItem(title=cls.phrase("title_plural"), url=cls.list_url()))

        if page_name == "list":  # The list is the parent of all others
            return breadcrumb

        breadcrumb.append(BreadcrumbItem(title=title, url=makeuri(request, [])))
        return breadcrumb

    @classmethod
    def page_list(cls):
        cls.load()

        # custom_columns = []
        # render_custom_buttons = None
        # render_custom_columns = None
        # check_deletable_handler = None

        cls.need_overriding_permission("edit")

        title_plural = cls.phrase("title_plural")
        breadcrumb = cls.breadcrumb(cls.phrase("title_plural"), "list")

        current_type_dropdown = PageMenuDropdown(
            name=cls.type_name(),
            title=title_plural,
            topics=[
                PageMenuTopic(
                    title=title_plural,
                    entries=[
                        PageMenuEntry(
                            title=cls.phrase("new"),
                            icon_name="new",
                            item=make_simple_link(cls.create_url()),
                            is_shortcut=True,
                            is_suggested=True,
                        ),
                        PageMenuEntry(
                            title=_("Delete selected"),
                            icon_name="delete",
                            item=make_confirmed_form_submit_link(
                                form_name="bulk_delete",
                                button_name="_bulk_delete",
                                message=_("Do you really want to delete the selected %s?")
                                % title_plural,
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
            cls.type_name(),
        )
        html.header(title_plural, breadcrumb, page_menu)

        for message in get_flashed_messages():
            html.show_message(message)

        # Deletion
        delname = request.var("_delete")
        if delname and transactions.check_transaction():
            owner = UserId(request.get_str_input_mandatory("_owner", user.id))
            pagetype_title = cls.phrase("title")

            try:
                instance = cls.instance((owner, delname))
            except KeyError:
                raise MKUserError(
                    "_delete",
                    _("The %s you are trying to delete " "does not exist.") % pagetype_title,
                )

            if not instance.may_delete():
                raise MKUserError("_delete", _("You are not permitted to perform this action."))

            try:
                cls.remove_instance((owner, delname))
                cls.save_user_instances(owner)
                html.reload_whole_page()
            except MKUserError as e:
                html.user_error(e)

            flash(_("Your %s has been deleted.") % pagetype_title)
            html.reload_whole_page(cls.list_url())

        elif request.var("_bulk_delete") and transactions.check_transaction():
            cls._bulk_delete_after_confirm()

        my_instances, foreign_instances, builtin_instances = cls.get_instances()
        for what, title, instances in [
            ("my", _("Customized"), my_instances),
            ("foreign", _("Owned by other users"), foreign_instances),
            ("builtin", _("Builtin"), builtin_instances),
        ]:
            if not instances:
                continue

            html.h3(title, class_="table")

            if what != "builtin":
                html.begin_form("bulk_delete", method="POST")

            with table_element(limit=None) as table:
                for instance in instances:
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
                            css="checkbox",
                        )
                        html.checkbox("_c_%s+%s" % (instance.owner(), instance.name()))

                    # Actions
                    table.cell(_("Actions"), css="buttons visuals")

                    # View
                    if isinstance(instance, PageRenderer):
                        html.icon_button(instance.page_url(), _("View"), cls.type_name())

                    # Clone / Customize
                    html.icon_button(
                        instance.clone_url(), _("Create a customized copy of this"), "clone"
                    )

                    # Delete
                    if instance.may_delete():
                        html.icon_button(instance.delete_url(), _("Delete!"), "delete")

                    # Edit
                    if instance.may_edit():
                        html.icon_button(instance.edit_url(), _("Edit"), "edit")

                    cls.custom_list_buttons(instance)

                    # Internal ID of instance (we call that 'name')
                    table.cell(_("ID"), instance.name(), css="narrow")

                    # Title
                    table.cell(_("Title"))
                    html.write_text(instance.render_title())
                    html.help(_u(instance.description()))

                    # Custom columns specific to that page type
                    instance.render_extra_columns(table)

                    # Owner
                    if instance.is_builtin():
                        ownertxt = html.render_i(_("builtin"))
                    else:
                        ownertxt = instance.owner()
                    table.cell(_("Owner"), ownertxt)
                    table.cell(_("Public"), _("yes") if instance.is_public() else _("no"))
                    table.cell(_("Hidden"), _("yes") if instance.is_hidden() else _("no"))

            if what != "builtin":
                html.hidden_field("selection_id", weblib.selection_id())
                html.hidden_fields()
                html.end_form()
                init_rowselect(cls.type_name())

        html.footer()

    @classmethod
    def get_instances(cls):
        my_instances, foreign_instances, builtin_instances = [], [], []

        for instance in cls.instances_sorted():
            if instance.may_see():
                if instance.is_builtin():
                    builtin_instances.append(instance)
                elif instance.is_mine():
                    my_instances.append(instance)
                elif instance.is_published_to_me() or instance.may_delete() or instance.may_edit():
                    foreign_instances.append(instance)

        return my_instances, foreign_instances, builtin_instances

    @classmethod
    def _bulk_delete_after_confirm(cls):
        to_delete: List[Tuple[UserId, str]] = []
        for varname, _value in request.itervars(prefix="_c_"):
            if html.get_checkbox(varname):
                raw_user, name = varname[3:].split("+")
                to_delete.append((UserId(raw_user), name))

        if not to_delete:
            return

        for owner, instance_id in to_delete:
            cls.remove_instance((owner, instance_id))

        for owner in {e[0] for e in to_delete}:
            cls.save_user_instances(owner)

        flash(_("The selected %s have been deleted.") % cls.phrase("title_plural"))
        html.reload_whole_page(cls.list_url())

    # Override this in order to display additional columns of an instance
    # in the table of all instances.
    def render_extra_columns(self, table):
        pass

    # Page for editing an existing page, or creating a new one
    @classmethod
    def page_edit(cls):
        back_url = request.get_url_input("back", cls.list_url())

        cls.load()
        cls.need_overriding_permission("edit")

        # Three possible modes:
        # "create" -> create completely new page
        # "clone"  -> like new, but prefill form with values from existing page
        # "edit"   -> edit existing page
        mode = request.get_ascii_input_mandatory("mode", "edit")
        owner_id = UserId(request.get_str_input_mandatory("owner", user.id))
        title = cls.phrase(mode)
        if mode == "create":
            page_name = ""
            page_dict = {
                "name": cls.default_name(),
                "topic": cls.default_topic(),
            }
        else:
            page_name = request.get_str_input_mandatory("load_name")
            page = cls.find_foreign_page(owner_id, page_name)
            if page is None:
                raise MKUserError(None, _("The requested %s does not exist") % cls.phrase("title"))

            page_dict = page.internal_representation()
            if mode == "edit":
                if not page.may_edit():
                    raise MKAuthException(
                        _("You do not have the permissions to edit this %s") % cls.phrase("title")
                    )
            else:  # clone
                page_dict = copy.deepcopy(page_dict)
                page_dict["name"] += "_clone"
                assert user.id is not None
                page_dict["owner"] = str(user.id)
                owner_id = user.id

        breadcrumb = cls.breadcrumb(title, mode)
        page_menu = make_edit_form_page_menu(
            breadcrumb,
            dropdown_name=cls.type_name(),
            mode=mode,
            type_title=cls.phrase("title"),
            type_title_plural=cls.phrase("title_plural"),
            ident_attr_name="name",
            sub_pages=[],
            form_name="edit",
            visualname=page_name,
        )

        html.header(title, breadcrumb, page_menu)

        parameters, keys_by_topic = cls._collect_parameters(mode)

        vs = Dictionary(
            title=_("General Properties"),
            render="form",
            optional_keys=False,
            elements=parameters,
            headers=keys_by_topic,
            validate=validate_id(
                mode, {p.name(): p for p in cls.permitted_instances_sorted() if p.is_mine()}
            ),
        )

        varprefix = ""
        if request.get_ascii_input("filled_in") == "edit" and transactions.check_transaction():
            try:
                new_page_dict = vs.from_html_vars(varprefix)
                vs.validate_value(new_page_dict, varprefix)
            except MKUserError as e:
                user_errors.add(e)

            # Take over keys from previous value that are specific to the page type
            # and not edited here.
            if mode in ("edit", "clone"):
                page_dict.update(new_page_dict)
            else:
                page_dict = new_page_dict
                page_dict["owner"] = str(user.id)  # because is not in vs elements

            new_page = cls(page_dict)

            if not user_errors:
                cls.add_page(new_page)
                cls.save_user_instances(owner_id)
                if mode == "create":
                    redirect_url = new_page.after_create_url() or back_url
                else:
                    redirect_url = back_url

                flash(_("Your changes haven been saved."))

                # Reload sidebar.TODO: This code logically belongs to PageRenderer. How
                # can we simply move it there?
                # TODO: This is not true for all cases. e.g. the BookmarkList is not
                # of type PageRenderer but has a dedicated sidebar snapin. Maybe
                # the best option would be to make a dedicated method to decide whether
                # or not to reload the sidebar.
                if not page_dict.get("hidden") or new_page_dict.get("hidden") != page_dict.get(
                    "hidden"
                ):
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

    def has_reporting():
        try:
            # The suppression below is OK, we just want to check if the module is there.
            import cmk.gui.cee.reporting as _dummy  # noqa: F401 # pylint: disable=import-outside-toplevel

            return True
        except ImportError:
            return False

    if has_reporting() and current_type_name != "reports":
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


def vs_no_permission_to_publish(type_title: str, title: str) -> FixedValue:
    return FixedValue(
        value=False,
        title=title,
        totext=_(
            "The %s is only visible to you because you don't have the " "permission to share it."
        )
        % type_title.lower(),
    )


def PublishTo(
    publish_all: bool,
    publish_groups: bool,
    title: _Optional[str] = None,
    type_title: _Optional[str] = None,
    with_foreign_groups: bool = True,
) -> CascadingDropdown:
    if title is None:
        title = _("Make this %s available for other users") % type_title

    choices: List[CascadingDropdownChoice] = []
    if publish_all:
        choices.append((True, _("Publish to all users")))

    if publish_groups or with_foreign_groups:
        choices.append(
            (
                "contact_groups",
                _("Publish to members of contact groups"),
                ContactGroupChoice(
                    with_foreign_groups=with_foreign_groups,
                    title=_("Publish to members of contact groups"),
                    rows=5,
                    size=80,
                ),
            )
        )

    return CascadingDropdown(title=title, choices=choices)


def make_edit_form_page_menu(
    breadcrumb: Breadcrumb,
    dropdown_name: str,
    mode: str,
    type_title: str,
    type_title_plural,
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


_save_pagetype_icons: Dict[str, Icon] = {
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
    "graph_tuning": {
        "icon": "save_graph",
        "emblem": "settings",
    },
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
        title=_("Abort"),
        icon_name="abort",
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
        yield PageMenuEntry(
            title=title,
            icon_name=icon,
            item=make_simple_link(
                makeuri_contextless(
                    request,
                    [(ident_attr_name, visualname)],
                    filename=pagename + ".py",
                )
            ),
        )


class ContactGroupChoice(DualListChoice):
    """A multiple selection of contact groups that are part of the current active config"""

    def __init__(self, with_foreign_groups=True, **kwargs):
        super().__init__(choices=self._load_groups, **kwargs)
        self._with_foreign_groups = with_foreign_groups

    def _load_groups(self):
        contact_group_choices = sites.all_groups("contact")
        return [
            (group_id, alias)
            for (group_id, alias) in contact_group_choices
            if self._with_foreign_groups or group_id in user.contact_groups
        ]


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


class Container(Base):
    def __init__(self, d):
        super().__init__(d)
        self._.setdefault("elements", [])

    # Which kind of elements are allowed to be added to this container?
    # Defaulting to all possible elements.
    @classmethod
    def may_contain(cls, element_type_name):
        return True

    def elements(self):
        return self._["elements"]

    def add_element(self, element):
        self._["elements"].append(element)

    def move_element(self, nr, whither):
        el = self._["elements"][nr]
        del self._["elements"][nr]
        self._["elements"][whither:whither] = [el]

    def is_empty(self):
        return not self.elements()


class OverridableContainer(Overridable, Container):
    @classmethod
    def page_menu_add_to_topics(cls, added_type: str) -> List[PageMenuTopic]:
        if not cls.may_contain(added_type):
            return []

        pages = cls.pages()
        if not pages:
            return []

        return [
            PageMenuTopic(
                title=cls.phrase("add_to"),
                entries=list(cls._page_menu_add_to_entries()),
            )
        ]

    @classmethod
    def _page_menu_add_to_entries(cls) -> Iterator[PageMenuEntry]:
        for page in cls.pages():
            yield PageMenuEntry(
                title=page.title(),
                icon_name=cls.type_name(),
                item=make_javascript_link(
                    "cmk.popup_menu.pagetype_add_to_container(%s, %s);"
                    % (json.dumps(cls.type_name()), json.dumps(page.name()))
                ),
            )

    @classmethod
    def page_handlers(cls):
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
    def ajax_add_element(cls):
        page_type_name = request.get_ascii_input_mandatory("page_type")
        page_name = request.get_ascii_input_mandatory("page_name")
        element_type = request.get_ascii_input_mandatory("element_type")
        create_info = json.loads(request.get_str_input_mandatory("create_info"))

        page_ty = page_types[page_type_name]
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
    def add_element_via_popup(cls, page_name, element_type, create_info):
        cls.need_overriding_permission("edit")

        need_sidebar_reload = False
        cls.load()
        page = cls.find_page(page_name)
        if not page.is_mine():
            page = page.clone()
            if isinstance(page, PageRenderer) and not page.is_hidden():
                need_sidebar_reload = True

        page.add_element(create_info)  # can be overridden
        cls.save_user_instances()
        return None, need_sidebar_reload
        # With a redirect directly to the page afterwards do it like this:
        # return page, need_sidebar_reload


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
page_types = {}


def declare(page_ty):
    page_ty.declare_overriding_permissions()
    page_types[page_ty.type_name()] = page_ty

    for path, page_func in page_ty.page_handlers().items():
        cmk.gui.pages.register_page_handler(path, page_func)


def page_type(page_type_name):
    return page_types[page_type_name]


def has_page_type(page_type_name):
    return page_type_name in page_types


def all_page_types():
    return page_types


# Global module functions for the integration into the rest of the code


def page_menu_add_to_topics(added_type: str) -> List[PageMenuTopic]:
    topics = []
    for page_ty in page_types.values():
        if issubclass(page_ty, Container):
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


class PagetypeTopics(Overridable):
    @classmethod
    def type_name(cls):
        return "pagetype_topic"

    @classmethod
    def type_icon(cls):
        return "pagetype_topic"

    @classmethod
    def phrase(cls, phrase):
        return {
            "title": _("Topic"),
            "title_plural": _("Topics"),
            "clone": _("Clone topic"),
            "create": _("Create topic"),
            "edit": _("Edit topic"),
            "new": _("New topic"),
        }.get(phrase, Base.phrase(phrase))

    @classmethod
    def parameters(cls, mode):
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

    def render_extra_columns(self, table):
        """Show some specific useful columns in the list view"""
        table.cell(_("Icon"), html.render_icon(self._["icon_name"]))
        table.cell(_("Nr. of items"), str(self.max_entries()))
        table.cell(_("Sort index"), str(self._["sort_index"]))

    @classmethod
    def builtin_pages(cls):
        return {
            "overview": {
                "title": _("Overview"),
                "icon_name": "topic_overview",
                "description": "",
                "sort_index": 20,
            },
            "monitoring": {
                "title": _("Monitoring"),
                "icon_name": "topic_monitoring",
                "description": "",
                "sort_index": 30,
            },
            "problems": {
                "title": _("Problems"),
                "icon_name": "topic_problems",
                "description": "",
                "sort_index": 40,
            },
            "history": {
                "title": _("History"),
                "icon_name": "topic_history",
                "description": "",
                "sort_index": 50,
            },
            "analyze": {
                "title": _("System"),
                "icon_name": "topic_checkmk",
                "description": "",
                "sort_index": 60,
            },
            "events": {
                "title": _("Event Console"),
                "icon_name": "topic_events",
                "description": "",
                "sort_index": 70,
            },
            "bi": {
                "title": _("Business Intelligence"),
                "icon_name": "topic_bi",
                "description": "",
                "sort_index": 80,
                "hide": _no_bi_aggregate_active(),
            },
            "applications": {
                "title": _("Applications"),
                "icon_name": "topic_applications",
                "description": "",
                "sort_index": 85,
            },
            "inventory": {
                "title": _("Inventory"),
                "icon_name": "topic_inventory",
                "description": "",
                "sort_index": 90,
            },
            "network_statistics": {
                "title": _("Network statistics"),
                "icon_name": "topic_network_statistics",
                "description": "",
                "sort_index": 95,
                "hide": not is_ntop_configured(),
            },
            "my_workplace": {
                "title": _("Workplace"),
                "icon_name": "topic_my_workplace",
                "description": "",
                "sort_index": 100,
            },
            # Only fallback for items without topic
            "other": {
                "title": _("Other"),
                "icon_name": "topic_other",
                "description": "",
                "sort_index": 105,
            },
        }

    def max_entries(self) -> int:
        return self._.get("max_entries", 10)

    def sort_index(self) -> int:
        return self._["sort_index"]

    def icon_name(self) -> str:
        return self._["icon_name"]

    def hide(self) -> str:
        return self._.get("hide", False)

    @classmethod
    def choices(cls):
        cls.load()
        return [
            (p.name(), p.title()) for p in sorted(cls.instances(), key=lambda p: p.sort_index())
        ]

    @classmethod
    def get_permitted_instances(cls):
        cls.load()
        return {p.name(): p for p in cls.permitted_instances_sorted()}

    @classmethod
    def get_topic(cls, topic_id) -> "PagetypeTopics":
        """Returns either the requested topic or fallback to "other"."""
        PagetypeTopics.load()
        return PagetypeTopics.find_page(topic_id) or PagetypeTopics.find_page("other")


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


def _customize_menu_topics() -> List[TopicMenuTopic]:
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

    if not cmk_version.is_raw_edition():
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
