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

screen_margin    = 5              # Distance from the left border of the main-frame to the dashboard area
dashlet_padding  = 23, 2, 2, 2, 2 # Margin (N, E, S, W, N w/o title) between outer border of dashlet and its content
corner_overlap   = 22
raster           = 10            # Raster the dashlet coords are measured in (px)
dashlet_min_size = 10, 10        # Minimum width and height of dashlets in raster units

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
    transform_dashboards(dashboards)
    available_dashboards = visuals.available('dashboards', dashboards)

# During implementation of the dashboard editor and recode of the visuals
# we had serveral different data structures, for example one where the
# views in user dashlets were stored with a context_type instead of the
# "single_info" key, which is the currently correct one.
#
# This code transforms views from user_dashboards.mk which have been
# migrated/created with daily snapshots from 2014-08 till beginning 2014-10.
# FIXME: Can be removed one day. Mark as incompatible change or similar.
def transform_dashboards(dashboards):
    for (u, n), dashboard in dashboards.items():
        visuals.transform_old_visual(dashboard)

        # Also transform dashlets
        for dashlet in dashboard['dashlets']:
            visuals.transform_old_visual(dashlet)

            if dashlet['type'] == 'pnpgraph':
                if 'service' not in dashlet['single_infos']:
                    dashlet['single_infos'].append('service')
                if 'host' not in dashlet['single_infos']:
                    dashlet['single_infos'].append('host')

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

            if dashlet.get('url', '').startswith('dashlet_hoststats') or dashlet.get('url', '').startswith('dashlet_servicestats'):
                # hoststats and servicestats
                dashlet['type'] = dashlet['url'][8:].split('.', 1)[0]

                if '?' in dashlet['url']:
                    # Transform old parameters:
                    # wato_folder
                    # host_contact_group
                    # service_contact_group
                    paramstr = dashlet['url'].split('?', 1)[1]
                    dashlet['context'] = {}
                    for key, val in [ p.split('=', 1) for p in paramstr.split('&') ]:
                        if key == 'host_contact_group':
                            dashlet['context']['opthost_contactgroup'] = {
                                'neg_opthost_contact_group': '',
                                'opthost_contact_group': val,
                            }
                        elif key == 'service_contact_group':
                            dashlet['context']['optservice_contactgroup'] = {
                                'neg_optservice_contact_group': '',
                                'optservice_contact_group': val,
                            }
                        elif key == 'wato_folder':
                            dashlet['context']['wato_folder'] = {
                                'wato_folder': val,
                            }

                del dashlet['url']

            elif dashlet.get('urlfunc') and type(dashlet['urlfunc']) != str:
                raise MKGeneralException(_('Unable to transform dashlet %d of dashboard %s: '
                                           'the dashlet is using "urlfunc" which can not be '
                                           'converted automatically.') % (nr, name))

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

            dashlet.setdefault('context', {})
            dashlet.setdefault('single_infos', [])

        # the modification time of builtin dashboards can not be checked as on user specific
        # dashboards. Set it to 0 to disable the modification chech.
        dashboard.setdefault('mtime', 0)

        dashboard.setdefault('show_title', True)
        if dashboard['title'] == None:
            dashboard['title'] = _('No title')
            dashboard['show_title'] = False

        dashboard.setdefault('single_infos', [])
        dashboard.setdefault('context', {})
        dashboard.setdefault('topic', _('Overview'))
        dashboard.setdefault('description', dashboard.get('title', ''))
    builtin_dashboards_transformed = True

