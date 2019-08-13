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

import functools
import os
import copy
import sys
import traceback
import json
from typing import Dict, List, Type, Callable  # pylint: disable=unused-import

import cmk.gui.pages
import cmk.gui.utils as utils
from cmk.gui.log import logger
from cmk.gui.exceptions import HTTPRedirect, MKGeneralException, MKAuthException, MKUserError
from cmk.gui.permissions import declare_permission
from cmk.gui.pages import page_registry
from cmk.gui.valuespec import (
    Dictionary,
    ListChoice,
    ValueSpec,
    ListOfMultiple,
    ABCPageListOfMultipleGetChoice,
    FixedValue,
    IconSelector,
    TextUnicode,
    TextAscii,
    TextAreaUnicode,
)
import cmk.gui.config as config
import cmk.gui.forms as forms
from cmk.gui.table import table_element
import cmk.gui.userdb as userdb
import cmk.gui.pagetypes as pagetypes
import cmk.utils.store as store
import cmk.gui.metrics as metrics
import cmk.gui.i18n
from cmk.gui.i18n import _u, _
from cmk.gui.globals import html

from cmk.gui.plugins.visuals.utils import (
    visual_info_registry,
    visual_type_registry,
    filter_registry,
)

# Needed for legacy (pre 1.6) plugins
from cmk.gui.plugins.visuals.utils import (  # pylint: disable=unused-import
    Filter, FilterTime, FilterTristate, FilterUnicodeFilter,
)
from cmk.gui.permissions import permission_registry

if not cmk.is_raw_edition():
    import cmk.gui.cee.plugins.visuals

if cmk.is_managed_edition():
    import cmk.gui.cme.plugins.visuals

#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

loaded_with_language = False
title_functions = []  # type: List[Callable]


def load_plugins(force):
    global loaded_with_language, title_functions
    if loaded_with_language == cmk.gui.i18n.get_current_language() and not force:
        return

    title_functions = []

    utils.load_web_plugins('visuals', globals())

    loaded_with_language = cmk.gui.i18n.get_current_language()


# TODO: This has been obsoleted by pagetypes.py
def declare_visual_permissions(what, what_plural):
    declare_permission(
        "general.edit_" + what,
        _("Customize %s and use them") % what_plural,
        _("Allows to create own %s, customize builtin %s and use them.") %
        (what_plural, what_plural),
        ["admin", "user"],
    )

    declare_permission(
        "general.publish_" + what,
        _("Publish %s") % what_plural,
        _("Make %s visible and usable for other users.") % what_plural,
        ["admin", "user"],
    )

    declare_permission(
        "general.publish_" + what + "_to_foreign_groups",
        _("Publish %s to foreign contact groups") % what_plural,
        _("Make %s visible and usable for users of contact groups the publishing user is not a member of."
         ) % what_plural,
        ["admin"],
    )

    declare_permission(
        "general.see_user_" + what,
        _("See user %s") % what_plural,
        _("Is needed for seeing %s that other users have created.") % what_plural,
        ["admin", "user", "guest"],
    )

    declare_permission(
        "general.force_" + what,
        _("Modify builtin %s") % what_plural,
        _("Make own published %s override builtin %s for all users.") % (what_plural, what_plural),
        ["admin"],
    )

    declare_permission(
        "general.edit_foreign_" + what,
        _("Edit foreign %s") % what_plural,
        _("Allows to edit %s created by other users.") % what_plural,
        ["admin"],
    )

    declare_permission(
        "general.delete_foreign_" + what,
        _("Delete foreign %s") % what_plural,
        _("Allows to delete %s created by other users.") % what_plural,
        ["admin"],
    )


#.
#   .--Save/Load-----------------------------------------------------------.
#   |          ____                     ___                    _           |
#   |         / ___|  __ ___   _____   / / |    ___   __ _  __| |          |
#   |         \___ \ / _` \ \ / / _ \ / /| |   / _ \ / _` |/ _` |          |
#   |          ___) | (_| |\ V /  __// / | |__| (_) | (_| | (_| |          |
#   |         |____/ \__,_| \_/ \___/_/  |_____\___/ \__,_|\__,_|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class UserVisualsCache(object):
    """Realizes a in memory cache (per apache process). This has been introduced to improve the
    situation where there are hundreds of custom visuals (views here). These visuals are rarely
    changed, but read and evaluated(!) during each page request which costs a lot of time."""
    def __init__(self):
        super(UserVisualsCache, self).__init__()
        self._cache = {}

    def get(self, path):
        try:
            cached_mtime, cached_user_visuals = self._cache[path]
            current_mtime = os.stat(path).st_mtime
            return cached_user_visuals if current_mtime <= cached_mtime else None
        except (KeyError, IOError):
            return None

    def add(self, path, modification_timestamp, user_visuals):
        self._cache[path] = modification_timestamp, user_visuals


_user_visuals_cache = UserVisualsCache()


def save(what, visuals, user_id=None):
    if user_id is None:
        user_id = config.user.id

    uservisuals = {}
    for (owner_id, name), visual in visuals.items():
        if user_id == owner_id:
            uservisuals[name] = visual
    config.save_user_file('user_' + what, uservisuals, user_id=user_id)


# FIXME: Currently all user visual files of this type are locked. We could optimize
# this not to lock all files but only lock the files the user is about to modify.
def load(what, builtin_visuals, skip_func=None, lock=False):
    visuals = {}

    # first load builtins. Set username to ''
    for name, visual in builtin_visuals.items():
        visual["owner"] = ''  # might have been forgotten on copy action
        visual["public"] = True
        visual["name"] = name

        # Dashboards had not all COMMON fields in previous versions. Add them
        # here to be compatible for a specific time. Seamless migration, yeah.
        visual.setdefault('description', '')
        visual.setdefault('hidden', False)

        visuals[('', name)] = visual

    # Now scan users subdirs for files "user_*.mk"
    visuals.update(load_user_visuals(what, builtin_visuals, skip_func, lock))

    return visuals


def load_user_visuals(what, builtin_visuals, skip_func, lock):
    visuals = {}

    subdirs = os.listdir(config.config_dir)
    for user in subdirs:
        try:
            dirpath = config.config_dir + "/" + user
            if not os.path.isdir(dirpath):
                continue

            # Be compatible to old views.mk. The views.mk contains customized views
            # in an old format which will be loaded, transformed and when saved stored
            # in users_views.mk. When this file exists only this file is used.
            path = "%s/user_%s.mk" % (dirpath, what)
            if what == 'views' and not os.path.exists(path):
                path = "%s/%s.mk" % (dirpath, what)

            if not os.path.exists(path):
                continue

            if not userdb.user_exists(user):
                continue

            user_visuals = _user_visuals_cache.get(path)
            if user_visuals is None:
                modification_timestamp = os.stat(path).st_mtime
                user_visuals = load_visuals_of_a_user(what, builtin_visuals, skip_func, lock, path,
                                                      user)
                _user_visuals_cache.add(path, modification_timestamp, user_visuals)

            visuals.update(user_visuals)

        except SyntaxError as e:
            raise MKGeneralException(_("Cannot load %s from %s: %s") % (what, path, e))

    return visuals


