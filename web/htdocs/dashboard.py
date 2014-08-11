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

import config, defaults, visuals, pprint, time, copy
from valuespec import *
from lib import *
import wato

# Python 2.3 does not have 'set' in normal namespace.
# But it can be imported from 'sets'
try:
    set()
except NameError:
    from sets import Set as set

loaded_with_language = False
builtin_dashboards = {}
dashlet_types = {}

# Declare constants to be used in the definitions of the dashboards
GROW = 0
MAX = -1

# These settings might go into the config module, sometime in future,
# in order to allow the user to customize this.

header_height    = 60             # Distance from top of the screen to the lower border of the heading
screen_margin    = 5              # Distance from the left border of the main-frame to the dashboard area
dashlet_padding  = 21, 5, 5, 0, 4 # Margin (N, E, S, W, N w/o title) between outer border of dashlet and its content
corner_overlap   = 22
title_height     = 0             # Height of dashlet title-box
raster           = 10, 10        # Raster the dashlet choords are measured in
dashlet_min_size = 10, 10        # Minimum width and height of dashlets

# Load plugins in web/plugins/dashboard and declare permissions,
# note: these operations produce language-specific results and
# thus must be reinitialized everytime a language-change has
# been detected.
def load_plugins():
    global loaded_with_language, dashboards, builtin_dashboards_transformed
    if loaded_with_language == current_language:
        return

    # Load plugins for dashboards. Currently these files
    # just may add custom dashboards by adding to builtin_dashboards.
    load_web_plugins("dashboard", globals())
    builtin_dashboards_transformed = False

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = current_language

    # Clear this structure to prevent users accessing dashboard structures created
    # by other users, make them see these dashboards
    dashboards = {}

    # Declare permissions for all dashboards
    config.declare_permission_section("dashboard", _("Dashboards"), do_sort = True)
    for name, board in builtin_dashboards.items():
        config.declare_permission("dashboard.%s" % name,
                board["title"],
                board.get("description", ""),
                config.builtin_role_ids)

    # Make sure that custom views also have permissions
    config.declare_dynamic_permissions(lambda: visuals.declare_custom_permissions('dashboards'))

def load_dashboards():
    global dashboards, available_dashboards
    transform_builtin_dashboards()
    dashboards = visuals.load('dashboards', builtin_dashboards)
    available_dashboards = visuals.available('dashboards', dashboards)

# be compatible to old definitions, where even internal dashlets were
# referenced by url, e.g. dashboard['url'] = 'hoststats.py'
# FIXME: can be removed one day. Mark as incompatible change or similar.
def transform_builtin_dashboards():
    global builtin_dashboards_transformed
    if builtin_dashboards_transformed:
        return # Only do this once
    for name, dashboard in builtin_dashboards.items():
        # Do not transform dashboards which are already in the new format
        if 'context' in dashboard:
            continue

        # Transform the dashlets
        for nr, dashlet in enumerate(dashboard['dashlets']):
            dashlet.setdefault('show_title', True)

            if dashlet.get('url', '').startswith('dashlet_') and dashlet['url'].endswith('.py'):
                # hoststats and servicestats
                dashlet['type'] = dashlet['url'][8:-3]
                del dashlet['url']

            elif dashlet.get('url', '') != '' or dashlet.get('urlfunc') or dashlet.get('iframe'):
                # Normal URL based dashlet
                dashlet['type'] = 'url'

                if dashlet.get('iframe'):
                    dashlet['url'] = dashlet['iframe']
                    del dashlet['iframe']

            elif dashlet.get('view', '') != '':
                # Transform views
                # There might be more than the name in the view definition
                view_name = dashlet['view'].split('&')[0]

                # Copy the view definition into the dashlet
                load_view_into_dashlet(dashlet, nr, view_name)
                del dashlet['view']

            else:
                raise MKGeneralException(_('Unable to transform dashlet %d of dashboard %s. '
                                           'You will need to migrate it on your own. Definition: %r' %
                                                            (nr, name, html.attrencode(dashlet))))

        # the modification time of builtin dashboards can not be checked as on user specific
        # dashboards. Set it to 0 to disable the modification chech.
        dashboard.setdefault('mtime', 0)

        dashboard.setdefault('show_title', True)
        if dashboard['title'] == None:
            dashboard['title'] = _('No title')
            dashboard['show_title'] = False

        dashboard.setdefault('context_type', 'global')
        dashboard.setdefault('context', {})
        dashboard.setdefault('topic', _('Overview'))
        dashboard.setdefault('description', dashboard.get('title', ''))
    builtin_dashboards_transformed = True

def load_view_into_dashlet(dashlet, nr, view_name):
    import views
    views.load_views()
    views = views.permitted_views()
    if view_name in views:
        dashlet.update(views[view_name])

    dashlet['type']       = 'view'
    dashlet['name']       = 'dashlet_%d' % nr
    dashlet['show_title'] = True

