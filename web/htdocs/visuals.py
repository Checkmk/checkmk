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
from valuespec import *
import config, table

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

def load_plugins():
    global loaded_with_language
    if loaded_with_language == current_language:
        return

    global context_types
    context_types = {}

    load_web_plugins('visuals', globals())
    loaded_with_language = current_language

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

def save(what, visuals):
    userviews = {}
    for (user_id, name), view in visuals.items():
        if config.user_id == user_id:
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

def page_list(what, visuals, custom_columns = []):
    what_s = what[:-1]
    if not config.may("general.edit_" + what):
        raise MKAuthException(_("You are not allowed to edit %s.") % what)

    html.header(_("Edit %s") % what, stylesheets=["pages","views","status"])
    html.help(_("Here you can create and edit customizable <b>views</b>. A view "
            "displays monitoring status or log data by combining filters, sortings, "
            "groupings and other aspects."))

    html.begin_context_buttons()
    html.context_button(_('Create %s') % what_s.title(), 'create_%s.py' % what_s, what_s)
    html.context_button(_('Views'), 'edit_views.py', 'view')
    html.context_button(_('Dashboards'), 'edit_dashboards.py', 'dashboard')
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
                html.icon_button("edit_%s.py?load_name=%s" % (what_s, viewname), _("Edit"), "edit")

            # Clone / Customize
            buttontext = not owner and _("Customize this %s") % what_s \
                         or _("Create a clone of this %s") % what_s
            backurl = html.urlencode(html.makeuri([]))
            clone_url = "edit_%s.py?load_user=%s&load_name=%s&back=%s" \
                        % (what_s, owner, viewname, backurl)
            html.icon_button(clone_url, buttontext, "clone")

            # Delete
            if owner == config.user_id:
                html.icon_button(html.makeactionuri([('_delete', viewname)]),
                    _("Delete this %s!") % what_s, "delete")

            # View Name
            table.cell(_('Name'), viewname)

            # Title
            table.cell(_('Title'))
            title = _u(view['title'])
            if not view["hidden"]:
                html.write("<a href=\"view.py?view_name=%s\">%s</a>" % (viewname, html.attrencode(title)))
            else:
                html.write(html.attrencode(title))
            html.help(html.attrencode(_u(view['description'])))

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

def page_create_visual(what, allow_global = False, next_url = None):
    what_s = what[:-1]

    vs_type = DropdownChoice(
        title = _('Context Type'),
        choices = [(None, _('--- Select a Context type ---'))]
                  + [ (k, v['title']) for k, v in context_types.items() if allow_global or k != 'global' ],
        help = _('The context of a %s controls the type of objects to be shown. It '
                 'also sets wether single or multiple objects are displayed. The context '
                 'type of a %s can not be changed anymore.') % (what_s, what_s),
    )

    html.header(_('Create %s') % what_s.title(), stylesheets=["pages"])
    html.begin_context_buttons()
    back_url = html.var("back", "")
    if back_url:
        html.context_button(_("Back"), back_url, "back")
    html.context_button(_("All %s") % what.title(), "edit_%s.py" % what, what_s)
    html.end_context_buttons()

    if html.var('save') and html.check_transaction():
        try:
            context_type = vs_type.from_html_vars('context_type')
            vs_type.validate_value(context_type, 'context_type')
            if context_type == None:
                raise MKUserError('context_type', _('Please select a context type'))

            if not next_url:
                next_url = 'edit_'+what_s+'.py?mode=create&context_type=%s'
            html.http_redirect(next_url % context_type)
            return

        except MKUserError, e:
            html.write("<div class=error>%s</div>\n" % e.message)
            html.add_user_error(e.varname, e.message)

    html.begin_form('create_visual')
    html.hidden_field('mode', 'create')

    forms.header(_('Select Context Type'))
    forms.section(vs_type.title())
    vs_type.render_input('context_type', '')
    html.help(vs_type.help())
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