def load_visuals_of_a_user(what, builtin_visuals, skip_func, lock, path, user):
    user_visuals = {}
    for name, visual in store.load_data_from_file(path, {}, lock).items():
        visual["owner"] = user
        visual["name"] = name

        if skip_func and skip_func(visual):
            continue

        # Maybe resolve inherited attributes. This was a feature for several versions
        # to make the visual texts localizable. This has been removed because the visual
        # texts can now be localized using the custom localization strings.
        # This is needed for backward compatibility to make the visuals without these
        # attributes get the attributes from their builtin visual.
        builtin_visual = builtin_visuals.get(name)
        if builtin_visual:
            for attr in ['title', 'linktitle', 'topic', 'description']:
                if attr not in visual and attr in builtin_visual:
                    visual[attr] = builtin_visual[attr]

        # Repair visuals with missing 'title' or 'description'
        visual.setdefault("title", name)
        visual.setdefault("description", "")

        # Declare custom permissions
        declare_visual_permission(what, name, visual)

        user_visuals[(user, name)] = visual

    return user_visuals


def declare_visual_permission(what, name, visual):
    permname = "%s.%s" % (what[:-1], name)
    if visual["public"] and permname not in permission_registry:
        declare_permission(permname, visual["title"], visual["description"],
                           ['admin', 'user', 'guest'])


# Load all users visuals just in order to declare permissions of custom visuals
def declare_custom_permissions(what):
    subdirs = os.listdir(config.config_dir)
    for user in subdirs:
        try:
            dirpath = config.config_dir + "/" + user
            if os.path.isdir(dirpath):
                path = "%s/%s.mk" % (dirpath, what)
                if not os.path.exists(path):
                    continue
                visuals = store.load_data_from_file(path, {})
                for name, visual in visuals.items():
                    declare_visual_permission(what, name, visual)
        except Exception:
            if config.debug:
                raise


# Get the list of visuals which are available to the user
# (which could be retrieved with get_visual)
def available(what, all_visuals):
    user = config.user.id
    visuals = {}
    permprefix = what[:-1]

    def published_to_user(visual):
        if visual["public"] is True:
            return True

        if isinstance(visual["public"], tuple) and visual["public"][0] == "contact_groups":
            user_groups = set(userdb.contactgroups_of_user(user))
            if user_groups.intersection(visual["public"][1]):
                return True

        return False

    # 1. user's own visuals, if allowed to edit visuals
    if config.user.may("general.edit_" + what):
        for (u, n), visual in all_visuals.items():
            if u == user:
                visuals[n] = visual

    # 2. visuals of special users allowed to globally override builtin visuals
    for (u, n), visual in all_visuals.items():
        if n not in visuals and published_to_user(visual) and config.user_may(
                u, "general.force_" + what):
            # Honor original permissions for the current user
            permname = "%s.%s" % (permprefix, n)
            if permname in permission_registry \
                and not config.user.may(permname):
                continue
            visuals[n] = visual

    # 3. Builtin visuals, if allowed.
    for (u, n), visual in all_visuals.items():
        if u == '' and n not in visuals and config.user.may("%s.%s" % (permprefix, n)):
            visuals[n] = visual

    # 4. other users visuals, if public. Sill make sure we honor permission
    #    for builtin visuals. Also the permission "general.see_user_visuals" is
    #    necessary.
    if config.user.may("general.see_user_" + what):
        for (u, n), visual in all_visuals.items():
            if n not in visuals and published_to_user(visual) and config.user_may(
                    u, "general.publish_" + what):
                # Is there a builtin visual with the same name? If yes, honor permissions.
                permname = "%s.%s" % (permprefix, n)
                if permname in permission_registry \
                    and not config.user.may(permname):
                    continue
                visuals[n] = visual

    return visuals


#.
#   .--Listing-------------------------------------------------------------.
#   |                    _     _     _   _                                 |
#   |                   | |   (_)___| |_(_)_ __   __ _                     |
#   |                   | |   | / __| __| | '_ \ / _` |                    |
#   |                   | |___| \__ \ |_| | | | | (_| |                    |
#   |                   |_____|_|___/\__|_|_| |_|\__, |                    |
#   |                                            |___/                     |
#   +----------------------------------------------------------------------+
#   | Show a list of all visuals with actions to delete/clone/edit         |
#   '----------------------------------------------------------------------'


