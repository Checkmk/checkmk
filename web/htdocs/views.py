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

import config, defaults, livestatus, time, os, re, pprint, time
import weblib, traceback, forms, valuespec, inventory, visuals
from lib import *

# Python 2.3 does not have 'set' in normal namespace.
# But it can be imported from 'sets'
try:
    set()
except NameError:
    from sets import Set as set

# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False

# Load all view plugins
def load_plugins():
    global loaded_with_language

    if loaded_with_language == current_language:
        # always reload the hosttag painters, because new hosttags might have been
        # added during runtime
        load_host_tag_painters()
        return

    global multisite_datasources     ; multisite_datasources      = {}
    global multisite_layouts         ; multisite_layouts          = {}
    global multisite_painters        ; multisite_painters         = {}
    global multisite_sorters         ; multisite_sorters          = {}
    global multisite_builtin_views   ; multisite_builtin_views    = {}
    global multisite_painter_options ; multisite_painter_options  = {}
    global multisite_commands        ; multisite_commands         = []
    global view_hooks                ; view_hooks                 = {}
    global inventory_displayhints    ; inventory_displayhints     = {}

    config.declare_permission_section("action", _("Commands on host and services"), do_sort = True)

    load_web_plugins("views", globals())
    load_host_tag_painters()

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = current_language

    # Declare permissions for builtin views
    config.declare_permission_section("view", _("Multisite Views"), do_sort = True)
    for name, view in multisite_builtin_views.items():
        config.declare_permission("view.%s" % name,
                _u(view["title"]),
                _u(view["description"]),
                config.builtin_role_ids)

    # Make sure that custom views also have permissions
    config.declare_dynamic_permissions(lambda: visuals.declare_custom_permissions('views'))

    # Add painter names to painter objects (e.g. for JSON web service)
    for n, p in multisite_painters.items():
        p["name"] = n

# Load all views - users or builtins
def load_views():
    global multisite_views, available_views
    # Skip views which do not belong to known datasources
    multisite_views = visuals.load('views', multisite_builtin_views,
                    skip_func = lambda v: v['datasource'] not in multisite_datasources)
    available_views = visuals.available('views', multisite_views)
    transform_old_views()

def permitted_views():
    return available_views

# Convert views that are saved in the pre 1.2.6-style
# FIXME: Can be removed one day. Mark as incompatible change or similar.
def transform_old_views():

    for view in multisite_views.values():
        ds_name    = view['datasource']
        datasource = multisite_datasources[ds_name]

        if "context" not in view: # legacy views did not have this explicitly
            view.setdefault("user_sortable", True)

        if 'context_type' in view:
            # This code transforms views from user_views.mk which have been migrated with
            # daily snapshots from 2014-08 till beginning 2014-10.
            visuals.transform_old_visual(view)

        elif 'single_infos' not in view:
            # This tries to map the datasource and additional settings of the
            # views to get the correct view context
            #
            # This code transforms views from views.mk (legacy format) to the current format
            try:
                hide_filters = view.get('hide_filters')

                if 'service' in hide_filters and 'host' in hide_filters:
                    view['single_infos'] = ['service', 'host']
                elif 'service' in hide_filters and 'host' not in hide_filters:
                    view['single_infos'] = ['service']
                elif 'host' in hide_filters:
                    view['single_infos'] = ['host']
                elif 'hostgroup' in hide_filters:
                    view['single_infos'] = ['hostgroup']
                elif 'servicegroup' in hide_filters:
                    view['single_infos'] = ['servicegroup']
                elif 'aggr_service' in hide_filters:
                    view['single_infos'] = ['service']
                elif 'aggr_name' in hide_filters:
                    view['single_infos'] = ['aggr']
                elif 'log_contact_name' in hide_filters:
                    view['single_infos'] = ['contact']
                elif 'event_host' in hide_filters:
                    view['single_infos'] = ['host']
                elif hide_filters == ['event_id', 'history_line']:
                    view['single_infos'] = ['history']
                elif 'event_id' in hide_filters:
                    view['single_infos'] = ['event']
                elif 'aggr_hosts' in hide_filters:
                    view['single_infos'] = ['host']
                else:
                    # For all other context types assume the view is showing multiple objects
                    # and the datasource can simply be gathered from the datasource
                    view['single_infos'] = []
            except: # Exceptions can happen for views saved with certain GIT versions
                if config.debug:
                    raise

        # Convert from show_filters, hide_filters, hard_filters and hard_filtervars
        # to context construct
        if 'context' not in view:
            view['show_filters'] = view['hide_filters'] + view['hard_filters'] + view['show_filters']

            single_keys = visuals.get_single_info_keys(view)

            # First get vars for the classic filters
            context = {}
            filtervars = dict(view['hard_filtervars'])
            all_vars = {}
            for filter_name in view['show_filters']:
                if filter_name in single_keys:
                    continue # skip conflictings vars / filters

                context.setdefault(filter_name, {})
                try:
                    f = visuals.get_filter(filter_name)
                except:
                    # The exact match filters have been removed. They where used only as
                    # link filters anyway - at least by the builtin views.
                    continue

                for var in f.htmlvars:
                    # Check whether or not the filter is supported by the datasource,
                    # then either skip or use the filter vars
                    if var in filtervars and f.info in datasource['infos']:
                        value = filtervars[var]
                        all_vars[var] = value
                        context[filter_name][var] = value

                # We changed different filters since the visuals-rewrite. This must be treated here, since
                # we need to transform views which have been created with the old filter var names.
                # Changes which have been made so far:
                changed_filter_vars = {
                    'serviceregex': { # Name of the filter
                        # old var name: new var name
                        'service': 'service_regex',
                    },
                    'hostregex': {
                        'host': 'host_regex',
                    },
                    'hostgroupnameregex': {
                        'hostgroup_name': 'hostgroup_regex',
                    },
                    'servicegroupnameregex': {
                        'servicegroup_name': 'servicegroup_regex',
                    },
                    'opthostgroup': {
                        'opthostgroup': 'opthost_group',
                        'neg_opthostgroup': 'neg_opthost_group',
                    },
                    'optservicegroup': {
                        'optservicegroup': 'optservice_group',
                        'neg_optservicegroup': 'neg_optservice_group',
                    },
                    'hostgroup': {
                        'hostgroup': 'host_group',
                        'neg_hostgroup': 'neg_host_group',
                    },
                    'servicegroup': {
                        'servicegroup': 'service_group',
                        'neg_servicegroup': 'neg_service_group',
                    },
                    'host_contactgroup': {
                        'host_contactgroup': 'host_contact_group',
                        'neg_host_contactgroup': 'neg_host_contact_group',
                    },
                    'service_contactgroup': {
                        'service_contactgroup': 'service_contact_group',
                        'neg_service_contactgroup': 'neg_service_contact_group',
                    },
                }

                if filter_name in changed_filter_vars and f.info in datasource['infos']:
                    for old_var, new_var in changed_filter_vars[filter_name].items():
                        if old_var in filtervars:
                            value = filtervars[old_var]
                            all_vars[new_var] = value
                            context[filter_name][new_var] = value

            # Now, when there are single object infos specified, add these keys to the
            # context
            for single_key in single_keys:
                if single_key in all_vars:
                    context[single_key] = all_vars[single_key]

            view['context'] = context

        # Cleanup unused attributes
        for k in [ 'hide_filters', 'hard_filters', 'show_filters', 'hard_filtervars' ]:
            try:
                del view[k]
            except KeyError:
                pass

def save_views(us):
    visuals.save('views', multisite_views)

#.
#   .--Table of views------------------------------------------------------.
#   |   _____     _     _               __         _                       |
#   |  |_   _|_ _| |__ | | ___    ___  / _| __   _(_) _____      _____     |
#   |    | |/ _` | '_ \| |/ _ \  / _ \| |_  \ \ / / |/ _ \ \ /\ / / __|    |
#   |    | | (_| | |_) | |  __/ | (_) |  _|  \ V /| |  __/\ V  V /\__ \    |
#   |    |_|\__,_|_.__/|_|\___|  \___/|_|     \_/ |_|\___| \_/\_/ |___/    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Show list of all views with buttons for editing                      |
#   '----------------------------------------------------------------------'

def page_edit_views():
    load_views()
    cols = [ (_('Datasource'), lambda v: multisite_datasources[v["datasource"]]['title']) ]
    visuals.page_list('views', _("Edit Views"), multisite_views, cols)

#.
#   .--Create View---------------------------------------------------------.
#   |        ____                _        __     ___                       |
#   |       / ___|_ __ ___  __ _| |_ ___  \ \   / (_) _____      __        |
#   |      | |   | '__/ _ \/ _` | __/ _ \  \ \ / /| |/ _ \ \ /\ / /        |
#   |      | |___| | |  __/ (_| | ||  __/   \ V / | |  __/\ V  V /         |
#   |       \____|_|  \___|\__,_|\__\___|    \_/  |_|\___| \_/\_/          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Select the view type of the new view                                 |
#   '----------------------------------------------------------------------'

# First step: Select the data source

# Create datasource selection valuespec, also for other modules
# FIXME: Sort the datasources by (assumed) common usage
def DatasourceSelection():
    # FIXME: Sort the datasources by (assumed) common usage
    datasources = []
    for ds_name, ds in multisite_datasources.items():
        datasources.append((ds_name, ds['title']))

    return DropdownChoice(
        title = _('Datasource'),
        help = _('The datasources define which type of objects should be displayed with this view.'),
        choices = datasources,
        sorted = True,
        columns = 1,
        default_value = 'services',
    )

