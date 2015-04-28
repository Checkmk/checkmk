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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import os
import config, table
from lib import *
try:
    import simplejson as json
except ImportError:
    import json


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
    def __init__(self, d):
        # The dictionary with the name _ holds all information about
        # the page in question - as a dictionary that can be loaded
        # and saved to files using repr().
        self._ = d

    def internal_representation(self):
        return self._

    # Object methods that *can* be overridden - for cases where
    # that pages in question of a dictionary format that is not
    # compatible.
    def name(self):
        return self._["name"]

    def title(self):
        return self._["title"]

    def description(self):
        return self._.get("description", "")

    # Store for all instances of this page type. The key into
    # this dictionary????
    # TODO: Brauchen wir hier überhaupt ein dict??
    __instances = {}

    @classmethod
    def clear_instances(self):
        self.__instances = {}

    @classmethod
    def add_instance(self, key, instance):
        self.__instances[key] = instance

    @classmethod
    def remove_instance(self, key):
        del self.__instances[key]

    # Return a list of all instances of this type
    @classmethod
    def instances(self):
        return self.__instances.values()

    @classmethod
    def instance(self, key):
        return self.__instances[key]

    # Return a dict of all instances of this type
    @classmethod
    def instances_dict(self):
        return self.__instances

    # Return a list of pairs if instance key and instance, which
    # is sorted by the title of the instance
    @classmethod
    def instances_sorted(self):
        instances = self.__instances.values()
        instances.sort(cmp = lambda a,b: cmp(a.title(), b.title()))
        return instances

    # Stub function for the list of all pages. In case of Overridable
    # several instances might exist that overlay each other. This
    # function returns the final list of pages visible to the user
    @classmethod
    def pages(self):
        for instance in self.__instances.values():
            return instance


    # Stub function for finding a page by name. Overriden by
    # Overridable.
    @classmethod
    def find_page(self, name):
        for instance in self.__instances.values():
            if instance.name() == name:
                return instance


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