# TODO: This code has been copied to a new live into htdocs/pagetypes.py
# We need to convert all existing page types (views, dashboards, reports)
# to pagetypes.py and then remove this function!
def page_list(what,
              title,
              visuals,
              custom_columns=None,
              render_custom_buttons=None,
              render_custom_columns=None,
              render_custom_context_buttons=None,
              check_deletable_handler=None):

    if custom_columns is None:
        custom_columns = []

    what_s = what[:-1]
    if not config.user.may("general.edit_" + what):
        raise MKAuthException(_("Sorry, you lack the permission for editing this type of visuals."))

    html.header(title)

    html.begin_context_buttons()
    html.context_button(_('New'), 'create_%s.py' % what_s, "new")
    if render_custom_context_buttons:
        render_custom_context_buttons()

    for plugin_class in visual_type_registry.values():
        plugin = plugin_class()
        if what != plugin.ident:
            html.context_button(plugin.plural_title.title(), 'edit_%s.py' % plugin.ident,
                                plugin.ident[:-1])

    # TODO: We hack in those visuals that already have been moved to pagetypes here
    if pagetypes.has_page_type("graph_collection"):
        html.context_button(_("Graph collections"), "graph_collections.py", "graph_collection")
    if pagetypes.has_page_type("custom_graph"):
        html.context_button(_("Custom graphs"), "custom_graphs.py", "custom_graph")
    if pagetypes.has_page_type("graph_tuning"):
        html.context_button(_("Graph tunings"), "graph_tunings.py", "graph_tuning")
    if pagetypes.has_page_type("sla_configuration"):
        html.context_button(_("SLAs"), "sla_configurations.py", "sla_configuration")
    if pagetypes.has_page_type("custom_snapin"):
        html.context_button(_("Custom snapins"), "custom_snapins.py", "custom_snapin")
    html.context_button(_("Bookmark lists"), "bookmark_lists.py", "bookmark_list")

    html.end_context_buttons()

    # Deletion of visuals
    delname = html.request.var("_delete")
    if delname and html.transaction_valid():
        if config.user.may('general.delete_foreign_%s' % what):
            user_id = html.request.var('_user_id', config.user.id)
        else:
            user_id = config.user.id

        deltitle = visuals[(user_id, delname)]['title']

        try:
            if check_deletable_handler:
                check_deletable_handler(visuals, user_id, delname)

            c = html.confirm(_("Please confirm the deletion of \"%s\".") % deltitle)
            if c:
                del visuals[(user_id, delname)]
                save(what, visuals, user_id)
                html.reload_sidebar()
            elif c is False:
                html.footer()
                return
        except MKUserError as e:
            html.user_error(e)

    keys_sorted = sorted(visuals.keys(),
                         key=functools.cmp_to_key(lambda a, b: -((a[0] > b[0]) - (a[0] < b[0])) or
                                                  (a[1] > b[1]) - (a[1] < b[1])))

    my_visuals, foreign_visuals, builtin_visuals = [], [], []
    for (owner, visual_name) in keys_sorted:
        if owner == "" and not config.user.may("%s.%s" % (what_s, visual_name)):
            continue  # not allowed to see this view

        visual = visuals[(owner, visual_name)]
        if visual["public"] and owner == "":
            builtin_visuals.append((owner, visual_name, visual))
        elif owner == config.user.id:
            my_visuals.append((owner, visual_name, visual))
        elif (visual["public"] and owner != '' and config.user_may(owner, "general.publish_%s" % what)) or \
                config.user.may("general.edit_foreign_%s" % what):
            foreign_visuals.append((owner, visual_name, visual))

    for title1, items in [(_('Customized'), my_visuals),
                          (_("Owned by other users"), foreign_visuals),
                          (_('Builtin'), builtin_visuals)]:
        html.open_h3()
        html.write(title1)
        html.close_h3()

        with table_element(css='data', limit=None) as table:

            for owner, visual_name, visual in items:
                table.row(css='data')

                # Actions
                table.cell(_('Actions'), css='buttons visuals')

                # Clone / Customize
                buttontext = _("Create a customized copy of this")
                backurl = html.urlencode(html.makeuri([]))
                clone_url = "edit_%s.py?load_user=%s&load_name=%s&back=%s" \
                            % (what_s, owner, visual_name, backurl)
                html.icon_button(clone_url, buttontext, "clone")

                # Delete
                if owner and (owner == config.user.id or
                              config.user.may('general.delete_foreign_%s' % what)):
                    add_vars = [('_delete', visual_name)]
                    if owner != config.user.id:
                        add_vars.append(('_user_id', owner))
                    html.icon_button(html.makeactionuri(add_vars), _("Delete!"), "delete")

                # Edit
                if owner == config.user.id or (owner != "" and
                                               config.user.may("general.edit_foreign_%s" % what)):
                    edit_vars = [("load_name", visual_name)]
                    if owner != config.user.id:
                        edit_vars.append(("owner", owner))
                    edit_url = html.makeuri_contextless(edit_vars, filename="edit_%s.py" % what_s)
                    html.icon_button(edit_url, _("Edit"), "edit")

                # Custom buttons - visual specific
                if render_custom_buttons:
                    render_custom_buttons(visual_name, visual)

                # visual Name
                table.cell(_('ID'), visual_name)

                # Title
                table.cell(_('Title'))
                title2 = _u(visual['title'])
                if _visual_can_be_linked(what, visual_name, visuals, visual, owner):
                    html.a(title2,
                           href="%s.py?%s=%s" %
                           (what_s, visual_type_registry[what]().ident_attr, visual_name))
                else:
                    html.write_text(title2)
                html.help(_u(visual['description']))

                # Custom cols
                for title3, renderer in custom_columns:
                    table.cell(title3, renderer(visual))

                # Owner
                if owner == "":
                    ownertxt = "<i>" + _("builtin") + "</i>"
                else:
                    ownertxt = owner
                table.cell(_('Owner'), ownertxt)
                table.cell(_('Public'), visual["public"] and _("yes") or _("no"))
                table.cell(_('Hidden'), visual["hidden"] and _("yes") or _("no"))

                if render_custom_columns:
                    render_custom_columns(table, visual_name, visual)

    html.footer()


def _visual_can_be_linked(what, visual_name, all_visuals, visual, owner):
    if visual["hidden"]:
        return False  # don't link to hidden visuals

    if owner == config.user.id:
        return True

    # Is this the visual which would be shown to the user in case the user
    # requests a visual with the current name?
    user_visuals = available(what, all_visuals)
    if user_visuals.get(visual_name) != visual:
        return False

    return visual["public"]


#.
#   .--Create Visual-------------------------------------------------------.
#   |      ____                _        __     ___                 _       |
#   |     / ___|_ __ ___  __ _| |_ ___  \ \   / (_)___ _   _  __ _| |      |
#   |    | |   | '__/ _ \/ _` | __/ _ \  \ \ / /| / __| | | |/ _` | |      |
#   |    | |___| | |  __/ (_| | ||  __/   \ V / | \__ \ |_| | (_| | |      |
#   |     \____|_|  \___|\__,_|\__\___|    \_/  |_|___/\__,_|\__,_|_|      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Realizes the steps before getting to the editor (context type)       |
#   '----------------------------------------------------------------------'


def page_create_visual(what, info_keys, next_url=None):
    title = visual_type_registry[what]().title
    what_s = what[:-1]

    # FIXME: Sort by (assumed) common usage
    info_choices = []
    for key in info_keys:
        info_choices.append(
            (key, _('Show information of a single %s') % visual_info_registry[key]().title))

    vs_infos = SingleInfoSelection(info_keys)

    html.header(_('Create %s') % title)
    html.begin_context_buttons()
    html.context_button(_("Back"), html.get_url_input("back", "edit_%s.py" % what), "back")
    html.end_context_buttons()

    html.open_p()
    html.write(
        _('Depending on the choosen datasource a %s can list <i>multiple</i> or <i>single</i> objects. '
          'For example the <i>services</i> datasource can be used to simply create a list '
          'of <i>multiple</i> services, a list of <i>multiple</i> services of a <i>single</i> host or even '
          'a list of services with the same name on <i>multiple</i> hosts. When you just want to '
          'create a list of objects, you do not need to make any selection in this dialog. '
          'If you like to create a view for one specific object of a specific type, select the '
          'object type below and continue.') % what_s)
    html.close_p()

    if html.request.var('save') and html.check_transaction():
        try:
            single_infos = vs_infos.from_html_vars('single_infos')
            vs_infos.validate_value(single_infos, 'single_infos')

            if not next_url:
                next_url = 'edit_' + what_s + '.py?mode=create&single_infos=%s' % ','.join(
                    single_infos)
            else:
                next_url += '&single_infos=%s' % ','.join(single_infos)
            raise HTTPRedirect(next_url)
        except MKUserError as e:
            html.user_error(e)

    html.begin_form('create_visual')
    html.hidden_field('mode', 'create')

    forms.header(_('Select specific object type'))
    forms.section(vs_infos.title())
    vs_infos.render_input('single_infos', '')
    html.help(vs_infos.help())
    forms.end()

    html.button('save', _('Continue'), 'submit')

    html.hidden_fields()
    html.end_form()
    html.footer()