def save_dashboards(us):
    visuals.save('dashboards', dashboards)

def permitted_dashboards():
    return available_dashboards

# HTML page handler for generating the (a) dashboard. The name
# of the dashboard to render is given in the HTML variable 'name'.
# This defaults to "main".
def page_dashboard():
    load_dashboards()

    name = html.var("name", "main")
    if name not in available_dashboards:
        raise MKGeneralException(_("The requested dashboard can not be found."))

    render_dashboard(name)

def add_wato_folder_to_url(url, wato_folder):
    if not wato_folder:
        return url
    elif '/' in url:
        return url # do not append wato_folder to non-Check_MK-urls
    elif '?' in url:
        return url + "&wato_folder=" + html.urlencode(wato_folder)
    else:
        return url + "?wato_folder=" + html.urlencode(wato_folder)

# Updates the current dashlet with the current context vars maybe loaded from
# the dashboards global configuration or HTTP vars, but also returns a list
# of all HTTP vars which have been used
def apply_global_context(board, dashlet):
    dashlet_type = dashlet_types[dashlet['type']]

    context_type = None
    if 'context_type' in dashlet:
        context_type = dashlet['context_type']
    elif 'context_type' in dashlet_type:
        context_type = dashlet_type['context_type']

    global_context = board.get('context', {})

    url_vars = []
    if context_type:
        ty = visuals.context_types[context_type]
        if ty['single']:
            needed_params = [ p for p, vs in visuals.context_types[context_type]['parameters'] ]
            for param in needed_params:
                if param not in dashlet['context']:
                    # Get the vars from the global context or http vars
                    if param in global_context:
                        dashlet['context'][param] = global_context[param]
                    else:
                        dashlet['context'][param] = html.var(param)
                        url_vars.append((param, html.var(param)))
    return url_vars

def load_dashboard_with_cloning(name, edit = True):
    board = available_dashboards[name]
    if edit and board['owner'] != config.user_id:
        # This dashboard which does not belong to the current user is about to
        # be edited. In order to make this possible, the dashboard is being
        # cloned now!
        board = copy.deepcopy(board)
        board['owner'] = config.user_id

        dashboards[(config.user_id, name)] = board
        available_dashboards[name] = board
        visuals.save('dashboards', dashboards)

    return board

