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

import os, copy

from lib import *
from valuespec import *
import config, table

visual_types = {
    'views': {
        'ident_attr':   'view_name',
        'title':         _("view"),
        'plural_title':  _("views"),
        'module_name':  'views',
    },
    'dashboards': {
        'ident_attr':   'name',
        'title':        _("dashboard"),
        'plural_title': _("dashboards"),
        'module_name':  'dashboard',
    },
}

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

    global title_functions ; title_functions = []
    global infos ; infos = {}
    global multisite_filters         ; multisite_filters          = {}
    global ubiquitary_filters        ; ubiquitary_filters         = [] # Always show this filters

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
    uservisuals = {}
    for (user_id, name), visual in visuals.items():
        if config.user_id == user_id:
            uservisuals[name] = visual
    config.save_user_file('user_' + what, uservisuals)


def load(what, builtin_visuals, skip_func = None):
    visuals = {}

    # first load builtins. Set username to ''
    for name, visual in builtin_visuals.items():
        visual["owner"] = '' # might have been forgotten on copy action
        visual["public"] = True
        visual["name"] = name

        # Dashboards had not all COMMON fields in previous versions. Add them
        # here to be compatible for a specific time. Seamless migration, yeah.
        visual.setdefault('description', '')
        visual.setdefault('hidden', False)

        visuals[('', name)] = visual

    # Now scan users subdirs for files "visuals.mk"
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

            user_visuals = eval(file(path).read())
            for name, visual in user_visuals.items():
                visual["owner"] = user
                visual["name"] = name

                if skip_func and skip_func(visual):
                    continue

                # Maybe resolve inherited attributes. This was a feature for several versions
                # to make the visual texts localizable. This has been removed because the visual
                # texts can now be localized using the custom localization strings.
                # This is needed for backward compatibility to make the visuals without these
                # attributes get the attributes from their builtin visual.
                builtin_visual = visuals.get(('', name))
                if builtin_visual:
                    for attr in [ 'title', 'linktitle', 'topic', 'description' ]:
                        if attr not in visual and attr in builtin_visual:
                            visual[attr] = builtin_visual[attr]

                # Declare custom permissions
                declare_visual_permission(what, name, visual)

                visuals[(user, name)] = visual

                # Repair visuals with missing 'title' or 'description'
                for key in [ "title", "description" ]:
                    if key not in visual:
                        visual[key] = _("Missing %s") % key

        except SyntaxError, e:
            raise MKGeneralException(_("Cannot load %s from %s: %s") % (what, path, e))

    return visuals

def declare_visual_permission(what, name, visual):
    permname = "%s.%s" % (what[:-1], name)
    if visual["public"] and not config.permission_exists(permname):
       config.declare_permission(permname, visual["title"],
                         visual["description"], ['admin','user','guest'])

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
                visuals = eval(file(path).read())
                for name, visual in visuals.items():
                    declare_visual_permission(what, name, visual)
        except:
            if config.debug:
                raise

# Get the list of visuals which are available to the user
# (which could be retrieved with get_visual)
def available(what, all_visuals):
    user = config.user_id
    visuals = {}
    permprefix = what[:-1]

    # 1. user's own visuals, if allowed to edit visuals
    if config.may("general.edit_" + what):
        for (u, n), visual in all_visuals.items():
            if u == user:
                visuals[n] = visual

    # 2. visuals of special users allowed to globally override builtin visuals
    for (u, n), visual in all_visuals.items():
        if n not in visuals and visual["public"] and config.user_may(u, "general.force_" + what):
            # Honor original permissions for the current user
            permname = "%s.%s" % (permprefix, n)
            if config.permission_exists(permname) \
                and not config.may(permname):
                continue
            visuals[n] = visual

    # 3. Builtin visuals, if allowed.
    for (u, n), visual in all_visuals.items():
        if u == '' and n not in visuals and config.may("%s.%s" % (permprefix, n)):
            visuals[n] = visual

    # 4. other users visuals, if public. Sill make sure we honor permission
    #    for builtin visuals. Also the permission "general.see_user_visuals" is
    #    necessary.
    if config.may("general.see_user_" + what):
        for (u, n), visual in all_visuals.items():
            if n not in visuals and visual["public"] and config.user_may(u, "general.publish_" + what):
                # Is there a builtin visual with the same name? If yes, honor permissions.
                permname = "%s.%s" % (permprefix, n)
                if config.permission_exists(permname) \
                    and not config.may(permname):
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