def page_create_view(next_url = None):

    vs_ds = DatasourceSelection()

    ds = 'services' # Default selection

    html.header(_('Create View'), stylesheets=["pages"])
    html.begin_context_buttons()
    back_url = html.var("back", "")
    html.context_button(_("Back"), back_url or "edit_views.py", "back")
    html.end_context_buttons()

    if html.var('save') and html.check_transaction():
        try:
            ds = vs_ds.from_html_vars('ds')
            vs_ds.validate_value(ds, 'ds')

            if not next_url:
                next_url = html.makeuri([('datasource', ds)], filename = "create_view_infos.py")
            else:
                next_url = next_url + '&datasource=%s' % ds
            html.http_redirect(next_url)
            return

        except MKUserError, e:
            html.write("<div class=error>%s</div>\n" % e.message)
            html.add_user_error(e.varname, e.message)

    html.begin_form('create_view')
    html.hidden_field('mode', 'create')

    forms.header(_('Select Datasource'))
    forms.section(vs_ds.title())
    vs_ds.render_input('ds', ds)
    html.help(vs_ds.help())
    forms.end()

    html.button('save', _('Continue'), 'submit')

    html.hidden_fields()
    html.end_form()
    html.footer()

def page_create_view_infos():
    ds_name = html.var('datasource')
    if ds_name not in multisite_datasources:
        raise MKGeneralException(_('The given datasource is not supported'))

    visuals.page_create_visual('views', multisite_datasources[ds_name]['infos'],
        next_url = 'edit_view.py?mode=create&datasource=%s&single_infos=%%s' % ds_name)

#.
#   .--Edit View-----------------------------------------------------------.
#   |             _____    _ _ _    __     ___                             |
#   |            | ____|__| (_) |_  \ \   / (_) _____      __              |
#   |            |  _| / _` | | __|  \ \ / /| |/ _ \ \ /\ / /              |
#   |            | |__| (_| | | |_    \ V / | |  __/\ V  V /               |
#   |            |_____\__,_|_|\__|    \_/  |_|\___| \_/\_/                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

# Return list of available datasources (used to render filters)
def get_view_infos(view):
    ds_name = view.get('datasource', html.var('datasource'))
    return multisite_datasources[ds_name]['infos']

def page_edit_view():
    load_views()

    visuals.page_edit_visual('views', multisite_views,
        custom_field_handler = render_view_config,
        load_handler = transform_view_to_valuespec_value,
        create_handler = create_view_from_valuespec,
        info_handler = get_view_infos,
        try_handler = lambda view: show_view(view, False, False)
    )

def view_choices(only_with_hidden = False):
    choices = [("", "")]
    for name, view in available_views.items():
        if not only_with_hidden or view['single_infos']:
            if view.get('mobile', False):
                title = _('Mobile: ') + _u(view["title"])
            else:
                title = _u(view["title"])
            choices.append(("%s" % name, title))
    return choices

def view_editor_options():
    return [
        ('mobile',           _('Show this view in the Mobile GUI')),
        ('mustsearch',       _('Show data only on search')),
        ('force_checkboxes', _('Always show the checkboxes')),
        ('user_sortable',    _('Make view sortable by user')),
        ('play_sounds',      _('Play alarm sounds')),
    # FIXME
    #html.help(_("If enabled and the view shows at least one host or service problem "
    #            "the a sound will be played by the browser. Please consult the %s for details.")
    #            % docu_link("multisite_sounds", _("documentation")))
    ]

def view_editor_specs(ds_name, general_properties=True):
    load_views() # make sure that available_views is present
    specs = []
    if general_properties:
        specs.append(
            ('view', Dictionary(
                title = _('View Properties'),
                render = 'form',
                optional_keys = None,
                elements = [
                    ('datasource', FixedValue(ds_name,
                        title = _('Datasource'),
                        totext = multisite_datasources[ds_name]['title'],
                        help = _('The datasource of a view cannot be changed.'),
                    )),
                    ('options', ListChoice(
                        title = _('Options'),
                        choices = view_editor_options(),
                        default_value = ['user_sortable'],
                    )),
                    ('browser_reload', Integer(
                        title = _('Automatic page reload'),
                        unit = _('seconds'),
                        minvalue = 0,
                        help = _('Leave this empty or at 0 for no automatic reload.'),
                    )),
                    ('layout', DropdownChoice(
                        title = _('Basic Layout'),
                        choices = [ (k, v["title"]) for k,v in multisite_layouts.items() if not v.get("hide")],
                        default_value = 'table',
                        sorted = True,
                    )),
                    ('num_columns', Integer(
                        title = _('Number of Columns'),
                        default_value = 1,
                        minvalue = 1,
                        maxvalue = 50,
                    )),
                    ('column_headers', DropdownChoice(
                        title = _('Column Headers'),
                        choices = [
                            ("off",      _("off")),
                            ("pergroup", _("once per group")),
                            ("repeat",   _("repeat every 20'th row")),
                        ],
                        default_value = 'pergroup',
                    )),
                ],
            ))
        )

    allowed = allowed_for_datasource(multisite_sorters, ds_name)

    def column_spec(ident, title, ds_name):
        allowed = allowed_for_datasource(multisite_painters, ds_name)
        collist = collist_of_collection(allowed)

        allow_empty = True
        empty_text = None
        if ident == 'columns':
            allow_empty = False
            empty_text = _("Please add at least one column to your view.")

        vs_column = Tuple(
            title = _('Column'),
            elements = [
                DropdownChoice(
                    title = _('Column'),
                    choices = collist,
                    sorted = True,
                    no_preselect = True,
                ),
                DropdownChoice(
                    title = _('Link'),
                    choices = view_choices,
                    sorted = True,
                ),
                DropdownChoice(
                    title = _('Tooltip'),
                    choices = [(None, "")] + collist,
                ),
            ]
        )

        joined = allowed_for_joined_datasource(multisite_painters, ds_name)
        if ident == 'columns' and joined:
            joined_cols = collist_of_collection(joined, collist)

            vs_column = Alternative(
                elements = [
                    vs_column,

                    Tuple(
                        title = _('Joined column'),
                        elements = [
                            DropdownChoice(
                                title = _('Column'),
                                choices = joined_cols,
                                sorted = True,
                                no_preselect = True,
                            ),
                            TextUnicode(
                                title = _('of Service'),
                                allow_empty = False,
                            ),
                            DropdownChoice(
                                title = _('Link'),
                                choices = view_choices,
                                sorted = True,
                            ),
                            DropdownChoice(
                                title = _('Tooltip'),
                                choices = [(None, "")] + joined_cols,
                            ),
                            TextUnicode(
                                title = _('Title'),
                            ),
                        ],
                    ),
                ],
                style = 'dropdown',
                match = lambda x: x != None and len(x) == 5 and 1 or 0,
            )

        return (ident, Dictionary(
            title = title,
            render = 'form',
            optional_keys = None,
            elements = [
                (ident, ListOf(vs_column,
                    title = title,
                    add_label = _('Add column'),
                    allow_empty = allow_empty,
                    empty_text = empty_text,
                )),
            ],
        ))

    specs.append(column_spec('columns', _('Columns'), ds_name))

    specs.append(
        ('sorting', Dictionary(
            title = _('Sorting'),
            render = 'form',
            optional_keys = None,
            elements = [
                ('sorters', ListOf(
                    Tuple(
                        elements = [
                            DropdownChoice(
                                title = _('Column'),
                                choices = [ (name, p["title"]) for name, p in allowed.items() ],
                                sorted = True,
                                no_preselect = True,
                            ),
                            DropdownChoice(
                                title = _('Order'),
                                choices = [(False, _("Ascending")),
                                           (True, _("Descending"))],
                            ),
                        ],
                        orientation = 'horizontal',
                    ),
                    title = _('Sorting'),
                    add_label = _('Add column'),
                )),
            ],
        )),
    )

    specs.append(column_spec('grouping', _('Grouping'), ds_name))

    return specs

def render_view_config(view, general_properties=True):
    ds_name = view.get("datasource", html.var("datasource"))
    if not ds_name:
        raise MKInternalError(_("No datasource defined."))
    if ds_name not in multisite_datasources:
        raise MKInternalError(_('The given datasource is not supported.'))

    view['datasource'] = ds_name

    for ident, vs in view_editor_specs(ds_name, general_properties):
        vs.render_input(ident, view.get(ident))

# Is used to change the view structure to be compatible to
# the valuespec This needs to perform the inverted steps of the
# transform_valuespec_value_to_view() function. FIXME: One day we should
# rewrite this to make no transform needed anymore
def transform_view_to_valuespec_value(view):
    view["view"] = {} # Several global variables are put into a sub-dict
    # Only copy our known keys. Reporting element, etc. might have their own keys as well
    for key in [ "datasource", "browser_reload", "layout", "num_columns", "column_headers" ]:
        if key in view:
            view["view"][key] = view[key]

    view["view"]['options'] = []
    for key, title in view_editor_options():
        if view.get(key):
            view['view']['options'].append(key)

    view['visibility'] = []
    for key in [ 'hidden', 'hidebutton', 'public' ]:
        if view.get(key):
            view['visibility'].append(key)

    view['grouping'] = { "grouping" : view.get('group_painters', []) }
    view['sorting']  = { "sorters" : view.get('sorters', {}) }

    columns = []
    view['columns'] = { "columns" : columns }
    for entry in view.get('painters', []):
        if len(entry) == 5:
            pname, viewname, tooltip, join_index, col_title = entry
            columns.append((pname, join_index, viewname, tooltip, col_title))

        elif len(entry) == 4:
            pname, viewname, tooltip, join_index = entry
            columns.append((pname, join_index, viewname, tooltip, ''))

        elif len(entry) == 3:
            pname, viewname, tooltip = entry
            columns.append((pname, viewname, tooltip))

        else:
            pname, viewname = entry
            columns.append((pname, viewname, ''))


def transform_valuespec_value_to_view(view):
    for ident, attrs in view.items():
        # Transform some valuespec specific options to legacy view
        # format. We do not want to change the view data structure
        # at the moment.
        if ident == 'view':
            if "options" in attrs:
                for option in attrs['options']:
                    view[option] = True
                del attrs['options']
            view.update(attrs)
            del view["view"]

        elif ident == 'sorting':
            view.update(attrs)
            del view["sorting"]

        elif ident == 'grouping':
            view['group_painters'] = attrs['grouping']
            del view["grouping"]

        elif ident == 'columns':
            painters = []
            for column in attrs['columns']:
                if len(column) == 5:
                    pname, join_index, viewname, tooltip, col_title = column
                else:
                    pname, viewname, tooltip = column
                    join_index, col_title = None, None

                viewname = viewname and viewname or None

                if join_index and col_title:
                    painters.append((pname, viewname, tooltip, join_index, col_title))
                elif join_index:
                    painters.append((pname, viewname, tooltip, join_index))
                else:
                    painters.append((pname, viewname, tooltip))
            view['painters'] = painters
            del view["columns"]


