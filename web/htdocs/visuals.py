#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

from lib import *
import config, table

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

def save(what, visuals):
    userviews = {}
    for (user, name), view in visuals.items():
        if us == user:
            userviews[name] = view
    config.save_user_file(what, userviews)


def load(what, builtin_visuals, skip_func = None):
    visuals = {}

    # first load builtins. Set username to ''
    for name, view in builtin_visuals.items():
        view["owner"] = '' # might have been forgotten on copy action
        view["public"] = True
        view["name"] = name

        # Dashboards had not all COMMON fields in previous versions. Add them
        # here to be compatible for a specific time. Seamless migration, yeah.
        view.setdefault('description', '')
        view.setdefault('hidden', False)

        visuals[('', name)] = view

    # Now scan users subdirs for files "views.mk"
    subdirs = os.listdir(config.config_dir)
    for user in subdirs:
        try:
            dirpath = config.config_dir + "/" + user
            if not os.path.isdir(dirpath):
                continue

            path = "%s/%s.mk" % (dirpath, what)
            if not os.path.exists(path):
                continue

            views = eval(file(path).read())
            for name, view in views.items():
                view["owner"] = user
                view["name"] = name

                if skip_func and skip_func(view):
                    continue

                # Maybe resolve inherited attributes. This was a feature for several versions
                # to make the view texts localizable. This has been removed because the view
                # texts can now be localized using the custom localization strings.
                # This is needed for backward compatibility to make the views without these
                # attributes get the attributes from their builtin view.
                builtin_view = visuals.get(('', name))
                if builtin_view:
                    for attr in [ 'title', 'linktitle', 'topic', 'description' ]:
                        if attr not in view and attr in builtin_view:
                            view[attr] = builtin_view[attr]

                # Declare custom permissions
                declare_visual_permission(what, name, view)

                visuals[(user, name)] = view

                # Repair views with missing 'title' or 'description'
                for key in [ "title", "description" ]:
                    if key not in view:
                        view[key] = _("Missing %s") % key

        except SyntaxError, e:
            raise MKGeneralException(_("Cannot load %ss from %s/views.mk: %s") % (what, dirpath, e))

    return visuals

def declare_visual_permission(what, name, visual):
    permname = "%s.%s" % (what[:-1], name)
    if visual["public"] and not config.permission_exists(permname):
       config.declare_permission(permname, visual["title"],
                         visual["description"], ['admin','user','guest'])

# Load all users views just in order to declare permissions of custom views
def declare_custom_permissions(what):
    subdirs = os.listdir(config.config_dir)
    for user in subdirs:
        try:
            dirpath = config.config_dir + "/" + user
            if os.path.isdir(dirpath):
                path = "%s/%s.mk" % (dirpath, what)
                if not os.path.exists(path):
                    continue
                views = eval(file(path).read())
                for name, view in views.items():
                    declare_visual_permission(what, name, view)
        except:
            if config.debug:
                raise

# Get the list of views which are available to the user
# (which could be retrieved with get_view)
def available(what, all_visuals):
    user = config.user_id
    views = {}
    permprefix = what[:-1]

    # 1. user's own views, if allowed to edit views
    if config.may("general.edit_" + what):
        for (u, n), view in all_visuals.items():
            if u == user:
                views[n] = view

    # 2. views of special users allowed to globally override builtin views
    for (u, n), view in all_visuals.items():
        if n not in views and view["public"] and config.user_may(u, "general.force_" + what):
            # Honor original permissions for the current user
            permname = "%s.%s" % (permprefix, n)
            if config.permission_exists(permname) \
                and not config.may(permname):
                continue
            views[n] = view

    # 3. Builtin views, if allowed.
    for (u, n), view in all_visuals.items():
        if u == '' and n not in views and config.may("%s.%s" % (permprefix, n)):
            views[n] = view

    # 4. other users views, if public. Sill make sure we honor permission
    #    for builtin views. Also the permission "general.see_user_views" is
    #    necessary.
    if config.may("general.see_user_" + what):
        for (u, n), view in all_visuals.items():
            if n not in views and view["public"] and config.user_may(u, "general.publish_" + what):
                # Is there a builtin view with the same name? If yes, honor permissions.
                permname = "%s.%s" % (permprefix, n)
                if config.permission_exists(permname) \
                    and not config.may(permname):
                    continue
                views[n] = view

    return views

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