# Actual rendering function
def render_dashboard(name):
    mode = 'display'
    if html.var('edit') == '1':
        mode = 'edit'

    if mode == 'edit' and not config.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = load_dashboard_with_cloning(name, edit = mode == 'edit')

    # The dashboard may be called with "wato_folder" set. In that case
    # the dashboard is assumed to restrict the shown data to a specific
    # WATO subfolder or file. This could be a configurable feature in
    # future, but currently we assume, that *all* dashboards are filename
    # sensitive.

    wato_folder = html.var("wato_folder")

    # The title of the dashboard needs to be prefixed with the WATO path,
    # in order to make it clear to the user, that he is seeing only partial
    # data.
    title = _u(board["title"])

    global header_height
    if not board.get('show_title'):
        # Remove the whole header line
        html.set_render_headfoot(False)
        header_height = 0

    elif wato_folder is not None:
        title = wato.api.get_folder_title(wato_folder) + " - " + title

    html.header(title, javascripts=["dashboard"], stylesheets=["pages", "dashboard", "status", "views"])

    html.write("<div id=dashboard class=\"dashboard_%s\">\n" % name) # Container of all dashlets

    used_types = list(set([ d['type'] for d in board['dashlets'] ]))

    # Render dashlet custom scripts
    scripts = '\n'.join([ dashlet_types[ty]['script'] for ty in used_types if dashlet_types[ty].get('script') ])
    if scripts:
        html.javascript(scripts)

    # Render dashlet custom styles
    styles = '\n'.join([ dashlet_types[ty]['styles'] for ty in used_types if dashlet_types[ty].get('styles') ])
    if styles:
        html.write("<style>\n%s\n</style>\n" % styles)

    refresh_dashlets = [] # Dashlets with automatic refresh, for Javascript
    dashlets_js      = []
    on_resize        = [] # javascript function to execute after ressizing the dashlet
    for nr, dashlet in enumerate(board["dashlets"]):
        # dashlets using the 'urlfunc' method will dynamically compute
        # an url (using HTML context variables at their wish).
        if "urlfunc" in dashlet:
            dashlet["url"] = dashlet["urlfunc"]()

        dashlet_type = dashlet_types[dashlet['type']]

        # dashlets using the 'url' method will be refreshed by us. Those
        # dashlets using static content (such as an iframe) will not be
        # refreshed by us but need to do that themselves.
        if "url" in dashlet or ('render' in dashlet_type and dashlet_type.get('refresh')):
            url = dashlet.get("url", "dashboard_dashlet.py?name="+name+"&id="+ str(nr));
            refresh = dashlet.get("refresh")
            if refresh:
                # FIXME: remove add_wato_folder_to_url
                refresh_dashlets.append([nr, refresh, str(add_wato_folder_to_url(url, wato_folder))])

        # Update the dashlets context with the dashboard global context when there are
        # useful information
        add_url_vars = apply_global_context(board, dashlet)

        # Paint the dashlet's HTML code
        render_dashlet(name, board, nr, dashlet, wato_folder, add_url_vars)

        if 'on_resize' in dashlet_type:
            try:
                on_resize.append('%d: function() {%s}' % (nr, dashlet_type['on_resize'](nr, dashlet)))
            except Exception, e:
                html.write('Error in "on_resize handler": %s' % html.attrencode(e))

        dimensions = {
            'x' : dashlet['position'][0],
            'y' : dashlet['position'][1]
        }
        if dashlet_type.get('resizable', True):
            dimensions['w'] = dashlet['size'][0]
            dimensions['h'] = dashlet['size'][1]
        else:
            dimensions['w'] = dashlet_type['size'][0]
            dimensions['h'] = dashlet_type['size'][1]
        dashlets_js.append(dimensions)

    # Show the edit menu to all users which are allowed to edit dashboards
    if config.may("general.edit_dashboards"):
        html.write('<ul id="controls" class="menu" style="display:none">\n')

        if board['owner'] != config.user_id:
            # Not owned dashboards must be cloned before being able to edit. Do not switch to
            # edit mode using javascript, use the URL with edit=1. When this URL is opened,
            # the dashboard will be cloned for this user
            html.write('<li><a href="%s">%s</a></li>\n' % (html.makeuri([('edit', 1)]), _('Edit Dashboard')))

        else:
            # Show these options only to the owner of the dashboard
            html.write('<li><a href="edit_dashboard.py?load_name=%s&back=%s" '
                       'onmouseover="hide_submenus();" >%s</a></li>\n' %
                (name, html.urlencode(html.makeuri([])), _('Properties')))

            # Links visible during editing
            display = html.var('edit') == '1' and 'block' or 'none'
            html.write('<li id="control_view" style="display:%s"><a href="javascript:void(0)" '
                       'onmouseover="hide_submenus();" '
                       'onclick="toggle_dashboard_edit(false)">%s</a>\n' %
                            (display, _('Stop Editing')))

            html.write('<li id="control_add" class="sublink" style="display:%s" '
                       'onmouseover="show_submenu(\'control_add\')"><a href="javascript:void(0)">%s</a>\n' %
                            (display, _('Add dashlet')))

            # The dashlet types which can be added to the view
            html.write('<ul id="control_add_sub" class="menu sub" style="display:none">\n')

            add_existing_view_type = dashlet_types['view'].copy()
            add_existing_view_type['title'] = _('Existing View')
            add_existing_view_type['add_urlfunc'] = lambda: 'create_view_dashlet.py?name=%s&create=0' % html.urlencode(name)

            choices = [ ('view', add_existing_view_type) ]
            choices += sorted(dashlet_types.items(), key = lambda x: x[1].get('sort_index', 0))

            for ty, dashlet_type in choices:
                if dashlet_type.get('selectable', True):
                    url = html.makeuri([('type', ty), ('back', html.makeuri([('edit', '1')]))], filename = 'edit_dashlet.py')
                    if 'add_urlfunc' in dashlet_type:
                        url = dashlet_type['add_urlfunc']()
                    html.write('<li><a href="%s">%s</a></li>\n' % (url, dashlet_type['title']))
            html.write('</ul>\n')

            html.write('</li>\n')

            # Enable editing link
            display = html.var('edit') != '1' and 'block' or 'none'
            html.write('<li id="control_edit" style="display:%s"><a href="javascript:void(0)" '
                       'onclick="toggle_dashboard_edit(true)">%s</a></li>\n' %
                            (display, _('Edit Dashboard')))

        html.write("</ul>\n")

        html.icon_button(None, _('Edit the Dashboard'), 'dashboard_controls', 'controls_toggle',
                        onclick = 'void(0)')

    html.write("</div>\n")

    # Put list of all autorefresh-dashlets into Javascript and also make sure,
    # that the dashbaord is painted initially. The resize handler will make sure
    # that every time the user resizes the browser window the layout will be re-computed
    # and all dashlets resized to their new positions and sizes.
    html.javascript("""
var MAX = %d;
var GROW = %d;
var grid_size = new vec%s;
var header_height = %d;
var screen_margin = %d;
var title_height = %d;
var dashlet_padding = Array%s;
var dashlet_min_size = Array%s;
var corner_overlap = %d;
var refresh_dashlets = %r;
var on_resize_dashlets = {%s};
var dashboard_name = '%s';
var dashboard_mtime = %d;
var dashboard_url = '%s';
var dashlets = %s;

calculate_dashboard();
window.onresize = function () { calculate_dashboard(); }
dashboard_scheduler(1);
    """ % (MAX, GROW, raster, header_height, screen_margin, title_height, dashlet_padding, dashlet_min_size,
           corner_overlap, refresh_dashlets, ','.join(on_resize), name, board['mtime'],
           html.makeuri([]), repr(dashlets_js)))

    if mode == 'edit':
        html.javascript('toggle_dashboard_edit(true)')

    html.body_end() # omit regular footer with status icons, etc.