def page_list(what, title, visuals, custom_columns = [], render_custom_buttons=None):
    what_s = what[:-1]
    if not config.may("general.edit_" + what):
        raise MKAuthException(_("Sorry, you lack the permission for editing this type of visuals."))

    html.header(title, stylesheets=["pages", "views", "status"])

    html.begin_context_buttons()
    html.context_button(_('New'), 'create_%s.py' % what_s, "new")
    for other_what, info in visual_types.items():
        if what != other_what:
            html.context_button(info["plural_title"].title(), 'edit_%s.py' % other_what, other_what[:-1])
    html.end_context_buttons()

    # Deletion of visuals
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

    keys_sorted = visuals.keys()
    keys_sorted.sort(cmp = lambda a,b: -cmp(a[0],b[0]) or cmp(a[1], b[1]))

    custom  = []
    builtin = []
    for (owner, visualname) in keys_sorted:
        if owner == "" and not config.may("%s.%s" % (what_s, visualname)):
            continue # not allowed to see this view

        visual = visuals[(owner, visualname)]
        if owner == config.user_id or \
           (visual["public"] and owner != '' and config.user_may(owner, "general.publish_" + what)):
            custom.append((owner, visualname, visual))
        elif visual["public"] and owner == "":
            builtin.append((owner, visualname, visual))

    for title, items in [ (_('Custom'), custom), (_('Builtin'), builtin) ]:
        html.write('<h3>' + title + '</h3>')

        table.begin(css = 'data', limit = None)

        for owner, visualname, visual in items:
            table.row(css = 'data')

            # Actions
            table.cell(_('Actions'), css = 'buttons')

            # Edit
            if owner == config.user_id:
                html.icon_button("edit_%s.py?load_name=%s" % (what_s, visualname), _("Edit"), "edit")

            # Clone / Customize
            buttontext = _("Create a customized copy of this")
            backurl = html.urlencode(html.makeuri([]))
            clone_url = "edit_%s.py?load_user=%s&load_name=%s&back=%s" \
                        % (what_s, owner, visualname, backurl)
            html.icon_button(clone_url, buttontext, "clone")

            # Delete
            if owner == config.user_id:
                html.icon_button(html.makeactionuri([('_delete', visualname)]),
                    _("Delete!"), "delete")

            # Custom buttons - visual specific
            if render_custom_buttons:
                render_custom_buttons(visualname, visual)

            # visual Name
            table.cell(_('ID'), visualname)

            # Title
            table.cell(_('Title'))
            title = _u(visual['title'])
            if not visual["hidden"]:
                html.write("<a href=\"%s.py?%s=%s\">%s</a>" %
                    (what_s, visual_types[what]['ident_attr'], visualname, html.attrencode(title)))
            else:
                html.write(html.attrencode(title))
            html.help(html.attrencode(_u(visual['description'])))

            # Custom cols
            for title, renderer in custom_columns:
                table.cell(title, renderer(visual))

            # Owner
            if owner == "":
                ownertxt = "<i>" + _("builtin") + "</i>"
            else:
                ownertxt = owner
            table.cell(_('Owner'), ownertxt)
            table.cell(_('Public'), visual["public"] and _("yes") or _("no"))
            table.cell(_('Hidden'), visual["hidden"] and _("yes") or _("no"))

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