# Extract properties of view from HTML variables and construct
# view object, to be used for saving or displaying
#
# old_view is the old view dict which might be loaded from storage.
# view is the new dict object to be updated.
def create_view_from_valuespec(old_view, view):
    ds_name = old_view.get('datasource', html.var('datasource'))
    view['datasource'] = ds_name
    datasource = multisite_datasources[ds_name]
    vs_value = {}
    for ident, vs in view_editor_specs(ds_name):
        attrs = vs.from_html_vars(ident)
        vs.validate_value(attrs, ident)
        vs_value[ident] = attrs

    transform_valuespec_value_to_view(vs_value)
    view.update(vs_value)
    return view

#.
#   .--Display View--------------------------------------------------------.
#   |      ____  _           _              __     ___                     |
#   |     |  _ \(_)___ _ __ | | __ _ _   _  \ \   / (_) _____      __      |
#   |     | | | | / __| '_ \| |/ _` | | | |  \ \ / /| |/ _ \ \ /\ / /      |
#   |     | |_| | \__ \ |_) | | (_| | |_| |   \ V / | |  __/\ V  V /       |
#   |     |____/|_|___/ .__/|_|\__,_|\__, |    \_/  |_|\___| \_/\_/        |
#   |                 |_|            |___/                                 |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def show_filter(f):
    if not f.visible():
        html.write('<div style="display:none">')
        f.display()
        html.write('</div>')
    else:
        html.write('<div class="floatfilter %s">' % (f.double_height() and "double" or "single"))
        html.write('<div class=legend>%s</div>' % f.title)
        html.write('<div class=content>')
        f.display()
        html.write("</div>")
        html.write("</div>")


def show_filter_form(is_open, filters):
    # Table muss einen anderen Namen, als das Formular
    html.write('<div class="view_form" id="filters" %s>'
            % (not is_open and 'style="display: none"' or '') )

    html.begin_form("filter")
    html.write("<table border=0 cellspacing=0 cellpadding=0 class=filterform><tr><td>")

    # sort filters according to title
    s = [(f.sort_index, f.title, f) for f in filters if f.available()]
    s.sort()
    col = 0

    # First show filters with double height (due to better floating
    # layout)
    for sort_index, title, f in s:
        if f.double_height():
            show_filter(f)

    # Now single height filters
    for sort_index, title, f in s:
        if not f.double_height():
            show_filter(f)

    html.write("</td></tr><tr><td>")
    html.button("search", _("Search"), "submit")
    html.write("</td></tr></table>")

    html.hidden_fields()
    html.end_form()

    html.write("</div>")


def show_painter_options(painter_options):
    html.write('<div class="view_form" id="painteroptions" style="display: none">')
    html.begin_form("painteroptions")
    forms.header(_("Display Options"))
    for on in painter_options:
        vs = multisite_painter_options[on]['valuespec']
        forms.section(vs.title())
        vs.render_input('po_' + on, get_painter_option(on))
    forms.end()

    html.button("painter_options", _("Submit"), "submit")

    html.hidden_fields()
    html.end_form()
    html.write('</div>')


def page_view():
    bi.reset_cache_status() # needed for status icon

    load_views()
    view_name = html.var("view_name")
    if view_name == None:
        raise MKGeneralException(_("Missing the variable view_name in the URL."))
    view = available_views.get(view_name)
    if not view:
        raise MKGeneralException(_("No view defined with the name '%s'.") % html.attrencode(view_name))

    html.set_page_context(visuals.get_singlecontext_html_vars(view))

    show_view(view, True, True, True)


# Get a list of columns we need to fetch in order to
# render a given list of painters. If join_columns is True,
# then we only return the list needed by "Join" columns, i.e.
# columns that need to fetch information from another table
# (e.g. from the services table while we are in a hosts view)
# If join_columns is False, we only return the "normal" columns.
def get_needed_columns(view, painters):
    # Make sure that the information about the available views is present. If
    # called via the reporting, than this might not be the case
    try:
        available_views
    except:
        load_views()

    columns = []
    for entry in painters:
        painter = entry[0]
        linkview_name = entry[1]
        columns += painter["columns"]
        if linkview_name:
            linkview = available_views.get(linkview_name)
            if linkview:
                for filt in [ visuals.get_filter(fn) for fn in visuals.get_single_info_keys(linkview) ]:
                    columns += filt.link_columns

                # The site attribute is no column. Filter it out here
                #if 'site' in columns:
                #    columns.remove('site')

        if len(entry) > 2 and entry[2]:
            tt = entry[2]
            columns += multisite_painters[tt]["columns"]
    return columns


# Display options are flags that control which elements of a
# view should be displayed (buttons, sorting, etc.). They can be
# specified via the URL variable display_options. The function
# extracts this variable, applies defaults and generates
# three versions of the display options:
# Return value -> display options to actually use
# html.display_options -> display options to use in for URLs to other views
# html.title_display_options -> display options for title sorter links
def prepare_display_options():
    # Display options (upper-case: show, lower-case: don't show)
    # H  The HTML header and body-tag (containing the tags <HTML> and <BODY>)
    # T  The title line showing the header and the logged in user
    # B  The blue context buttons that link to other views
    # F  The button for using filters
    # C  The button for using commands and all icons for commands (e.g. the reschedule icon)
    # O  The view options number of columns and refresh
    # D  The Display button, which contains column specific formatting settings
    # E  The button for editing the view
    # Z  The footer line, where refresh: 30s is being displayed
    # R  The auto-refreshing in general (browser reload)
    # S  The playing of alarm sounds (on critical and warning services)
    # U  Load persisted user row selections
    # I  All hyperlinks pointing to other views
    # X  All other hyperlinks (pointing to external applications like PNP, WATO or others)
    # M  If this option is not set, then all hyperlinks are targeted to the HTML frame
    #    with the name main. This is useful when using views as elements in the dashboard.
    # L  The column title links in multisite views
    # W  The limit and livestatus error message in views
    all_display_options = "HTBFCEOZRSUIXDMLW"

    # Parse display options and
    if html.output_format == "html":
        display_options = html.var("display_options", "")
    else:
        display_options = all_display_options.lower()

    # If all display_options are upper case assume all not given values default
    # to lower-case. Vice versa when all display_options are lower case.
    # When the display_options are mixed case assume all unset options to be enabled
    def apply_display_option_defaults(opts):
        do_defaults = opts.isupper() and all_display_options.lower() or all_display_options
        for c in do_defaults:
            if c.lower() not in opts.lower():
                opts += c
        return opts

    display_options = apply_display_option_defaults(display_options)
    # Add the display_options to the html object for later linking etc.
    html.display_options = display_options

    # This is needed for letting only the data table reload. The problem is that
    # the data table is re-fetched via javascript call using special display_options
    # but these special display_options must not be used in links etc. So we use
    # a special var _display_options for defining the display_options for rendering
    # the data table to be reloaded. The contents of "display_options" are used for
    # linking to other views.
    if html.has_var('_display_options'):
        display_options = html.var("_display_options", "")
        display_options = apply_display_option_defaults(display_options)
        html.display_options = display_options

    # But there is one special case: The sorter links! These links need to know
    # about the provided display_option parameter. The links could use
    # "html.display_options" but this contains the implicit options which should
    # not be added to the URLs. So the real parameters need to be preserved for
    # this case. It is stored in the var "html.display_options"
    if html.var('display_options'):
        html.title_display_options = html.var("display_options")

    # If display option 'M' is set, then all links are targetet to the 'main'
    # frame. Also the display options are removed since the view in the main
    # frame should be displayed in standard mode.
    if 'M' not in display_options:
        html.set_link_target("main")
        html.del_var("display_options")

    # Below we have the following display_options vars:
    # html.display_options        - Use this when rendering the current view
    # html.var("display_options") - Use this for linking to other views
    return display_options