def render_dashlet_content(nr, the_dashlet):
    dashlet_type = dashlet_types[the_dashlet['type']]
    if 'iframe_render' in dashlet_type:
        dashlet_type['iframe_render'](nr, the_dashlet)
    else:
        dashlet_type['render'](nr, the_dashlet)

# Create the HTML code for one dashlet. Each dashlet has an id "dashlet_%d",
# where %d is its index (in board["dashlets"]). Javascript uses that id
# for the resizing. Within that div there is an inner div containing the
# actual dashlet content.
def render_dashlet(name, board, nr, dashlet, wato_folder, add_url_vars):
    dashlet_type = dashlet_types[dashlet['type']]

    classes = ['dashlet', dashlet['type']]
    if dashlet_type.get('resizable', True):
        classes.append('resizable')

    html.write('<div class="%s" id="dashlet_%d">' % (' '.join(classes), nr))

    title = dashlet.get('title', dashlet_type.get('title'))
    if title and dashlet.get('show_title'):
        url = dashlet.get("title_url", None)
        if url:
            title = '<a href="%s">%s</a>' % (url, title)
        html.write('<div class="title" id="dashlet_title_%d">%s</div>' % (nr, title))
    if dashlet.get("background", True):
        bg = " background"
    else:
        bg = ""
    html.write('<div class="dashlet_inner%s" id="dashlet_inner_%d">' % (bg, nr))

    # Optional way to render a dynamic iframe URL
    if "iframe_urlfunc" in dashlet_type:
        dashlet["iframe"] = dashlet_type["iframe_urlfunc"](dashlet)

    elif "iframe_render" in dashlet_type:
        dashlet["iframe"] = html.makeuri_contextless([
            ('name', name),
            ('id', nr),
            ('mtime', board['mtime'])] + add_url_vars, filename = "dashboard_dashlet.py")

    # The content is rendered only if it is fixed. In the
    # other cases the initial (re)-size will paint the content.
    if "render" in dashlet_type:
        try:
            render_dashlet_content(nr, dashlet)
        except MKUserError, e:
            html.write('Problem while rendering the dashlet: %s' % html.attrencode(e))
        except Exception, e:
            if config.debug:
                import traceback
                html.write(traceback.format_exc().replace('\n', '<br>\n'))
            else:
                html.write('Problem while rendering the dashlet: %s' % html.attrencode(e))

    elif "content" in dashlet: # fixed content
        html.write(dashlet["content"])

    elif "iframe" in dashlet: # fixed content containing iframe
        if not dashlet.get("reload_on_resize"):
            url = add_wato_folder_to_url(dashlet["iframe"], wato_folder)
        else:
            url = 'about:blank'

        # Fix of iPad >:-P
        html.write('<div style="width: 100%; height: 100%; -webkit-overflow-scrolling:touch; overflow: hidden;">')
        html.write('<iframe id="dashlet_iframe_%d" allowTransparency="true" frameborder="0" width="100%%" '
                   'height="100%%" src="%s"> </iframe>' % (nr, url))
        html.write('</div>')
        if dashlet.get("reload_on_resize"):
            html.javascript('reload_on_resize["%d"] = "%s"' %
                            (nr, add_wato_folder_to_url(dashlet["iframe"], wato_folder)))

    html.write("</div></div>\n")

#.
#   .--Draw Dashlet--------------------------------------------------------.
#   |     ____                       ____            _     _      _        |
#   |    |  _ \ _ __ __ ___      __ |  _ \  __ _ ___| |__ | | ___| |_      |
#   |    | | | | '__/ _` \ \ /\ / / | | | |/ _` / __| '_ \| |/ _ \ __|     |
#   |    | |_| | | | (_| |\ V  V /  | |_| | (_| \__ \ | | | |  __/ |_      |
#   |    |____/|_|  \__,_| \_/\_/   |____/ \__,_|___/_| |_|_|\___|\__|     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Draw dashlet HTML code which are rendered by the multisite dashboard |
#   '----------------------------------------------------------------------'