def page_edit_visual(what, all_visuals, custom_field_handler = None, create_handler = None, try_handler = None,
                     load_handler = None):
    what_s = what[:-1]
    if not config.may("general.edit_" + what):
        raise MKAuthException(_("You are not allowed to edit %s.") % what)

    view = {}

    # Load existing view from disk - and create a copy if 'load_user' is set
    viewname = html.var("load_name")
    oldname  = viewname
    mode     = html.var('mode', 'edit')
    if viewname:
        cloneuser = html.var("load_user")
        if cloneuser:
            mode  = 'clone'
            view = copy.deepcopy(all_visuals.get((cloneuser, viewname), None))
            if not view:
                raise MKUserError('cloneuser', _('The %s does not exist.') % what_s)

            # Make sure, name is unique
            if cloneuser == config.user_id: # Clone own view
                newname = viewname + "_clone"
            else:
                newname = viewname
            # Name conflict -> try new names
            n = 1
            while (config.user_id, newname) in all_visuals:
                n += 1
                newname = viewname + "_clone%d" % n
            view["name"] = newname
            viewname = newname
            oldname = None # Prevent renaming
            if cloneuser == config.user_id:
                view["title"] += _(" (Copy)")
        else:
            view = all_visuals.get((config.user_id, viewname))
            if not view:
                view = all_visuals.get(('', viewname)) # load builtin view

        context_type = view['context_type']

        if load_handler:
            load_handler(view)
    else:
        mode = 'create'
        context_type = html.var('context_type')
        if not context_type:
            raise MKUserError('context_type', _('The context type is missing.'))
        if context_type not in context_types:
            raise MKUserError('context_type', _('The context type does not exist.'))

    if mode == 'clone':
        title = _('Clone %s') % what_s.title()
    elif mode == 'create':
        title = _('Create %s') % what_s.title()
    else:
        title = _('Edit %s') % what_s.title()

    html.header(title, stylesheets=["pages", "views", "status", "bi"])
    html.begin_context_buttons()
    back_url = html.var("back", "")
    if back_url:
        html.context_button(_("Back"), back_url, "back")
    html.context_button(_("All %s") % what.title(), "edit_%s.py" % what, what_s)
    html.end_context_buttons()

    vs_general = Dictionary(
        title = _("General Properties"),
        render = 'form',
        optional_keys = None,
        elements = [
            ('context_type', FixedValue(context_type,
                title = _('Context Type'),
                totext = context_types[context_type]['title'],
            )),
            ('name', TextAscii(
                title = _('Name'),
                help = _("The name will be used in URLs that point to a view, e.g. "
                         "<tt>view.py?view_name=<b>myview</b></tt>. It will also be used "
                         "internally for identifying a view. You can create several views "
                         "with the same title but only one per view name. If you create a "
                         "view that has the same view name as a builtin view, then your "
                         "view will override that (shadowing it)."),
                regex = '^[a-zA-Z0-9_]+$',
                regex_error = _('The name of the view may only contain letters, digits and underscores.'),
                size = 24, allow_empty = False)),
            ('title', TextUnicode(
                title = _('Title') + '<sup>*</sup>',
                size = 50, allow_empty = False)),
            ('topic', TextUnicode(
                title = _('Topic') + '<sup>*</sup>',
                size = 50)),
            ('description', TextAreaUnicode(
                title = _('Description') + '<sup>*</sup>',
                rows = 4, cols = 50)),
            ('linktitle', TextUnicode(
                title = _('Button Text') + '<sup>*</sup>',
                help = _('If you define a text here, then it will be used in '
                         'context buttons linking to the %s instead of the regular title.') % what_s,
                size = 26)),
            ('icon', IconSelector(
                title = _('Button Icon'),
            )),
            ('visibility', ListChoice(
                title = _('Visibility'),
                choices = (config.may("general.publish_" + what) and [
                           ('public', _('Make this %s available for all users') % what_s),
                           ] or []) +
                          [ ('hidden', _('Hide this %s from the sidebar') % what_s),
                            ('hidebutton', _('Do not show a context button to this %s') % what_s)
                          ],
            )),
        ],
    )

    # handle case of save or try or press on search button
    if html.var("save") or html.var("try") or html.var("search"):
        try:
            general_properties = vs_general.from_html_vars('general')
            vs_general.validate_value(general_properties, 'general')

            if not general_properties['linktitle']:
                general_properties['linktitle'] = general_properties['title']
            if not general_properties['topic']:
                general_properties['topic'] = _("Other")

            old_view = view
            view = {
                'context_type': general_properties['context_type'],
                'name'        : general_properties['name'],
                'title'       : general_properties['title'],
                'topic'       : general_properties['topic'],
                'description' : general_properties['description'],
                'linktitle'   : general_properties['linktitle'],
                'icon'        : general_properties['icon'],
                'public'      : 'public' in general_properties['visibility'] and config.may("general.publish_" + what),
                'hidden'      : 'hidden' in general_properties['visibility'],
                'hidebutton'  : 'hidebutton' in general_properties['visibility'],
            }

            if create_handler:
                view = create_handler(old_view, view)

            if html.var("save"):
                back = html.var('back')
                if not back:
                    back = 'edit_%s.py' % what

                if html.check_transaction():
                    all_visuals[(config.user_id, view["name"])] = view
                    oldname = html.var("load_name")
                    # Handle renaming of views
                    if oldname and oldname != view["name"]:
                        # -> delete old entry
                        if (config.user_id, oldname) in all_visuals:
                            del all_visuals[(config.user_id, oldname)]
                        # -> change view_name in back parameter
                        if back:
                            back = back.replace('view_name=' + oldname, 'view_name=' + view["name"])
                    save(what, all_visuals)

                html.immediate_browser_redirect(1, back)
                html.message(_('Your %s has been saved.') % what_s)
                html.reload_sidebar()
                html.footer()
                return

        except MKUserError, e:
            html.write("<div class=error>%s</div>\n" % e.message)
            html.add_user_error(e.varname, e.message)

    html.begin_form("view", method = "POST")
    html.hidden_field("back", back_url)
    html.hidden_field("mode", mode)
    html.hidden_field("load_user", html.var("load_user", "")) # safe old name in case user changes it
    html.hidden_field("load_name", oldname) # safe old name in case user changes it

    vs_general.render_input("general", view)

    if custom_field_handler:
        custom_field_handler(view)

    forms.end()
    url = "wato.py?mode=edit_configvar&varname=user_localizations"
    html.message("<sup>*</sup>" + _("These texts may be localized depending on the users' "
          "language. You can configure the localizations <a href=\"%s\">in the global settings</a>.") % url)

    html.button("save", _("Save"))
    html.hidden_fields()
    html.end_form()

    if try_handler:
        html.write(" ")
        html.button("try", _("Try out"))
        html.end_form()

        if html.has_var("try") or html.has_var("search"):
            html.set_var("search", "on")
            if view:
                import bi
                bi.reset_cache_status()
                try_handler(view)
            return # avoid second html footer

    html.footer()

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