# Display view with real data. This is *the* function everying
# is about.
def show_view(view, show_heading = False, show_buttons = True,
              show_footer = True, render_function = None, only_count=False,
              all_filters_active=False, limit=None):
    if html.var("mode") == "availability" and html.has_var("av_aggr_name") and html.var("timeline"):
        bi.page_timeline()
        return

    display_options = prepare_display_options()

    # User can override the layout settings via HTML variables (buttons)
    # which are safed persistently. This is known as "view options". Note: a few
    # can be anonymous (e.g. when embedded into a report). In that case there
    # are no display options.
    if "name" in view:
        vo = view_options(view["name"])
    else:
        vo = {}
    num_columns     = vo.get("num_columns",     view.get("num_columns",    1))
    browser_reload  = vo.get("refresh",         view.get("browser_reload", None))

    force_checkboxes = view.get("force_checkboxes", False)
    show_checkboxes = force_checkboxes or html.var('show_checkboxes', '0') == '1'

    # Get the datasource (i.e. the logical table)
    datasource = multisite_datasources[view["datasource"]]
    tablename = datasource["table"]

    # Filters to use in the view
    # In case of single object views, the needed filters are fixed, but not always present
    # in context. In this case, take them from the context type definition.
    use_filters = visuals.filters_of_visual(view, datasource['infos'], all_filters_active)

    # Not all filters are really shown later in show_filter_form(), because filters which
    # have a hardcoded value are not changeable by the user
    show_filters = visuals.visible_filters_of_visual(view, use_filters)

    # Now populate the HTML vars with context vars from the view definition. Hard
    # coded default values are treated differently:
    #
    # a) single context vars of the view are enforced
    # b) multi context vars can be overwritten by existing HTML vars
    visuals.add_context_to_uri_vars(view, datasource["infos"], only_count)

    # Check that all needed information for configured single contexts are available
    visuals.verify_single_contexts('views', view)

    # Af any painter, sorter or filter needs the information about the host's
    # inventory, then we load it and attach it as column "host_inventory"
    need_inventory_data = False

    # Prepare Filter headers for Livestatus
    filterheaders = ""
    only_sites = None
    all_active_filters = [ f for f in use_filters if f.available() ]
    for filt in all_active_filters:
        header = filt.filter(tablename)
        if header.startswith("Sites:"):
            only_sites = header.strip().split(" ")[1:]
        else:
            filterheaders += header
        if filt.need_inventory():
            need_inventory_data = True

    # Prepare limit:
    # We had a problem with stats queries on the logtable where
    # the limit was not applied on the resulting rows but on the
    # lines of the log processed. This resulted in wrong stats.
    # For these datasources we ignore the query limits.
    if limit == None: # Otherwise: specified as argument
        if not datasource.get('ignore_limit', False):
            limit = get_limit()

    # Fork to availability view. We just need the filter headers, since we do not query the normal
    # hosts and service table, but "statehist". This is *not* true for BI availability, though (see later)
    if html.var("mode") == "availability" and (
          "aggr" not in datasource["infos"] or html.var("timeline_aggr")):
        return render_availability(view, datasource, filterheaders, display_options, only_sites, limit)

    query = filterheaders + view.get("add_headers", "")

    # Sorting - use view sorters and URL supplied sorters
    if not only_count:
        sorter_list = html.has_var('sort') and parse_url_sorters(html.var('sort')) or view["sorters"]
        sorters = [ (multisite_sorters[s[0]],) + s[1:] for s in sorter_list ]
    else:
        sorters = []

    # Prepare grouping information
    group_painters = [ (multisite_painters[e[0]],) + e[1:] for e in view["group_painters"] ]

    # Prepare columns to paint
    painters = [ (multisite_painters[e[0]],) + e[1:] for e in view["painters"] ]

    # Now compute the list of all columns we need to query via Livestatus.
    # Those are: (1) columns used by the sorters in use, (2) columns use by
    # column- and group-painters in use and - note - (3) columns used to
    # satisfy external references (filters) of views we link to. The last bit
    # is the trickiest. Also compute this list of view options use by the
    # painters

    all_painters = group_painters + painters
    join_painters = [ p for p in all_painters if len(p) >= 4 ]
    master_painters = [ p for p in all_painters if len(p) < 4 ]
    columns      = get_needed_columns(view, master_painters)
    join_columns = get_needed_columns(view, join_painters)

    # Columns needed for sorters
    for s in sorters:
        if len(s) == 2:
            columns += s[0]["columns"]
        else:
            join_columns += s[0]["columns"]
        if s[0].get("load_inv"):
            need_inventory_data = True

    # Add key columns, needed for executing commands
    columns += datasource["keys"]

    # Add idkey columns, needed for identifying the row
    columns += datasource["idkeys"]

    # BI availability needs aggr_tree
    if html.var("mode") == "availability" and "aggr" in datasource["infos"]:
        columns = [ "aggr_tree", "aggr_name", "aggr_group" ]

    # Make column list unique and remove (implicit) site column
    colset = set(columns)
    if "site" in colset:
        colset.remove("site")
    columns = list(colset)

    # Get list of painter options we need to display (such as PNP time range
    # or the format being used for timestamp display)
    painter_options = []
    for entry in all_painters:
        p = entry[0]
        painter_options += p.get("options", [])
        if p.get("load_inv"):
            need_inventory_data = True

    painter_options = list(set(painter_options))
    painter_options.sort()

    # Fetch data. Some views show data only after pressing [Search]
    if (only_count or (not view.get("mustsearch")) or html.var("filled_in") in ["filter", 'actions', 'confirm']):
        # names for additional columns (through Stats: headers)
        add_columns = datasource.get("add_columns", [])

        # tablename may be a function instead of a livestatus tablename
        # In that case that function is used to compute the result.

        if type(tablename) == type(lambda x:None):
            rows = tablename(columns, query, only_sites, limit, all_active_filters)
        else:
            rows = query_data(datasource, columns, add_columns, query, only_sites, limit)

        # Now add join information, if there are join columns
        if len(join_painters) > 0:
            do_table_join(datasource, rows, filterheaders, join_painters, join_columns, only_sites)

        # Add inventory data if one of the painters needs it
        if need_inventory_data:
            for row in rows:
                row["host_inventory"] = inventory.host(row["host_name"])

        sort_data(rows, sorters)
    else:
        rows = []

    # Apply non-Livestatus filters
    for filter in all_active_filters:
        rows = filter.filter_table(rows)

    if html.var("mode") == "availability":
        render_bi_availability(view_title(view), rows)
        return

    # TODO: Use livestatus Stats: instead of fetching rows!
    if only_count:
        for fname, filter_vars in view["context"].items():
            for varname, value in filter_vars.items():
                html.del_var(varname)
        return len(rows)

    # Set browser reload
    if browser_reload and 'R' in display_options and not only_count:
        html.set_browser_reload(browser_reload)

    # The layout of the view: it can be overridden by several specifying
    # an output format (like json or python). Note: the layout is not
    # always needed. In case of an embedded view in the reporting this
    # field is simply missing, because the rendering is done by the
    # report itself.
    if html.output_format == "html":
        if "layout" in view:
            layout = multisite_layouts[view["layout"]]
        else:
            layout = None
    else:
        layout = multisite_layouts.get(html.output_format)
        if not layout:
            layout = multisite_layouts["json"]

    # Until now no single byte of HTML code has been output.
    # Now let's render the view. The render_function will be
    # replaced by the mobile interface for an own version.
    if not render_function:
        render_function = render_view

    render_function(view, rows, datasource, group_painters, painters,
                display_options, painter_options, show_heading, show_buttons,
                show_checkboxes, layout, num_columns, show_filters, show_footer,
                browser_reload)


# Output HTML code of a view. If you add or remove paramters here,
# then please also do this in htdocs/mobile.py!
def render_view(view, rows, datasource, group_painters, painters,
                display_options, painter_options, show_heading, show_buttons,
                show_checkboxes, layout, num_columns, show_filters, show_footer,
                browser_reload):

    if html.transaction_valid() and html.do_actions():
        html.set_browser_reload(0)

    # Show heading (change between "preview" mode and full page mode)
    if show_heading:
        # Show/Hide the header with page title, MK logo, etc.
        if 'H' in display_options:
            # FIXME: view/layout/module related stylesheets/javascripts e.g. in case of BI?
            html.body_start(view_title(view), stylesheets=["pages","views","status","bi"], javascripts=['bi'])
        if 'T' in display_options:
            html.top_heading(view_title(view))

    has_done_actions = False
    row_count = len(rows)

    # This is a general flag which makes the command form render when the current
    # view might be able to handle commands. When no commands are possible due missing
    # permissions or datasources without commands, the form is not rendered
    command_form = should_show_command_form(display_options, datasource)

    if command_form:
        weblib.init_selection()

    # Is the layout able to display checkboxes?
    can_display_checkboxes = layout.get('checkboxes', False)

    if show_buttons:
        show_context_links(view, show_filters, display_options,
                       painter_options,
                       # Take into account: permissions, display_options
                       row_count > 0 and command_form,
                       # Take into account: layout capabilities
                       can_display_checkboxes and not view.get("force_checkboxes"), show_checkboxes,
                       # Show link to availability. This exists only for plain hosts
                       # and services table. The grouping tables have columns that statehist
                       # is missing. That way some of the filters might fail.
                       datasource["table"] in [ "hosts", "services", ] or "aggr" in datasource["infos"])

    # User errors in filters
    html.show_user_errors()

    # Filter form
    filter_isopen = html.var("filled_in") != "filter" and view.get("mustsearch")
    if 'F' in display_options and len(show_filters) > 0:
        show_filter_form(filter_isopen, show_filters)

    # Actions
    if command_form:
        # If we are currently within an action (confirming or executing), then
        # we display only the selected rows (if checkbox mode is active)
        if show_checkboxes and html.do_actions():
            rows = filter_selected_rows(view, rows, weblib.get_rowselection('view-' + view['name']))

        if html.do_actions() and html.transaction_valid(): # submit button pressed, no reload
            try:
                # Create URI with all actions variables removed
                backurl = html.makeuri([], delvars=['filled_in', 'actions'])
                has_done_actions = do_actions(view, datasource["infos"][0], rows, backurl)
            except MKUserError, e:
                html.show_error(e.message)
                html.add_user_error(e.varname, e.message)
                if 'C' in display_options:
                    show_command_form(True, datasource)

        elif 'C' in display_options: # (*not* display open, if checkboxes are currently shown)
            show_command_form(False, datasource)

    # Also execute commands in cases without command form (needed for Python-
    # web service e.g. for NagStaMon)
    elif row_count > 0 and config.may("general.act") \
         and html.do_actions() and html.transaction_valid():
        try:
            do_actions(view, datasource["infos"][0], rows, '')
        except:
            pass # currently no feed back on webservice

    if 'O' in display_options and len(painter_options) > 0 and config.may("general.painter_options"):
        show_painter_options(painter_options)

    # The refreshing content container
    if 'R' in display_options:
        html.write("<div id=data_container>\n")

    if not has_done_actions:
        # Limit exceeded? Show warning
        if 'W' in display_options:
            html.check_limit(rows, get_limit())
        layout["render"](rows, view, group_painters, painters, num_columns,
                         show_checkboxes and not html.do_actions())
        headinfo = "%d %s" % (row_count, row_count == 1 and _("row") or _("rows"))
        if show_checkboxes:
            selected = filter_selected_rows(view, rows, weblib.get_rowselection('view-' + view['name']))
            headinfo = "%d/%s" % (len(selected), headinfo)

        if html.output_format == "html":
            html.javascript("update_headinfo('%s');" % headinfo)

            # The number of rows might have changed to enable/disable actions and checkboxes
            if show_buttons:
                update_context_links(
                    # don't take display_options into account here ('c' is set during reload)
                    row_count > 0 and should_show_command_form('C', datasource),
                    # and not html.do_actions(),
                    can_display_checkboxes
                )

        # Play alarm sounds, if critical events have been displayed
        if 'S' in display_options and view.get("play_sounds"):
            play_alarm_sounds()
    else:
        # Always hide action related context links in this situation
        update_context_links(False, False)

    # In multi site setups error messages of single sites do not block the
    # output and raise now exception. We simply print error messages here.
    # In case of the web service we show errors only on single site installations.
    if config.show_livestatus_errors \
       and 'W' in display_options \
       and (html.output_format == "html" or not config.is_multisite()):
        for sitename, info in html.live.deadsites.items():
            html.show_error("<b>%s - %s</b><br>%s" % (info["site"]["alias"], _('Livestatus error'), info["exception"]))

    # FIXME: Sauberer wäre noch die Status Icons hier mit aufzunehmen
    if 'R' in display_options:
        html.write("</div>\n")

    if show_footer:
        pid = os.getpid()
        if html.live.successfully_persisted():
            html.add_status_icon("persist", _("Reused persistent livestatus connection from earlier request (PID %d)") % pid)
        if bi.reused_compilation():
            html.add_status_icon("aggrcomp", _("Reused cached compiled BI aggregations (PID %d)") % pid)

        if config.may('wato.users'):
            try:
                msg = file(defaults.var_dir + '/web/ldap_sync_fail.mk').read()
                html.add_status_icon("ldap", _('Last LDAP sync failed! %s') % html.attrencode(msg))
            except IOError:
                pass

        html.bottom_focuscode()
        if 'Z' in display_options:
            html.bottom_footer()

        if 'H' in display_options:
            html.body_end()