def page_list(what, visuals, render_create_form = None, custom_columns = [], render_context_buttons = None):
    what_s = what[:-1]
    if not config.may("general.edit_" + what):
        raise MKAuthException(_("You are not allowed to edit %s.") % what)

    html.header(_("Edit %s") % what, stylesheets=["pages","views","status"])
    html.help(_("Here you can create and edit customizable <b>views</b>. A view "
            "displays monitoring status or log data by combining filters, sortings, "
            "groupings and other aspects."))

    html.begin_context_buttons()
    html.context_button(_('Views'), 'edit_views.py', 'view')
    html.context_button(_('Dashboards'), 'edit_dashboards.py', 'dashboard')
    if render_context_buttons:
        render_context_buttons()
    html.end_context_buttons()

    # Deletion of views
    delname  = html.var("_delete")
    if delname and html.transaction_valid():
        deltitle = visuals[(config.user_id, delname)]['title']
        c = html.confirm(_("Please confirm the deletion of \"%s\".") % deltitle)
        if c:
            del visuals[(config.user_id, delname)]
            save(what, visuals)
            html.reload_sidebar()
        elif c == False:
            html.footer()
            return

    if render_create_form:
        render_create_form()

    html.write('<h3>' + (_("Existing %s") % what.title()) + '</h3>')

    table.begin(css = 'data', limit = None)

    keys_sorted = visuals.keys()
    keys_sorted.sort(cmp = lambda a,b: -cmp(a[0],b[0]) or cmp(a[1], b[1]))

    for (owner, viewname) in keys_sorted:
        if owner == "" and not config.may("%s.%s" % (what_s, viewname)):
            continue
        view = visuals[(owner, viewname)]
        if owner == config.user_id or (view["public"] \
            and (owner == "" or config.user_may(owner, "general.publish_" + what))):

            table.row(css = 'data')

            # Actions
            table.cell(_('Actions'), css = 'buttons')

            # Edit
            if owner == config.user_id:
                html.icon_button("edit_view.py?load_view=%s" % viewname, _("Edit"), "edit")

            # Clone / Customize
            buttontext = not owner and _("Customize this %s") % what_s \
                         or _("Create a clone of this %s") % what_s
            backurl = html.urlencode(html.makeuri([]))
            clone_url = "edit_view.py?clonefrom=%s&load_view=%s&back=%s" \
                        % (owner, viewname, backurl)
            html.icon_button(clone_url, buttontext, "clone")

            # Delete
            if owner == config.user_id:
                html.icon_button(html.makeactionuri([('_delete', viewname)]),
                    _("Delete this %s!") % what_s, "delete")

            # View Name
            table.cell(_('Name'), viewname)

            # Title
            table.cell(_('Title'))
            title = view['title']
            if not view["hidden"]:
                html.write("<a href=\"view.py?view_name=%s\">%s</a>" % (viewname, html.attrencode(title)))
            else:
                html.write(html.attrencode(title))
            html.help(html.attrencode(view['description']))

            # Custom cols
            for title, renderer in custom_columns:
                table.cell(title, renderer(view))

            # Owner
            if owner == "":
                ownertxt = "<i>" + _("builtin") + "</i>"
            else:
                ownertxt = owner
            table.cell(_('Owner'), ownertxt)
            table.cell(_('Public'), view["public"] and _("yes") or _("no"))
            table.cell(_('Hidden'), view["hidden"] and _("yes") or _("no"))

    table.end()
    html.footer()