# FIXME: title is not needed, that's contained in visual_types
def page_create_visual(what, title, info_keys, next_url = None):
    what_s = what[:-1]

    # FIXME: Sort by (assumed) common usage
    info_choices = []
    for key in info_keys:
        info_choices.append((key, _('Show information of a single %s') % infos[key]['title']))

    vs_infos = SingleInfoSelection(info_keys)

    html.header(_('Create %s') % title, stylesheets=["pages"])
    html.begin_context_buttons()
    back_url = html.var("back", "")
    html.context_button(_("Back"), back_url or "edit_%s.py" % what, "back")
    html.end_context_buttons()

    html.write('<p>')
    html.write(
        _('Depending on the choosen datasource a %s can list <i>multiple</i> or <i>single</i> objects. '
          'For example the <i>services</i> datasource can be used to simply create a list '
          'of <i>multiple</i> services, a list of <i>multiple</i> services of a <i>single</i> host or even '
          'a list of services with the same name on <i>multiple</i> hosts. When you just want to '
          'create a list of objects, you do not need to make any selection in this dialog. '
          'If you like to create a view for one specific object of a specific type, select the '
          'object type below and continue.') % what_s)
    html.write('</p>')

    if html.var('save') and html.check_transaction():
        try:
            single_infos = vs_infos.from_html_vars('single_infos')
            vs_infos.validate_value(single_infos, 'single_infos')

            if not next_url:
                next_url = 'edit_'+what_s+'.py?mode=create&single_infos=%s' % ','.join(single_infos)
            else:
                next_url += '&single_infos=%s' % ','.join(single_infos)
            html.http_redirect(next_url)
            return

        except MKUserError, e:
            html.write("<div class=error>%s</div>\n" % e.message)
            html.add_user_error(e.varname, e.message)

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
    context_specs = []
    info_keys = info_handler and info_handler(visual) or infos.keys()
    for info_key in info_keys:
        info = infos[info_key]

        if info_key in visual['single_infos']:
            params = info['single_spec']
            optional = True
            isopen = True
            vs = Dictionary(
                title = info['title'],
                # render = 'form',
                form_isopen = isopen,
                optional_keys = optional,
                elements = params,
            )
        else:
            filter_list  = VisualFilterList([info_key], title=info['title'])
            filter_names = filter_list.filter_names()
            params = [
                ('filters', filter_list),
            ]
            optional = None
            # Make it open by default when at least one filter is used
            isopen = bool([ fn for fn in visual.get('context', {}).keys()
                                                   if fn in filter_names ])
            vs = filter_list


        # Single info context specifications should be listed first
        if info_key in visual['single_infos']:
            context_specs.insert(0, (info_key, vs))
        else:
            context_specs.append((info_key, vs))
    return context_specs

def process_context_specs(context_specs):
    context = {}
    for info_key, spec in context_specs:
        ident = 'context_' + info_key

        attrs = spec.from_html_vars(ident)
        html.debug(attrs)
        spec.validate_value(attrs, ident)
        context.update(attrs)
    return context

def render_context_specs(visual, context_specs):
    forms.header(_("Context / Search Filters"))
    for info_key, spec in context_specs:
        forms.section(spec.title())
        ident = 'context_' + info_key
        value = visual.get('context', {})
        spec.render_input(ident, value)