#.
#   .--Edit Visual---------------------------------------------------------.
#   |           _____    _ _ _    __     ___                 _             |
#   |          | ____|__| (_) |_  \ \   / (_)___ _   _  __ _| |            |
#   |          |  _| / _` | | __|  \ \ / /| / __| | | |/ _` | |            |
#   |          | |__| (_| | | |_    \ V / | \__ \ |_| | (_| | |            |
#   |          |_____\__,_|_|\__|    \_/  |_|___/\__,_|\__,_|_|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Edit global settings of the visual                                   |
#   '----------------------------------------------------------------------'


def get_context_specs(visual, info_handler):
    info_keys = []
    if info_handler:
        info_keys = info_handler(visual)

    if not info_keys:
        info_keys = visual_info_registry.keys()

    single_info_keys = [key for key in info_keys if key in visual['single_infos']]
    multi_info_keys = [key for key in info_keys if key not in single_info_keys]

    def visual_spec_single(info_key):
        info = visual_info_registry[info_key]()
        params = info.single_spec
        optional = True
        isopen = True
        return Dictionary(
            title=info.title,
            form_isopen=isopen,
            optional_keys=optional,
            elements=params,
        )

    def visual_spec_multi(info_key):
        info = visual_info_registry[info_key]()
        filter_list = VisualFilterList([info_key], title=info.title, ignore=set(single_info_keys))
        filter_names = filter_list.filter_names()
        # Skip infos which have no filters available
        return filter_list if filter_names else None

    # single infos first, the rest afterwards
    return [(info_key, visual_spec_single(info_key))
            for info_key in single_info_keys] + \
           [(info_key, visual_spec_multi(info_key))
            for info_key in multi_info_keys
            if visual_spec_multi(info_key)]


def process_context_specs(context_specs):
    context = {}
    for info_key, spec in context_specs:
        ident = 'context_' + info_key

        attrs = spec.from_html_vars(ident)
        spec.validate_value(attrs, ident)
        context.update(attrs)
    return context


def render_context_specs(visual, context_specs):
    forms.header(_("Context / Search Filters"))
    for info_key, spec in context_specs:
        forms.section(spec.title())
        ident = 'context_' + info_key
        # Trick: the field "context" contains a dictionary with
        # all filter settings, from which the value spec will automatically
        # extract those that it needs.
        value = visual.get('context', {})
        spec.render_input(ident, value)