# We should rename this into "painter_options". Also the saved file.
def view_options(viewname):
    # Options are stored per view. Get all options for all views
    vo = config.load_user_file("viewoptions", {})

    # Now get options for the view in question
    v = vo.get(viewname, {})
    must_save = False

    # Now override the loaded options with new option settings that are
    # provided by the URL. Our problem: we do not know the URL variables
    # that a valuespec expects. But we know the common prefix of all
    # variables for each option.
    if config.may("general.painter_options"):
        for option_name, opt in multisite_painter_options.items():
            have_old_value = option_name in v
            if have_old_value:
                old_value = v.get(option_name)

            # Are there settings for this painter option present?
            var_prefix = 'po_' + option_name
            if html.has_var_prefix(var_prefix):

                # Get new value for the option from the value spec
                vs = opt['valuespec']
                value = vs.from_html_vars(var_prefix)

                v[option_name] = value
                opt['value'] = value # make globally present for painters

                if not have_old_value or v[option_name] != old_value:
                    must_save = True

            elif have_old_value:
                opt['value'] = old_value # make globally present for painters
            elif 'value' in opt:
                del opt['value']

    # If the user has no permission for changing painter options
    # (or has *lost* his permission) then we need to remove all
    # of the options. But we do not save.
    else:
        for on, opt in multisite_painter_options.items():
            if on in v:
                del v[on]
                must_save = True
            if 'value' in opt:
                del opt['value']

    if must_save:
        vo[viewname] = v
        config.save_user_file("viewoptions", vo)

    return v


def do_table_join(master_ds, master_rows, master_filters, join_painters, join_columns, only_sites):
    join_table, join_master_column = master_ds["join"]
    slave_ds = multisite_datasources[join_table]
    join_slave_column = slave_ds["joinkey"]

    # Create additional filters
    join_filter = ""
    for entry in join_painters:
        paintfunc, linkview, title, join_key = entry[:4]
        join_filter += "Filter: %s = %s\n" % (join_slave_column, join_key )
    join_filter += "Or: %d\n" % len(join_painters)
    query = master_filters + join_filter
    rows = query_data(slave_ds, [join_master_column, join_slave_column] + join_columns, [], query, only_sites, None)
    per_master_entry = {}
    current_key = None
    current_entry = None
    for row in rows:
        master_key = (row["site"], row[join_master_column])
        if master_key != current_key:
            current_key = master_key
            current_entry = {}
            per_master_entry[current_key] = current_entry
        current_entry[row[join_slave_column]] = row

    # Add this information into master table in artificial column "JOIN"
    for row in master_rows:
        key = (row["site"], row[join_master_column])
        joininfo = per_master_entry.get(key, {})
        row["JOIN"] = joininfo


def play_alarm_sounds():
    if not config.enable_sounds:
        return

    url = config.sound_url
    if not url.endswith("/"):
        url += "/"
    for event, wav in config.sounds:
        if not event or html.has_event(event):
            html.play_sound(url + wav)
            break # only one sound at one time

# How many data rows may the user query?
def get_limit():
    limitvar = html.var("limit", "soft")
    if limitvar == "hard" and config.may("general.ignore_soft_limit"):
        return config.hard_query_limit
    elif limitvar == "none" and config.may("general.ignore_hard_limit"):
        return None
    else:
        return config.soft_query_limit

def view_title(view):
    return visuals.visual_title('view', view)

def view_optiondial(view, option, choices, help):
    vo = view_options(view["name"])
    # Darn: The option "refresh" has the name "browser_reload" in the
    # view definition
    if option == "refresh":
        von = "browser_reload"
    else:
        von = option
    value = vo.get(option, view.get(von, choices[0][0]))
    title = dict(choices).get(value, value)
    html.begin_context_buttons() # just to be sure
    # Remove unicode strings
    choices = [ [c[0], str(c[1])] for c in choices ]
    html.write('<div title="%s" id="optiondial_%s" class="optiondial %s val_%s" '
       'onclick="view_dial_option(this, \'%s\', \'%s\', %r);"><div>%s</div></div>' % (
        help, option, option, value, view["name"], option, choices, title))
    html.final_javascript("init_optiondial('optiondial_%s');" % option)

def view_optiondial_off(option):
    html.write('<div class="optiondial off %s"></div>' % option)

def toggler(id, icon, help, onclick, value, hidden = False):
    html.begin_context_buttons() # just to be sure
    hide = hidden and ' style="display:none"' or ''
    html.write('<div id="%s_on" title="%s" class="togglebutton %s %s" '
       'onclick="%s"%s></div>' % (
        id, help, icon, value and "down" or "up", onclick, hide))


# Will be called when the user presses the upper button, in order
# to persist the new setting - and to make it active before the
# browser reload of the DIV containing the actual status data is done.
def ajax_set_viewoption():
    view_name = html.var("view_name")
    option = html.var("option")
    value = html.var("value")
    value = { 'true' : True, 'false' : False }.get(value, value)
    if type(value) == str and value[0].isdigit():
        try:
            value = int(value)
        except:
            pass

    vo = config.load_user_file("viewoptions", {})
    vo.setdefault(view_name, {})
    vo[view_name][option] = value
    config.save_user_file("viewoptions", vo)

def togglebutton_off(id, icon, hidden = False):
    html.begin_context_buttons()
    hide = hidden and ' style="display:none"' or ''
    html.write('<div id="%s_off" class="togglebutton off %s"%s></div>' % (id, icon, hide))

def togglebutton(id, isopen, icon, help, hidden = False):
    html.begin_context_buttons()
    if isopen:
        cssclass = "down"
    else:
        cssclass = "up"
    hide = hidden and ' style="display:none"' or ''
    html.write('<div id="%s_on" class="togglebutton %s %s" title="%s" '
               'onclick="view_toggle_form(this, \'%s\');"%s></div>' % (id, icon, cssclass, help, id, hide))

def show_context_links(thisview, show_filters, display_options,
                       painter_options, enable_commands, enable_checkboxes, show_checkboxes,
                       show_availability):
    # html.begin_context_buttons() called automatically by html.context_button()
    # That way if no button is painted we avoid the empty container
    if 'B' in display_options:
        execute_hooks('buttons-begin')

    filter_isopen = html.var("filled_in") != "filter" and thisview.get("mustsearch")
    if 'F' in display_options:
        if len(show_filters) > 0:
            if html.var("filled_in") == "filter":
                icon = "filters_set"
                help = _("The current data is being filtered")
            else:
                icon = "filters"
                help = _("Set a filter for refining the shown data")
            togglebutton("filters", filter_isopen, icon, help)
        else:
            togglebutton_off("filters", "filters")

    if 'D' in display_options:
        if len(painter_options) > 0 and config.may("general.painter_options"):
            togglebutton("painteroptions", False, "painteroptions", _("Modify display options"))
        else:
            togglebutton_off("painteroptions", "painteroptions")

    if 'C' in display_options:
        togglebutton("commands", False, "commands", _("Execute commands on hosts, services and other objects"),
                     hidden = not enable_commands)
        togglebutton_off("commands", "commands", hidden = enable_commands)

        selection_enabled = enable_commands and enable_checkboxes
        if not thisview.get("force_checkboxes"):
            toggler("checkbox", "checkbox", _("Enable/Disable checkboxes for selecting rows for commands"),
                    "location.href='%s';" % html.makeuri([('show_checkboxes', show_checkboxes and '0' or '1')]),
                    show_checkboxes, hidden = True) # not selection_enabled)
        togglebutton_off("checkbox", "checkbox", hidden = selection_enabled)
        html.javascript('g_selection_enabled = %s;' % (selection_enabled and 'true' or 'false'))

    if 'O' in display_options:
        if config.may("general.view_option_columns"):
            choices = [ [x, "%s" % x] for x in config.view_option_columns ]
            view_optiondial(thisview, "num_columns", choices, _("Change the number of display columns"))
        else:
            view_optiondial_off("num_columns")

        if 'R' in display_options and config.may("general.view_option_refresh"):
            choices = [ [x, {0:_("off")}.get(x,str(x) + "s") + (x and "" or "")] for x in config.view_option_refreshes ]
            view_optiondial(thisview, "refresh", choices, _("Change the refresh rate"))
        else:
            view_optiondial_off("refresh")


    if 'B' in display_options:
        # WATO: If we have a host context, then show button to WATO, if permissions allow this
        if html.has_var("host") \
           and config.wato_enabled \
           and config.may("wato.use") \
           and (config.may("wato.hosts") or config.may("wato.seeall")) \
           and wato.using_wato_hosts():
            host = html.var("host")
            if host:
                url = wato.link_to_host(host)
            else:
                url = wato.link_to_path(html.var("wato_folder", ""))
            html.context_button(_("WATO"), url, "wato", id="wato",
                bestof = config.context_buttons_to_show)

        # Button for creating an instant report (if reporting is available)
        if config.reporting_available():
            html.context_button(_("Export as PDF"), html.makeuri([], filename="report_instant.py"), "report")

        # Buttons to other views, dashboards, etc.
        links = visuals.collect_context_links(thisview)
        for linktitle, uri, icon, buttonid in links:
            html.context_button(linktitle, url=uri, icon=icon, id=buttonid, bestof=config.context_buttons_to_show)

    # Customize/Edit view button
    if 'E' in display_options and config.may("general.edit_views"):
        backurl = html.urlencode(html.makeuri([]))
        if thisview["owner"] == config.user_id:
            url = "edit_view.py?load_name=%s&back=%s" % (thisview["name"], backurl)
        else:
            url = "edit_view.py?load_user=%s&load_name=%s&back=%s" % \
                  (thisview["owner"], thisview["name"], backurl)
        html.context_button(_("Edit View"), url, "edit", id="edit", bestof=config.context_buttons_to_show)

    if 'E' in display_options and show_availability:
        html.context_button(_("Availability"), html.makeuri([("mode", "availability")]), "availability")

    if 'B' in display_options:
        execute_hooks('buttons-end')

    html.end_context_buttons()