class PageRenderer:
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
    def ident_attr(self):
        return "name"

    def topic(self):
        return self._.get("topic", _("Other"))

    # Helper functions for page handlers and render function
    def page_header(self):
        return self.type_title() + " - " + self.title()

    def page_url(self):
        return html.makeuri_contextless([(self.ident_attr(), self.name())], filename = "%s.py" % self.type_name())


    # Define page handlers for the neccessary pages like listing all pages, editing
    # one and so on. This is being called (indirectly) in index.py. That way we do
    # not need to hard code page handlers for all types of PageTypes in plugins/pages.
    # It is simply sufficient to register a PageType and all page handlers will exist :-)
    @classmethod
    def page_handlers(self):
        return {
            "%ss" % self.type_name()     : lambda: self.page_list(),
            "edit_%s" % self.type_name() : lambda: self.page_edit(),
            self.type_name()             : lambda: self.page_show(),
        }

    # Most important: page for showing the page ;-)
    @classmethod
    def page_show(self):
        name = html.var(self.ident_attr())
        page = self.find_page(name)
        if not page:
            raise MKGeneralException(_("Cannot find %s with the name %s") % (
                        self.type_title(), name))
        page.render()



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
class Overridable:
    def page_header(self):
        header = self.type_title() + " - " + self.title()
        if not self.is_mine():
            header += " (%s)" % self.owner()
        return header

    # Checks wether a page is publicly visible. This does not only need a flag
    # in the page itself, but also the permission from its owner to publish it.
    def is_public(self):
        return self._["public"] and (
            not self.owner() or config.user_may(self.owner(), "general.publish_" + self.type_name()))

    # Same, but checks if the owner has the permission to override builtin views
    def is_public_forced(self):
        return self.is_public() and \
          config.user_may(self.owner(), "general.force_" + self.type_name())


    def is_hidden(self):
        return self._.get("hidden", False)


    # Derived method for conveniance
    def is_builtin(self):
        return not self.owner()


    def is_mine(self):
        return self.owner() == config.user_id

    def owner(self):
        return self._["owner"]

    # Checks if the current user is allowed to see a certain page
    # TODO: Wie is die Semantik hier genau? Umsetzung vervollständigen!
    def may_see(self):
        perm_name = "%s.%s" % (self.type_name(), self.name())
        if config.permission_exists(perm_name) and not config.may(perm_name):
            return False

        # if self.owner() == "" and not config.may(perm_name):
        #    return False

        return True
        #    continue # not allowed to see this view

        # TODO: Permissions
        ### visual = visuals[(owner, visual_name)]
        ### if owner == config.user_id or \
        ###    (visual["public"] and owner != '' and config.user_may(owner, "general.publish_" + what)):
        ###     custom.append((owner, visual_name, visual))
        ### elif visual["public"] and owner == "":
        ###     builtin.append((owner, visual_name, visual))

    def may_delete(self):
        if self.is_builtin():
            return False
        elif self.is_mine():
            return True
        else:
            return config.may('general.delete_foreign_%s' % self.type_name())

    def edit_url(self):
        return "edit_%s.py?load_name=%s" % (self.type_name(), self.name())

    def clone_url(self):
        backurl = html.urlencode(html.makeuri([]))
        return "edit_%s.py?load_user=%s&load_name=%s&back=%s" \
                    % (self.type_name(), self.owner(), self.name(), backurl)

    def delete_url(self):
        add_vars = [('_delete', self.name())]
        if not self.is_mine():
            add_vars.append(('_owner', self.owner()))
        return html.makeactionuri(add_vars)

    @classmethod
    def declare_overriding_permissions(self):
        config.declare_permission("general.edit_" + self.type_name(),
             _("Customize %s and use them") % self.type_title_plural(),
             _("Allows to create own %s, customize builtin %s and use them.") % (self.type_title_plural(), self.type_title_plural()),
             [ "admin", "user" ])

        config.declare_permission("general.publish_" + self.type_name(),
             _("Publish %s") % self.type_title_plural(),
             _("Make %s visible and usable for other users.") % self.type_title_plural(),
             [ "admin", "user" ])

        config.declare_permission("general.see_user_" + self.type_name(),
             _("See user %s") % self.type_title_plural(),
             _("Is needed for seeing %s that other users have created.") % self.type_title_plural(),
             [ "admin", "user", "guest" ])

        config.declare_permission("general.force_" + self.type_name(),
             _("Modify builtin %s") % self.type_title_plural(),
             _("Make own published %s override builtin %s for all users.") % (self.type_title_plural(), self.type_title_plural()),
             [ "admin" ])

        config.declare_permission("general.delete_foreign_" + self.type_name(),
             _("Delete foreign %s") % self.type_title_plural(),
             _("Allows to delete %s created by other users.") % self.type_title_plural(),
             [ "admin" ])


    @classmethod
    def need_overriding_permission(self, how):
        if not config.may("general.%s_%s" % (how, self.type_name())):
            raise MKAuthException(_("Sorry, you lack the permission. Operation: %s, table: %s") % (
                                    how, self.type_title_plural()))



    # Return all pages visible to the user, implements shadowing etc.
    @classmethod
    def pages(self):
        self.load()
        pages = {}

        # Builtin pages
        for page in self.instances():
            if page.is_public() and page.may_see() and page.is_builtin():
                pages[page.name()] = page

        # Public pages by normal other users
        for page in self.instances():
            if page.is_public() and page.may_see():
                pages[page.name()] = page

        # Public pages by admin users, forcing their versions over others
        for page in self.instances():
            if page.is_public() and page.may_see() and page.is_public_forced():
                pages[page.name()] = page

        # My own pages
        for page in self.instances():
            if page.is_mine() and config.may("general.edit_" + self.type_name()):
                pages[page.name()] = page

        return sorted(pages.values(), cmp = lambda a, b: cmp(a.title(), b.title()))


    # Find a page by name, implements shadowing and
    # publishing und overriding by admins
    @classmethod
    def find_page(self, name):
        self.load()

        mine = None
        forced = None
        builtin = None
        foreign = None

        for page in self.instances():
            if page.name() != name:
                continue

            if page.is_mine() and config.may("general.edit_" + self.type_name()):
                mine = page

            elif page.is_public() and page.may_see():
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
        else:
            return None

    # Lädt alle Dinge vom aktuellen User-Homeverzeichnis und
    # mergt diese mit den übergebenen eingebauten
    @classmethod
    def load(self):
        self.clear_instances()

        # First load builtin pages. Set username to ''
        for name, page_dict in self.builtin_pages().items():
            page_dict["owner"]  = '' # might have been forgotten on copy action
            page_dict["public"] = True
            page_dict["name"]   = name
            self.add_instance(("", name), self(page_dict))

        # Now scan users subdirs for files "user_$type_name.mk"
        subdirs = os.listdir(config.config_dir)
        for user in subdirs:
            try:
                path = "%s/%s/user_%ss.mk" % (config.config_dir, user, self.type_name())
                if not os.path.exists(path):
                    continue

                user_pages = eval(file(path).read())
                for name, page_dict in user_pages.items():
                    page_dict["owner"] = user
                    page_dict["name"] = name
                    self.add_instance((user, name), self(page_dict))

            except SyntaxError, e:
                raise MKGeneralException(_("Cannot load %s from %s: %s") % (what, path, e))

        # Declare permissions - one for each of the pages, if it is public
        config.declare_permission_section(self.type_name(), self.type_title_plural(), do_sort = True)

        for instance in self.instances():
            if instance.is_public():
                self.declare_permission(instance)

    @classmethod
    def save_user_instances(self, owner=None):
        if not owner:
            owner = config.user_id

        save_dict = {}
        for page in self.instances():
            if page.owner() == owner:
                save_dict[page.name()] = page.internal_representation()

        config.save_user_file('user_%ss' % self.type_name(), save_dict, user=owner)

    @classmethod
    def add_page(self, new_page):
        self.add_instance((new_page.owner(), new_page.name()), new_page)

    def clone(self):
        page_dict = {}
        page_dict.update(self._)
        page_dict["owner"] = config.user_id
        new_page = self.__class__(page_dict)
        self.add_page(new_page)
        return new_page

    @classmethod
    def declare_permission(self, page):
        permname = "%s.%s" % (self.type_name(), page.name())
        if page.is_public() and not config.permission_exists(permname):
            config.declare_permission(permname, page.title(),
                             page.description(), ['admin','user','guest'])


    @classmethod
    def page_list(self):
        self.load()

        # custom_columns = []
        # render_custom_buttons = None
        # render_custom_columns = None
        # render_custom_context_buttons = None
        # check_deletable_handler = None

        self.need_overriding_permission("edit")

        html.header(self.type_title_plural(), stylesheets=["pages", "views", "status"])
        html.begin_context_buttons()
        html.context_button(_('New'), 'create_%s.py' % self.type_name(), "new_" + self.type_name())

        # TODO: Remove this legacy code as soon as views, dashboards and reports have been
        # moved to pagetypes.py
        html.context_button(_("Views"), "edit_views.py", "view")
        html.context_button(_("Dashboards"), "edit_dashboards.py", "dashboard")
        html.context_button(_("Reports"), "edit_reports.py", "report")

        ### if render_custom_context_buttons:
        ###     render_custom_context_buttons()
        ### for other_what, info in visual_types.items():
        ###     if what != other_what:
        ###         html.context_button(info["plural_title"].title(), 'edit_%s.py' % other_what, other_what[:-1])
        ### html.end_context_buttons()
        html.end_context_buttons()

        # Deletion
        delname  = html.var("_delete")
        if delname and html.transaction_valid():
            owner = html.var('_owner', config.user_id)
            if owner != config.user_id:
                self.need_overriding_permission("delete_foreign")

            instance = self.instance((owner, delname))

            try:
                if owner != config.user_id:
                    owned_by = _(" (owned by %s)") % owner
                else:
                    owned_by = ""
                c = html.confirm(_("Please confirm the deletion of \"%s\"%s.") % (
                  instance.title(), owned_by))
                if c:
                    self.remove_instance((owner, delname))
                    self.save_user_instances(owner)
                    html.reload_sidebar()
                elif c == False:
                    html.footer()
                    return
            except MKUserError, e:
                html.write("<div class=error>%s</div>\n" % e.message)
                html.add_user_error(e.varname, e.message)


        my_instances  = []
        foreign_instances  = []
        builtin_instances = []
        for instance in self.instances_sorted():
            if instance.may_see():
                if instance.is_builtin():
                    builtin_instances.append(instance)
                elif instance.is_mine():
                    my_instances.append(instance)
                else:
                    foreign_instances.append(instance)

        for title, instances in [
            (_('Customized'),           my_instances),
            (_('Owned by other users'), foreign_instances),
            (_('Builtin'),              builtin_instances),
        ]:
            if not instances:
                continue

            html.write('<h3>' + title + '</h3>')

            table.begin(limit = None)
            for instance in instances:
                table.row()

                # Actions
                table.cell(_('Actions'), css = 'buttons visuals')

                # Clone / Customize
                buttontext = _("Create a customized copy of this")
                html.icon_button(instance.clone_url(), buttontext, "new_" + self.type_name())

                # Delete
                if instance.may_delete():
                    html.icon_button(instance.delete_url(), _("Delete!"), "delete")

                # Edit
                # TODO: Reihenfolge der Aktionen. Ist nicht delete immer nach edit? Sollte
                # nicht clone und edit am gleichen Platz sein?
                if instance.is_mine():
                    html.icon_button(instance.edit_url(), _("Edit"), "edit")

                ### # Custom buttons - visual specific
                ### if render_custom_buttons:
                ###     render_custom_buttons(visual_name, visual)

                # Internal ID of instance (we call that 'name')
                table.cell(_('ID'), instance.name())

                # Title
                table.cell(_('Title'))
                title = _u(instance.title())
                if not instance.is_hidden():
                    html.write("<a href=\"%s.py?%s=%s\">%s</a>" %
                        (self.type_name(), self.ident_attr(), instance.name(), html.attrencode(instance.title())))
                else:
                    html.write(html.attrencode(instance.title()))
                html.help(html.attrencode(_u(instance.description())))

                # Custom columns
                ### for title, renderer in custom_columns:
                ###     table.cell(title, renderer(visual))

                # Owner
                if instance.is_builtin():
                    ownertxt = "<i>" + _("builtin") + "</i>"
                else:
                    ownertxt = instance.owner()
                table.cell(_('Owner'), ownertxt)
                table.cell(_('Public'), instance.is_public() and _("yes") or _("no"))
                table.cell(_('Hidden'), instance.is_hidden() and _("yes") or _("no"))

                # TODO: Haeeh? Another custom columns
                ### if render_custom_columns:
                ###     render_custom_columns(visual_name, visual)
            table.end()

        html.footer()
        return

    # Page for editing an existing page, or creating a new one
    @classmethod
    def page_edit(self):
        html.debug("EDIT")


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