def page_edit_visual(what,
                     all_visuals,
                     custom_field_handler=None,
                     create_handler=None,
                     load_handler=None,
                     info_handler=None,
                     sub_pages=None):
    if sub_pages is None:
        sub_pages = []

    visual_type = visual_type_registry[what]()
    if not config.user.may("general.edit_" + what):
        raise MKAuthException(_("You are not allowed to edit %s.") % visual_type.plural_title)
    visual = {}

    # Load existing visual from disk - and create a copy if 'load_user' is set
    visualname = html.request.var("load_name")
    oldname = visualname
    mode = html.request.var('mode', 'edit')
    owner_user_id = config.user.id
    if visualname:
        cloneuser = html.request.var("load_user")
        if cloneuser is not None:
            mode = 'clone'
            visual = copy.deepcopy(all_visuals.get((cloneuser, visualname), None))
            if not visual:
                raise MKUserError('cloneuser', _('The %s does not exist.') % visual_type.title)

            # Make sure, name is unique
            if cloneuser == owner_user_id:  # Clone own visual
                newname = visualname + "_clone"
            else:
                newname = visualname
            # Name conflict -> try new names
            n = 1
            while (owner_user_id, newname) in all_visuals:
                n += 1
                newname = visualname + "_clone%d" % n
            visual["name"] = newname
            visual["public"] = False
            visualname = newname
            oldname = None  # Prevent renaming
            if cloneuser == owner_user_id:
                visual["title"] += _(" (Copy)")
        else:
            owner_user_id = html.request.var("owner", config.user.id)
            visual = all_visuals.get((owner_user_id, visualname))
            if not visual:
                visual = all_visuals.get(('', visualname))  # load builtin visual
                mode = 'clone'
                if not visual:
                    raise MKUserError(None,
                                      _('The requested %s does not exist.') % visual_type.title)
                visual["public"] = False

        single_infos = visual['single_infos']

        if load_handler:
            load_handler(visual)

    else:
        mode = 'create'
        single_infos = []
        single_infos_raw = html.request.var('single_infos')
        if single_infos_raw:
            single_infos = single_infos_raw.split(',')
            for key in single_infos:
                if key not in visual_info_registry:
                    raise MKUserError('single_infos', _('The info %s does not exist.') % key)
        visual['single_infos'] = single_infos

    if mode == 'clone':
        title = _('Clone %s') % visual_type.title
    elif mode == 'create':
        title = _('Create %s') % visual_type.title
    else:
        title = _('Edit %s') % visual_type.title

    html.header(title)
    html.begin_context_buttons()
    back_url = html.get_url_input("back", "edit_%s.py" % what)
    html.context_button(_("Back"), back_url, "back")

    # Extra buttons to sub modules. These are used for things to edit about
    # this visual that are more complex to be done in one value spec.
    if mode not in ["clone", "create"]:
        for title, pagename, icon in sub_pages:
            uri = html.makeuri_contextless([(visual_type.ident_attr, visualname)],
                                           filename=pagename + '.py')
            html.context_button(title, uri, icon)
    html.end_context_buttons()

    # A few checkboxes concerning the visibility of the visual. These will
    # appear as boolean-keys directly in the visual dict, but encapsulated
    # in a list choice in the value spec.
    visibility_elements = [
        ('hidden',
         FixedValue(
             True,
             title=_('Hide this %s from the sidebar') % visual_type.title,
             totext="",
         )),
        ('hidebutton',
         FixedValue(
             True,
             title=_('Do not show a context button to this %s') % visual_type.title,
             totext="",
         )),
    ]
    if config.user.may("general.publish_" + what):
        with_foreign_groups = config.user.may("general.publish_" + what + "_to_foreign_groups")
        visibility_elements.append(('public',
                                    pagetypes.PublishTo(
                                        type_title=visual_type.title,
                                        with_foreign_groups=with_foreign_groups,
                                    )))

    vs_general = Dictionary(
        title=_("General Properties"),
        render='form',
        optional_keys=None,
        elements=[
            single_infos_spec(single_infos),
            ('name',
             TextAscii(
                 title=_('Unique ID'),
                 help=_("The ID will be used in URLs that point to a view, e.g. "
                        "<tt>view.py?view_name=<b>myview</b></tt>. It will also be used "
                        "internally for identifying a view. You can create several views "
                        "with the same title but only one per view name. If you create a "
                        "view that has the same view name as a builtin view, then your "
                        "view will override that (shadowing it)."),
                 regex='^[a-zA-Z0-9_]+$',
                 regex_error=_(
                     'The name of the view may only contain letters, digits and underscores.'),
                 size=50,
                 allow_empty=False)),
            ('title', TextUnicode(title=_('Title') + '<sup>*</sup>', size=50, allow_empty=False)),
            ('topic', TextUnicode(title=_('Topic') + '<sup>*</sup>', size=50)),
            ('description', TextAreaUnicode(title=_('Description') + '<sup>*</sup>',
                                            rows=4,
                                            cols=50)),
            ('linktitle',
             TextUnicode(title=_('Button Text') + '<sup>*</sup>',
                         help=_('If you define a text here, then it will be used in '
                                'context buttons linking to the %s instead of the regular title.') %
                         visual_type.title,
                         size=26)),
            ('icon', IconSelector(title=_('Button Icon'),)),
            ('visibility', Dictionary(
                title=_('Visibility'),
                elements=visibility_elements,
            )),
        ],
    )

    context_specs = get_context_specs(visual, info_handler)

    # handle case of save or try or press on search button
    save_and_go = None
    for nr, (title, pagename, icon) in enumerate(sub_pages):
        if html.request.var("save%d" % nr):
            save_and_go = pagename

    if save_and_go or html.request.var("save") or html.request.var("search"):
        try:
            general_properties = vs_general.from_html_vars('general')
            vs_general.validate_value(general_properties, 'general')

            if not general_properties['linktitle']:
                general_properties['linktitle'] = general_properties['title']
            if not general_properties['topic']:
                general_properties['topic'] = _("Other")

            old_visual = visual
            visual = {}

            # The dict of the value spec does not match exactly the dict
            # of the visual. We take over some keys...
            for key in [
                    'single_infos',
                    'name',
                    'title',
                    'topic',
                    'description',
                    'linktitle',
                    'icon',
            ]:
                visual[key] = general_properties[key]

            # ...and import the visibility flags directly into the visual
            for key, _value in visibility_elements:
                visual[key] = general_properties['visibility'].get(key, False)

            if not config.user.may("general.publish_" + what):
                visual['public'] = False

            if create_handler:
                visual = create_handler(old_visual, visual)

            visual['context'] = process_context_specs(context_specs)

            if html.request.var("save") or save_and_go:
                if save_and_go:
                    back_url = html.makeuri_contextless([(visual_type.ident_attr, visual['name'])],
                                                        filename=save_and_go + '.py')

                if html.check_transaction():
                    all_visuals[(owner_user_id, visual["name"])] = visual
                    # Handle renaming of visuals
                    if oldname and oldname != visual["name"]:
                        # -> delete old entry
                        if (owner_user_id, oldname) in all_visuals:
                            del all_visuals[(owner_user_id, oldname)]
                        # -> change visual_name in back parameter
                        if back_url:
                            varstring = visual_type.ident_attr + "="
                            back_url = back_url.replace(varstring + oldname,
                                                        varstring + visual["name"])
                    save(what, all_visuals, owner_user_id)

                html.immediate_browser_redirect(1, back_url)
                html.message(_('Your %s has been saved.') % visual_type.title)
                html.reload_sidebar()
                html.footer()
                return

        except MKUserError as e:
            html.user_error(e)

    html.begin_form("visual", method="POST")
    html.hidden_field("back", back_url)
    html.hidden_field("mode", mode)
    if html.request.has_var("load_user"):
        html.hidden_field("load_user",
                          html.request.var("load_user"))  # safe old name in case user changes it
    html.hidden_field("load_name", oldname)  # safe old name in case user changes it

    # FIXME: Hier werden die Flags aus visibility nicht korrekt geladen. Wäre es nicht besser,
    # diese in einem Unter-Dict zu lassen, anstatt diese extra umzukopieren?
    visib = {}
    for key, _vs in visibility_elements:
        if visual.get(key):
            visib[key] = visual[key]
    visual["visibility"] = visib

    vs_general.render_input("general", visual)

    if custom_field_handler:
        custom_field_handler(visual)

    render_context_specs(visual, context_specs)

    forms.end()
    html.show_localization_hint()

    html.button("save", _("Save"))

    for nr, (title, pagename, icon) in enumerate(sub_pages):
        html.button("save%d" % nr, _("Save and go to ") + title)

    html.hidden_fields()
    html.end_form()
    html.footer()


#.
#   .--Filters-------------------------------------------------------------.
#   |                     _____ _ _ _                                      |
#   |                    |  ___(_) | |_ ___ _ __ ___                       |
#   |                    | |_  | | | __/ _ \ '__/ __|                      |
#   |                    |  _| | | | ||  __/ |  \__ \                      |
#   |                    |_|   |_|_|\__\___|_|  |___/                      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def show_filter(f):
    html.open_div(class_=["floatfilter", "double" if f.double_height() else "single", f.ident])
    html.div(f.title, class_="legend")
    html.open_div(class_="content")
    try:
        with html.plugged():
            f.display()
            html.write(html.drain())
    except Exception as e:
        logger.exception("error showing filter")
        tb = sys.exc_info()[2]
        tbs = ['Traceback (most recent call last):\n']
        tbs += traceback.format_tb(tb)
        html.icon(_("This filter cannot be displayed") + " (%s)\n%s" % (e, "".join(tbs)), "alert")
        html.write_text(_("This filter cannot be displayed"))
    html.close_div()
    html.close_div()


def get_filter(name):
    # type: (str) -> Type[Filter]
    """Returns the filter object identified by the given name
    Raises a KeyError in case a not existing filter is requested."""
    return filter_registry[name]()


def filters_allowed_for_info(info):
    # type: (str) -> Dict[str, Type[Filter]]
    """Returns a map of filter names and filter objects that are registered for the given info"""
    allowed = {}
    for fname, filter_class in filter_registry.items():
        filt = filter_class()
        if filt.info is None or info == filt.info:
            allowed[fname] = filt
    return allowed


def filters_allowed_for_infos(info_list):
    # type: (List[str]) -> Dict[str, Type[Filter]]
    """Same as filters_allowed_for_info() but for multiple infos"""
    filters = {}
    for info in info_list:
        filters.update(filters_allowed_for_info(info))
    return filters