def ajax_dashlet():
    board = html.var('name')
    if not board:
        raise MKGeneralException(_('The name of the dashboard is missing.'))

    try:
        ident = int(html.var('id'))
    except ValueError:
        raise MKGeneralException(_('Invalid dashlet ident provided.'))

    load_dashboards()

    if board not in available_dashboards:
        raise MKGeneralException(_('The requested dashboard does not exist.'))
    dashboard = available_dashboards[board]

    mtime = saveint(html.var('mtime'))
    if mtime < dashboard['mtime']:
        # prevent reloading on the dashboard which already has the current mtime,
        # this is normally the user editing this dashboard. All others: reload
        # the whole dashboard once.
        html.javascript('if (parent.dashboard_mtime < %d) {\n'
                        '    parent.location.reload();\n'
                        '}' % dashboard['mtime'])

    the_dashlet = None
    for nr, dashlet in enumerate(dashboard['dashlets']):
        if nr == ident:
            the_dashlet = dashlet
            break

    if not the_dashlet:
        raise MKGeneralException(_('The dashlet can not be found on the dashboard.'))

    if the_dashlet['type'] not in dashlet_types:
        raise MKGeneralException(_('The requested dashlet type does not exist.'))

    render_dashlet_content(ident, the_dashlet)

#.
#   .--Dashboard List------------------------------------------------------.
#   |           ____            _     _        _     _     _               |
#   |          |  _ \  __ _ ___| |__ | |__    | |   (_)___| |_             |
#   |          | | | |/ _` / __| '_ \| '_ \   | |   | / __| __|            |
#   |          | |_| | (_| \__ \ | | | |_) |  | |___| \__ \ |_             |
#   |          |____/ \__,_|___/_| |_|_.__(_) |_____|_|___/\__|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def page_edit_dashboards():
    load_dashboards()
    visuals.page_list('dashboards', dashboards)

#.
#   .--Create Dashb.-------------------------------------------------------.
#   |      ____                _         ____            _     _           |
#   |     / ___|_ __ ___  __ _| |_ ___  |  _ \  __ _ ___| |__ | |__        |
#   |    | |   | '__/ _ \/ _` | __/ _ \ | | | |/ _` / __| '_ \| '_ \       |
#   |    | |___| | |  __/ (_| | ||  __/ | |_| | (_| \__ \ | | | |_) |      |
#   |     \____|_|  \___|\__,_|\__\___| |____/ \__,_|___/_| |_|_.__(_)     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | When clicking on create dashboard, this page is opened to make the   |
#   | context type of the new dashboard selectable.                        |
#   '----------------------------------------------------------------------'

def page_create_dashboard():
    visuals.page_create_visual('dashboards', allow_global = True)

#.
#   .--Dashb. Config-------------------------------------------------------.
#   |     ____            _     _         ____             __ _            |
#   |    |  _ \  __ _ ___| |__ | |__     / ___|___  _ __  / _(_) __ _      |
#   |    | | | |/ _` / __| '_ \| '_ \   | |   / _ \| '_ \| |_| |/ _` |     |
#   |    | |_| | (_| \__ \ | | | |_) |  | |__| (_) | | | |  _| | (_| |     |
#   |    |____/ \__,_|___/_| |_|_.__(_)  \____\___/|_| |_|_| |_|\__, |     |
#   |                                                           |___/      |
#   +----------------------------------------------------------------------+
#   | Configures the global settings of a dashboard.                       |
#   '----------------------------------------------------------------------'

def context_spec(dashboard):
    if 'context_type' in dashboard:
        context_type = visuals.context_types[dashboard['context_type']]

        if context_type['single']:
            return Dictionary(
                title = _('Context'),
                render = 'form',
                optional_keys = True,
                elements = context_type['parameters'],
            )
    return None

global vs_dashboard

def page_edit_dashboard():
    load_dashboards()

    global vs_dashboard
    vs_dashboard = Dictionary(
        title = _('Dashboard Properties'),
        render = 'form',
        optional_keys = None,
        elements = [
            ('show_title', Checkbox(
                title = _('Display dashboard title'),
                label = _('Show the header of the dashboard with the configured title.'),
                default_value = True,
            )),
        ],
    )

    visuals.page_edit_visual('dashboards', dashboards,
        create_handler = create_dashboard,
        custom_field_handler = custom_field_handler
    )

def custom_field_handler(dashboard):
    vs_dashboard.render_input('dashboard', dashboard and dashboard or None)

    vs_context = context_spec(dashboard)
    if vs_context:
        vs_context.render_input('context', dashboard and dashboard or None)