def page_edit_visual(what, all_visuals, custom_field_handler = None,
                     create_handler = None, try_handler = None,
                     load_handler = None, info_handler = None,
                     sub_pages = []):
    visual_type = visual_types[what]

    visual_type = visual_types[what]
    if not config.may("general.edit_" + what):
        raise MKAuthException(_("You are not allowed to edit %s.") % visual_type["plural_title"])
    what_s = what[:-1]

    visual = {}

    # Load existing visual from disk - and create a copy if 'load_user' is set
    visualname = html.var("load_name")
    oldname  = visualname
    mode     = html.var('mode', 'edit')
    if visualname:
        cloneuser = html.var("load_user")
        if cloneuser:
            mode  = 'clone'
            visual = copy.deepcopy(all_visuals.get((cloneuser, visualname), None))
            if not visual:
                raise MKUserError('cloneuser', _('The %s does not exist.') % visual_type["title"])

            # Make sure, name is unique
            if cloneuser == config.user_id: # Clone own visual
                newname = visualname + "_clone"
            else:
                newname = visualname
            # Name conflict -> try new names
            n = 1
            while (config.user_id, newname) in all_visuals:
                n += 1
                newname = visualname + "_clone%d" % n
            visual["name"] = newname
            visualname = newname
            oldname = None # Prevent renaming
            if cloneuser == config.user_id:
                visual["title"] += _(" (Copy)")
        else:
            visual = all_visuals.get((config.user_id, visualname))
            if not visual:
                visual = all_visuals.get(('', visualname)) # load builtin visual

        single_infos = visual['single_infos']

        if load_handler:
            load_handler(visual)
    else:
        mode = 'create'
        single_infos = []
        single_infos_raw = html.var('single_infos')
        if single_infos_raw:
            single_infos = single_infos_raw.split(',')
            for key in single_infos:
                if key not in infos:
                    raise MKUserError('single_infos', _('The info %s does not exist.') % key)
        visual['single_infos'] = single_infos

    if mode == 'clone':
        title = _('Clone %s') % visual_type["title"]
    elif mode == 'create':
        title = _('Create %s') % visual_type["title"]
    else:
        title = _('Edit %s') % visual_type["title"]

    html.header(title, stylesheets=["pages", "views", "status", "bi"])
    html.begin_context_buttons()
    back_url = html.var("back", "")
    html.context_button(_("Back"), back_url or "edit_%s.py" % what, "back")

    # Extra buttons to sub modules. These are used for things to edit about
    # this visual that are more complex to be done in one value spec.
    if mode not in [ "clone", "create" ]:
        for title, pagename, icon in sub_pages:
            uri = html.makeuri_contextless([(visual_types[what]['ident_attr'], visualname)],
                                           filename = pagename + '.py')
            html.context_button(title, uri, icon)
    html.end_context_buttons()

    # A few checkboxes concerning the visibility of the visual. These will
    # appear as boolean-keys directly in the visual dict, but encapsulated
    # in a list choice in the value spec.
    visibility_choices = [
        ('hidden',     _('Hide this %s from the sidebar') % visual_type["title"]),
        ('hidebutton', _('Do not show a context button to this %s') % visual_type["title"]),
    ]
    if config.may("general.publish_" + what):
        visibility_choices.append(
            ('public', _('Make this %s available for all users') % visual_type["title"]))

    vs_general = Dictionary(
        title = _("General Properties"),
        render = 'form',
        optional_keys = None,
        elements = [
            ('single_infos', FixedValue(single_infos,
                title = _('Specific objects'),
                totext = single_infos and ', '.join(single_infos) \
                                      or _('Showing information of multiple objects.'),
            )),
            ('name', TextAscii(
                title = _('Unique ID'),
                help = _("The ID will be used in URLs that point to a view, e.g. "
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
                         'context buttons linking to the %s instead of the regular title.') % visual_type["title"],
                size = 26)),
            ('icon', IconSelector(
                title = _('Button Icon'),
            )),
            ('visibility', ListChoice(
                title = _('Visibility'),
                choices = visibility_choices,
            )),
        ],
    )

    context_specs = get_context_specs(visual, info_handler)

    # handle case of save or try or press on search button
    save_and_go = None
    for nr, (title, pagename, icon) in enumerate(sub_pages):
        if html.var("save%d" % nr):
            save_and_go = html.makeuri_contextless([(visual_types[what]['ident_attr'], visualname)],
                                                   filename = pagename + '.py')

    if save_and_go or html.var("save") or html.var("try") or html.var("search"):
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
            for key in ['single_infos', 'name', 'title',
                        'topic', 'description', 'linktitle', 'icon']:
                visual[key] = general_properties[key]

            # ...and import the visibility flags directly into the visual
            for key, title in visibility_choices:
                visual[key] = key in general_properties['visibility']

            if create_handler:
                visual = create_handler(old_visual, visual)

            visual['context'] = process_context_specs(context_specs)

            if html.var("save") or save_and_go:
                if save_and_go:
                    back = save_and_go
                else:
                    back = html.var('back')
                    if not back:
                        back = 'edit_%s.py' % what

                if html.check_transaction():
                    all_visuals[(config.user_id, visual["name"])] = visual
                    # Handle renaming of visuals
                    if oldname and oldname != visual["name"]:
                        # -> delete old entry
                        if (config.user_id, oldname) in all_visuals:
                            del all_visuals[(config.user_id, oldname)]
                        # -> change visual_name in back parameter
                        if back:
                            varstring = visual_type["ident_attr"] + "="
                            back = back.replace(varstring + oldname, varstring + visual["name"])
                    save(what, all_visuals)

                html.immediate_browser_redirect(1, back)
                html.message(_('Your %s has been saved.') % visual_type["title"])
                html.reload_sidebar()
                html.footer()
                return

        except MKUserError, e:
            html.write("<div class=error>%s</div>\n" % e.message)
            html.add_user_error(e.varname, e.message)

    html.begin_form("visual", method = "POST")
    html.hidden_field("back", back_url)
    html.hidden_field("mode", mode)
    html.hidden_field("load_user", html.var("load_user", "")) # safe old name in case user changes it
    html.hidden_field("load_name", oldname) # safe old name in case user changes it

    # FIXME: Hier werden die Flags aus visbility nicht korrekt geladen. Wäre es nicht besser,
    # diese in einem Unter-Dict zu lassen, anstatt diese extra umzukopieren?
    visib = []
    for key, title in visibility_choices:
        if visual.get(key):
            visib.append(key)
    visual["visibility"] = visib

    vs_general.render_input("general", visual)

    if custom_field_handler:
        custom_field_handler(visual)

    render_context_specs(visual, context_specs)

    forms.end()
    url = "wato.py?mode=edit_configvar&varname=user_localizations"
    html.message("<sup>*</sup>" + _("These texts may be localized depending on the users' "
          "language. You can configure the localizations <a href=\"%s\">in the global settings</a>.") % url)

    html.button("save", _("Save"))
    for nr, (title, pagename, icon) in enumerate(sub_pages):
        html.button("save%d" % nr, _("Save and go to ") + title)
    html.hidden_fields()

    if try_handler:
        html.write(" ")
        html.button("try", _("Try out"))
        html.end_form()

        if html.has_var("try") or html.has_var("search"):
            html.set_var("search", "on")
            if visual:
                import bi
                bi.reset_cache_status()
                try_handler(visual)
            return # avoid second html footer
    else:
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