# For all single_infos which are configured for a view which datasource
# does not provide these infos, try to match the keys of the single_info
# attributes to a filter which can then be used to filter the data of
# the available infos.
# This is needed to make the "hostgroup" single_info possible on datasources
# which do not have the "hostgroup" info, but the "host" info. This
# is some kind of filter translation between a filter of the "hostgroup" info
# and the "hosts" info.
def get_link_filter_names(visual, info_keys, link_filters):
    names = []
    for info_key in visual['single_infos']:
        if info_key not in info_keys:
            for key in info_params(info_key):
                if key in link_filters:
                    names.append((key, link_filters[key]))
    return names


# Collects all filters to be used for the given visual
def filters_of_visual(visual, info_keys, link_filters=None):
    if link_filters is None:
        link_filters = []

    filters = {}

    for info_key in info_keys:
        if info_key in visual['single_infos']:
            for key in info_params(info_key):
                filters[key] = get_filter(key)
            continue

        for key, val in visual['context'].items():
            if isinstance(val, dict):  # this is a real filter
                try:
                    filters[key] = get_filter(key)
                except KeyError:
                    pass  # Silently ignore not existing filters

    # See get_link_filter_names() comment for details
    for key, dst_key in get_link_filter_names(visual, info_keys, link_filters):
        filters[dst_key] = get_filter(dst_key)

    # add ubiquitary_filters that are possible for these infos
    for fn in get_ubiquitary_filters():
        # Disable 'wato_folder' filter, if WATO is disabled or there is a single host view
        filter_ = get_filter(fn)

        if fn == "wato_folder" and (not filter_.available() or 'host' in visual['single_infos']):
            continue
        if not filter_.info or filter_.info in info_keys:
            filters[fn] = filter_

    return filters.values()


# TODO: Cleanup this special case
def get_ubiquitary_filters():
    return ["wato_folder"]


# Reduces the list of the visuals used filters. The result are the ones
# which are really presented to the user later.
# For the moment we only remove the single context filters which have a
# hard coded default value which is treated as enforced value.
def visible_filters_of_visual(visual, use_filters):
    show_filters = []

    single_keys = get_single_info_keys(visual)

    for f in use_filters:
        if f.ident not in single_keys or \
           not visual['context'].get(f.ident):
            show_filters.append(f)

    return show_filters


def add_context_to_uri_vars(visual, only_count=False):
    # Populate the HTML vars with missing context vars. The context vars set
    # in single context are enforced (can not be overwritten by URL). The normal
    # filter vars in "multiple" context are not enforced.
    for key in get_single_info_keys(visual):
        if key in visual['context']:
            html.request.set_var(key, "%s" % visual['context'][key])

    # Now apply the multiple context filters
    for filter_vars in visual['context'].itervalues():
        if isinstance(filter_vars, dict):  # this is a multi-context filter
            # We add the filter only if *none* of its HTML variables are present on the URL
            # This important because checkbox variables are not present if the box is not checked.
            skip = any(html.request.has_var(uri_varname) for uri_varname in filter_vars.iterkeys())
            if not skip or only_count:
                for uri_varname, value in filter_vars.items():
                    html.request.set_var(uri_varname, "%s" % value)


# Vice versa: find all filters that belong to the current URI variables
# and create a context dictionary from that.
def get_context_from_uri_vars(only_infos=None, single_infos=None):
    if single_infos is None:
        single_infos = []

    context = {}
    for filter_name, filter_class in filter_registry.items():
        filter_object = filter_class()
        if only_infos is None or filter_object.info in only_infos:
            this_filter_vars = {}
            for varname in filter_object.htmlvars:
                if html.request.has_var(varname):
                    if filter_object.info in single_infos:
                        context[filter_name] = html.request.var(varname)
                        break
                    else:
                        this_filter_vars[varname] = html.request.var(varname)
            if this_filter_vars:
                context[filter_name] = this_filter_vars
    return context


# Compute Livestatus-Filters based on a given context. Returns
# the only_sites list and a string with the filter headers
# TODO: Untangle only_sites and filter headers
def get_filter_headers(table, infos, context):
    # Prepare Filter headers for Livestatus
    filter_headers = ""
    with html.stashed_vars():
        for filter_name, filter_vars in context.items():
            # first set the HTML variables. Sorry - the filters need this
            if isinstance(filter_vars, dict):  # this is a multi-context filter
                for uri_varname, value in filter_vars.items():
                    html.request.set_var(uri_varname, value)
            else:
                html.request.set_var(filter_name, filter_vars)

        # Apply the site hint / filter (Same logic as in views.py)
        if html.request.var("site"):
            only_sites = [html.request.var("site")]
        else:
            only_sites = None

        # Now compute filter headers for all infos of the used datasource
        for filter_name, filter_class in filter_registry.items():
            filter_object = filter_class()
            if filter_object.info in infos:
                header = filter_object.filter(table)
                filter_headers += header
    return filter_headers, only_sites


#.
#   .--ValueSpecs----------------------------------------------------------.
#   |        __     __    _            ____                                |
#   |        \ \   / /_ _| |_   _  ___/ ___| _ __   ___  ___ ___           |
#   |         \ \ / / _` | | | | |/ _ \___ \| '_ \ / _ \/ __/ __|          |
#   |          \ V / (_| | | |_| |  __/___) | |_) |  __/ (__\__ \          |
#   |           \_/ \__,_|_|\__,_|\___|____/| .__/ \___|\___|___/          |
#   |                                       |_|                            |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class VisualFilterList(ListOfMultiple):
    """Implements a list of available filters for the given infos. By default no
    filter is selected. The user may select a filter to be activated, then the
    filter is rendered and the user can provide a default value.
    """
    @classmethod
    def get_choices(cls, infos, ignore):
        return sorted(cls._get_filter_specs(infos, ignore).items(),
                      key=lambda x: (x[1]._filter.sort_index, x[1].title()))

    @classmethod
    def _get_filters(cls, infos, ignore):
        return {
            fname: fspec._filter
            for fname, fspec in cls._get_filter_specs(infos, ignore).iteritems()
        }

    @classmethod
    def _get_filter_specs(cls, infos, ignore):
        fspecs = {}
        for info in infos:
            for fname, filter_ in filters_allowed_for_info(info).items():
                if fname not in fspecs and fname not in ignore:
                    fspecs[fname] = VisualFilter(
                        fname,
                        title=filter_.title,
                    )
        return fspecs

    def __init__(self, info_list, **kwargs):
        ignore = kwargs.get("ignore", set())
        self._filters = self._get_filters(info_list, ignore)

        kwargs.setdefault('title', _('Filters'))
        kwargs.setdefault('add_label', _('Add filter'))
        kwargs.setdefault('del_label', _('Remove filter'))
        kwargs["delete_style"] = "filter"

        super(VisualFilterList, self).__init__(self.get_choices(info_list, ignore),
                                               "ajax_visual_filter_list_get_choice",
                                               page_request_vars={
                                                   "infos": info_list,
                                                   "ignore": list(ignore),
                                               },
                                               **kwargs)

    def filter_names(self):
        return self._filters.keys()


