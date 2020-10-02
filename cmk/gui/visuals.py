#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import copy
import sys
import traceback
import json
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union

from livestatus import SiteId

import cmk.utils.version as cmk_version
import cmk.utils.store as store
from cmk.utils.type_defs import UserId

import cmk.gui.pages
import cmk.gui.utils as utils
from cmk.gui.log import logger
from cmk.gui.exceptions import HTTPRedirect, MKGeneralException, MKAuthException, MKUserError
from cmk.gui.permissions import declare_permission
from cmk.gui.pages import page_registry
from cmk.gui.type_defs import (
    FilterHTTPVariables,
    FilterName,
    HTTPVariables,
    InfoName,
    SingleInfos,
    Visual,
    VisualContext,
    VisualTypeName,
)
from cmk.gui.valuespec import (
    Dictionary,
    DualListChoice,
    ValueSpec,
    ListOfMultiple,
    ABCPageListOfMultipleGetChoice,
    FixedValue,
    IconSelector,
    Checkbox,
    TextUnicode,
    TextAscii,
    TextAreaUnicode,
    DropdownChoice,
    Integer,
    ListOfMultipleChoiceGroup,
    GroupedListOfMultipleChoices,
)

import cmk.gui.config as config
import cmk.gui.forms as forms
from cmk.gui.table import table_element
import cmk.gui.userdb as userdb
import cmk.gui.pagetypes as pagetypes
import cmk.gui.i18n
from cmk.gui.i18n import _u, _
from cmk.gui.globals import html
from cmk.gui.breadcrumb import make_main_menu_breadcrumb, Breadcrumb, BreadcrumbItem
from cmk.gui.page_menu import (
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    PageMenuLink,
    make_javascript_link,
    make_simple_link,
    make_simple_form_page_menu,
)
from cmk.gui.main_menu import mega_menu_registry

from cmk.gui.plugins.visuals.utils import (
    visual_info_registry,
    visual_type_registry,
    filter_registry,
)

# Needed for legacy (pre 1.6) plugins
from cmk.gui.plugins.visuals.utils import (  # noqa: F401 # pylint: disable=unused-import
    Filter, FilterTime, FilterTristate,
)
from cmk.gui.permissions import permission_registry

if not cmk_version.is_raw_edition():
    import cmk.gui.cee.plugins.visuals  # pylint: disable=no-name-in-module

if cmk_version.is_managed_edition():
    import cmk.gui.cme.plugins.visuals  # pylint: disable=no-name-in-module

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

loaded_with_language: Union[bool, None, str] = False
title_functions: List[Callable] = []


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


class UserVisualsCache:
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
def load(what: str,
         builtin_visuals: Dict[Any, Any],
         skip_func: Optional[Callable[[Dict[Any, Any]], bool]] = None,
         lock: bool = False) -> Dict[Tuple[UserId, str], Dict[str, Any]]:
    visuals: Dict[Tuple[UserId, str], Dict[str, Any]] = {}

    # first load builtins. Set username to ''
    for name, visual in builtin_visuals.items():
        visual["owner"] = ''  # might have been forgotten on copy action
        visual["public"] = True
        visual["name"] = name

        # Dashboards had not all COMMON fields in previous versions. Add them
        # here to be compatible for a specific time. Seamless migration, yeah.
        visual.setdefault('description', '')
        visual.setdefault('hidden', False)

        visuals[(UserId(''), name)] = visual

    # Now scan users subdirs for files "user_*.mk"
    visuals.update(load_user_visuals(what, builtin_visuals, skip_func, lock))

    return visuals


# This is currently not called by load() because some visual type (e.g. view) specific transform
# needs to be executed in advance. This should be cleaned up.
def transform_old_visual(visual):
    """Prepare visuals for working with them. Migrate old formats or add default settings, for example"""
    visual.setdefault('single_infos', [])
    visual.setdefault('context', {})
    visual.setdefault('link_from', {})
    visual.setdefault('topic', '')
    visual.setdefault("icon", None)

    # 1.6 introduced this setting: Ensure all visuals have it set
    visual.setdefault("add_context_to_title", True)

    # 1.7 introduced these settings for the new mega menus
    visual.setdefault("sort_index", 99)
    visual.setdefault("is_advanced", False)