def load_view_into_dashlet(dashlet, nr, view_name, add_context=None):
    import views
    views.load_views()
    views = views.permitted_views()
    if view_name in views:
        view = copy.deepcopy(views[view_name])
        dashlet.update(view)
        if add_context:
            dashlet['context'].update(add_context)

        # Overwrite the views default title with the context specific title
        dashlet['title'] = visuals.visual_title('view', view)
        dashlet['title_url'] = html.makeuri_contextless(
                [('view_name', view_name)] + visuals.get_singlecontext_vars(view).items(),
                filename='view.py')

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

    name = html.var("name")
    if not name:
        name = "main"
        html.set_var("name", name) # make sure that URL context is always complete
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

    # Either load the single object info from the dashlet or the dashlet type
    single_infos = []
    if 'single_infos' in dashlet:
        single_infos = dashlet['single_infos']
    elif 'single_infos' in dashlet_type:
        single_infos = dashlet_type['single_infos']

    global_context = board.get('context', {})

    url_vars = []
    for info_key in single_infos:
        for param in visuals.info_params(info_key):
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

    title = visuals.visual_title('dashboard', board)

    # Distance from top of the screen to the lower border of the heading
    header_height = 55

    # The title of the dashboard needs to be prefixed with the WATO path,
    # in order to make it clear to the user, that he is seeing only partial
    # data.
    if not board.get('show_title'):
        # Remove the whole header line
        html.set_render_headfoot(False)
        header_height = 0

    elif wato_folder is not None:
        title = wato.get_folder_title(wato_folder) + " - " + title

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
            urlfunc = dashlet['urlfunc']
            # We need to support function pointers to be compatible to old dashboard plugin
            # based definitions. The new dashboards use strings to reference functions within
            # the global context or functions of a module. An example would be:
            #
            # urlfunc: "my_custom_url_rendering_function"
            #
            # or within a module:
            #
            # urlfunc: "my_module.render_my_url"
            if type(urlfunc) == type(lambda x: x):
                dashlet["url"] = urlfunc()
            else:
                if '.' in urlfunc:
                    module_name, func_name = urlfunc.split('.', 1)
                    module = __import__(module_name)
                    fp = module.__dict__[func_name]
                else:
                    fp = globals()[urlfunc]
                dashlet["url"] = fp()

        dashlet_type = dashlet_types[dashlet['type']]

        # dashlets using the 'url' method will be refreshed by us. Those
        # dashlets using static content (such as an iframe) will not be
        # refreshed by us but need to do that themselves.
        if "url" in dashlet or ('render' in dashlet_type and dashlet_type.get('refresh')):
            url = dashlet.get("url", "dashboard_dashlet.py?name="+name+"&id="+ str(nr))
            refresh = dashlet.get("refresh", dashlet_type.get("refresh"))
            if refresh:
                action = None
                if 'on_refresh' in dashlet_type:
                    try:
                        action = 'function() {%s}' % dashlet_type['on_refresh'](nr, dashlet)
                    except Exception, e:
                        # Ignore the exceptions in non debug mode, assuming the exception also occures
                        # while dashlet rendering, which is then shown in the dashlet itselfs.
                        if config.debug:
                            raise
                else:
                    # FIXME: remove add_wato_folder_to_url
                    action = '"%s"' % add_wato_folder_to_url(url, wato_folder) # url to dashboard_dashlet.py

                if action:
                    refresh_dashlets.append('[%d, %d, %s]' % (nr, refresh, action))


        # Update the dashlets context with the dashboard global context when there are
        # useful information
        add_url_vars = apply_global_context(board, dashlet)

        # Paint the dashlet's HTML code
        render_dashlet(name, board, nr, dashlet, wato_folder, add_url_vars)

        if 'on_resize' in dashlet_type:
            try:
                on_resize.append('%d: function() {%s}' % (nr, dashlet_type['on_resize'](nr, dashlet)))
            except Exception, e:
                # Ignore the exceptions in non debug mode, assuming the exception also occures
                # while dashlet rendering, which is then shown in the dashlet itselfs.
                if config.debug:
                    raise

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
            #
            # Add dashlet menu
            #

            display = html.var('edit') == '1' and 'block' or 'none'
            html.write('<li id="control_add" class="sublink" style="display:%s" '
                       'onmouseover="show_submenu(\'control_add\')"><a href="javascript:void(0)">'
                       '<img src="images/dashboard_menuarrow.png" />%s</a>\n' % (display, _('Add dashlet')))

            # The dashlet types which can be added to the view
            html.write('<ul id="control_add_sub" class="menu sub" style="display:none">\n')

            add_existing_view_type = dashlet_types['view'].copy()
            add_existing_view_type['title'] = _('Existing View')
            add_existing_view_type['add_urlfunc'] = lambda: 'create_view_dashlet.py?name=%s&create=0&back=%s' % \
                                                            (html.urlencode(name), html.urlencode(html.makeuri([('edit', '1')])))

            choices = [ ('view', add_existing_view_type) ]
            choices += sorted(dashlet_types.items(), key = lambda x: x[1].get('sort_index', 0))

            for ty, dashlet_type in choices:
                if dashlet_type.get('selectable', True):
                    url = html.makeuri([('type', ty), ('back', html.makeuri([('edit', '1')]))], filename = 'edit_dashlet.py')
                    if 'add_urlfunc' in dashlet_type:
                        url = dashlet_type['add_urlfunc']()
                    html.write('<li><a href="%s"><img src="images/dashlet_%s.png" />%s</a></li>\n' %
                                                                (url, ty, dashlet_type['title']))
            html.write('</ul>\n')

            html.write('</li>\n')

            #
            # Properties link
            #

            html.write('<li><a href="edit_dashboard.py?load_name=%s&back=%s" '
                       'onmouseover="hide_submenus();" ><img src="images/trans.png" />%s</a></li>\n' %
                (name, html.urlencode(html.makeuri([])), _('Properties')))

            #
            # Stop editing
            #

            display = html.var('edit') == '1' and 'block' or 'none'
            html.write('<li id="control_view" style="display:%s"><a href="javascript:void(0)" '
                       'onmouseover="hide_submenus();" '
                       'onclick="toggle_dashboard_edit(false)"><img src="images/trans.png" />%s</a></li>\n' %
                            (display, _('Stop Editing')))

            #
            # Enable editing link
            #

            display = html.var('edit') != '1' and 'block' or 'none'
            html.write('<li id="control_edit" style="display:%s"><a href="javascript:void(0)" '
                       'onclick="toggle_dashboard_edit(true)"><img src="images/trans.png" />%s</a></li>\n' %
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
var grid_size = %d;
var header_height = %d;
var screen_margin = %d;
var dashlet_padding = Array%s;
var dashlet_min_size = Array%s;
var corner_overlap = %d;
var refresh_dashlets = [%s];
var on_resize_dashlets = {%s};
var dashboard_name = '%s';
var dashboard_mtime = %d;
var dashlets = %s;

calculate_dashboard();
window.onresize = function () { calculate_dashboard(); }
dashboard_scheduler(1);
    """ % (MAX, GROW, raster, header_height, screen_margin, dashlet_padding, dashlet_min_size,
           corner_overlap, ','.join(refresh_dashlets), ','.join(on_resize),
           name, board['mtime'], repr(dashlets_js)))

    if mode == 'edit':
        html.javascript('toggle_dashboard_edit(true)')

    html.body_end() # omit regular footer with status icons, etc.

def render_dashlet_content(nr, the_dashlet, stash_html_vars = False):
    if stash_html_vars:
        html.stash_vars()
        html.del_all_vars()
    visuals.add_context_to_uri_vars(the_dashlet)

    dashlet_type = dashlet_types[the_dashlet['type']]
    if 'iframe_render' in dashlet_type:
        dashlet_type['iframe_render'](nr, the_dashlet)
    else:
        dashlet_type['render'](nr, the_dashlet)

    if stash_html_vars:
        html.unstash_vars()

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

    # Get the title of the dashlet type (might be dynamically defined)
    title = dashlet_type.get('title')
    if dashlet_type.get('title_func'):
        title = dashlet_type.get('title_func')(dashlet)
    title = dashlet.get('title', title)
    if title != None and dashlet.get('show_title'):
        url = dashlet.get("title_url", None)
        if url:
            title = '<a href="%s">%s</a>' % (url, _u(title))
        else:
            title = _u(title)
        html.write('<div class="title" id="dashlet_title_%d"><span>%s</span></div>' % (nr, title))
    if dashlet.get("background", True):
        bg = " background"
    else:
        bg = ""
    html.write('<div class="dashlet_inner%s" id="dashlet_inner_%d">' % (bg, nr))

    try:
        # Optional way to render a dynamic iframe URL
        if "iframe_urlfunc" in dashlet_type:
            url = dashlet_type["iframe_urlfunc"](dashlet)
            if url != None:
                dashlet["iframe"] = url

        elif "iframe_render" in dashlet_type:
            dashlet["iframe"] = html.makeuri_contextless([
                ('name', name),
                ('id', nr),
                ('mtime', board['mtime'])] + add_url_vars, filename = "dashboard_dashlet.py")

        # The content is rendered only if it is fixed. In the
        # other cases the initial (re)-size will paint the content.
        if "render" in dashlet_type:
            render_dashlet_content(nr, dashlet)

        elif "content" in dashlet: # fixed content
            html.write(dashlet["content"])

        elif "iframe" in dashlet: # fixed content containing iframe
            if not dashlet.get("reload_on_resize"):
                url = add_wato_folder_to_url(dashlet["iframe"], wato_folder)
            else:
                url = 'about:blank'

            # Fix of iPad >:-P
            html.write('<div style="width: 100%; height: 100%; -webkit-overflow-scrolling:touch;">')
            html.write('<iframe id="dashlet_iframe_%d" allowTransparency="true" frameborder="0" width="100%%" '
                       'height="100%%" src="%s"> </iframe>' % (nr, url))
            html.write('</div>')
            if dashlet.get("reload_on_resize"):
                html.javascript('reload_on_resize["%d"] = "%s"' %
                                (nr, add_wato_folder_to_url(dashlet["iframe"], wato_folder)))
    except MKUserError, e:
        html.write('Problem while rendering the dashlet: %s' % html.attrencode(e))
    except Exception, e:
        if config.debug:
            import traceback
            html.write(traceback.format_exc().replace('\n', '<br>\n'))
        else:
            html.write('Problem while rendering the dashlet: %s' % html.attrencode(e))

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

    render_dashlet_content(ident, the_dashlet, stash_html_vars=False)

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
    visuals.page_list('dashboards', _("Edit Dashboards"), dashboards)

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
    visuals.page_create_visual('dashboards', visuals.infos.keys())

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

global vs_dashboard

def page_edit_dashboard():
    load_dashboards()

    # This is not defined here in the function in order to be l10n'able
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

def create_dashboard(old_dashboard, dashboard):
    board_properties = vs_dashboard.from_html_vars('dashboard')
    vs_dashboard.validate_value(board_properties, 'dashboard')
    dashboard.update(board_properties)

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
        import views
        url = html.makeuri([('back', html.makeuri([]))], filename = "create_view_dashlet_infos.py")
        views.page_create_view(next_url=url)

    else:
        # Choose an existing view from the list of available views
        choose_view(name)

def page_create_view_dashlet_infos():
    import views
    ds_name = html.var('datasource')
    if ds_name not in views.multisite_datasources:
        raise MKGeneralException(_('The given datasource is not supported'))

    # Create a new view by choosing the datasource and the single object types
    visuals.page_create_visual('views', views.multisite_datasources[ds_name]['infos'],
        next_url = html.makeuri_contextless([
            ('name', html.var('name')),
            ('type', 'view'),
            ('datasource', ds_name),
            ('back', html.makeuri([])),
            ('next', html.makeuri_contextless([('name', html.var('name')), ('edit', '1')],'dashboard.py')),
        ], filename = 'edit_dashlet.py'))

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
    back_url = html.var("back", "dashboard.py?edit=1&name=%s" % html.urlencode(html.var('name')))
    html.context_button(_("Back"), back_url, "back")
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
        raise MKGeneralException(_('The ID of the dashlet is missing.'))

    load_dashboards()

    if board not in available_dashboards:
        raise MKGeneralException(_('The requested dashboard does not exist.'))
    dashboard = available_dashboards[board]

    if ident == None:
        mode         = 'add'
        title        = _('Add Dashlet')
        dashlet_type = dashlet_types[ty]
        # Initial configuration
        dashlet = {
            'position'     : (1, 1),
            'size'         : dashlet_type.get('size', dashlet_min_size),
            'single_infos' : dashlet_type.get('single_infos', []),
            'type'         : ty,
        }
        ident   =  len(dashboard['dashlets'])
        dashboard['dashlets'].append(dashlet)

        single_infos_raw = html.var('single_infos')
        single_infos = []
        if single_infos_raw:
            single_infos = single_infos_raw.split(',')
            for key in single_infos:
                if key not in visuals.infos:
                    raise MKUserError('single_infos', _('The info %s does not exist.') % key)

        if not single_infos:
            single_infos = dashlet_types[ty].get('single_infos', [])

        dashlet['single_infos'] = single_infos
    else:
        mode    = 'edit'
        title   = _('Edit Dashlet')

        try:
            dashlet = dashboard['dashlets'][ident]
        except IndexError:
            raise MKGeneralException(_('The dashlet does not exist.'))

        ty           = dashlet['type']
        dashlet_type = dashlet_types[ty]
        single_infos = dashlet['single_infos']

    html.header(title, stylesheets=["pages","views"])

    html.begin_context_buttons()
    back_url = html.var('back', 'dashboard.py?name=%s&edit=1' % board)
    next_url = html.var('next', back_url)
    html.context_button(_('Back'), back_url, 'back')
    html.context_button(_('All Dashboards'), 'edit_dashboards.py', 'dashboard')
    html.end_context_buttons()

    vs_general = Dictionary(
        title = _('General Settings'),
        render = 'form',
        optional_keys = ['title', 'title_url'],
        elements = [
            ('type', FixedValue(ty,
                totext = dashlet_type['title'],
                title = _('Dashlet Type'),
            )),
            visuals.single_infos_spec(single_infos),
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
                title = _('Custom Title') + '<sup>*</sup>',
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

    context_specs = visuals.get_context_specs(dashlet,
        info_handler=lambda dashlet: dashlet_types[dashlet['type']].get('infos'))

    vs_type = None
    params = dashlet_type.get('parameters')
    render_input_func = None
    handle_input_func = None
    if type(params) == list:
        vs_type = Dictionary(
            title = _('Properties'),
            render = 'form',
            optional_keys = dashlet_type.get('opt_params'),
            validate = dashlet_type.get('validate_params'),
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

            if context_specs:
                dashlet['context'] = visuals.process_context_specs(context_specs)

            visuals.save('dashboards', dashboards)

            html.immediate_browser_redirect(1, next_url)
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

    html.begin_form("dashlet", method="POST")
    vs_general.render_input("general", dashlet)

    if vs_type:
        vs_type.render_input("type", dashlet)
    elif render_input_func:
        render_input_func(dashlet)

    visuals.render_context_specs(dashlet, context_specs)

    forms.end()
    html.show_localization_hint()
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

    result = html.confirm(_('Do you really want to delete this dashlet?'), method='GET', add_transid=True)
    if result == False:
        html.footer()
        return # confirm dialog shown
    elif result == True: # do it!
        try:
            dashboard['dashlets'].pop(ident)
            dashboard['mtime'] = int(time.time())
            visuals.save('dashboards', dashboards)

            html.message(_('The dashlet has been deleted.'))
        except MKUserError, e:
            html.write("<div class=error>%s</div>\n" % html.attrencode(e.message))
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

def popup_list_dashboards():
    if not config.may("general.edit_dashboards"):
        return []

    load_dashboards()
    return [ (name, board["title"])
             for (name, board)
             in available_dashboards.items() ]

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

def popup_add_dashlet(dashboard_name, dashlet_type, context, params):
    if not config.may("general.edit_dashboards"):
	# Exceptions do not work here.
	return

    load_dashboards()

    if dashboard_name not in available_dashboards:
	return
    dashboard = load_dashboard_with_cloning(dashboard_name)

    dashlet = default_dashlet_definition(dashlet_type)

    dashlet["context"] = context
    if dashlet_type == 'view':
        view_name = params['name']
    else:
        dashlet.update(params)

    # When a view shal be added to the dashboard, load the view and put it into the dashlet
    if dashlet_type == 'view':
        # save the original context and override the context provided by the view
        context = dashlet['context']
        load_view_into_dashlet(dashlet, len(dashboard['dashlets']), view_name, add_context=context)

    add_dashlet(dashlet, dashboard)

    # Directly go to the dashboard in edit mode. We send the URL as an answer
    # to the AJAX request
    html.write('dashboard.py?name=' + dashboard_name + '&edit=1')