def create_dashboard(old_dashboard, dashboard):
    board_properties = vs_dashboard.from_html_vars('dashboard')
    vs_dashboard.validate_value(board_properties, 'dashboard')
    dashboard.update(board_properties)

    vs_context = context_spec(dashboard)
    if vs_context:
        context = vs_context.from_html_vars('context')
        vs_context.validate_value(context, 'context')
        dashboard['context'] = context

    # Do not remove the dashlet configuration during general property editing
    dashboard['dashlets'] = old_dashboard.get('dashlets', [])
    dashboard['mtime'] = int(time.time())

    return dashboard

#.
#   .--Dashlet Editor------------------------------------------------------.
#   |    ____            _     _      _     _____    _ _ _                 |
#   |   |  _ \  __ _ ___| |__ | | ___| |_  | ____|__| (_) |_ ___  _ __     |
#   |   | | | |/ _` / __| '_ \| |/ _ \ __| |  _| / _` | | __/ _ \| '__|    |
#   |   | |_| | (_| \__ \ | | | |  __/ |_  | |__| (_| | | || (_) | |       |
#   |   |____/ \__,_|___/_| |_|_|\___|\__| |_____\__,_|_|\__\___/|_|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def page_create_view_dashlet():
    create = html.var('create', '1') == '1'
    name = html.var('name')

    if create:
        # Create a new view by choosing the context type and then the datasource
        visuals.page_create_visual('views', allow_global = False,
            next_url = 'create_view_dashlet_ds.py?mode=create&context_type=%s'
                       + '&name=%s' % html.urlencode(name))

    else:
        # Choose an existing view from the list of available views
        choose_view(name)

def choose_view(name):
    import views
    views.load_views()
    vs_view = DropdownChoice(
        title = _('View Name'),
        choices = views.view_choices,
        sorted = True,
    )

    html.header(_('Create Dashlet from existing View'), stylesheets=["pages"])
    html.begin_context_buttons()
    html.context_button(_("Back"), html.makeuri([('edit', 1)], filename = "dashboard.py"), "back")
    html.end_context_buttons()

    if html.var('save') and html.check_transaction():
        try:
            view_name = vs_view.from_html_vars('view')
            vs_view.validate_value(view_name, 'view')

            load_dashboards()
            dashboard = available_dashboards[name]

            # Add the dashlet!
            dashlet = default_dashlet_definition('view')

            # save the original context and override the context provided by the view
            dashlet_id = len(dashboard['dashlets'])
            load_view_into_dashlet(dashlet, dashlet_id, view_name)
            add_dashlet(dashlet, dashboard)

            html.http_redirect('edit_dashlet.py?name=%s&id=%d' % (name, dashlet_id))
            return

        except MKUserError, e:
            html.write("<div class=error>%s</div>\n" % e.message)
            html.add_user_error(e.varname, e.message)

    html.begin_form('choose_view')
    forms.header(_('Select View'))
    forms.section(vs_view.title())
    vs_view.render_input('view', '')
    html.help(vs_view.help())
    forms.end()

    html.button('save', _('Continue'), 'submit')

    html.hidden_fields()
    html.end_form()
    html.footer()

def page_create_view_dashlet_ds():
    import views
    url = 'edit_dashlet.py?name=%s&type=view' % html.urlencode(html.var('name'))
    url += '&context_type=%s&datasource=%s'
    views.page_create_view_ds(url)