def update_context_links(enable_command_toggle, enable_checkbox_toggle):
    html.javascript("update_togglebutton('commands', %d);" % (enable_command_toggle and 1 or 0))
    html.javascript("update_togglebutton('checkbox', %d);" % (enable_command_toggle and enable_checkbox_toggle and 1 or 0, ))


def ajax_count_button():
    id = html.var("id")
    counts = config.load_user_file("buttoncounts", {})
    for i in counts:
        counts[i] *= 0.95
    counts.setdefault(id, 0)
    counts[id] += 1
    config.save_user_file("buttoncounts", counts)


# Retrieve data via livestatus, convert into list of dicts,
# prepare row-function needed for painters
# datasource: the datasource object as defined in plugins/views/datasources.py
# columns: the list of livestatus columns to query
# add_columns: list of columns the datasource is known to add itself
#  (couldn't we get rid of this parameter by looking that up ourselves?)
# add_headers: additional livestatus headers to add
# only_sites: list of sites the query is limited to
# limit: maximum number of data rows to query
def query_data(datasource, columns, add_columns, add_headers, only_sites = [], limit = None):
    tablename = datasource["table"]
    add_headers += datasource.get("add_headers", "")
    merge_column = datasource.get("merge_by")
    if merge_column:
        columns = [merge_column] + columns

    # Most layouts need current state of object in order to
    # choose background color - even if no painter for state
    # is selected. Make sure those columns are fetched. This
    # must not be done for the table 'log' as it cannot correctly
    # distinguish between service_state and host_state
    if "log" not in datasource["infos"]:
        state_columns = []
        if "service" in datasource["infos"]:
            state_columns += [ "service_has_been_checked", "service_state" ]
        if "host" in datasource["infos"]:
            state_columns += [ "host_has_been_checked", "host_state" ]
        for c in state_columns:
            if c not in columns:
                columns.append(c)

    # Remove columns which are implicitely added by the datasource
    columns = [ c for c in columns if c not in add_columns ]
    query = "GET %s\n" % tablename
    return do_query_data(query, columns, add_columns, merge_column,
                         add_headers, only_sites, limit)

def do_query_data(query, columns, add_columns, merge_column,
                  add_headers, only_sites, limit):
    query += "Columns: %s\n" % " ".join(columns)
    query += add_headers
    html.live.set_prepend_site(True)
    if limit != None:
        html.live.set_limit(limit + 1) # + 1: We need to know, if limit is exceeded
    if config.debug_livestatus_queries \
            and html.output_format == "html" and 'W' in html.display_options:
        html.write('<div class="livestatus message">'
                   '<tt>%s</tt></div>\n' % (query.replace('\n', '<br>\n')))

    if only_sites:
        html.live.set_only_sites(only_sites)
    data = html.live.query(query)
    html.live.set_only_sites(None)
    html.live.set_prepend_site(False)
    html.live.set_limit() # removes limit

    if merge_column:
        data = merge_data(data, columns)

    # convert lists-rows into dictionaries.
    # performance, but makes live much easier later.
    columns = ["site"] + columns + add_columns
    rows = [ dict(zip(columns, row)) for row in data ]

    return rows



# Merge all data rows with different sites but the same value
# in merge_column. We require that all column names are prefixed
# with the tablename. The column with the merge key is required
# to be the *second* column (right after the site column)
def merge_data(data, columns):
    merged = {}
    mergefuncs = [lambda a,b: ""] # site column is not merged

    def worst_service_state(a, b):
        if a == 2 or b == 2:
            return 2
        else:
            return max(a, b)

    def worst_host_state(a, b):
        if a == 1 or b == 1:
            return 1
        else:
            return max(a, b)

    for c in columns:
        tablename, col = c.split("_", 1)
        if col.startswith("num_") or col.startswith("members"):
            mergefunc = lambda a,b: a+b
        elif col.startswith("worst_service"):
            return worst_service_state
        elif col.startswith("worst_host"):
            return worst_host_state
        else:
            mergefunc = lambda a,b: a
        mergefuncs.append(mergefunc)

    for row in data:
        mergekey = row[1]
        if mergekey in merged:
            oldrow = merged[mergekey]
            merged[mergekey] = [ f(a,b) for f,a,b in zip(mergefuncs, oldrow, row) ]
        else:
            merged[mergekey] = row

    # return all rows sorted according to merge key
    mergekeys = merged.keys()
    mergekeys.sort()
    return [ merged[k] for k in mergekeys ]


# Sort data according to list of sorters. The tablename
# is needed in order to handle different column names
# for same objects (e.g. host_name in table services and
# simply name in table hosts)
def sort_data(data, sorters):

    if len(sorters) == 0:
        return

    # Handle case where join columns are not present for all rows
    def save_compare(compfunc, row1, row2, args):
        if row1 == None and row2 == None:
            return 0
        elif row1 == None:
            return -1
        elif row2 == None:
            return 1
        else:
            if args:
                return compfunc(row1, row2, *args)
            else:
                return compfunc(row1, row2)

    sort_cmps = []
    for s in sorters:
        cmpfunc = s[0]["cmp"]
        negate = s[1] and -1 or 1
        if len(s) > 2:
            joinkey = s[2] # e.g. service description
        else:
            joinkey = None
        sort_cmps.append((cmpfunc, negate, joinkey, s[0].get('args')))

    def multisort(e1, e2):
        for func, neg, joinkey, args in sort_cmps:
            if joinkey: # Sorter for join column, use JOIN info
                c = neg * save_compare(func, e1["JOIN"].get(joinkey), e2["JOIN"].get(joinkey), args)
            else:
                if args:
                    c = neg * func(e1, e2, *args)
                else:
                    c = neg * func(e1, e2)
            if c != 0: return c
        return 0 # equal

    data.sort(multisort)

# Filters a list of sorters or painters and decides which of
# those are available for a certain data source
def allowed_for_datasource(collection, datasourcename):
    datasource = multisite_datasources[datasourcename]
    infos_available = set(datasource["infos"])
    add_columns = datasource.get("add_columns", [])

    allowed = {}
    for name, item in collection.items():
        columns = item["columns"]
        infos_needed = set([ c.split("_", 1)[0] for c in columns if c != "site" and c not in add_columns])
        if len(infos_needed.difference(infos_available)) == 0:
            allowed[name] = item
    return allowed

def allowed_for_joined_datasource(collection, datasourcename):
    if 'join' not in multisite_datasources[datasourcename]:
        return {}
    return allowed_for_datasource(collection, multisite_datasources[datasourcename]['join'][0])

def collist_of_collection(collection, join_target = []):
    def sort_list(l):
        # Sort the lists but don't mix them up
        swapped = [ (disp, key) for key, disp in l ]
        swapped.sort()
        return [ (key, disp) for disp, key in swapped ]

    if not join_target:
        return sort_list([ (name, p["title"]) for name, p in collection.items() ])
    else:
        return sort_list([ (name, p["title"]) for name, p in collection.items() if (name, p["title"]) not in join_target ])

#.
#   .--Commands------------------------------------------------------------.
#   |         ____                                          _              |
#   |        / ___|___  _ __ ___  _ __ ___   __ _ _ __   __| |___          |
#   |       | |   / _ \| '_ ` _ \| '_ ` _ \ / _` | '_ \ / _` / __|         |
#   |       | |__| (_) | | | | | | | | | | | (_| | | | | (_| \__ \         |
#   |        \____\___/|_| |_| |_|_| |_| |_|\__,_|_| |_|\__,_|___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Functions dealing with external commands send to the monitoring      |
#   | core. The commands themselves are defined as a plugin. Shipped       |
#   | command definitions are in plugins/views/commands.py.                |
#   | We apologize for the fact that we one time speak of "commands" and   |
#   | the other time of "action". Both is the same here...                 |
#   '----------------------------------------------------------------------'

# Checks wether or not this view handles commands for the current user
# When it does not handle commands the command tab, command form, row
# selection and processing commands is disabled.
def should_show_command_form(display_options, datasource):
    if not 'C' in display_options:
        return False
    if not config.may("general.act"):
        return False
    if html.has_var("try"):
        return False

    # What commands are available depends on the Livestatus table we
    # deal with. If a data source provides information about more
    # than one table, (like services datasource also provide host
    # information) then the first info is the primary table. So 'what'
    # will be one of "host", "service", "command" or "downtime".
    what = datasource["infos"][0]
    for command in multisite_commands:
        if what in command["tables"] and config.may(command["permission"]):
            return True

    return False