def declare_filter(sort_index, f, comment = None):
    multisite_filters[f.name] = f
    f.comment = comment
    f.sort_index = sort_index

# Base class for all filters
# name:          The unique id of that filter. This id is e.g. used in the
#                persisted view configuration
# title:         The title of the filter visible to the user. This text
#                may be localized
# info:          The datasource info this filter needs to work. If this
#                is "service", the filter will also be available in tables
#                showing service information. "host" is available in all
#                service and host views. The log datasource provides both
#                "host" and "service". Look into datasource.py for which
#                datasource provides which information
# htmlvars:      HTML variables this filter uses
# link_columns:  If this filter is used for linking (state "hidden"), then
#                these Livestatus columns are needed to fill the filter with
#                the proper information. In most cases, this is just []. Only
#                a few filters are useful for linking (such as the host_name and
#                service_description filters with exact match)
class Filter:
    def __init__(self, name, title, info, htmlvars, link_columns):
        self.name = name
        self.info = info
        self.title = title
        self.htmlvars = htmlvars
        self.link_columns = link_columns

    # Some filters can be unavailable due to the configuration (e.g.
    # the WATO Folder filter is only available if WATO is enabled.
    def available(self):
        return True

    # Some filters can be invisible. This is useful to hide filters which have always
    # the same value but can not be removed using available() because the value needs
    # to be set during runtime.
    # A good example is the "site" filter which does not need to be available to the
    # user in single site setups.
    def visible(self):
        return True

    # More complex filters need more height in the HTML layout
    def double_height(self):
        return False

    def display(self):
        raise MKInternalError(_("Incomplete implementation of filter %s '%s': missing display()") % \
                (self.name, self.title))
        html.write(_("FILTER NOT IMPLEMENTED"))

    def filter(self, tablename):
        return ""

    # Wether this filter needs to load host inventory data
    def need_inventory(self):
        return False

    # post-Livestatus filtering (e.g. for BI aggregations)
    def filter_table(self, rows):
        return rows

    def variable_settings(self, row):
        return [] # return pairs of htmlvar and name according to dataset in row

    def infoprefix(self, infoname):
        if self.info == infoname:
            return ""
        else:
            return self.info[:-1] + "_"

    # Hidden filters may contribute to the pages headers of the views
    def heading_info(self):
        return None

    # Returns the current representation of the filter settings from the HTML
    # var context. This can be used to persist the filter settings.
    def value(self):
        val = {}
        for varname in self.htmlvars:
            val[varname] = html.var(varname, '')
        return val

    # Is used to populate a value, for example loaded from persistance, into
    # the HTML context where it can be used by e.g. the display() method.
    def set_value(self, value):
        val = {}
        for varname in self.htmlvars:
            html.set_var(varname, value.get(varname))