def page_edit_dashlet():
    if not config.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = html.var('name')
    if not board:
        raise MKGeneralException(_('The name of the dashboard is missing.'))

    ty = html.var('type')

    if html.has_var('id'):
        try:
            ident = int(html.var('id'))
        except ValueError:
            raise MKGeneralException(_('Invalid dashlet id'))
    else:
        ident = None

    if ident == None and not ty:
        raise MKGeneralException(_('The ident of the dashlet is missing.'))

    load_dashboards()

    if board not in available_dashboards:
        raise MKGeneralException(_('The requested dashboard does not exist.'))
    dashboard = available_dashboards[board]

    if ident == None:
        mode    = 'add'
        title   = _('Add Dashlet')
        # Initial configuration
        dashlet = {}
        ident   =  len(dashboard['dashlets'])
        dashboard['dashlets'].append(dashlet)
    else:
        mode    = 'edit'
        title   = _('Edit Dashlet')

        try:
            dashlet = dashboard['dashlets'][ident]
        except IndexError:
            raise MKGeneralException(_('The dashlet does not exist.'))

        ty = dashlet['type']

    dashlet_type = dashlet_types[ty]

    if not dashlet: # Initial configuration
        dashlet.update({
            'position': (1, 1),
            'size':     dashlet_type.get('size', dashlet_min_size)
        })

        if html.has_var('context_type'):
            dashlet['context_type'] = html.var('context_type')

    html.header(title, stylesheets=["pages","views"])

    html.begin_context_buttons()
    back_url = html.var('back', 'dashboard.py?name=%s&edit=1' % board)
    html.context_button(_('Back'), back_url, 'back')
    html.end_context_buttons()

    vs_general = Dictionary(
        title = _('General'),
        render = 'form',
        optional_keys = ['title', 'title_url'],
        elements = [
            ('type', FixedValue(ty,
                totext = dashlet_type['title'],
                title = _('Dashlet Type'),
            )),
            ('background', Checkbox(
                title = _('Colored Background'),
                label = _('Render background'),
                help = _('Render gray background color behind the dashlets content.'),
                default_value = True,
            )),
            ('show_title', Checkbox(
                title = _('Show Title'),
                label = _('Render the titlebar above the dashlet'),
                help = _('Render the titlebar including title and link above the dashlet.'),
                default_value = True,
            )),
            ('title', TextUnicode(
                title = _('Custom Title'),
                help = _('Most dashlets have a hard coded default title. For example the view snapin '
                         'has even a dynamic title which defaults to the real title of the view. If you '
                         'like to use another title, set it here.'),
                size = 50,
            )),
            ('title_url', TextUnicode(
                title = _('Link of Title'),
                help = _('The URL of the target page the link of the dashlet should link to.'),
                size = 50,
            )),
        ],
    )

    vs_context = None
    if 'context_type' in dashlet_type:
        vs_context = Dictionary(
            title = _('Context'),
            render = 'form',
            optional_keys = True,
            elements = visuals.context_types[dashlet_type['context_type']]['parameters'],
        )

    vs_type = None
    params = dashlet_type.get('parameters')
    render_input_func = None
    handle_input_func = None
    if type(params) == list:
        vs_type = Dictionary(
            title = _('Properties'),
            render = 'form',
            optional_keys = dashlet_type.get('opt_params'),
            elements = params,
        )
    elif type(params) == type(lambda x: x):
        # It's a tuple of functions which should be used to render and parse the params
        render_input_func, handle_input_func = params()

    if html.var('save') and html.transaction_valid():
        try:
            general_properties = vs_general.from_html_vars('general')
            vs_general.validate_value(general_properties, 'general')
            dashlet.update(general_properties)
            # Remove unset optional attributes
            if 'title' not in general_properties and 'title' in dashlet:
                del dashlet['title']

            if vs_type:
                type_properties = vs_type.from_html_vars('type')
                vs_type.validate_value(type_properties, 'type')
                dashlet.update(type_properties)

            elif handle_input_func:
                dashlet = handle_input_func(ident, dashlet)

            if vs_context:
                context = vs_context.from_html_vars('context')
                vs_context.validate_value(context, 'context')
                dashlet['context'] = context

            visuals.save('dashboards', dashboards)

            html.immediate_browser_redirect(1, back_url)
            if mode == 'edit':
                html.message(_('The dashlet has been saved.'))
            else:
                html.message(_('The dashlet has been added to the dashboard.'))
            html.reload_sidebar()
            html.footer()
            return

        except MKUserError, e:
            html.write("<div class=error>%s</div>\n" % e.message)
            html.add_user_error(e.varname, e.message)

    html.begin_form("dashlet")
    vs_general.render_input("general", dashlet)

    if vs_type:
        vs_type.render_input("type", dashlet)
    elif render_input_func:
        render_input_func(dashlet)

    if vs_context:
        vs_context.render_input("context", dashlet.get('context', {}))

    forms.end()
    html.button("save", _("Save"))
    html.hidden_fields()
    html.end_form()

    html.footer()

def page_delete_dashlet():
    if not config.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = html.var('name')
    if not board:
        raise MKGeneralException(_('The name of the dashboard is missing.'))

    try:
        ident = int(html.var('id'))
    except ValueError:
        raise MKGeneralException(_('Invalid dashlet id'))

    load_dashboards()

    if board not in available_dashboards:
        raise MKGeneralException(_('The requested dashboard does not exist.'))
    dashboard = available_dashboards[board]

    try:
        dashlet = dashboard['dashlets'][ident]
    except IndexError:
        raise MKGeneralException(_('The dashlet does not exist.'))

    html.header(_('Confirm Dashlet Deletion'), stylesheets=["pages","views"])

    html.begin_context_buttons()
    back_url = html.var('back', 'dashboard.py?name=%s&edit=1' % board)
    html.context_button(_('Back'), back_url, 'back')
    html.end_context_buttons()

    result = html.confirm(_('Do you really want to delete this dashlet?'), method = 'GET')
    if result == False:
        html.footer()
        return # confirm dialog shown
    elif result == True: # do it!
        try:
            dashboard['dashlets'].pop(ident)
            dashboard['mtime'] = int(time.time())
            visuals.save('dashboards', dashboards)

            html.message(_('The dashlet has deleted.'))
        except MKUserError, e:
            html.write("<div class=error>%s</div>\n" % e.message)
            return

    html.immediate_browser_redirect(1, back_url)
    html.reload_sidebar()
    html.footer()