@page_registry.register_page("ajax_visual_filter_list_get_choice")
class PageAjaxVisualFilterListGetChoice(ABCPageListOfMultipleGetChoice):
    def _get_choices(self, request):
        return VisualFilterList.get_choices(request["infos"], set(request["ignore"]))


# Realizes a Multisite/visual filter in a valuespec. It can render the filter form, get
# the filled in values and provide the filled in information for persistance.
class VisualFilter(ValueSpec):
    def __init__(self, name, **kwargs):
        self._name = name
        self._filter = filter_registry[name]()

        ValueSpec.__init__(self, **kwargs)

    def title(self):
        return self._filter.title

    def canonical_value(self):
        return {}

    def render_input(self, varprefix, value):
        # kind of a hack to make the current/old filter API work. This should
        # be cleaned up some day
        if value is not None:
            self._filter.set_value(value)

        # A filter can not be used twice on a page, because the varprefix is not used
        show_filter(self._filter)

    def value_to_text(self, value):
        # FIXME: optimize. Needed?
        return repr(value)

    def from_html_vars(self, varprefix):
        # A filter can not be used twice on a page, because the varprefix is not used
        return self._filter.value()

    def validate_datatype(self, value, varprefix):
        if not isinstance(value, dict):
            raise MKUserError(varprefix,
                              _("The value must be of type dict, but it has type %s") % type(value))

    def validate_value(self, value, varprefix):
        ValueSpec.custom_validate(self, value, varprefix)


def SingleInfoSelection(info_keys, **args):
    info_choices = []
    for key in info_keys:
        info_choices.append(
            (key, _('Show information of a single %s') % visual_info_registry[key]().title))

    args.setdefault("title", _('Specific objects'))
    args["choices"] = info_choices
    return ListChoice(**args)


# Converts a context from the form { filtername : { ... } } into
# the for { infoname : { filtername : { } } for editing.
def pack_context_for_editing(visual, info_handler):
    # We need to pack all variables into dicts with the name of the
    # info. Since we have no mapping from info the the filter variable,
    # we pack into every info every filter. The dict valuespec will
    # pick out what it needs. Yurks.
    packed_context = {}
    info_keys = info_handler(visual) if info_handler else visual_info_registry.keys()
    for info_name in info_keys:
        packed_context[info_name] = visual.get('context', {})
    return packed_context


def unpack_context_after_editing(packed_context):
    context = {}
    for _info_type, its_context in packed_context.items():
        context.update(its_context)
    return context


#.
#   .--Misc----------------------------------------------------------------.
#   |                          __  __ _                                    |
#   |                         |  \/  (_)___  ___                           |
#   |                         | |\/| | / __|/ __|                          |
#   |                         | |  | | \__ \ (__                           |
#   |                         |_|  |_|_|___/\___|                          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def is_single_site_info(info_key):
    return visual_info_registry[info_key]().single_site


def single_infos_spec(single_infos):
    return ('single_infos', FixedValue(single_infos,
        title = _('Show information of single'),
        totext = single_infos and ', '.join(single_infos) \
                    or _('Not restricted to showing a specific object.'),
    ))


def verify_single_contexts(what, visual, link_filters):
    for k, v in get_singlecontext_html_vars(visual).items():
        if v is None and k not in link_filters:
            raise MKUserError(
                k,
                _('This %s can not be displayed, because the '
                  'necessary context information "%s" is missing.') %
                (visual_type_registry[what]().title, k))


def visual_title(what, visual):
    # Beware: if a single context visual is being visited *without* a context, then
    # the value of the context variable(s) is None. In order to avoid exceptions,
    # we simply drop these here.
    extra_titles = [v for v in get_singlecontext_html_vars(visual).itervalues() if v is not None]

    # FIXME: Is this really only needed for visuals without single infos?
    if not visual['single_infos']:
        used_filters = []
        for fn in visual["context"].keys():
            try:
                used_filters.append(get_filter(fn))
            except KeyError:
                pass  # silently ignore not existing filters

        for filt in used_filters:
            heading = filt.heading_info()
            if heading:
                extra_titles.append(heading)

    title = _u(visual["title"])
    if extra_titles:
        title += " " + ", ".join(extra_titles)

    for fn in get_ubiquitary_filters():
        # Disable 'wato_folder' filter, if WATO is disabled or there is a single host view
        if fn == "wato_folder" and (not config.wato_enabled or 'host' in visual['single_infos']):
            continue

        heading = get_filter(fn).heading_info()
        if heading:
            title = heading + " - " + title

    # Execute title plugin functions which might be added by the user to
    # the visuals plugins. When such a plugin function returns None, the regular
    # title of the page is used, otherwise the title returned by the plugin
    # function is used.
    for func in title_functions:
        result = func(what, visual, title)
        if result is not None:
            return result

    return title


# Determines the names of HTML variables to be set in order to
# specify a specify row in a datasource with a certain info.
# Example: the info "history" (Event Console History) needs
# the variables "event_id" and "history_line" to be set in order
# to exactly specify one history entry.
def info_params(info_key):
    single_spec = visual_info_registry[info_key]().single_spec
    if single_spec is None:
        return []
    return dict(single_spec).keys()


def get_single_info_keys(visual):
    keys = []
    for info_key in visual.get('single_infos', []):
        keys += info_params(info_key)
    return list(set(keys))


def get_singlecontext_vars(visual):
    vars_ = {}
    for key in get_single_info_keys(visual):
        vars_[key] = visual['context'].get(key)
    return vars_


def get_singlecontext_html_vars(visual):
    vars_ = get_singlecontext_vars(visual)
    for key in get_single_info_keys(visual):
        val = html.get_unicode_input(key)
        if val is not None:
            vars_[key] = val
    return vars_


# Collect all visuals that share a context with visual. For example
# if a visual has a host context, get all relevant visuals.
def collect_context_links(this_visual, mobile=False, only_types=None):
    if only_types is None:
        only_types = []

    # compute list of html variables needed for this visual
    active_filter_vars = set([])
    for var in get_singlecontext_html_vars(this_visual).iterkeys():
        if html.request.has_var(var):
            active_filter_vars.add(var)

    context_links = []
    for what in visual_type_registry.keys():
        if not only_types or what in only_types:
            context_links += collect_context_links_of(what, this_visual, active_filter_vars, mobile)
    return context_links