def load_user_visuals(what: str, builtin_visuals: Dict[Any, Any],
                      skip_func: Optional[Callable[[Dict[Any, Any]],
                                                   bool]], lock: bool) -> Dict[Any, Any]:
    visuals: Dict[Any, Any] = {}

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

            if not userdb.user_exists(UserId(user)):
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
    for name, visual in store.load_object_from_file(path, default={}, lock=lock).items():
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
                visuals = store.load_object_from_file(path, default={})
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
            user_groups = set([] if user is None else userdb.contactgroups_of_user(user))
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
              custom_page_menu_entries=None,
              check_deletable_handler=None):

    if custom_columns is None:
        custom_columns = []

    what_s = what[:-1]
    if not config.user.may("general.edit_" + what):
        raise MKAuthException(_("Sorry, you lack the permission for editing this type of visuals."))

    breadcrumb = visual_page_breadcrumb(what, title, "list")

    visual_type = visual_type_registry[what]()
    current_type_dropdown = PageMenuDropdown(
        name=what,
        title=visual_type.plural_title.title(),
        topics=[
            PageMenuTopic(
                title=visual_type.plural_title.title(),
                entries=[
                    PageMenuEntry(
                        title=_('Add %s') % visual_type.title,
                        icon_name="new",
                        item=make_simple_link("create_%s.py" % what_s),
                        is_shortcut=True,
                        is_suggested=True,
                    ),
                ] + (list(custom_page_menu_entries()) if custom_page_menu_entries else []),
            ),
        ],
    )

    page_menu = pagetypes.configure_page_menu(breadcrumb, current_type_dropdown, what)
    html.header(title, breadcrumb, page_menu)

    # Deletion of visuals
    delname = html.request.var("_delete")
    if delname and html.transaction_valid():
        if config.user.may('general.delete_foreign_%s' % what):
            user_id_str = html.request.get_unicode_input('_user_id', config.user.id)
            user_id = None if user_id_str is None else UserId(user_id_str)
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

    keys_sorted = sorted(sorted(visuals.keys(), key=lambda x: x[1]),
                         key=lambda x: x[0],
                         reverse=True)

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
    if what != "dashboards" and visual["hidden"]:
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
    title = _('Create %s') % visual_type_registry[what]().title
    what_s = what[:-1]

    vs_infos = SingleInfoSelection(info_keys)

    breadcrumb = visual_page_breadcrumb(what, title, "create")
    html.header(
        title, breadcrumb,
        make_simple_form_page_menu(breadcrumb,
                                   form_name="create_visual",
                                   button_name="save",
                                   save_title=_("Continue")))

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
    info_keys = list(visual_info_registry.keys())
    if info_handler:
        handler_keys = info_handler(visual)
        if handler_keys is not None:
            info_keys = handler_keys

    single_info_keys = [key for key in info_keys if key in visual['single_infos']]
    multi_info_keys = [key for key in info_keys if key not in single_info_keys]

    # single infos first, the rest afterwards
    return [(info_key, visual_spec_single(info_key))
            for info_key in single_info_keys] + \
           [(info_key, visual_spec_multi(info_key, single_info_keys))
            for info_key in multi_info_keys
            if visual_spec_multi(info_key, single_info_keys)]


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


def visual_spec_multi(info_key, single_info_keys):
    info = visual_info_registry[info_key]()
    filter_list = VisualFilterList([info_key], title=info.title, ignore=set(single_info_keys))
    filter_names = filter_list.filter_names()
    # Skip infos which have no filters available
    return filter_list if filter_names else None


def process_context_specs(context_specs):
    context: Dict[Any, Any] = {}
    for info_key, spec in context_specs:
        ident = 'context_' + info_key

        attrs = spec.from_html_vars(ident)
        spec.validate_value(attrs, ident)
        context.update(attrs)
    return context


def render_context_specs(visual, context_specs):
    if not context_specs:
        return

    forms.header(_("Context / Search Filters"))
    # Trick: the field "context" contains a dictionary with
    # all filter settings, from which the value spec will automatically
    # extract those that it needs.
    value = visual.get('context', {})
    for info_key, spec in context_specs:
        forms.section(spec.title())
        ident = 'context_' + info_key
        spec.render_input(ident, value)


