#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

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

import os
import json

import cmk.utils.store as store

import cmk.gui.pages
import cmk.gui.sites as sites
import cmk.gui.config as config
from cmk.gui.table import table_element
import cmk.gui.forms as forms
import cmk.gui.userdb as userdb
from cmk.gui.valuespec import (
    ID,
    Dictionary,
    Checkbox,
    TextUnicode,
    TextAreaUnicode,
    CascadingDropdown,
    DualListChoice,
    Optional,
)
from cmk.gui.i18n import _u, _
from cmk.gui.globals import html

from cmk.gui.exceptions import (
    MKUserError,
    MKGeneralException,
    MKAuthException,
)
from cmk.gui.permissions import (
    permission_registry,
    declare_permission_section,
    declare_permission,
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


class Base(object):
    def __init__(self, d):
        super(Base, self).__init__()

        # The dictionary with the name _ holds all information about
        # the page in question - as a dictionary that can be loaded
        # and saved to files using repr().
        self._ = d

    def internal_representation(self):
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
    def phrase(cls, phrase):
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
        return [(_("General Properties"), [
            (1.1, 'name',
             ID(
                 title=_('Unique ID'),
                 help=
                 _("The ID will be used do identify this page in URLs. If this page has the "
                   "same ID as a builtin page of the type <i>%s</i> then it will shadow the builtin one."
                  ) % cls.phrase("title"),
             )),
            (1.2, 'title',
             TextUnicode(
                 title=_('Title') + '<sup>*</sup>',
                 size=50,
                 allow_empty=False,
             )),
            (1.3, 'description',
             TextAreaUnicode(
                 title=_('Description') + '<sup>*</sup>',
                 help=_(
                     "The description is optional and can be used for explanations or documentation"
                 ),
                 rows=4,
                 cols=50,
             )),
        ])]

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
        topics = {}
        for topic, elements in cls.parameters(mode):
            el = topics.setdefault(topic, [])
            el += elements

        # Sort topics and elements in the topics
        for topic in topics.values():
            topic.sort()

        sorted_topics = topics.items()
        sorted_topics.sort(key=lambda x: x[1][0])

        # Now remove order numbers and produce the structures for the Dictionary VS
        parameters, keys_by_topic = [], []
        for topic, elements in sorted_topics:
            topic_keys = []

            for _unused_order, key, vs in elements:
                parameters.append((key, vs))
                topic_keys.append(key)

            keys_by_topic.append((topic, topic_keys))

        return parameters, keys_by_topic

    # Object methods that *can* be overridden - for cases where
    # that pages in question of a dictionary format that is not
    # compatible.
    def name(self):
        return self._["name"]

    def title(self):
        return self._["title"]

    def description(self):
        return self._.get("description", "")

    def is_hidden(self):
        return False

    def _can_be_linked(self):
        return True

    def render_title(self):
        return _u(self.title())

    def is_empty(self):
        return False

    def _show_in_sidebar(self):
        return not self.is_empty() and not self.is_hidden()

    # Default values for the creation dialog can be overridden by the
    # sub class.
    @classmethod
    def default_name(cls):
        stem = cls.type_name()
        nr = 1
        while True:
            name = "%s_%d" % (stem, nr)
            conflict = False
            for instance in cls.__instances.values():
                if instance.name() == name:
                    conflict = True
                    break
            if not conflict:
                return name
            else:
                nr += 1

    @classmethod
    def default_topic(cls):
        return _("Other")

    # Store for all instances of this page type. The key into
    # this dictionary????
    # TODO: Brauchen wir hier überhaupt ein dict??
    __instances = {}

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
        return cls.__instances.values()

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
        instances = cls.__instances.values()
        instances.sort(key=lambda x: x.title())
        return instances

    # Stub function for the list of all pages. In case of Overridable
    # several instances might exist that overlay each other. This
    # function returns the final list of pages visible to the user
    @classmethod
    def pages(cls):
        for instance in cls.__instances.values():
            return instance

    # Stub function for finding a page by name. Overriden by
    # Overridable.
    @classmethod
    def find_page(cls, name):
        for instance in cls.__instances.values():
            if instance.name() == name:
                return instance

    @classmethod
    def type_name(cls):
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


#.
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
        parameters = super(PageRenderer, cls).parameters(mode)

        parameters += [(_("General Properties"), [
            (1.4, 'topic',
             TextUnicode(
                 title=_('Topic') + '<sup>*</sup>',
                 size=50,
                 allow_empty=False,
             )),
            (2.0, 'hidden',
             Checkbox(
                 title=_("Sidebar integration"),
                 label=_('Do not add a link to this page in sidebar'),
             )),
        ])]

        return parameters

    @classmethod
    def page_handlers(cls):
        handlers = super(PageRenderer, cls).page_handlers()
        handlers.update({
            cls.type_name(): cls.page_show,
        })
        return handlers

    # Most important: page for showing the page ;-)
    @classmethod
    def page_show(cls):
        page = cls.requested_page()
        page.render()

    @classmethod
    def requested_page(cls):
        name = html.request.var(cls.ident_attr())
        cls.load()
        page = cls.find_page(name)
        if not page:
            raise MKGeneralException(
                _("Cannot find %s with the name %s") % (cls.phrase("title"), name))
        return page

    # Links for the sidebar
    @classmethod
    def sidebar_links(cls):
        for page in cls.pages():
            if page._show_in_sidebar():
                yield page.topic(), page.title(), page.page_url()

    def topic(self):
        return self._.get("topic", _("Other"))

    # Helper functions for page handlers and render function
    def page_header(self):
        return self.phrase("title") + " - " + self.title()

    def page_url(self):
        return html.makeuri_contextless([(self.ident_attr(), self.name())],
                                        filename="%s.py" % self.type_name())

    def render_title(self):
        if self._can_be_linked():
            return html.render_a(self.title(), href=self.page_url())
        return self.title()


#.
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
        super(Overridable, self).__init__(d)
        self._.setdefault("public", False)

    @classmethod
    def parameters(cls, mode):
        parameters = super(Overridable, cls).parameters(mode)

        if cls.has_overriding_permission("publish"):

            parameters += [
                (_("General Properties"), [
                    (2.2, 'public',
                     Optional(
                         title=_("Visibility"),
                         label=_('Make this %s available for other users') % cls.phrase("title"),
                         none_label=_("Don't publish to other users"),
                         none_value=False,
                         valuespec=PublishTo(
                             title="",
                             type_title=cls.phrase("title"),
                             with_foreign_groups=cls.has_overriding_permission(
                                 "publish_to_foreign_groups"),
                         ),
                     )),
                ]),
            ]

        return parameters

    @classmethod
    def page_handlers(cls):
        handlers = super(Overridable, cls).page_handlers()
        handlers.update({
            "%ss" % cls.type_name(): cls.page_list,
            "edit_%s" % cls.type_name(): cls.page_edit,
        })
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

        return not self.owner() or config.user_may(self.owner(),
                                                   "general.publish_" + self.type_name())

    # Same, but checks if the owner has the permission to override builtin views
    def is_public_forced(self):
        return self.is_public() and \
          config.user_may(self.owner(), "general.force_" + self.type_name())

    def is_published_to_me(self):
        """Whether or not the page is published to the currently active user"""
        if self._["public"] is True:
            return True

        if isinstance(self._["public"], tuple) and self._["public"][0] == "contact_groups":
            if set(config.user.contact_groups()).intersection(self._["public"][1]):
                return True

        return False

    def is_hidden(self):
        return self._.get("hidden", False)

    # Derived method for conveniance
    def is_builtin(self):
        return not self.owner()

    def is_mine(self):
        return self.owner() == config.user.id

    def is_mine_and_may_have_own(self):
        return self.is_mine() and config.user.may("general.edit_" + self.type_name())

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

    def owner(self):
        return self._["owner"]

    # Checks if the current user is allowed to see a certain page
    # TODO: Wie is die Semantik hier genau? Umsetzung vervollständigen!
    def may_see(self):
        perm_name = "%s.%s" % (self.type_name(), self.name())
        if perm_name in permission_registry and not config.user.may(perm_name):
            return False

        # if self.owner() == "" and not config.user.may(perm_name):
        #    return False

        return True
        #    continue # not allowed to see this view

        # TODO: Permissions
        ### visual = visuals[(owner, visual_name)]
        ### if owner == config.user.id or \
        ###    (visual["public"] and owner != '' and config.user_may(owner, "general.publish_" + what)):
        ###     custom.append((owner, visual_name, visual))
        ### elif visual["public"] and owner == "":
        ###     builtin.append((owner, visual_name, visual))

    @classmethod
    def permitted_instances_sorted(cls):
        instances = []
        for instance in cls.instances_sorted():
            if (instance.is_mine() and instance.may_see()) or \
               (not instance.is_mine() and instance.is_published_to_me() and instance.may_see()):
                instances.append(instance)
        return instances

    def may_delete(self):
        if self.is_builtin():
            return False
        elif self.is_mine() and config.user.may(self._delete_permission()):
            return True
        return config.user.may('general.delete_foreign_%s' % self.type_name())

    def may_edit(self):
        if self.is_builtin():
            return False
        elif self.is_mine() and config.user.may("general.edit_%s" % self.type_name()):
            return True
        return config.user.may('general.edit_foreign_%s' % self.type_name())

    def edit_url(self):
        owner = ("&owner=%s" % self.owner()) if not self.is_mine() else ""
        return "edit_%s.py?load_name=%s%s" % (self.type_name(), self.name(), owner)

    def clone_url(self):
        backurl = html.urlencode(html.makeuri([]))
        return "edit_%s.py?load_user=%s&load_name=%s&mode=clone&back=%s" \
                    % (self.type_name(), self.owner(), self.name(), backurl)

    def delete_url(self):
        add_vars = [('_delete', self.name())]
        if not self.is_mine():
            add_vars.append(('_owner', self.owner()))
        return html.makeactionuri(add_vars)

    @classmethod
    def create_url(cls):
        return "edit_%s.py?mode=create" % cls.type_name()

    @classmethod
    def list_url(cls):
        return "%ss.py" % cls.type_name()

    def after_create_url(self):
        return None  # where redirect after a create should go

    @classmethod
    def context_button_list(cls):
        html.context_button(cls.phrase("title_plural"), cls.list_url(), cls.type_name())

    def context_button_edit(self):
        html.context_button(_("Edit"), self.edit_url(), "edit")

    @classmethod
    def declare_overriding_permissions(cls):
        declare_permission_section(cls.type_name(), cls.phrase("title_plural"), do_sort=True)

        declare_permission(
            "general.edit_" + cls.type_name(),
            _("Customize %s and use them") % cls.phrase("title_plural"),
            _("Allows to create own %s, customize builtin %s and use them.") %
            (cls.phrase("title_plural"), cls.phrase("title_plural")),
            ["admin", "user"],
        )

        declare_permission(
            "general.publish_" + cls.type_name(),
            _("Publish %s") % cls.phrase("title_plural"),
            _("Make %s visible and usable for other users.") % cls.phrase("title_plural"),
            ["admin", "user"],
        )

        config.declare_permission(
            "general.publish_to_foreign_groups_" + cls.type_name(),
            _("Publish %s to foreign contact groups") % cls.phrase("title_plural"),
            _("Make %s visible and usable for users of contact groups the publishing user is not a member of."
             ) % cls.phrase("title_plural"),
            ["admin"],
        )

        # TODO: Bug: This permission does not seem to be used
        declare_permission(
            "general.see_user_" + cls.type_name(),
            _("See user %s") % cls.phrase("title_plural"),
            _("Is needed for seeing %s that other users have created.") %
            cls.phrase("title_plural"),
            ["admin", "user", "guest"],
        )

        declare_permission(
            "general.force_" + cls.type_name(),
            _("Modify builtin %s") % cls.phrase("title_plural"),
            _("Make own published %s override builtin %s for all users.") %
            (cls.phrase("title_plural"), cls.phrase("title_plural")),
            ["admin"],
        )

        declare_permission(
            "general.edit_foreign_" + cls.type_name(),
            _("Edit foreign %s") % cls.phrase("title_plural"),
            _("Allows to edit %s created by other users.") % cls.phrase("title_plural"),
            ["admin"],
        )

        declare_permission(
            "general.delete_foreign_" + cls.type_name(),
            _("Delete foreign %s") % cls.phrase("title_plural"),
            _("Allows to delete %s created by other users.") % cls.phrase("title_plural"),
            ["admin"],
        )

    @classmethod
    def has_overriding_permission(cls, how):
        return config.user.may("general.%s_%s" % (how, cls.type_name()))

    @classmethod
    def need_overriding_permission(cls, how):
        if not cls.has_overriding_permission(how):
            raise MKAuthException(
                _("Sorry, you lack the permission. Operation: %s, table: %s") %
                (how, cls.phrase("title_plural")))

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
        elif forced:
            return forced
        elif builtin:
            return builtin
        elif foreign:
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
            page_dict["owner"] = ''  # might have been forgotten on copy action
            page_dict["public"] = True
            page_dict["name"] = name
            new_page = cls(page_dict)
            cls.add_instance(("", name), new_page)

        # Now scan users subdirs for files "user_$type_name.mk"
        for user in os.listdir(config.config_dir):
            user = user.decode("utf-8")
            try:
                path = "%s/%s/user_%ss.mk" % (config.config_dir, user.encode("utf-8"),
                                              cls.type_name())
                if not os.path.exists(path):
                    continue

                if not userdb.user_exists(user):
                    continue

                user_pages = store.load_data_from_file(path, {})
                for name, page_dict in user_pages.items():
                    page_dict["owner"] = user
                    page_dict["name"] = name
                    cls.add_instance((user, name), cls(page_dict))

            except SyntaxError as e:
                raise MKGeneralException(
                    _("Cannot load %s from %s: %s") % (cls.type_name(), path, e))

        cls._load()
        cls._declare_instance_permissions()

    @classmethod
    def _declare_instance_permissions(cls):
        for instance in cls.instances():
            if instance.is_public():
                cls.declare_permission(instance)

    @classmethod
    def save_user_instances(cls, owner=None):
        if not owner:
            owner = config.user.id

        save_dict = {}
        for page in cls.instances():
            if page.owner() == owner:
                save_dict[page.name()] = page.internal_representation()

        config.save_user_file('user_%ss' % cls.type_name(), save_dict, owner)

    @classmethod
    def add_page(cls, new_page):
        cls.add_instance((new_page.owner(), new_page.name()), new_page)

    def clone(self):
        page_dict = {}
        page_dict.update(self._)
        page_dict["owner"] = config.user.id
        new_page = self.__class__(page_dict)
        self.add_page(new_page)
        return new_page

    @classmethod
    def declare_permission(cls, page):
        permname = "%s.%s" % (cls.type_name(), page.name())
        if page.is_public() and permname not in permission_registry:
            declare_permission(permname, page.title(), page.description(),
                               ['admin', 'user', 'guest'])

    @classmethod
    def custom_list_buttons(cls, instance):
        pass

    @classmethod
    def page_list(cls):
        cls.load()

        # custom_columns = []
        # render_custom_buttons = None
        # render_custom_columns = None
        # render_custom_context_buttons = None
        # check_deletable_handler = None

        cls.need_overriding_permission("edit")

        html.header(cls.phrase("title_plural"))
        html.begin_context_buttons()
        html.context_button(cls.phrase("new"), cls.create_url(), "new_" + cls.type_name())

        # TODO: Remove this legacy code as soon as views, dashboards and reports have been
        # moved to pagetypes.py
        html.context_button(_("Views"), "edit_views.py", "view")
        html.context_button(_("Dashboards"), "edit_dashboards.py", "dashboard")

        def has_reporting():
            try:
                # The suppression below is OK, we just want to check if the module is there.
                import cmk.gui.cee.reporting  # pylint: disable=unused-variable,redefined-outer-name
                return True
            except ImportError:
                return False

        if has_reporting():
            html.context_button(_("Reports"), "edit_reports.py", "report")

        ### if render_custom_context_buttons:
        ###     render_custom_context_buttons()

        for other_type_name, other_pagetype in page_types.items():
            if cls.type_name() != other_type_name:
                html.context_button(
                    other_pagetype.phrase("title_plural").title(), '%ss.py' % other_type_name,
                    other_type_name)
        html.end_context_buttons()

        # Deletion
        delname = html.request.var("_delete")
        if delname and html.transaction_valid():
            owner = html.request.var('_owner', config.user.id)

            try:
                instance = cls.instance((owner, delname))
            except KeyError:
                raise MKUserError(
                    "_delete",
                    _("The %s you are trying to delete "
                      "does not exist.") % cls.phrase("title"))

            if not instance.may_delete():
                raise MKUserError("_delete", _("You are not permitted to perform this action."))

            try:
                if owner != config.user.id:
                    owned_by = _(" (owned by %s)") % owner
                else:
                    owned_by = ""
                c = html.confirm(
                    _("Please confirm the deletion of \"%s\"%s.") % (instance.title(), owned_by))
                if c:
                    cls.remove_instance((owner, delname))
                    cls.save_user_instances(owner)
                    html.reload_sidebar()
                elif c is False:
                    html.footer()
                    return
            except MKUserError as e:
                html.user_error(e)

        # Bulk delete
        if html.request.var("_bulk_delete_my") and html.transaction_valid():
            if cls._bulk_delete_after_confirm("my") is False:
                html.footer()
                return

        elif html.request.var("_bulk_delete_foreign") and html.transaction_valid():
            if cls._bulk_delete_after_confirm("foreign") is False:
                html.footer()
                return

        my_instances, foreign_instances, builtin_instances = cls.get_instances()
        for what, title, instances in [
            ("my", _('Customized'), my_instances),
            ("foreign", _('Owned by other users'), foreign_instances),
            ("builtin", _('Builtin'), builtin_instances),
        ]:
            if not instances:
                continue

            html.open_h3()
            html.write(title)
            html.close_h3()

            if what != "builtin":
                html.begin_form("bulk_delete_%s" % what, method="POST")

            with table_element(limit=None) as table:
                for instance in instances:
                    table.row()

                    if what != "builtin" and instance.may_delete():
                        table.cell(html.render_input(
                            "_toggle_group",
                            type_="button",
                            class_="checkgroup",
                            onclick="cmk.selection.toggle_all_rows(this.form);",
                            value='X'),
                                   sortable=False,
                                   css="checkbox")
                        html.checkbox("_c_%s+%s+%s" % (what, instance.owner(), instance.name()))

                    # Actions
                    table.cell(_('Actions'), css='buttons visuals')

                    # Clone / Customize
                    buttontext = _("Create a customized copy of this")
                    html.icon_button(instance.clone_url(), buttontext, "new_" + cls.type_name())

                    # Delete
                    if instance.may_delete():
                        html.icon_button(instance.delete_url(), _("Delete!"), "delete")

                    # Edit
                    if instance.may_edit():
                        html.icon_button(instance.edit_url(), _("Edit"), "edit")

                    cls.custom_list_buttons(instance)

                    # Internal ID of instance (we call that 'name')
                    table.cell(_('ID'), instance.name(), css="narrow")

                    # Title
                    table.cell(_('Title'))
                    html.write_text(instance.render_title())
                    html.help(_u(instance.description()))

                    # Custom columns specific to that page type
                    instance.render_extra_columns(table)

                    ### for title, renderer in custom_columns:
                    ###     table.cell(title, renderer(visual))

                    # Owner
                    if instance.is_builtin():
                        ownertxt = html.i(_("builtin"))
                    else:
                        ownertxt = instance.owner()
                    table.cell(_('Owner'), ownertxt)
                    table.cell(_('Public'), _("yes") if instance.is_public() else _("no"))
                    table.cell(_('Hidden'), _("yes") if instance.is_hidden() else _("no"))

                    # FIXME: WTF?!?
                    # TODO: Haeeh? Another custom columns
                    ### if render_custom_columns:
                    ###     render_custom_columns(visual_name, visual)

            if what != "builtin":
                html.button("_bulk_delete_%s" % what,
                            _("Bulk delete"),
                            "submit",
                            style="margin-top:10px")
                html.hidden_fields()
                html.end_form()

        html.footer()
        return

    @classmethod
    def get_instances(cls):
        my_instances, foreign_instances, builtin_instances = [], [], []

        for instance in cls.instances_sorted():
            if instance.may_see():
                if instance.is_builtin():
                    builtin_instances.append(instance)
                elif instance.is_mine():
                    my_instances.append(instance)
                elif instance.is_published_to_me() \
                     or instance.may_delete() or instance.may_edit():
                    foreign_instances.append(instance)

        return my_instances, foreign_instances, builtin_instances

    @classmethod
    def _bulk_delete_after_confirm(cls, what):
        to_delete = []
        for varname, _value in html.request.itervars(prefix="_c_%s+" % what):
            if html.get_checkbox(varname):
                checkbox_ident = varname.split("_c_%s+" % what)[-1]
                to_delete.append(checkbox_ident.split("+", 1))

        if not to_delete:
            return

        c = html.confirm(
            _("Do you really want to delete %d %s?") % (len(to_delete), cls.phrase("title_plural")))

        if c:
            for owner, instance_id in to_delete:
                cls.remove_instance((owner, instance_id))

            for owner in {e[0] for e in to_delete}:
                cls.save_user_instances(owner)

            html.reload_sidebar()
        elif c is False:
            return False

    # Override this in order to display additional columns of an instance
    # in the table of all instances.
    def render_extra_columns(self, table):
        pass

    # Page for editing an existing page, or creating a new one
    @classmethod
    def page_edit(cls):
        back_url = html.get_url_input("back", cls.list_url())

        cls.load()
        cls.need_overriding_permission("edit")

        # Three possible modes:
        # "create" -> create completely new page
        # "clone"  -> like new, but prefill form with values from existing page
        # "edit"   -> edit existing page
        mode = html.request.var('mode', 'edit')
        if mode == "create":
            title = cls.phrase("create")
            page_dict = {
                "name": cls.default_name(),
                "topic": cls.default_topic(),
            }
        else:
            # Load existing page. visual from disk - and create a copy if 'load_user' is set
            page_name = html.request.var("load_name")
            if mode == "edit":
                title = cls.phrase("edit")

                owner_user_id = html.request.var("owner", config.user.id)
                if owner_user_id == config.user.id:
                    page = cls.find_my_page(page_name)
                else:
                    page = cls.find_foreign_page(owner_user_id, page_name)

                if page is None:
                    raise MKUserError(None,
                                      _("The requested %s does not exist") % cls.phrase("title"))

                # TODO FIXME: Looks like a hack
                cls.remove_instance((owner_user_id, page_name))  # will be added later again
            else:  # clone
                title = cls.phrase("clone")
                load_user = html.get_unicode_input("load_user")  # FIXME: Change varname to "owner"

                try:
                    page = cls.instance((load_user, page_name))
                except KeyError:
                    raise MKUserError(None,
                                      _("The requested %s does not exist") % cls.phrase("title"))
            page_dict = page.internal_representation()

        html.header(title)
        html.begin_context_buttons()
        html.context_button(_("Back"), back_url, "back")
        html.end_context_buttons()

        parameters, keys_by_topic = cls._collect_parameters(mode)
        vs = Dictionary(
            title=_("General Properties"),
            render='form',
            optional_keys=None,
            elements=parameters,
            headers=keys_by_topic,
        )

        def validate(page_dict):
            owner_user_id = html.request.var("owner", config.user.id)
            page_name = page_dict["name"]
            if owner_user_id == config.user.id:
                page = cls.find_my_page(page_name)
            else:
                page = cls.find_foreign_page(owner_user_id, page_name)
            if page:
                raise MKUserError(
                    "_p_name",
                    _("You already have an element with the ID <b>%s</b>") % page_dict["name"])

        new_page_dict = forms.edit_valuespec(vs,
                                             page_dict,
                                             validate=validate,
                                             focus="_p_title",
                                             method="POST")
        if new_page_dict is not None:
            # Take over keys from previous value that are specific to the page type
            # and not edited here.
            if mode in ("edit", "clone"):
                for key, value in page_dict.items():
                    new_page_dict.setdefault(key, value)

            owner = html.request.var("owner", config.user.id)
            new_page_dict["owner"] = owner
            new_page = cls(new_page_dict)

            cls.add_page(new_page)
            cls.save_user_instances(owner)
            if mode == "create":
                redirect_url = new_page.after_create_url() or back_url
            else:
                redirect_url = back_url

            html.immediate_browser_redirect(0.5, redirect_url)
            html.message(_('Your changes haven been saved.'))
            # Reload sidebar.TODO: This code logically belongs to PageRenderer. How
            # can we simply move it there?
            # TODO: This is not true for all cases. e.g. the BookmarkList is not
            # of type PageRenderer but has a dedicated sidebar snapin. Maybe
            # the best option would be to make a dedicated method to decide whether
            # or not to reload the sidebar.
            if new_page_dict.get("hidden") in [ None, False ] \
               or new_page_dict.get("hidden") != page_dict.get("hidden"):
                html.reload_sidebar()

        else:
            html.show_localization_hint()

        html.footer()
        return


class PublishTo(CascadingDropdown):
    def __init__(self, type_title=None, with_foreign_groups=True, **kwargs):
        kwargs.setdefault("title", _('Make this %s available for other users') % type_title)
        super(PublishTo, self).__init__(choices=[
            (True, _("Publish to all users")),
            ("contact_groups", _("Publish to members of contact groups"),
             ContactGroupChoice(
                 with_foreign_groups=with_foreign_groups,
                 title=_("Publish to members of contact groups"),
                 rows=5,
                 size=80,
             )),
        ],
                                        **kwargs)


class ContactGroupChoice(DualListChoice):
    """A multiple selection of contact groups that are part of the current active config"""
    def __init__(self, with_foreign_groups=True, **kwargs):
        super(ContactGroupChoice, self).__init__(choices=self._load_groups, **kwargs)
        self._with_foreign_groups = with_foreign_groups

    def _load_groups(self):
        contact_group_choices = sites.all_groups("contact")
        return [(group_id, alias)
                for (group_id, alias) in contact_group_choices
                if self._with_foreign_groups or group_id in config.user.contact_groups()]


#.
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
        super(Container, self).__init__(d)
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
    # The popup for "Add to ...", e.g. for adding a graph to a report
    # or dashboard. This is needed for page types with the aspect "ElementContainer".
    @classmethod
    def render_addto_popup(cls, added_type):
        if not cls.may_contain(added_type):
            return

        pages = cls.pages()
        if pages:
            cls.render_addto_popup_title(cls.phrase("add_to"))
            for page in pages:
                cls.render_addto_popup_entry(cls.type_name(), page.name(), page.title())

    # Helper functions for layouting the add-to popup
    @classmethod
    def render_addto_popup_title(cls, title):
        html.open_li()
        html.open_span()
        html.write("%s:" % title)
        html.close_span()
        html.close_li()

    @classmethod
    def render_addto_popup_entry(cls, type_name, name, title):
        html.open_li()
        html.open_a(
            href="javascript:void(0)",
            onclick=
            "cmk.popup_menu.pagetype_add_to_container('%s', '%s');cmk.utils.reload_sidebar();" %
            (type_name, name))
        html.render_icon(type_name)
        html.write_text(title)
        html.close_a()
        html.close_li()

    @classmethod
    def page_handlers(cls):
        handlers = super(OverridableContainer, cls).page_handlers()
        handlers.update({
            # Ajax handler for adding elements to a container
            "ajax_pagetype_add_element": cls.ajax_add_element
        })
        return handlers

    # Callback for the Javascript function cmk.popup_menu.pagetype_add_to_container(). The
    # create_info will contain a dictionary that is known to the underlying
    # element. Note: this is being called with the base class object Container,
    # not with any actual subclass like GraphCollection. We need to find that
    # class by the URL variable page_type.
    @classmethod
    def ajax_add_element(cls):
        page_type_name = html.request.var("page_type")
        page_name = html.request.var("page_name")
        element_type = html.request.var("element_type")
        create_info = json.loads(html.request.var("create_info"))

        page_ty = page_types[page_type_name]
        target_page, need_sidebar_reload = page_ty.add_element_via_popup(
            page_name, element_type, create_info)
        # Redirect user to tha page this displays the thing we just added to
        if target_page:
            if not isinstance(target_page, str):
                target_page = target_page.page_url()
            html.write(target_page)
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


#.
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


def render_addto_popup(added_type):
    for page_ty in page_types.values():
        if issubclass(page_ty, Container):
            page_ty.render_addto_popup(added_type)