def collect_context_links_of(visual_type_name, this_visual, active_filter_vars, mobile):
    context_links = []

    visual_type = visual_type_registry[visual_type_name]()
    visual_type.load_handler()
    available_visuals = visual_type.permitted_visuals

    # sort buttons somehow
    visuals = available_visuals.values()
    visuals.sort(key=lambda x: x.get('icon'))

    for visual in visuals:
        name = visual["name"]
        linktitle = visual.get("linktitle")
        if not linktitle:
            linktitle = visual["title"]
        if visual == this_visual:
            continue
        if visual.get("hidebutton", False):
            continue  # this visual does not want a button to be displayed

        if not mobile and visual.get('mobile') \
           or mobile and not visual.get('mobile'):
            continue

        # For dashboards and views we currently only show a link button,
        # if the target dashboard/view shares a single info with the
        # current visual.
        if not visual['single_infos'] and not visual_type.multicontext_links:
            continue  # skip non single visuals for dashboard, views

        # We can show a button only if all single contexts of the
        # target visual are known currently
        needed_vars = get_singlecontext_html_vars(visual).items()
        skip = False
        vars_values = []
        for var, val in needed_vars:
            if var not in active_filter_vars:
                skip = True  # At least one single context missing
                break
            vars_values.append((var, val))

        add_site_hint = may_add_site_hint(name,
                                          info_keys=visual_info_registry.keys(),
                                          single_info_keys=visual["single_infos"],
                                          filter_names=dict(vars_values).keys())

        if add_site_hint and html.request.var('site'):
            vars_values.append(('site', html.request.var('site')))

        # Optional feature of visuals: Make them dynamically available as links or not.
        # This has been implemented for HW/SW inventory views which are often useless when a host
        # has no such information available. For example the "Oracle Tablespaces" inventory view
        # is useless on hosts that don't host Oracle databases.
        if not skip:
            skip = not visual_type.is_enabled_for(this_visual, visual, vars_values)

        if not skip:
            # add context link to this visual. For reports we put in
            # the *complete* context, even the non-single one.
            if visual_type.multicontext_links:
                uri = html.makeuri([(visual_type.ident_attr, name)], filename=visual_type.show_url)

            # For views and dashboards currently the current filter
            # settings
            else:
                uri = html.makeuri_contextless(vars_values + [(visual_type.ident_attr, name)],
                                               filename=visual_type.show_url)
            icon = visual.get("icon")
            buttonid = "cb_" + name
            context_links.append((_u(linktitle), uri, icon, buttonid))

    return context_links


def may_add_site_hint(visual_name, info_keys, single_info_keys, filter_names):
    """Whether or not the site hint may be set when linking to a visual with the given details"""
    # When there is one non single site info used don't add the site hint
    if [info_key for info_key in single_info_keys if not is_single_site_info(info_key)]:
        return False

    # Alternatively when the infos allow a site hint it is also needed to skip the site hint based
    # on the filters used by the target visual
    for info_key in info_keys:
        for filter_key in visual_info_registry[info_key]().multiple_site_filters:
            if filter_key in filter_names:
                return False

    # Hack for servicedesc view which is meant to show all services with the given
    # description: Don't add the site filter for this view.
    if visual_name in ["servicedesc", "servicedescpnp"]:
        return False

    return True


def transform_old_visual(visual):
    if 'context_type' in visual:
        if visual['context_type'] in ['host', 'service', 'hostgroup', 'servicegroup']:
            visual['single_infos'] = [visual['context_type']]
        else:
            visual['single_infos'] = []  # drop the context type and assume a "multiple visual"
        del visual['context_type']
    elif 'single_infos' not in visual:
        visual['single_infos'] = []

    visual.setdefault('context', {})


#.
#   .--Popup Add-----------------------------------------------------------.
#   |          ____                              _       _     _           |
#   |         |  _ \ ___  _ __  _   _ _ __      / \   __| | __| |          |
#   |         | |_) / _ \| '_ \| | | | '_ \    / _ \ / _` |/ _` |          |
#   |         |  __/ (_) | |_) | |_| | |_) |  / ___ \ (_| | (_| |          |
#   |         |_|   \___/| .__/ \__,_| .__/  /_/   \_\__,_|\__,_|          |
#   |                    |_|         |_|                                   |
#   +----------------------------------------------------------------------+
#   |  Handling of popup for adding a visual element to a dashboard, etc.  |
#   '----------------------------------------------------------------------'


# TODO: Remove this code as soon as everything is moved over to pagetypes.py
@cmk.gui.pages.register("ajax_popup_add_visual")
def ajax_popup_add():
    add_type = html.request.var("add_type")

    html.open_ul()

    pagetypes.render_addto_popup(add_type)

    for visual_type_name, visual_type_class in visual_type_registry.items():
        visual_type = visual_type_class()
        visuals = visual_type.popup_add_handler(add_type)
        if not visuals:
            continue

        html.open_li()
        html.open_span()
        html.write("%s %s:" % (_('Add to'), visual_type.title))
        html.close_span()
        html.close_li()

        for name, title in sorted(visuals, key=lambda x: x[1]):
            html.open_li()
            html.open_a(href="javascript:void(0)",
                        onclick="cmk.popup_menu.add_to_visual(\'%s\', \'%s\')" %
                        (visual_type_name, name))
            html.icon(None, visual_type_name.rstrip('s'))
            html.write(title)
            html.close_a()
            html.close_li()

    # TODO: Find a good place for this special case. This needs to be modularized.
    if add_type == "pnpgraph" and metrics.cmk_graphs_possible():
        html.open_li()
        html.open_span()
        html.write("%s:" % _("Export"))
        html.close_span()
        html.close_li()

        html.open_li()
        html.open_a(href="javascript:cmk.popup_menu.graph_export(\"graph_export\")")
        html.icon(None, "download")
        html.write(_("Export as JSON"))
        html.close_a()
        html.open_a(href="javascript:cmk.popup_menu.graph_export(\"graph_image\")")
        html.icon(None, "download")
        html.write(_("Export as PNG"))
        html.close_a()
        html.close_li()

    html.close_ul()


@cmk.gui.pages.register("ajax_add_visual")
def ajax_add_visual():
    visual_type_name = html.request.var('visual_type')  # dashboards / views / ...
    visual_type = visual_type_registry[visual_type_name]()

    visual_name = html.request.var("visual_name")  # add to this visual

    # type of the visual to add (e.g. view)
    element_type = html.request.var("type")

    create_info = json.loads(html.request.var("create_info"))
    visual_type.add_visual_handler(visual_name, element_type, create_info["context"],
                                   create_info["params"])