#.
#   .--Ajax Updater--------------------------------------------------------.
#   |       _     _              _   _           _       _                 |
#   |      / \   (_) __ ___  __ | | | |_ __   __| | __ _| |_ ___ _ __      |
#   |     / _ \  | |/ _` \ \/ / | | | | '_ \ / _` |/ _` | __/ _ \ '__|     |
#   |    / ___ \ | | (_| |>  <  | |_| | |_) | (_| | (_| | ||  __/ |        |
#   |   /_/   \_\/ |\__,_/_/\_\  \___/| .__/ \__,_|\__,_|\__\___|_|        |
#   |          |__/                   |_|                                  |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def check_ajax_update():
    if not config.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = html.var('name')
    if not board:
        raise MKGeneralException(_('The name of the dashboard is missing.'))

    ident = int(html.var('id'))

    load_dashboards()

    if board not in available_dashboards:
        raise MKGeneralException(_('The requested dashboard does not exist.'))
    dashboard = available_dashboards[board]

    try:
        dashlet = dashboard['dashlets'][ident]
    except IndexError:
        raise MKGeneralException(_('The dashlet does not exist.'))

    return dashlet, dashboard

def ajax_dashlet_pos():
    dashlet, board = check_ajax_update()

    board['mtime'] = int(time.time())

    dashlet['position'] = saveint(html.var('x')), saveint(html.var('y'))
    dashlet['size']     = saveint(html.var('w')), saveint(html.var('h'))
    visuals.save('dashboards', dashboards)
    html.write('OK %d' % board['mtime'])

#.
#   .--Dashlet Popup-------------------------------------------------------.
#   |   ____            _     _      _     ____                            |
#   |  |  _ \  __ _ ___| |__ | | ___| |_  |  _ \ ___  _ __  _   _ _ __     |
#   |  | | | |/ _` / __| '_ \| |/ _ \ __| | |_) / _ \| '_ \| | | | '_ \    |
#   |  | |_| | (_| \__ \ | | | |  __/ |_  |  __/ (_) | |_) | |_| | |_) |   |
#   |  |____/ \__,_|___/_| |_|_|\___|\__| |_|   \___/| .__/ \__,_| .__/    |
#   |                                                |_|         |_|       |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def ajax_popup_add_dashlet():
    if not config.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    load_dashboards()
    html.write('<ul>\n')
    html.write('<li><span>%s</span></li>' % _('Add to dashboard:'))
    for dname, board in available_dashboards.items():
        html.write('<li>')
        html.write('<a href="javascript:void(0)" onclick="add_to_dashboard(\'%s\')">%s</a>' %
                                                               (dname, board['title']))
        html.write('</li>')
    html.write('</ul>\n')

def default_dashlet_definition(ty):
    return {
        'type'       : ty,
        'position'   : (1, 1),
        'size'       : dashlet_types[ty].get('size', dashlet_min_size),
        'show_title' : True,
    }

def add_dashlet(dashlet, dashboard):
    dashboard['dashlets'].append(dashlet)
    dashboard['mtime'] = int(time.time())
    visuals.save('dashboards', dashboards)

def ajax_add_dashlet():
    if not config.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = html.var('name')
    if not board:
        raise MKGeneralException(_('The name of the dashboard is missing.'))

    load_dashboards()

    if board not in available_dashboards:
        raise MKGeneralException(_('The requested dashboard does not exist.'))

    dashboard = load_dashboard_with_cloning(board)

    ty = html.var('type')
    if not ty:
        raise MKGeneralException(_('The type of the dashlet is missing.'))

    dashlet_type = dashlet_types[ty]

    dashlet = default_dashlet_definition(ty)

    # Parse context and params
    view_name = None
    for what in [ 'context', 'params' ]:
        val = html.var(what)
        data = {}
        if val == None:
            raise MKGeneralException(_('Unable to parse the dashlet parameter "%s".') % what)
        elif val == '':
            dashlet[what] = {}
            continue # silently skip empty vars

        for entry in val.split('|'):
            key, vartype, val = entry.split(':', 2)
            if vartype == 'number':
                val = int(val)
            data[key] = val

        if what == 'context':
            dashlet[what] = data
        else:
            if ty == 'view':
                view_name = data['name']
            dashlet.update(data)

    # When a view shal be added to the dashboard, load the view and put it into the dashlet
    if ty == 'view':
        # save the original context and override the context provided by the view
        context = dashlet['context']
        load_view_into_dashlet(dashlet, len(dashboard['dashlets']), view_name)
        dashlet['context'] = context

    add_dashlet(dashlet, dashboard)