def page_edit_visual(what,
                     all_visuals,
                     custom_field_handler=None,
                     create_handler=None,
                     load_handler=None,
                     info_handler=None,
                     sub_pages: pagetypes.SubPagesSpec = None):
    if sub_pages is None:
        sub_pages = []

    visual_type = visual_type_registry[what]()
    if not config.user.may("general.edit_" + what):
        raise MKAuthException(_("You are not allowed to edit %s.") % visual_type.plural_title)
    visual: Dict[str, Any] = {
        'link_from': {},
    }

    # Load existing visual from disk - and create a copy if 'load_user' is set
    visualname = html.request.var("load_name")
    oldname = visualname
    mode = html.request.get_ascii_input_mandatory('mode', 'edit')
    owner_user_id = config.user.id
    if visualname:
        cloneuser = html.request.var("load_user")
        if cloneuser is not None:
            mode = 'clone'
            visual = copy.deepcopy(all_visuals.get((cloneuser, visualname), None))
            if not visual:
                raise MKUserError('cloneuser', _('The %s does not exist.') % visual_type.title)

            # Make sure, name is unique
            if UserId(cloneuser) == owner_user_id:  # Clone own visual
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
            if UserId(cloneuser) == owner_user_id:
                visual["title"] += _(" (Copy)")
        else:
            user_id_str = html.request.get_unicode_input("owner", config.user.id)
            owner_user_id = None if user_id_str is None else UserId(user_id_str)
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

    back_url = html.get_url_input("back", "edit_%s.py" % what)

    breadcrumb = visual_page_breadcrumb(what, title, mode)
    page_menu = pagetypes.make_edit_form_page_menu(
        breadcrumb,
        dropdown_name=what[:-1],
        mode=mode,
        type_title=visual_type.title,
        ident_attr_name=visual_type.ident_attr,
        sub_pages=sub_pages,
        form_name="visual",
        visualname=visualname,
    )
    html.header(title, breadcrumb, page_menu)

    # A few checkboxes concerning the visibility of the visual. These will
    # appear as boolean-keys directly in the visual dict, but encapsulated
    # in a list choice in the value spec.
    visibility_elements: List[Tuple[str, ValueSpec]] = [
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
        optional_keys=False,
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
            ('add_context_to_title',
             Checkbox(
                 title=_('Add context information to title'),
                 help=_("Whether or not additional information from the page context "
                        "(filters) should be added to the title given above."),
             )),
            ('topic', DropdownChoice(
                title=_('Topic'),
                choices=pagetypes.PagetypeTopics.choices(),
            )),
            ("sort_index",
             Integer(
                 title=_("Sort index"),
                 default_value=99,
                 help=_("You can customize the order of the %s by changing "
                        "this number. Lower numbers will be sorted first. "
                        "Topics with the same number will be sorted alphabetically.") %
                 visual_type.title,
             )),
            ("is_advanced",
             Checkbox(
                 title=_("Is advanced"),
                 default_value=99,
                 help=_("The navigation allows to hide items based on a basic / advanced "
                        "toggle. You can specify here whether or not this %s should be "
                        "treated as basic or advanced %s.") %
                 (visual_type.title, visual_type.title),
             )),
            ('description', TextAreaUnicode(title=_('Description') + '<sup>*</sup>',
                                            rows=4,
                                            cols=50)),
            ('linktitle',
             TextUnicode(title=_('Button Text') + '<sup>*</sup>',
                         help=_('If you define a text here, then it will be used in '
                                'context buttons linking to the %s instead of the regular title.') %
                         visual_type.title,
                         size=26)),
            ('icon', IconSelector(title=_('Button Icon'))),
            ('visibility', Dictionary(
                title=_('Visibility'),
                elements=visibility_elements,
            )),
        ],
    )

    context_specs = get_context_specs(visual, info_handler)

    # handle case of save or try or press on search button
    save_and_go = None
    for nr, (title, pagename, _icon) in enumerate(sub_pages):
        if html.request.var("save%d" % nr):
            save_and_go = pagename

    if save_and_go or html.request.var("save") or html.request.var("search"):
        try:
            general_properties = vs_general.from_html_vars('general')
            vs_general.validate_value(general_properties, 'general')

            if not general_properties['linktitle']:
                general_properties['linktitle'] = general_properties['title']
            if not general_properties['topic']:
                general_properties['topic'] = "other"

            old_visual = visual
            # TODO: Currently not editable, but keep settings
            visual = {'link_from': old_visual['link_from']}

            # The dict of the value spec does not match exactly the dict
            # of the visual. We take over some keys...
            for key in [
                    'single_infos',
                    'name',
                    'title',
                    'topic',
                    'sort_index',
                    'is_advanced',
                    'description',
                    'linktitle',
                    'icon',
                    'add_context_to_title',
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
                html.show_message(_('Your %s has been saved.') % visual_type.title)
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


def show_filter(f: Filter) -> None:
    html.open_div(class_=["floatfilter", f.ident])
    html.open_div(class_="legend")
    html.span(f.title)
    html.close_div()
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
        html.icon("alert", _("This filter cannot be displayed") + " (%s)\n%s" % (e, "".join(tbs)))
        html.write_text(_("This filter cannot be displayed"))
    html.close_div()
    html.close_div()


def get_filter(name: str) -> Filter:
    """Returns the filter object identified by the given name
    Raises a KeyError in case a not existing filter is requested."""
    return filter_registry[name]


def filters_allowed_for_info(info: str) -> Dict[str, Filter]:
    """Returns a map of filter names and filter objects that are registered for the given info"""
    allowed = {}
    for fname, filt in filter_registry.items():
        if filt.info is None or info == filt.info:
            allowed[fname] = filt
    return allowed


def filters_allowed_for_infos(info_list: List[str]) -> Dict[str, Filter]:
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
def get_link_filter_names(
        visual: Visual, info_keys: List[InfoName],
        link_filters: Dict[FilterName, FilterName]) -> List[Tuple[FilterName, FilterName]]:
    names: List[Tuple[FilterName, FilterName]] = []
    for info_key in visual['single_infos']:
        if info_key not in info_keys:
            for key in info_params(info_key):
                if key in link_filters:
                    names.append((key, link_filters[key]))
    return names


def filters_of_visual(visual: Visual,
                      info_keys: List[InfoName],
                      link_filters: Optional[Dict[FilterName, FilterName]] = None) -> List[Filter]:
    """Collects all filters to be used for the given visual"""
    if link_filters is None:
        link_filters = {}

    filters: Dict[FilterName, Filter] = {}

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

    return list(filters.values())


# TODO: Cleanup this special case
def get_ubiquitary_filters() -> List[FilterName]:
    return ["wato_folder"]


# Reduces the list of the visuals used filters. The result are the ones
# which are really presented to the user later.
# For the moment we only remove the single context filters which have a
# hard coded default value which is treated as enforced value.
def visible_filters_of_visual(visual: Visual, use_filters: List[Filter]) -> List[Filter]:
    show_filters = []

    single_keys = get_single_info_keys(visual["single_infos"])

    for f in use_filters:
        if f.ident not in single_keys or \
           not visual['context'].get(f.ident):
            show_filters.append(f)

    return show_filters


def add_context_to_uri_vars(context: VisualContext, single_infos: SingleInfos) -> None:
    """Populate the HTML vars with missing context vars

    The context vars set in single context are enforced (can not be overwritten by URL). The normal
    filter vars in "multiple" context are not enforced."""
    uri_vars = dict(get_context_uri_vars(context, single_infos))
    single_info_keys = get_single_info_keys(single_infos)

    for filter_name, filter_vars in context.items():
        # Enforce the single context variables that are available in the visual context
        if filter_name in single_info_keys:
            html.request.set_var(filter_name, "%s" % uri_vars[filter_name])
            continue

        if not isinstance(filter_vars, dict):
            continue  # Skip invalid filter values

        # This is a multi-context filter
        # We add the filter only if *none* of its HTML variables are present on the URL. This is
        # important because checkbox variables are not present if the box is not checked.
        if any(html.request.has_var(uri_varname) for uri_varname in filter_vars):
            continue

        for uri_varname in filter_vars.keys():
            html.request.set_var(uri_varname, "%s" % uri_vars[uri_varname])


def get_context_uri_vars(context: VisualContext, single_infos: SingleInfos) -> HTTPVariables:
    """Produce key/value tuples for HTTP variables from the visual context"""
    uri_vars: HTTPVariables = []
    single_info_keys = get_single_info_keys(single_infos)

    for filter_name, filter_vars in context.items():
        # Enforce the single context variables that are available in the visual context
        if filter_name in single_info_keys:
            uri_vars.append((filter_name, "%s" % context[filter_name]))

        if not isinstance(filter_vars, dict):
            continue  # Skip invalid filter values

        # This is a multi-context filter
        for uri_varname, value in filter_vars.items():
            uri_vars.append((uri_varname, "%s" % value))

    return uri_vars


@contextmanager
def context_uri_vars(context: VisualContext, single_infos: SingleInfos) -> Iterator[None]:
    """Updates the current HTTP variable context"""
    with html.stashed_vars():
        add_context_to_uri_vars(context, single_infos)
        yield


# Vice versa: find all filters that belong to the current URI variables
# and create a context dictionary from that.
def get_context_from_uri_vars(only_infos: Optional[List[InfoName]] = None,
                              single_infos: Optional[SingleInfos] = None) -> VisualContext:
    if single_infos is None:
        single_infos = []

    single_info_keys = set(get_single_info_keys(single_infos))

    context: VisualContext = {}
    for filter_name, filter_object in filter_registry.items():
        if only_infos is not None and filter_object.info not in only_infos:
            continue  # Skip filters related to not relevant infos

        this_filter_vars: FilterHTTPVariables = {}
        for varname in filter_object.htmlvars:
            if not html.request.has_var(varname):
                continue  # Variable to set in environment

            filter_value = html.request.get_str_input_mandatory(varname)
            if not filter_value:
                continue

            if varname in single_info_keys:
                context[filter_name] = filter_value
                break

            this_filter_vars[varname] = filter_value

        if this_filter_vars:
            context[filter_name] = this_filter_vars

    return context


def get_merged_context(*contexts: VisualContext) -> VisualContext:
    """Merges multiple filter contexts to a single one

    The last context that sets a filter wins. The intended order is to provide contexts in
    "descending order", e.g. like this for dashboards:

    1. URL context
    2. Dashboard context
    3. Dashlet context
    """
    merged_context = {}
    for c in contexts:
        merged_context.update(c)
    return merged_context


# Compute Livestatus-Filters based on a given context. Returns
# the only_sites list and a string with the filter headers
# TODO: Untangle only_sites and filter headers
# TODO: Reduce redundancies with filters_of_visual()
def get_filter_headers(table, infos, context):
    with html.stashed_vars():
        for filter_name, filter_vars in context.items():
            # first set the HTML variables. Sorry - the filters need this
            if isinstance(filter_vars, dict):  # this is a multi-context filter
                for uri_varname, value in filter_vars.items():
                    html.request.set_var(uri_varname, value)
            else:
                html.request.set_var(filter_name, filter_vars)

        filter_headers = "".join(collect_filter_headers(infos, table))
    return filter_headers, get_only_sites_from_context(context)


def get_only_sites_from_context(context: dict) -> Optional[List[SiteId]]:
    """Gather possible existing "only sites" information from context

      We need to deal with

      a) all possible site filters (site and siteopt).
      b) with single and multiple contexts

      Single contexts are structured like this:

      {"site": "sitename"}

      Multiple contexts are structured like this:

      {"site": {"site": "sitename"}}

      The difference is no fault or "old" data structure. We can have both kind of structures.
      These are the data structure the visuals work with.
      """

    for var in [("site"), ("siteopt")]:
        if var in context:
            if isinstance(context[var], dict):
                site_name = context[var].get("site")
                if site_name:
                    return [SiteId(site_name)]
                return None
            return [SiteId(context[var])]

    return None


def collect_filter_headers(info_keys, table):
    # Collect all available filters for these infos
    for filter_obj in filter_registry.values():
        if filter_obj.info in info_keys and filter_obj.available():
            yield filter_obj.filter(table)


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


def FilterChoices(infos: List[InfoName], title: str, help: str):  # pylint: disable=redefined-builtin
    """Select names of filters for the given infos"""
    return DualListChoice(
        choices=[(x[0], x[1].title()) for x in VisualFilterList.get_choices(infos, ignore=set())],
        title=title,
        help=help,
    )


class VisualFilterList(ListOfMultiple):
    """Implements a list of available filters for the given infos. By default no
    filter is selected. The user may select a filter to be activated, then the
    filter is rendered and the user can provide a default value.
    """
    @classmethod
    def get_choices(cls, info, ignore):
        return sorted(cls._get_filter_specs([info], ignore).items(),
                      key=lambda x: (x[1]._filter.sort_index, x[1].title()))

    @classmethod
    def _get_filters(cls, infos, ignore):
        return {
            fname: fspec._filter for fname, fspec in cls._get_filter_specs(infos, ignore).items()
        }

    @classmethod
    def _get_filter_specs(cls, infos, ignore):
        fspecs: Dict[str, VisualFilter] = {}
        for info in infos:
            for fname, filter_ in filters_allowed_for_info(info).items():
                if fname not in fspecs and fname not in ignore:
                    fspecs[fname] = VisualFilter(fname, title=filter_.title)
        return fspecs

    def __init__(self, info_list, **kwargs):
        ignore: Set[str] = kwargs.pop("ignore", set())
        self._filters = self._get_filters(info_list, ignore)

        kwargs.setdefault('title', _('Filters'))
        kwargs.setdefault('add_label', _('Add filter'))
        kwargs.setdefault('del_label', _('Remove filter'))
        kwargs["delete_style"] = "filter"

        grouped: GroupedListOfMultipleChoices = [
            ListOfMultipleChoiceGroup(title=visual_info_registry[info]().title,
                                      choices=self.get_choices(info, ignore)) for info in info_list
        ]
        super(VisualFilterList, self).__init__(grouped,
                                               "ajax_visual_filter_list_get_choice",
                                               page_request_vars={
                                                   "infos": info_list,
                                                   "ignore": list(ignore),
                                               },
                                               **kwargs)

    def filter_names(self):
        return self._filters.keys()


class VisualFilterListWithAddPopup(VisualFilterList):
    """Special form of the visual filter list to be used in the views and dashboards"""
    @staticmethod
    def filter_list_id(varprefix: str) -> str:
        return "%s_popup_filter_list" % varprefix

    def _show_add_elements(self, varprefix: str) -> None:
        filter_list_id = VisualFilterListWithAddPopup.filter_list_id(varprefix)
        filter_list_selected_id = filter_list_id + "_selected"

        html.open_div(id_=filter_list_id, class_="popup_filter_list")
        html.more_button(filter_list_id, 1)
        for group in self._grouped_choices:
            if not group.choices:
                continue

            group_id = "filter_group_" + "".join(group.title.split()).lower()

            html.open_div(id_=group_id, class_="filter_group")
            # Show / hide all entries of this group
            html.a(group.title,
                   href="",
                   class_="filter_group_title",
                   onclick="cmk.page_menu.toggle_filter_group_display(this.nextSibling)")

            # Display all entries of this group
            html.open_ul(class_="active")
            for choice in group.choices:
                filter_name = choice[0]

                filter_obj = filter_registry[filter_name]
                html.open_li(class_="advanced" if filter_obj.is_advanced else "basic")

                html.a(choice[1].title() or filter_name,
                       href="javascript:void(0)",
                       onclick="cmk.valuespecs.listofmultiple_add(%s, %s, %s, this);"
                       "cmk.page_menu.update_filter_list_scroll(%s)" %
                       (json.dumps(varprefix), json.dumps(self._choice_page_name),
                        json.dumps(self._page_request_vars), json.dumps(filter_list_selected_id)),
                       id_="%s_add_%s" % (varprefix, filter_name))

                html.close_li()
            html.close_ul()

            html.close_div()
        html.close_div()
        filters_applied = html.request.get_ascii_input("filled_in") == "filter"
        html.javascript('cmk.valuespecs.listofmultiple_init(%s, %s);' %
                        (json.dumps(varprefix), json.dumps(filters_applied)))
        # TODO: Currently does not work, because the filter popup (a parent element) has a simplebar
        # scrollbar. Need to investigate...
        html.final_javascript("cmk.utils.add_simplebar_scrollbar(%s);" % json.dumps(filter_list_id))


@page_registry.register_page("ajax_visual_filter_list_get_choice")
class PageAjaxVisualFilterListGetChoice(ABCPageListOfMultipleGetChoice):
    def _get_choices(self, request):
        infos, ignore = request["infos"], request["ignore"]
        return [
            ListOfMultipleChoiceGroup(title=visual_info_registry[info]().title,
                                      choices=VisualFilterList.get_choices(info, ignore))
            for info in infos
        ]


def render_filter_form(info_list: List[InfoName], mandatory_filters: List[Tuple[str, ValueSpec]],
                       context: VisualContext, page_name: str, reset_ajax_page: str) -> str:
    with html.plugged():
        show_filter_form(info_list, mandatory_filters, context, page_name, reset_ajax_page)
        return html.drain()


def show_filter_form(info_list: List[InfoName], mandatory_filters: List[Tuple[str, ValueSpec]],
                     context: VisualContext, page_name: str, reset_ajax_page: str) -> None:
    html.show_user_errors()
    html.begin_form("filter", method="GET", add_transid=False)
    varprefix = ""
    mandatory_filter_names = [f[0] for f in mandatory_filters]
    vs_filters = VisualFilterListWithAddPopup(info_list=info_list, ignore=mandatory_filter_names)

    filter_list_id = VisualFilterListWithAddPopup.filter_list_id(varprefix)
    filter_list_selected_id = filter_list_id + "_selected"
    _show_filter_form_buttons(varprefix, filter_list_id, vs_filters._page_request_vars, page_name,
                              reset_ajax_page)

    html.open_div(id_=filter_list_selected_id, class_="side_popup_content")
    try:
        # Configure required single info keys (the ones that are not set by the config)
        if mandatory_filters:
            html.h2(_("Mandatory context"))
            for filter_name, valuespec in mandatory_filters:
                html.h3(valuespec.title())
                valuespec.render_input(filter_name, None)

        # Give the user the option to redefine filters configured in the dashboard config
        # and also give the option to add some additional filters
        if mandatory_filters:
            html.h3(_("Additional context"))

        vs_filters.render_input(varprefix, context)
    except Exception:
        # TODO: Analyse possible cycle
        import cmk.gui.crash_reporting as crash_reporting
        crash_reporting.handle_exception_as_gui_crash_report()
    html.close_div()

    forms.end()

    html.hidden_fields()
    html.end_form()
    html.javascript("cmk.utils.add_simplebar_scrollbar(%s);" % json.dumps(filter_list_selected_id))

    # The filter popup is shown automatically when it has been submitted before on page reload. To
    # know that the user closed the popup after filtering, we have to hook into the close_popup
    # function.
    html.final_javascript(
        "cmk.page_menu.register_on_open_handler('popup_filters', cmk.page_menu.on_filter_popup_open);"
        "cmk.page_menu.register_on_close_handler('popup_filters', cmk.page_menu.on_filter_popup_close);"
    )


def _show_filter_form_buttons(varprefix: str, filter_list_id: str,
                              page_request_vars: Optional[Dict[str, Any]], view_name: str,
                              reset_ajax_page: str) -> None:
    html.open_div(class_="side_popup_controls")

    html.open_a(href="javascript:void(0);",
                onclick="cmk.page_menu.toggle_popup_filter_list(this, %s)" %
                json.dumps(filter_list_id),
                class_="add")
    html.icon("add")
    html.div(html.render_text("Add filter"), class_="description")
    html.close_a()

    html.open_div(class_="update_buttons")
    html.jsbutton("%s_reset" % varprefix,
                  _("Reset"),
                  cssclass="reset",
                  onclick="cmk.valuespecs.visual_filter_list_reset(%s, %s, %s, %s)" %
                  (json.dumps(varprefix), json.dumps(page_request_vars), json.dumps(view_name),
                   json.dumps(reset_ajax_page)))
    html.button("%s_apply" % varprefix, _("Apply filters"), cssclass="apply submit")
    html.close_div()
    html.close_div()


# Realizes a Multisite/visual filter in a valuespec. It can render the filter form, get
# the filled in values and provide the filled in information for persistance.
class VisualFilter(ValueSpec):
    def __init__(self, name, **kwargs):
        self._name = name
        self._filter = filter_registry[name]

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
        self._filter.validate_value(value)


def SingleInfoSelection(info_keys: List[InfoName]) -> DualListChoice:
    infos = [visual_info_registry[key]() for key in info_keys]
    choices = [(i.ident, _('Show information of a single %s') % i.title)
               for i in sorted(infos, key=lambda inf: (inf.sort_index, inf.title))]

    return DualListChoice(
        title=_('Specific objects'),
        choices=choices,
        rows=10,
    )


# Converts a context from the form { filtername : { ... } } into
# the for { infoname : { filtername : { } } for editing.
def pack_context_for_editing(visual: Visual,
                             info_handler: Optional[Callable[[Visual], List[InfoName]]]) -> Dict:
    # We need to pack all variables into dicts with the name of the
    # info. Since we have no mapping from info the the filter variable,
    # we pack into every info every filter. The dict valuespec will
    # pick out what it needs. Yurks.
    packed_context = {}
    info_keys = info_handler(visual) if info_handler else visual_info_registry.keys()
    for info_name in info_keys:
        packed_context[info_name] = visual.get('context', {})
    return packed_context


def unpack_context_after_editing(packed_context: Dict) -> VisualContext:
    context: VisualContext = {}
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


def visual_page_breadcrumb(what: str, title: str, page_name: str) -> Breadcrumb:
    breadcrumb = make_main_menu_breadcrumb(mega_menu_registry.menu_customize())

    list_title = visual_type_registry[what]().plural_title
    breadcrumb.append(BreadcrumbItem(title=list_title.title(), url="edit_%s.py" % what))

    if page_name == "list":  # The list is the parent of all others
        return breadcrumb

    breadcrumb.append(BreadcrumbItem(title=title, url=html.makeuri([])))
    return breadcrumb


def is_single_site_info(info_key: InfoName) -> bool:
    return visual_info_registry[info_key]().single_site


def single_infos_spec(single_infos: SingleInfos) -> Tuple[str, FixedValue]:
    return ('single_infos',
            FixedValue(
                single_infos,
                title=_('Show information of single'),
                totext=single_infos and ', '.join(single_infos) or
                _('Not restricted to showing a specific object.'),
            ))


def verify_single_infos(visual: Visual, context: VisualContext) -> None:
    """Check if all single infos from the element are known"""

    missing_single_infos = get_missing_single_infos(visual["single_infos"], context)

    # Special hack for the situation where hostgroup views link to host views: The host view uses
    # the datasource "hosts" which does not have the "hostgroup" info, but is configured to have a
    # single_info "hostgroup". To make this possible there exists a feature in
    # (ABCDataSource.link_filters, views._patch_view_context) which is a very specific hack. Have a
    # look at the description there.  We workaround the issue here by allowing this specific
    # situation but validating all others.
    #
    # The more correct approach would be to find a way which allows filters of different datasources
    # to have equal names. But this would need a bigger refactoring of the filter mechanic. One
    # day...
    if (visual.get("datasource") in ["hosts", "services"] and
            missing_single_infos == {'hostgroup'} and "opthostgroup" in context):
        return
    if (visual.get("datasource") == "services" and missing_single_infos == {"servicegroup"} and
            "optservicegroup" in context):
        return

    if missing_single_infos:
        raise MKUserError(
            None,
            _("Missing context information: %s. You can either add this as a fixed "
              "setting, or call the with the missing HTTP variables.") %
            (", ".join(missing_single_infos)))


def get_missing_single_infos(single_infos: SingleInfos, context: VisualContext) -> Set[FilterName]:
    single_info_keys = get_single_info_keys(single_infos)
    return set(single_info_keys).difference(context)


def visual_title(what: VisualTypeName, visual: Visual) -> str:
    title = _u(visual["title"])

    if visual["add_context_to_title"]:
        title = _add_context_title(visual, title)

    # Execute title plugin functions which might be added by the user to
    # the visuals plugins. When such a plugin function returns None, the regular
    # title of the page is used, otherwise the title returned by the plugin
    # function is used.
    for func in title_functions:
        result = func(what, visual, title)
        if result is not None:
            return result

    return title


def _add_context_title(visual: Visual, title: str) -> str:
    extra_titles = list(
        get_singlecontext_html_vars(visual["context"], visual["single_infos"]).values())

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

    if extra_titles:
        title += " " + ", ".join(extra_titles)

    for fn in get_ubiquitary_filters():
        # Disable 'wato_folder' filter, if WATO is disabled or there is a single host view
        if fn == "wato_folder" and (not config.wato_enabled or 'host' in visual['single_infos']):
            continue

        heading = get_filter(fn).heading_info()
        if heading:
            title = heading + " - " + title

    return title


# Determines the names of HTML variables to be set in order to
# specify a specify row in a datasource with a certain info.
# Example: the info "history" (Event Console History) needs
# the variables "event_id" and "history_line" to be set in order
# to exactly specify one history entry.
def info_params(info_key: InfoName) -> List[FilterName]:
    single_spec = visual_info_registry[info_key]().single_spec
    if single_spec is None:
        return []
    return list(dict(single_spec).keys())


def get_single_info_keys(single_infos: SingleInfos) -> List[FilterName]:
    keys: List[FilterName] = []
    for info_key in single_infos:
        keys.extend(info_params(info_key))
    return list(set(keys))


def get_singlecontext_vars(context: VisualContext, single_infos: SingleInfos) -> Dict[str, str]:
    return {
        key: val  #
        for key in get_single_info_keys(single_infos)
        for val in [context.get(key)]
        if isinstance(val, str)
    }


def get_singlecontext_html_vars(context: VisualContext,
                                single_infos: SingleInfos) -> Dict[str, str]:
    vars_ = get_singlecontext_vars(context, single_infos)
    for key in get_single_info_keys(single_infos):
        val = html.request.get_unicode_input(key)
        if val is not None:
            vars_[key] = val
    return vars_


def may_add_site_hint(visual_name: str, info_keys: List[InfoName], single_info_keys: SingleInfos,
                      filter_names: List[FilterName]) -> bool:
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


#.
#   .--Popup Add-----------------------------------------------------------.
#   |          ____                              _       _     _           |
#   |         |  _ \ ___  _ __  _   _ _ __      / \   __| | __| |          |
#   |         | |_) / _ \| '_ \| | | | '_ \    / _ \ / _` |/ _` |          |
#   |         |  __/ (_) | |_) | |_| | |_) |  / ___ \ (_| | (_| |          |
#   |         |_|   \___/| .__/ \__,_| .__/  /_/   \_\__,_|\__,_|          |
#   |                    |_|         |_|                                   |
#   +----------------------------------------------------------------------+
#   |  Handling of adding a visual element to a dashboard, etc.            |
#   '----------------------------------------------------------------------'


@cmk.gui.pages.register("ajax_popup_add_visual")
def ajax_popup_add() -> None:
    # name is unused at the moment in this, hand over as empty name
    page_menu_dropdown = page_menu_dropdown_add_to_visual(
        add_type=html.request.get_ascii_input_mandatory("add_type"), name="")[0]

    html.open_ul()

    for topic in page_menu_dropdown.topics:
        html.open_li()
        html.open_span()
        html.write(topic.title)
        html.close_span()
        html.close_li()

        for entry in topic.entries:
            html.open_li()

            if not isinstance(entry.item, PageMenuLink):
                html.write_text("Unhandled entry type '%s': %s" % (type(entry.item), entry.name))
                continue

            html.open_a(href=entry.item.link.url,
                        onclick=entry.item.link.onclick,
                        target=entry.item.link.target)
            html.icon(entry.icon_name or "trans")
            html.write(entry.title)
            html.close_a()
            html.close_li()

    html.close_ul()


def page_menu_dropdown_add_to_visual(add_type: str, name: str) -> List[PageMenuDropdown]:
    """Create the dropdown menu for adding a visual to other visuals / pagetypes

    Please not that this data structure is not only used for rendering the dropdown
    in the page menu. There is also the case of graphs which open a popup menu to
    show these entries.
    """

    visual_topics = []

    for visual_type_class in visual_type_registry.values():
        visual_type = visual_type_class()

        entries = list(visual_type.page_menu_add_to_entries(add_type))
        if not entries:
            continue

        visual_topics.append(
            PageMenuTopic(
                title=_("Add to %s") % visual_type.title,
                entries=entries,
            ))

    if add_type == "pnpgraph" and not cmk_version.is_raw_edition():
        visual_topics.append(
            PageMenuTopic(
                title=_("Export"),
                entries=[
                    PageMenuEntry(
                        title=_("Export as JSON"),
                        icon_name="download",
                        item=make_javascript_link("cmk.popup_menu.graph_export('graph_export')"),
                    ),
                    PageMenuEntry(
                        title=_("Export as PNG"),
                        icon_name="download",
                        item=make_javascript_link("cmk.popup_menu.graph_export('graph_image')"),
                    ),
                ],
            ))

    return [
        PageMenuDropdown(
            name="add_to",
            title=_("Add to"),
            topics=pagetypes.page_menu_add_to_topics(add_type) + visual_topics,
            popup_data=[add_type,
                        _encode_page_context(html.page_context), {
                            "name": name,
                        }],
        )
    ]


def _encode_page_context(page_context: VisualContext) -> VisualContext:
    return {k: "" if v is None else v for k, v in page_context.items()}


@cmk.gui.pages.register("ajax_add_visual")
def ajax_add_visual() -> None:
    visual_type_name = html.request.get_str_input_mandatory(
        'visual_type')  # dashboards / views / ...
    visual_type = visual_type_registry[visual_type_name]()

    visual_name = html.request.get_str_input_mandatory("visual_name")  # add to this visual

    # type of the visual to add (e.g. view)
    element_type = html.request.get_str_input_mandatory("type")

    create_info_raw = html.request.get_str_input_mandatory("create_info")

    create_info = json.loads(create_info_raw)
    visual_type.add_visual_handler(visual_name, element_type, create_info["context"],
                                   create_info["params"])