def get_filter(name):
    return multisite_filters[name]

def filters_allowed_for_info(info):
    allowed = {}
    for fname, filt in multisite_filters.items():
        if filt.info == None or info == filt.info:
            allowed[fname] = filt
    return allowed

# Collects all filters to be shown for the given visual
def show_filters(visual, info_keys):
    show_filters = []
    for info_key in info_keys:
        if info_key in visual['single_infos']:
            for key in info_params(info_key):
                show_filters.append(get_filter(key))
        else:
            for key, val in visual['context'].items():
                if type(val) == dict: # this is a real filter
                    show_filters.append(get_filter(key))

    # add ubiquitary_filters that are possible for these infos
    for fn in ubiquitary_filters:
        # Disable 'wato_folder' filter, if WATO is disabled or there is a single host view
        if fn == "wato_folder" and (not config.wato_enabled or 'host' in visual['single_infos']):
            continue
        filter = get_filter(fn)
        if not filter.info or filter.info in info_keys:
            show_filters.append(filter)

    return list(set(show_filters)) # remove duplicates

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

# Implements a list of available filters for the given infos. By default no
# filter is selected. The user may select a filter to be activated, then the
# filter is rendered and the user can provide a default value.
class VisualFilterList(ListOfMultiple):
    def __init__(self, infos, **kwargs):
        self._infos = infos

        # First get all filters useful for the infos, then create VisualFilter
        # valuespecs from them and then sort them
        fspecs = {}
        self._filters = {}
        for info in self._infos:
            for fname, filter in filters_allowed_for_info(info).items():
                if fname not in fspecs and fname not in ubiquitary_filters:
                    fspecs[fname] = VisualFilter(fname,
                        title = filter.title,
                    )
                    self._filters[fname] = fspecs[fname]._filter

        # Convert to list and sort them!
        fspecs = fspecs.items()
        fspecs.sort(key = lambda x: (x[1]._filter.sort_index, x[1].title()))

        kwargs.setdefault('title', _('Filters'))
        kwargs.setdefault('add_label', _('Add filter'))
        kwargs.setdefault("size", 50)

        ListOfMultiple.__init__(self, fspecs, **kwargs)

    def filter_names(self):
        return self._filters.keys()

    # get the filters to be used from the value and the data from the filter
    # objects using the row data
    def filter_variable_settings(self, value, row):
        vars = []
        for fname in value.keys():
            try:
                vars += self._filters[fname].variable_settings(row)
            except KeyError:
                # When the row misses at least one var for a filter ignore this filter completely
                pass
        return vars

# Realizes a Multisite/visual filter in a valuespec. It can render the filter form, get
# the filled in values and provide the filled in information for persistance.
class VisualFilter(ValueSpec):
    def __init__(self, name, **kwargs):
        self._name   = name
        self._filter = multisite_filters[name]

        ValueSpec.__init__(self, **kwargs)

    def title(self):
        return self._filter.title

    def canonical_value(self):
        return {}

    def render_input(self, varprefix, value):
        # kind of a hack to make the current/old filter API work. This should
        # be cleaned up some day
        if value != None:
            self._filter.set_value(value)

        # A filter can not be used twice on a page, because the varprefix is not used
        html.write('<div class="floatfilter %s">' % (self._filter.double_height() and "double" or "single"))
        html.write('<div class=legend>%s</div>' % self._filter.title)
        html.write('<div class=content>')
        self._filter.display()
        html.write("</div>")
        html.write("</div>")

    def value_to_text(self, value):
        # FIXME: optimize. Needed?
        return repr(value)

    def from_html_vars(self, varprefix):
        # A filter can not be used twice on a page, because the varprefix is not used
        return self._filter.value()

    def validate_datatype(self, value, varprefix):
        if type(value) != dict:
            raise MKUserError(varprefix, _("The value must be of type dict, but it has type %s") %
                                                                    type_name(value))

    def validate_value(self, value, varprefix):
        ValueSpec.custom_validate(self, value, varprefix)