class Container(Overridable):
    @classmethod
    def type_add_to_title(self):
        raise MKInternalError("Missing implementation")

    def elements(self):
        return self._.get("elements", [])

    def add_element(self, element):
        self._.setdefault("elements", []).append(element)

    def move_element(self, nr, whither):
        el = self._["elements"][nr]
        del self._["elements"][nr]
        self._["elements"][whither:whither] = [ el ]

    def is_empty(self):
        return not self.elements()

    # The popup for "Add to ...", e.g. for adding a graph to a report
    # or dashboard. This is needed for page types with the aspect "ElementContainer".
    @classmethod
    def render_addto_popup(self):
        pages = self.pages()
        if pages:
            html.write('<li><span>%s:</span></li>' % self.type_add_to_title())
            for page in pages:
                html.write('<li><a href="javascript:void(0)" '
                           'onclick="pagetype_add_to_container(\'%s\', \'%s\'); reload_sidebar();"><img src="images/icon_%s.png"> %s</a></li>' %
                           (self.type_name(), page.name(), self.type_name(), page.title()))


    # Callback for the Javascript function pagetype_add_to_container(). The
    # create_info will contain a dictionary that is known to the underlying
    # element. Note: this is being called with the base class object Container,
    # not with any actual subclass like GraphCollection. We need to find that
    # class by the URL variable page_type.
    @classmethod
    def ajax_add_element(self):
        page_type_name = html.var("page_type")
        page_name      = html.var("page_name")
        element_type   = html.var("element_type")
        create_info    = json.loads(html.var("create_info"))

        page_type = page_types[page_type_name]
        target_page, need_sidebar_reload = page_type.add_element_via_popup(page_name, element_type, create_info)
        if target_page:
            # Redirect user to that page
            html.write(target_page.page_url())
        html.write("\n%s" % (need_sidebar_reload and "true" or "false"))


    # Default implementation for generic containers - used e.g. by GraphCollection
    @classmethod
    def add_element_via_popup(self, page_name, element_type, create_info):
        self.need_overriding_permission("edit")

        need_sidebar_reload = False
        page = self.find_page(page_name)
        if not page.is_mine():
            page = page.clone()
            if isinstance(page, PageRenderer) and not page.is_hidden():
                need_sidebar_reload = True

        page.add_element(create_info) # can be overridden
        self.save_user_instances()
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

def declare(page_type):
    page_type.declare_overriding_permissions()
    page_types[page_type.type_name()] = page_type

def page_type(page_type_name):
    return page_types[page_type_name]

def has_page_type(page_type_name):
    return page_type_name in page_types


# Global module functions for the integration into the rest of the code

# index.py uses the following function in order to complete its
# page handler table
def page_handlers():
    page_handlers = {}
    for page_type in page_types.values():
        page_handlers.update(page_type.page_handlers())

    # Ajax handler for adding elements to a container
    # TODO: Shouldn't we move that declaration into the class?
    page_handlers["ajax_pagetype_add_element"] = lambda: Container.ajax_add_element()
    return page_handlers


def render_addto_popup():
    for page_type in page_types.values():
        # TODO: Wie sorgen wir dafür, dass nur geeignete Elemente zum hinzufügen
        # angeboten werden? Eine View in eine GraphCollection macht keinen Sinn...
        if issubclass(page_type, Container):
            page_type.render_addto_popup()