def show_command_form(is_open, datasource):
    # What commands are available depends on the Livestatus table we
    # deal with. If a data source provides information about more
    # than one table, (like services datasource also provide host
    # information) then the first info is the primary table. So 'what'
    # will be one of "host", "service", "command" or "downtime".
    what = datasource["infos"][0]

    html.write('<div class="view_form" id="commands" %s>' %
                (not is_open and 'style="display: none"' or '') )
    html.begin_form("actions")
    html.hidden_field("_do_actions", "yes")
    html.hidden_field("actions", "yes")
    html.hidden_fields() # set all current variables, exception action vars

    # Show command forms, grouped by (optional) command group
    by_group = {}
    for command in multisite_commands:
        if what in command["tables"] and config.may(command["permission"]):
            # Some special commands can be shown on special views using this option.
            # It is currently only used in custom views, not shipped with check_mk.
            if command.get('only_view') and html.var('view_name') != command['only_view']:
                continue
            group = command.get("group", _("Various Commands"))
            by_group.setdefault(group, []).append(command)

    groups = by_group.keys()
    groups.sort()
    for group in groups:
        forms.header(group, narrow=True)
        for command in by_group[group]:
            forms.section(command["title"])
            command["render"]()

    forms.end()
    html.end_form()
    html.write("</div>")

# Examine the current HTML variables in order determine, which
# command the user has selected. The fetch ids from a data row
# (host name, service description, downtime/commands id) and
# construct one or several core command lines and a descriptive
# title.
def core_command(what, row, row_nr, total_rows):
    host = row.get("host_name")
    descr = row.get("service_description")

    if what == "host":
        spec = host
        cmdtag = "HOST"
        prefix = "host_"
    elif what == "service":
        spec = "%s;%s" % (host, descr)
        cmdtag = "SVC"
        prefix = "service_"
    else:
        spec = row.get(what + "_id")
        if descr:
            cmdtag = "SVC"
        else:
            cmdtag = "HOST"

    commands = None
    title = None
    # Call all command actions. The first one that detects
    # itself to be executed (by examining the HTML variables)
    # will return a command to execute and a title for the
    # confirmation dialog.
    for cmd in multisite_commands:
        if config.may(cmd["permission"]):

            # Does the command need information about the total number of rows
            # and the number of the current row? Then specify that
            if cmd.get("row_stats"):
                result = cmd["action"](cmdtag, spec, row, row_nr, total_rows)
            else:
                result = cmd["action"](cmdtag, spec, row)

            if result:
                executor = cmd.get("executor", command_executor_livestatus)
                commands, title = result
                break

    # Use the title attribute to determine if a command exists, since the list
    # of commands might be empty (e.g. in case of "remove all downtimes" where)
    # no downtime exists in a selection of rows.
    if not title:
        raise MKUserError(None, _("Sorry. This command is not implemented."))

    # Some commands return lists of commands, others
    # just return one basic command. Convert those
    if type(commands) != list:
        commands = [commands]

    return commands, title, executor


def command_executor_livestatus(command, site):
    html.live.command("[%d] %s" % (int(time.time()), command), site)

# make gettext localize some magic texts
_("services")
_("hosts")
_("commands")
_("downtimes")
_("aggregations")

# Returns:
# True -> Actions have been done
# False -> No actions done because now rows selected
# [...] new rows -> Rows actions (shall/have) be performed on
def do_actions(view, what, action_rows, backurl):
    if not config.may("general.act"):
        html.show_error(_("You are not allowed to perform actions. "
                          "If you think this is an error, please ask "
                          "your administrator grant you the permission to do so."))
        return False # no actions done

    if not action_rows:
        message = _("No rows selected to perform actions for.")
        if html.output_format == "html": # sorry for this hack
            message += '<br><a href="%s">%s</a>' % (backurl, _('Back to view'))
        html.show_error(message)
        return False # no actions done

    command = None
    title, executor = core_command(what, action_rows[0], 0, len(action_rows))[1:3] # just get the title and executor
    if not html.confirm(_("Do you really want to %(title)s the following %(count)d %(what)s?") %
            { "title" : title, "count" : len(action_rows), "what" : visuals.infos[what]["title_plural"], }, method = 'GET'):
        return False

    count = 0
    already_executed = set([])
    for nr, row in enumerate(action_rows):
        core_commands, title, executor = core_command(what, row, nr, len(action_rows))
        for command_entry in core_commands:
            if command_entry not in already_executed:
                # Some command functions return the information about the site per-command (e.g. for BI)
                if type(command_entry) == tuple:
                    site, command = command_entry
                else:
                    command = command_entry
                    site = row["site"]

                if type(command) == unicode:
                    command = command.encode("utf-8")

                executor(command, site)
                already_executed.add(command_entry)
                count += 1

    message = None
    if command:
        message = _("Successfully sent %d commands.") % count
        if config.debug:
            message += _("The last one was: <pre>%s</pre>") % command
    elif count == 0:
        message = _("No matching data row. No command sent.")

    if message:
        if html.output_format == "html": # sorry for this hack
            message += '<br><a href="%s">%s</a>' % (backurl, _('Back to view'))
            if html.var("show_checkboxes") == "1":
                html.del_var("selection")
                weblib.selection_id()
                backurl += "&selection=" + html.var("selection")
                message += '<br><a href="%s">%s</a>' % (backurl, _('Back to view with checkboxes reset'))
        html.message(message)

    return True

def filter_selected_rows(view, rows, selected_ids):
    action_rows = []
    for row in rows:
        if row_id(view, row) in selected_ids:
            action_rows.append(row)
    return action_rows


def get_context_link(user, viewname):
    if viewname in available_views:
        return "view.py?view_name=%s" % viewname
    else:
        return None

def ajax_export():
    load_views()
    for name, view in available_views.items():
        view["owner"] = ''
        view["public"] = True
    html.write(pprint.pformat(available_views))

def get_view_by_name(view_name):
    load_views()
    return available_views[view_name]

#.
#   .--Plugin Helpers------------------------------------------------------.
#   |   ____  _             _         _   _      _                         |
#   |  |  _ \| |_   _  __ _(_)_ __   | | | | ___| |_ __   ___ _ __ ___     |
#   |  | |_) | | | | |/ _` | | '_ \  | |_| |/ _ \ | '_ \ / _ \ '__/ __|    |
#   |  |  __/| | |_| | (_| | | | | | |  _  |  __/ | |_) |  __/ |  \__ \    |
#   |  |_|   |_|\__,_|\__, |_|_| |_| |_| |_|\___|_| .__/ \___|_|  |___/    |
#   |                 |___/                       |_|                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def register_hook(hook, func):
    if not hook in view_hooks:
        view_hooks[hook] = []

    if func not in view_hooks[hook]:
        view_hooks[hook].append(func)

def execute_hooks(hook):
    for hook_func in view_hooks.get(hook, []):
        try:
            hook_func()
        except:
            if config.debug:
                raise MKGeneralException(_('Problem while executing hook function %s in hook %s: %s')
                                           % (hook_func.__name__, hook, traceback.format_exc()))
            else:
                pass

def paint(p, row, tdattrs=""):
    tdclass, content = prepare_paint(p, row)

    if tdclass:
        html.write("<td %s class=\"%s\">%s</td>\n" % (tdattrs, tdclass, content))
    else:
        html.write("<td %s>%s</td>" % (tdattrs, content))
    return content != ""

def paint_painter(painter, row):
    if not row:
        return "", ""  # no join information available for that column

    if "args" in painter:
        return painter["paint"](row, *painter["args"])
    else:
        return painter["paint"](row)

def join_row(row, p):
    join_key = len(p) >= 4 and p[3] or None
    if join_key != None:
        return row.get("JOIN", {}).get(join_key)
    else:
        return row

def prepare_paint(p, row):
    painter = p[0]
    linkview = p[1]
    tooltip = len(p) > 2 and p[2] or None

    row = join_row(row, p)
    tdclass, content = paint_painter(painter, row)
    if tdclass == "" and content == "":
        return tdclass, content

    content = html.utf8_to_entities(content)

    # Create contextlink to other view
    if content and linkview:
        content = link_to_view(content, row, linkview)

    # Tooltip
    if content != '' and tooltip:
        cla, txt = multisite_painters[tooltip]["paint"](row)
        tooltiptext = html.utf8_to_entities(html.strip_tags(txt))
        content = '<span title="%s">%s</span>' % (tooltiptext, content)
    return tdclass, content

def link_to_view(content, row, view_name):
    if 'I' not in html.display_options:
        return content

    view = available_views.get(view_name)
    if view:
        # Get the context type of the view to link to, then get the parameters of this
        # context type and try to construct the context from the data of the row
        vars = []
        datasource = multisite_datasources[view['datasource']]
        for info_key in datasource['infos']:
            if info_key in view['single_infos']:
                # Determine which filters (their names) need to be set
                # for specifying in order to select correct context for the
                # target view.
                for filter_name in visuals.info_params(info_key):
                    filter_object = visuals.get_filter(filter_name)
                    # Get the list of URI vars to be set for that filter
                    new_vars = filter_object.variable_settings(row)
                    vars += new_vars

        do = html.var("display_options")
        if do:
            vars.append(("display_options", do))

        filename = html.mobile and "mobile_view.py" or "view.py"
        uri = filename + "?" + html.urlencode_vars([("view_name", view_name)] + vars)
        content = "<a href=\"%s\">%s</a>" % (uri, content)
    return content

def docu_link(topic, text):
    return '<a href="%s" target="_blank">%s</a>' % (config.doculink_urlformat % topic, text)

def row_id(view, row):
    '''
    Calculates a uniq id for each data row which identifies the current
    row accross different page loadings.
    '''
    key = ''
    for col in multisite_datasources[view['datasource']]['idkeys']:
        key += '~%s' % row[col]
    return str(hash(key))

def paint_stalified(row, text):
    if is_stale(row):
        return "stale", text
    else:
        return "", text


def substract_sorters(base, remove):
    for s in remove:
        if s in base:
            base.remove(s)
        elif (s[0], not s[1]) in base:
            base.remove((s[0], not s[1]))