def SingleInfoSelection(info_keys, **args):
    info_choices = []
    for key in info_keys:
        info_choices.append((key, _('Show information of a single %s') % infos[key]['title']))

    args.setdefault("title", _('Specific objects'))
    args["choices"] = info_choices
    return  ListChoice(**args)


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

def visual_title(what, visual):
    extra_titles = []

    # Beware: if a single context visual is being visited *without* a context, then
    # the value of the context variable(s) is None. In order to avoid exceptions,
    # we simply drop these here.
    extra_titles = [ v for k, v in get_context_html_vars(visual) if v != None ]
    # FIXME: Is this really only needed for visuals without single infos?
    if not visual['single_infos']:
        used_filters = [ multisite_filters[fn] for fn in visual["context"].keys() ]
        for filt in used_filters:
            heading = filt.heading_info()
            if heading:
                extra_titles.append(heading)

    title = _u(visual["title"])
    if extra_titles:
        title += " " + ", ".join(extra_titles)

    for fn in ubiquitary_filters:
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
        if result != None:
            return result

    return title

def info_params(info_key):
    return dict(infos[info_key]['single_spec']).keys()

def get_single_info_keys(visual):
    keys = []
    for info_key in visual['single_infos']:
        keys += info_params(info_key)
    return list(set(keys))

def get_context_html_vars(visual):
    vars = []
    for key in get_single_info_keys(visual):
        vars.append((key, html.var(key, visual['context'].get(key))))
    return vars

# Collect all visuals that share a context with visual. For example
# if a visual has a host context, get all relevant visuals.
def collect_context_links(this_visual, mobile = False, only_types = []):
    # compute list of html variables needed for this visual
    active_filter_vars = set([])
    for var, val in get_context_html_vars(this_visual):
        if html.has_var(var):
            active_filter_vars.add(var)

    context_links = []
    for what in visual_types.keys():
        if not only_types or what in only_types:
            context_links += collect_context_links_of(what, this_visual, active_filter_vars, mobile)
    return context_links

def collect_context_links_of(what, this_visual, active_filter_vars, mobile):
    context_links = []

    # FIXME: Make this cross module access cleaner
    module_name = visual_types[what]["module_name"]
    thing_module = __import__(module_name)
    thing_module.__dict__['load_%s'% what]()
    available = thing_module.__dict__['permitted_%s' % what]()

    # sort buttons somehow
    visuals = available.values()
    visuals.sort(cmp = lambda b,a: cmp(a.get('icon'), b.get('icon')))

    for visual in visuals:
        name = visual["name"]
        linktitle = visual.get("linktitle")
        if not linktitle:
            linktitle = visual["title"]
        if visual == this_visual:
            continue
        if visual.get("hidebutton", False):
            continue # this visual does not want a button to be displayed

        if not mobile and visual.get('mobile') \
           or mobile and not visual.get('mobile'):
            continue

        if not visual['single_infos']:
            continue # skip non single visuals

        needed_vars = get_context_html_vars(visual)
        skip = False
        vars_values = []
        for var, val in needed_vars:
            if var not in active_filter_vars:
                skip = True
                break

            vars_values.append((var, val))

        if not skip:
            # add context link to this visual
            uri = html.makeuri_contextless(vars_values + [(visual_types[what]['ident_attr'], name)],
                                           filename = what[:-1] + '.py')
            icon = visual.get("icon")
            buttonid = "cb_" + name
            context_links.append((_u(linktitle), uri, icon, buttonid))

    return context_links