def parse_url_sorters(sort):
    sorters = []
    if not sort:
        return sorters
    for s in sort.split(','):
        if not '~' in s:
            sorters.append((s.replace('-', ''), s.startswith('-')))
        else:
            sorter, join_index = s.split('~', 1)
            sorters.append((sorter.replace('-', ''), sorter.startswith('-'), join_index))
    return sorters

def get_sorter_name_of_painter(painter):
    if 'sorter' in painter:
        return painter['sorter']
    elif painter['name'] in multisite_sorters:
        return painter['name']

def get_primary_sorter_order(view, painter):
    sorter_name = get_sorter_name_of_painter(painter)
    this_asc_sorter  = (sorter_name, False)
    this_desc_sorter = (sorter_name, True)
    group_sort, user_sort, view_sort = get_separated_sorters(view)
    if user_sort and this_asc_sorter == user_sort[0]:
        return 'asc'
    elif user_sort and this_desc_sorter == user_sort[0]:
        return 'desc'
    else:
        return ''

def get_separated_sorters(view):
    group_sort = [ (get_sorter_name_of_painter(multisite_painters[p[0]]), False)
                   for p in view['group_painters']
                   if p[0] in multisite_painters
                      and get_sorter_name_of_painter(multisite_painters[p[0]]) is not None ]
    view_sort  = [ s for s in view['sorters'] if not s[0] in group_sort ]

    # Get current url individual sorters. Parse the "sort" url parameter,
    # then remove the group sorters. The left sorters must be the user
    # individual sorters for this view.
    # Then remove the user sorters from the view sorters
    user_sort = parse_url_sorters(html.var('sort'))

    substract_sorters(user_sort, group_sort)
    substract_sorters(view_sort, user_sort)

    return group_sort, user_sort, view_sort

def sort_url(view, painter, join_index):
    """
    The following sorters need to be handled in this order:

    1. group by sorter (needed in grouped views)
    2. user defined sorters (url sorter)
    3. configured view sorters
    """
    sort = html.var('sort', None)
    sorter = []

    group_sort, user_sort, view_sort = get_separated_sorters(view)

    sorter = group_sort + user_sort + view_sort

    # Now apply the sorter of the current column:
    # - Negate/Disable when at first position
    # - Move to the first position when already in sorters
    # - Add in the front of the user sorters when not set
    sorter_name = get_sorter_name_of_painter(painter)
    if join_index:
        this_asc_sorter  = (sorter_name, False, join_index)
        this_desc_sorter = (sorter_name, True, join_index)
    else:
        this_asc_sorter  = (sorter_name, False)
        this_desc_sorter = (sorter_name, True)

    if user_sort and this_asc_sorter == user_sort[0]:
        # Second click: Change from asc to desc order
        sorter[sorter.index(this_asc_sorter)] = this_desc_sorter
    elif user_sort and this_desc_sorter == user_sort[0]:
        # Third click: Remove this sorter
        sorter.remove(this_desc_sorter)
    else:
        # First click: add this sorter as primary user sorter
        # Maybe the sorter is already in the user sorters or view sorters, remove it
        for s in [ user_sort, view_sort ]:
            if this_asc_sorter in s:
                s.remove(this_asc_sorter)
            if this_desc_sorter in s:
                s.remove(this_desc_sorter)
        # Now add the sorter as primary user sorter
        sorter = group_sort + [this_asc_sorter] + user_sort + view_sort

    p = []
    for s in sorter:
        if len(s) == 2:
            p.append((s[1] and '-' or '') + s[0])
        else:
            p.append((s[1] and '-' or '') + s[0] + '~' + s[2])

    return ','.join(p)

def paint_header(view, p):
    # The variable p is a tuple with the following components:
    # p[0] --> painter object, from multisite_painters[]
    # p[1] --> view name to link to or None (not needed here)
    # p[2] --> tooltip (title) to display (not needed here)
    # p[3] --> optional: join key (e.g. service description)
    # p[4] --> optional: column title to use instead default
    painter = p[0]
    join_index = None
    t = painter.get("short", painter["title"])
    if len(p) >= 4: # join column
        join_index = p[3]
        t = p[3] # use join index (service name) as title
    if len(p) >= 5 and p[4]:
        t = p[4] # use custom defined title

    # Optional: Sort link in title cell
    # Use explicit defined sorter or implicit the sorter with the painter name
    # Important for links:
    # - Add the display options (Keeping the same display options as current)
    # - Link to _self (Always link to the current frame)
    # - Keep the _body_class variable (e.g. for dashlets)
    thclass = ''
    onclick = ''
    title = ''
    if 'L' in html.display_options \
       and view.get('user_sortable', False) \
       and get_sorter_name_of_painter(painter) is not None:
        params = [
            ('sort', sort_url(view, painter, join_index)),
        ]
        if html.has_var('_body_class'):
            params.append(('_body_class',     html.var('_body_class')))
        if hasattr(html, 'title_display_options'):
            params.append(('display_options', html.title_display_options))

        thclass = ' class="sort %s"' % get_primary_sorter_order(view, painter)
        onclick = ' onclick="location.href=\'%s\'"' % html.makeuri(params, 'sort')
        title   = ' title="%s"' % (_('Sort by %s') % t)

    html.write("<th%s%s%s>%s</th>" % (thclass, onclick, title, t))

def register_events(row):
    if config.sounds != []:
        host_state = row.get("host_hard_state", row.get("host_state"))
        if host_state != None:
            html.register_event({0:"up", 1:"down", 2:"unreachable"}[saveint(host_state)])
        svc_state = row.get("service_last_hard_state", row.get("service_state"))
        if svc_state != None:
            html.register_event({0:"up", 1:"warning", 2:"critical", 3:"unknown"}[saveint(svc_state)])

# The Group-value of a row is used for deciding wether
# two rows are in the same group or not
def group_value(row, group_painters):
    group = []
    for p in group_painters:
        groupvalfunc = p[0].get("groupby")
        if groupvalfunc:
            if "args" in p[0]:
                group.append(groupvalfunc(row, *p[0]["args"]))
            else:
                group.append(groupvalfunc(row))
        else:
            for c in p[0]["columns"]:
                group.append(row[c])
    return group

def get_painter_option(name):
    opt = multisite_painter_options[name]
    if "forced_value" in opt:
        return opt["forced_value"]
    elif not config.may("general.painter_options"):
        return opt['valuespec'].default_value()
    else:
        return opt.get("value", opt['valuespec'].default_value())

def get_host_tags(row):
    if type(row.get("host_custom_variables")) == dict:
        return row["host_custom_variables"].get("TAGS", "")

    if type(row.get("host_custom_variable_names")) != list:
        return ""

    for name, val in zip(row["host_custom_variable_names"],
                         row["host_custom_variable_values"]):
        if name == "TAGS":
            return  val
    return ""

# Get the definition of a tag group
g_taggroups_by_id = {}
def get_tag_group(tgid):
    # Build a cache
    if not g_taggroups_by_id:
        for entry in config.wato_host_tags:
            g_taggroups_by_id[entry[0]] = (entry[1], entry[2])

    return g_taggroups_by_id.get(tgid)

def get_custom_var(row, key):
    for name, val in zip(row["custom_variable_names"],
                         row["custom_variable_values"]):
        if name == key:
            return  val
    return ""

def is_stale(row):
    return row.get('service_staleness', row.get('host_staleness', 0)) >= config.staleness_threshold

def cmp_insensitive_string(v1, v2):
    c = cmp(v1.lower(), v2.lower())
    # force a strict order in case of equal spelling but different
    # case!
    if c == 0:
        return cmp(v1, v2)
    else:
        return c

# Sorting
def cmp_ip_address(column, r1, r2):
    def split_ip(ip):
        try:
            return tuple(int(part) for part in ip.split('.'))
        except:
            return ip
    v1, v2 = split_ip(r1.get(column, '')), split_ip(r2.get(column, ''))
    return cmp(v1, v2)


def cmp_simple_string(column, r1, r2):
    v1, v2 = r1.get(column, ''), r2.get(column, '')
    return cmp_insensitive_string(v1, v2)

def cmp_num_split(column, r1, r2):
    c1 = r1[column]
    c2 = r2[column]
    return cmp(num_split(c1) + (c1,), num_split(c2) + (c2,))

def cmp_string_list(column, r1, r2):
    v1 = ''.join(r1.get(column, []))
    v2 = ''.join(r2.get(column, []))
    return cmp_insensitive_string(v1, v2)

def cmp_simple_number(column, r1, r2):
    return cmp(r1.get(column), r2.get(column))

def cmp_custom_variable(r1, r2, key, cmp_func):
    return cmp(get_custom_var(r1, key), get_custom_var(r2, key))

def declare_simple_sorter(name, title, column, func):
    multisite_sorters[name] = {
        "title"   : title,
        "columns" : [ column ],
        "cmp"     : lambda r1, r2: func(column, r1, r2)
    }

def declare_1to1_sorter(painter_name, func, col_num = 0, reverse = False):
    multisite_sorters[painter_name] = {
        "title"   : multisite_painters[painter_name]['title'],
        "columns" : multisite_painters[painter_name]['columns'],
    }
    if not reverse:
        multisite_sorters[painter_name]["cmp"] = \
            lambda r1, r2: func(multisite_painters[painter_name]['columns'][col_num], r1, r2)
    else:
        multisite_sorters[painter_name]["cmp"] = \
            lambda r1, r2: func(multisite_painters[painter_name]['columns'][col_num], r2, r1)
    return painter_name



# Ajax call for fetching parts of the tree
def ajax_inv_render_tree():
    hostname = html.var("host")
    invpath = html.var("path")
    tree_id = html.var("treeid", "")
    if tree_id:
        tree = inventory.load_delta_tree(hostname, int(tree_id[1:]))
    else:
        tree = inventory.host(hostname)
    node = inventory.get(tree, invpath)
    if not node:
        html.show_error(_("Invalid path %s in inventory tree") % invpath)
    else:
        render_inv_subtree_container(hostname, tree_id, invpath, node)


