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

import time
import os
import re
import pprint
import traceback
import inspect
import livestatus
import types

import cmk.paths

import cmk.gui.utils as utils
import cmk.gui.config as config
import cmk.gui.weblib as weblib
import cmk.gui.forms as forms
import cmk.gui.valuespec as valuespec
import cmk.gui.inventory as inventory
import cmk.gui.visuals as visuals
import cmk.gui.metrics as metrics
import cmk.gui.sites as sites
import cmk.gui.bi as bi
import cmk.gui.i18n
import cmk.gui.pages
from cmk.gui.display_options import display_options
from cmk.gui.valuespec import *
from cmk.gui.i18n import _u, _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
from cmk.gui.log import logger
from cmk.gui.exceptions import MKGeneralException, MKUserError, MKInternalError

from cmk.gui.plugins.views.utils import (
    load_all_views,
    get_permitted_views,
    view_title,
    multisite_painter_options,
    multisite_datasources,
    multisite_layouts,
    multisite_painters,
    multisite_sorters,
    multisite_builtin_views,
    multisite_commands,
    multisite_command_groups,
    view_hooks,
    inventory_displayhints,
    register_command_group,
    transform_action_url,
    is_stale,
    paint_stalified,
    paint_host_list,
    format_plugin_output,
    link_to_view,
    url_to_view,
    get_host_tags,
    row_id,
    group_value,
    get_painter_columns,
    view_is_enabled,
    paint_age,
    declare_1to1_sorter,
    declare_simple_sorter,
    cmp_simple_number,
    cmp_simple_string,
    cmp_insensitive_string,
    cmp_num_split,
    cmp_custom_variable,
    cmp_service_name_equiv,
    cmp_string_list,
    cmp_ip_address,
    get_custom_var,
    get_perfdata_nth_value,
    get_tag_group,
    query_data,
    do_query_data,
    PainterOptions,
    join_row,
    get_view_infos,
    replace_action_url_macros,
    Cell,
    JoinCell,
    get_cells,
    get_group_cells,
    get_sorter_name_of_painter,
    get_separated_sorters,
    get_primary_sorter_order,
    get_painter_params_valuespec,
    parse_url_sorters,
    substract_sorters,
    painter_options,
)

from cmk.gui.plugins.views.icons import (
    multisite_icons,
    multisite_icons_and_actions,
    get_multisite_icons,
    get_icons,
    iconpainter_columns,
)

import cmk.gui.plugins.views.inventory
import cmk.gui.plugins.views.availability

if not cmk.is_raw_edition():
    import cmk.gui.cee.plugins.views
    import cmk.gui.cee.plugins.views.icons

if cmk.is_managed_edition():
    import cmk.gui.cme.plugins.views

# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False

# Load all view plugins
def load_plugins(force):
    global loaded_with_language

    if loaded_with_language == cmk.gui.i18n.get_current_language() and not force:
        # always reload the hosttag painters, because new hosttags might have been
        # added during runtime
        load_host_tag_painters()
        clear_alarm_sound_states()
        return

    config.declare_permission_section("action", _("Commands on host and services"), do_sort = True)

    utils.load_web_plugins("views", globals())
    utils.load_web_plugins('icons', globals())
    load_host_tag_painters()
    clear_alarm_sound_states()

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = cmk.gui.i18n.get_current_language()

    # Declare permissions for builtin views
    config.declare_permission_section("view", _("Multisite Views"), do_sort = True)
    for name, view in multisite_builtin_views.items():
        config.declare_permission("view.%s" % name,
                format_view_title(view),
                "%s - %s" % (name, _u(view["description"])),
                config.builtin_role_ids)

    # Make sure that custom views also have permissions
    config.declare_dynamic_permissions(lambda: visuals.declare_custom_permissions('views'))

    cmk.gui.plugins.views.inventory.declare_inventory_columns()


# Load all views - users or builtins
# TODO: Clean these request specific module scope variables
def load_views():
    global multisite_views, available_views
    multisite_views = load_all_views()
    available_views = get_permitted_views(multisite_views)

def permitted_views():
    try:
        return available_views
    except:
        # In some cases, for example when handling AJAX calls the views might
        # have not been loaded yet
        load_views()
        return available_views

def all_views():
    return multisite_views


def save_views(us):
    visuals.save('views', multisite_views)



def is_enabled_for(linking_view, view, context_vars):
    if view["name"] not in view_is_enabled:
        return True # Not registered are always visible!

    return view_is_enabled[view["name"]](linking_view, view, context_vars)


def paint_host_tag(row, tgid):
    tags_of_host = get_host_tags(row).split()

    for t in get_tag_group(tgid)[1]:
        if t[0] in tags_of_host:
            return "", t[1]
    return "", _("N/A")


# Use title of the tag value for grouping, not the complete
# dictionary of custom variables!
def groupby_host_tag(row, tgid):
    _cssclass, title = paint_host_tag(row, tgid)
    return title


def load_host_tag_painters():
    # first remove all old painters to reflect delted painters during runtime
    # FIXME: Do not modify the dict while iterating over it.
    for key in list(multisite_painters.keys()):
        if key.startswith('host_tag_'):
            del multisite_painters[key]

    for entry in config.host_tag_groups():
        tgid = entry[0]
        tit  = entry[1]

        long_tit = tit
        if '/' in tit:
            topic, tit = tit.split('/', 1)
            if topic:
                long_tit = topic + ' / ' + tit
            else:
                long_tit = tit

        multisite_painters["host_tag_" + tgid] = {
            "title"   : _("Host tag:") + ' ' + long_tit,
            "name"    : "host_tag_" + tgid,
            "short"   : tit,
            "columns" : [ "host_custom_variables" ],
            "paint"   : paint_host_tag,
            "groupby" : groupby_host_tag,
            "args"    : [ tgid ],
        }


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

@cmk.gui.pages.register("edit_views")
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

@cmk.gui.pages.register("create_view")
def page_create_view(next_url = None):

    vs_ds = DatasourceSelection()

    ds = 'services' # Default selection

    html.header(_('Create View'), stylesheets=["pages"])
    html.begin_context_buttons()
    back_url = html.var("back", "")
    if not utils.is_allowed_url(back_url):
        back_url = "edit_views.py"
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
            html.response.http_redirect(next_url)
            return

        except MKUserError, e:
            html.div(e, class_=["error"])
            html.add_user_error(e.varname, e)

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


@cmk.gui.pages.register("create_view_infos")
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

@cmk.gui.pages.register("edit_view")
def page_edit_view():
    load_views()

    visuals.page_edit_visual('views', multisite_views,
        custom_field_handler = render_view_config,
        load_handler = transform_view_to_valuespec_value,
        create_handler = create_view_from_valuespec,
        info_handler = get_view_infos,
    )

def view_choices(only_with_hidden = False):
    choices = [("", "")]
    for name, view in available_views.items():
        if not only_with_hidden or view['single_infos']:
            title = format_view_title(view)
            choices.append(("%s" % name, title))
    return choices

def format_view_title(view):
    if view.get('mobile', False):
        return _('Mobile: ') + _u(view["title"])
    else:
        return _u(view["title"])

def view_editor_options():
    return [
        ('mobile',           _('Show this view in the Mobile GUI')),
        ('mustsearch',       _('Show data only on search')),
        ('force_checkboxes', _('Always show the checkboxes')),
        ('user_sortable',    _('Make view sortable by user')),
        ('play_sounds',      _('Play alarm sounds')),
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

    def column_spec(ident, title, ds_name):
        painters = painters_of_datasource(ds_name)

        allow_empty = True
        empty_text = None
        if ident == 'columns':
            allow_empty = False
            empty_text = _("Please add at least one column to your view.")

        vs_column = Tuple(
            title = _('Column'),
            elements = [
                CascadingDropdown(
                    title = _('Column'),
                    choices = painter_choices_with_params(painters),
                    no_preselect = True,
                ),
                DropdownChoice(
                    title = _('Link'),
                    choices = view_choices,
                    sorted = True,
                ),
                DropdownChoice(
                    title = _('Tooltip'),
                    choices = [(None, "")] + painter_choices(painters),
                ),
            ],
        )

        join_painters = join_painters_of_datasource(ds_name)
        if ident == 'columns' and join_painters:
            join_painters = join_painters_of_datasource(ds_name)

            vs_column = Alternative(
                elements = [
                    vs_column,

                    Tuple(
                        title = _('Joined column'),
                        help = _("A joined column can display information about specific services for "
                                 "host objects in a view showing host objects. You need to specify the "
                                 "service description of the service you like to show the data for."),
                        elements = [
                            CascadingDropdown(
                                title = _('Column'),
                                choices = painter_choices_with_params(join_painters),
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
                                choices = [(None, "")] + painter_choices(join_painters),
                            ),
                            TextUnicode(
                                title = _('Title'),
                            ),
                        ],
                    ),
                ],
                style = 'dropdown',
                match = lambda x: 1 * (x is not None and len(x) == 5),
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
                                choices = [ (name, get_painter_title_for_choices(p)) for name, p
                                            in sorters_of_datasource(ds_name).items() ],
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
                    add_label = _('Add sorter'),
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
    for key, _title in view_editor_options():
        if view.get(key):
            view['view']['options'].append(key)

    view['visibility'] = {}
    for key in [ 'hidden', 'hidebutton', 'public' ]:
        if view.get(key):
            view['visibility'][key] = view[key]

    view['grouping'] = { "grouping" : view.get('group_painters', []) }
    view['sorting']  = { "sorters" : view.get('sorters', {}) }

    columns = []
    view['columns'] = { "columns" : columns }
    for entry in view.get('painters', []):
        if len(entry) == 5:
            pname, viewname, tooltip, join_index, col_title = entry
            columns.append((pname, join_index, viewname, tooltip or None, col_title))

        elif len(entry) == 4:
            pname, viewname, tooltip, join_index = entry
            columns.append((pname, join_index, viewname, tooltip or None, ''))

        elif len(entry) == 3:
            pname, viewname, tooltip = entry
            columns.append((pname, viewname, tooltip or None))

        else:
            pname, viewname = entry
            columns.append((pname, viewname, None))


def transform_valuespec_value_to_view(view):
    for ident, attrs in view.items():
        # Transform some valuespec specific options to legacy view
        # format. We do not want to change the view data structure
        # at the moment.
        if ident == 'view':
            if "options" in attrs:
                # First set all options to false
                for option, _title in view_editor_options():
                    view[option] = False

                # Then set the selected single options
                for option in attrs['options']:
                    view[option] = True

                # And cleanup
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

                viewname = viewname if viewname else None

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
        html.open_div(style="display:none;")
        f.display()
        html.close_div()
    else:
        visuals.show_filter(f)


def show_filter_form(is_open, filters):
    # Table muss einen anderen Namen, als das Formular
    html.open_div(id_="filters", class_=["view_form"], style="display: none;" if not is_open else None)

    html.begin_form("filter")
    html.open_table(class_=["filterform"], cellpadding="0", cellspacing="0", border="0")
    html.open_tr()
    html.open_td()

    # sort filters according to title
    s = [(f.sort_index, f.title, f) for f in filters if f.available()]
    s.sort()

    # First show filters with double height (due to better floating
    # layout)
    for _sort_index, _title, f in s:
        if f.double_height():
            show_filter(f)

    # Now single height filters
    for _sort_index, _title, f in s:
        if not f.double_height():
            show_filter(f)

    html.close_td()
    html.close_tr()

    html.open_tr()
    html.open_td()
    html.button("search", _("Search"), "submit")
    html.close_td()
    html.close_tr()

    html.close_table()

    html.hidden_fields()
    html.end_form()
    html.close_div()


@cmk.gui.pages.register("view")
def page_view():
    bi.reset_cache_status() # needed for status icon

    load_views()
    view_name = html.var("view_name")
    if view_name == None:
        raise MKGeneralException(_("Missing the variable view_name in the URL."))
    view = available_views.get(view_name)
    if not view:
        raise MKGeneralException(_("No view defined with the name '%s'.") % html.attrencode(view_name))

    # Gather the page context which is needed for the "add to visual" popup menu
    # to add e.g. views to dashboards or reports
    datasource = multisite_datasources[view['datasource']]
    context = visuals.get_context_from_uri_vars(datasource['infos'])
    context.update(visuals.get_singlecontext_html_vars(view))
    html.set_page_context(context)

    painter_options.load(view_name)
    painter_options.update_from_url(view_name, view)

    show_view(view, True, True, True)


# Display view with real data. This is *the* function everying
# is about.
def show_view(view, show_heading = False, show_buttons = True,
              show_footer = True, render_function = None, only_count=False,
              all_filters_active=False, limit=None):

    display_options.load_from_html()

    # Load from hard painter options > view > hard coded default
    num_columns     = painter_options.get("num_columns",     view.get("num_columns",    1))
    browser_reload  = painter_options.get("refresh",         view.get("browser_reload", None))

    force_checkboxes = view.get("force_checkboxes", False)
    show_checkboxes = force_checkboxes or html.var('show_checkboxes', '0') == '1'

    # Get the datasource (i.e. the logical table)
    try:
        datasource = multisite_datasources[view["datasource"]]
    except KeyError:
        if view["datasource"].startswith("mkeventd_"):
            raise MKUserError(None,
                _("The Event Console view '%s' can not be rendered. The Event Console is possibly "
                  "disabled.") % view["name"])
        else:
            raise MKUserError(None,
                _("The view '%s' using the datasource '%s' can not be rendered "
                  "because the datasource does not exist.") % (view["name"], view["datasource"]))

    tablename = datasource["table"]

    # Filters to use in the view
    # In case of single object views, the needed filters are fixed, but not always present
    # in context. In this case, take them from the context type definition.
    use_filters = visuals.filters_of_visual(view, datasource['infos'],
                                        all_filters_active, datasource.get('link_filters', {}))

    # Not all filters are really shown later in show_filter_form(), because filters which
    # have a hardcoded value are not changeable by the user
    show_filters = visuals.visible_filters_of_visual(view, use_filters)

    # FIXME TODO HACK to make grouping single contextes possible on host/service infos
    # Is hopefully cleaned up soon.
    if view['datasource'] in ['hosts', 'services']:
        if html.has_var('hostgroup') and not html.has_var("opthost_group"):
            html.set_var("opthost_group", html.var("hostgroup"))
        if html.has_var('servicegroup') and not html.has_var("optservice_group"):
            html.set_var("optservice_group", html.var("servicegroup"))

    # TODO: Another hack :( Just like the above one: When opening the view "ec_events_of_host",
    # which is of single context "host" using a host name of a unrelated event, the list of
    # events is always empty since the single context filter "host" is sending a "host_name = ..."
    # filter to livestatus which is not matching a "unrelated event". Instead the filter event_host
    # needs to be used.
    # But this may only be done for the unrelated events view. The "ec_events_of_monhost" view still
    # needs the filter. :-/
    # Another idea: We could change these views to non single context views, but then we would not
    # be able to show the buttons to other host related views, which is also bad. So better stick
    # with the current mode.
    if view["datasource"] in [ "mkeventd_events", "mkeventd_history" ] \
       and "host" in view["single_infos"] and view["name"] != "ec_events_of_monhost":
        # Remove the original host name filter
        use_filters = [ f for f in use_filters if f.name != "host" ]

        # Set the value for the event host filter
        if not html.has_var("event_host"):
            html.set_var("event_host", html.var("host"))

    # Now populate the HTML vars with context vars from the view definition. Hard
    # coded default values are treated differently:
    #
    # a) single context vars of the view are enforced
    # b) multi context vars can be overwritten by existing HTML vars
    visuals.add_context_to_uri_vars(view, only_count)

    # Check that all needed information for configured single contexts are available
    visuals.verify_single_contexts('views', view, datasource.get('link_filters', {}))


    # Prepare Filter headers for Livestatus
    # TODO: When this is used by the reporting then *all* filters are
    # active. That way the inventory data will always be loaded. When
    # we convert this to the visuals principle the we need to optimize
    # this.
    filterheaders = ""
    all_active_filters = [ f for f in use_filters if f.available() ]
    for filt in all_active_filters:
        header = filt.filter(tablename)
        filterheaders += header

    # Apply the site hint / filter
    if html.var("site"):
        only_sites = [html.var("site")]
    else:
        only_sites = None

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

        context = visuals.get_context_from_uri_vars(datasource['infos'])
        context.update(visuals.get_singlecontext_html_vars(view))

        return cmk.gui.plugins.views.availability.render_availability_page(view, datasource, context, filterheaders, only_sites, limit)

    query = filterheaders + view.get("add_headers", "")

    # Sorting - use view sorters and URL supplied sorters
    if not only_count:
        user_sorters = parse_url_sorters(html.var("sort"))
        if user_sorters:
            sorter_list = user_sorters
        else:
            sorter_list = view["sorters"]

        sorters = [ (multisite_sorters[s[0]],) + s[1:] for s in sorter_list
                        if s[0] in multisite_sorters ]
    else:
        sorters = []

    # Prepare cells of the view
    # Group cells:   Are displayed as titles of grouped rows
    # Regular cells: Are displaying information about the rows of the type the view is about
    # Join cells:    Are displaying information of a joined source (e.g.service data on host views)
    group_cells   = get_group_cells(view)
    cells         = get_cells(view)
    join_cells    = get_join_cells(cells)

    # Now compute the list of all columns we need to query via Livestatus.
    # Those are: (1) columns used by the sorters in use, (2) columns use by
    # column- and group-painters in use and - note - (3) columns used to
    # satisfy external references (filters) of views we link to. The last bit
    # is the trickiest. Also compute this list of view options use by the
    # painters
    columns      = get_needed_regular_columns(group_cells + cells, sorters, datasource)
    join_columns = get_needed_join_columns(join_cells, sorters, datasource)

    # Fetch data. Some views show data only after pressing [Search]
    if (only_count or (not view.get("mustsearch")) or html.var("filled_in") in ["filter", 'actions', 'confirm', 'painteroptions']):
        # names for additional columns (through Stats: headers)
        add_columns = datasource.get("add_columns", [])

        # tablename may be a function instead of a livestatus tablename
        # In that case that function is used to compute the result.
        # It may also be a tuple. In this case the first element is a function and the second element
        # is a list of argument to hand over to the function together with all other arguments that
        # are passed to query_data().

        if type(tablename) == type(lambda x:None):
            rows = tablename(columns, query, only_sites, limit, all_active_filters)
        elif type(tablename) == tuple:
            func, args = tablename
            rows = func(datasource, columns, add_columns, query, only_sites, limit, *args)
        else:
            rows = query_data(datasource, columns, add_columns, query, only_sites, limit)

        # Now add join information, if there are join columns
        if join_cells:
            do_table_join(datasource, rows, filterheaders, join_cells, join_columns, only_sites)

        # If any painter, sorter or filter needs the information about the host's
        # inventory, then we load it and attach it as column "host_inventory"
        if is_inventory_data_needed(group_cells, cells, sorters, all_active_filters):
            for row in rows:
                 if "host_name" in row:
                     row["host_inventory"] = inventory.load_filtered_and_merged_tree(row)

        if not cmk.is_raw_edition():
            import cmk.gui.cee.sla as sla
            sla_params = []
            for cell in cells:
                if cell.painter_name() in ["sla_specific", "sla_fixed"]:
                    sla_params.append(cell.painter_parameters())
            if sla_params:
                sla_configurations_container = sla.SLAConfigurationsContainerFactory.create_from_cells(sla_params, rows)
                sla.SLAProcessor(sla_configurations_container).add_sla_data_to_rows(rows)

        sort_data(rows, sorters)
    else:
        rows = []

    # Apply non-Livestatus filters
    for filter in all_active_filters:
        rows = filter.filter_table(rows)

    if html.var("mode") == "availability":
        cmk.gui.plugins.views.availability.render_bi_availability(view_title(view), rows)
        return


    # TODO: Use livestatus Stats: instead of fetching rows!
    if only_count:
        for filter_vars in view["context"].itervalues():
            for varname in filter_vars.iterkeys():
                html.del_var(varname)
        return len(rows)

    # The layout of the view: it can be overridden by several specifying
    # an output format (like json or python). Note: the layout is not
    # always needed. In case of an embedded view in the reporting this
    # field is simply missing, because the rendering is done by the
    # report itself.
    # TODO: CSV export should be handled by the layouts. It cannot
    # be done generic in most cases
    if html.output_format == "html":
        if "layout" in view:
            layout = multisite_layouts[view["layout"]]
        else:
            layout = None
    else:
        if "layout" in view and "csv_export" in multisite_layouts[view["layout"]]:
            multisite_layouts[view["layout"]]["csv_export"](rows, view, group_cells, cells)
            return

        else:
            # Generic layout of export
            layout = multisite_layouts.get(html.output_format)
            if not layout:
                layout = multisite_layouts["json"]

    # Set browser reload
    if browser_reload and display_options.enabled(display_options.R) and not only_count:
        html.set_browser_reload(browser_reload)

    if config.enable_sounds and config.sounds and html.output_format == "html":
        for row in rows:
            save_state_for_playing_alarm_sounds(row)


    # Until now no single byte of HTML code has been output.
    # Now let's render the view. The render_function will be
    # replaced by the mobile interface for an own version.
    if not render_function:
        render_function = render_view

    render_function(view, rows, datasource, group_cells, cells,
                show_heading, show_buttons,
                show_checkboxes, layout, num_columns, show_filters, show_footer,
                browser_reload)


def get_join_cells(cell_list):
    return [x for x in cell_list if type(x) == JoinCell]


def get_regular_cells(cell_list):
    return [x for x in cell_list if type(x) == Cell]


def get_needed_regular_columns(cells, sorters, datasource):
    # BI availability needs aggr_tree
    # TODO: wtf? a full reset of the list? Move this far away to a special place!
    if html.var("mode") == "availability" and "aggr" in datasource["infos"]:
        return [ "aggr_tree", "aggr_name", "aggr_group" ]

    columns = columns_of_cells(cells)

    # Columns needed for sorters
    # TODO: Move sorter parsing and logic to something like Cells()
    for s in sorters:
        if len(s) == 2:
            columns.update(s[0]["columns"])

    # Add key columns, needed for executing commands
    columns.update(datasource["keys"])

    # Add idkey columns, needed for identifying the row
    columns.update(datasource["idkeys"])

    # Remove (implicit) site column
    try:
        columns.remove("site")
    except KeyError:
        pass

    return list(columns)


def get_needed_join_columns(join_cells, sorters, datasource):
    join_columns = columns_of_cells(join_cells)

    # Columns needed for sorters
    # TODO: Move sorter parsing and logic to something like Cells()
    for s in sorters:
        if len(s) != 2:
            join_columns.update(s[0]["columns"])

    return list(join_columns)


def is_sla_data_needed(group_cells, cells, sorters, all_active_filters):
    pass

def is_inventory_data_needed(group_cells, cells, sorters, all_active_filters):
    for cell in cells:
        if cell.has_tooltip():
            if cell.tooltip_painter_name().startswith("inv_"):
                return True

    for s in sorters:
        if s[0].get("load_inv"):
            return True

    for cell in group_cells + cells:
        if cell.painter().get("load_inv"):
            return True

    for filt in all_active_filters:
        if filt.need_inventory():
            return True

    return False


def columns_of_cells(cells):
    columns = set([])
    for cell in cells:
        columns.update(cell.needed_columns())
    return columns


# Output HTML code of a view. If you add or remove paramters here,
# then please also do this in htdocs/mobile.py!
def render_view(view, rows, datasource, group_painters, painters,
                show_heading, show_buttons,
                show_checkboxes, layout, num_columns, show_filters, show_footer,
                browser_reload):

    if html.transaction_valid() and html.do_actions():
        html.set_browser_reload(0)

    # Show heading (change between "preview" mode and full page mode)
    if show_heading:
        # Show/Hide the header with page title, MK logo, etc.
        if display_options.enabled(display_options.H):
            # FIXME: view/layout/module related stylesheets/javascripts e.g. in case of BI?
            html.body_start(view_title(view), stylesheets=["pages","views","status","bi"])

        if display_options.enabled(display_options.T):
            html.top_heading(view_title(view))

    has_done_actions = False
    row_count = len(rows)

    # This is a general flag which makes the command form render when the current
    # view might be able to handle commands. When no commands are possible due missing
    # permissions or datasources without commands, the form is not rendered
    command_form = should_show_command_form(datasource)

    if command_form:
        weblib.init_selection()

    # Is the layout able to display checkboxes?
    can_display_checkboxes = layout.get('checkboxes', False)
    if show_buttons:
        show_combined_graphs_button  = \
            ("host" in datasource["infos"] or "service" in datasource["infos"]) and \
            (type(datasource["table"]) == str) and \
            ("host" in datasource["table"] or "service" in datasource["table"])
        show_context_links(view, datasource, show_filters,
                       # Take into account: permissions, display_options
                       row_count > 0 and command_form,
                       # Take into account: layout capabilities
                       can_display_checkboxes and not view.get("force_checkboxes"), show_checkboxes,
                       # Show link to availability
                       datasource["table"] in [ "hosts", "services" ] or "aggr" in datasource["infos"],
                       # Show link to combined graphs
                       show_combined_graphs_button,)
    # User errors in filters
    html.show_user_errors()

    # Filter form
    filter_isopen = view.get("mustsearch") and not html.var("filled_in")
    if display_options.enabled(display_options.F) and len(show_filters) > 0:
        show_filter_form(filter_isopen, show_filters)

    # Actions
    if command_form:
        # If we are currently within an action (confirming or executing), then
        # we display only the selected rows (if checkbox mode is active)
        if show_checkboxes and html.do_actions():
            rows = filter_selected_rows(view, rows, weblib.get_rowselection('view-' + view['name']))

        # There are one shot actions which only want to affect one row, filter the rows
        # by this id during actions
        if html.has_var("_row_id") and html.do_actions():
            rows = filter_by_row_id(view, rows)

        if html.do_actions() and html.transaction_valid(): # submit button pressed, no reload
            try:
                # Create URI with all actions variables removed
                backurl = html.makeuri([], delvars=['filled_in', 'actions'])
                has_done_actions = do_actions(view, datasource["infos"][0], rows, backurl)
            except MKUserError, e:
                html.show_error(e)
                html.add_user_error(e.varname, e)
                if display_options.enabled(display_options.C):
                    show_command_form(True, datasource)

        elif display_options.enabled(display_options.C): # (*not* display open, if checkboxes are currently shown)
            show_command_form(False, datasource)

    # Also execute commands in cases without command form (needed for Python-
    # web service e.g. for NagStaMon)
    elif row_count > 0 and config.user.may("general.act") \
         and html.do_actions() and html.transaction_valid():

        # There are one shot actions which only want to affect one row, filter the rows
        # by this id during actions
        if html.has_var("_row_id") and html.do_actions():
            rows = filter_by_row_id(view, rows)

        try:
            do_actions(view, datasource["infos"][0], rows, '')
        except:
            pass # currently no feed back on webservice

    painter_options.show_form(view)

    # The refreshing content container
    if display_options.enabled(display_options.R):
        html.open_div(id_="data_container")

    if not has_done_actions:
        # Limit exceeded? Show warning
        if display_options.enabled(display_options.W):
            utils.check_limit(rows, get_limit(), config.user)
        layout["render"](rows, view, group_painters, painters, num_columns,
                         show_checkboxes and not html.do_actions())
        headinfo = "%d %s" % (row_count, _("row") if row_count == 1 else _("rows"))
        if show_checkboxes:
            selected = filter_selected_rows(view, rows, weblib.get_rowselection('view-' + view['name']))
            headinfo = "%d/%s" % (len(selected), headinfo)

        if html.output_format == "html":
            html.javascript("update_headinfo('%s');" % headinfo)

            # The number of rows might have changed to enable/disable actions and checkboxes
            if show_buttons:
                update_context_links(
                    # don't take display_options into account here ('c' is set during reload)
                    row_count > 0 and should_show_command_form(datasource, ignore_display_option=True),
                    # and not html.do_actions(),
                    can_display_checkboxes
                )

        # Play alarm sounds, if critical events have been displayed
        if display_options.enabled(display_options.S) and view.get("play_sounds"):
            play_alarm_sounds()
    else:
        # Always hide action related context links in this situation
        update_context_links(False, False)

    # In multi site setups error messages of single sites do not block the
    # output and raise now exception. We simply print error messages here.
    # In case of the web service we show errors only on single site installations.
    if config.show_livestatus_errors \
       and display_options.enabled(display_options.W) \
       and html.output_format == "html":
        for info in sites.live().dead_sites().itervalues():
            html.show_error("<b>%s - %s</b><br>%s" %
                (info["site"]["alias"], _('Livestatus error'), info["exception"]))

    # FIXME: Sauberer waere noch die Status Icons hier mit aufzunehmen
    if display_options.enabled(display_options.R):
        html.close_div()

    if show_footer:
        pid = os.getpid()
        if sites.live().successfully_persisted():
            html.add_status_icon("persist", _("Reused persistent livestatus connection from earlier request (PID %d)") % pid)
        if bi.reused_compilation():
            html.add_status_icon("aggrcomp", _("Reused cached compiled BI aggregations (PID %d)") % pid)

        html.bottom_focuscode()
        if display_options.enabled(display_options.Z):
            html.bottom_footer()

        if display_options.enabled(display_options.H):
            html.body_end()


def do_table_join(master_ds, master_rows, master_filters, join_cells, join_columns, only_sites):
    join_table, join_master_column = master_ds["join"]
    slave_ds = multisite_datasources[join_table]
    join_slave_column = slave_ds["joinkey"]

    # Create additional filters
    join_filters = []
    for cell in join_cells:
        join_filters.append(cell.livestatus_filter(join_slave_column))

    join_filters.append("Or: %d" % len(join_filters))
    query = "%s%s\n" % (master_filters, "\n".join(join_filters))
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


g_alarm_sound_states = set([])


def clear_alarm_sound_states():
    g_alarm_sound_states.clear()


def save_state_for_playing_alarm_sounds(row):
    if not config.enable_sounds or not config.sounds:
        return

    # TODO: Move this to a generic place. What about -1?
    host_state_map = { 0: "up", 1: "down", 2: "unreachable"}
    service_state_map = { 0: "up", 1: "warning", 2: "critical", 3: "unknown"}

    for state_map, state in [
            (host_state_map, row.get("host_hard_state", row.get("host_state"))),
            (service_state_map, row.get("service_last_hard_state", row.get("service_state"))) ]:
        if state is None:
            continue

        try:
            state_name = state_map[int(state)]
        except KeyError:
            continue

        g_alarm_sound_states.add(state_name)


def play_alarm_sounds():
    if not config.enable_sounds or not config.sounds:
        return

    url = config.sound_url
    if not url.endswith("/"):
        url += "/"

    for state_name, wav in config.sounds:
        if not state_name or state_name in g_alarm_sound_states:
            html.play_sound(url + wav)
            break # only one sound at one time


# How many data rows may the user query?
def get_limit():
    limitvar = html.var("limit", "soft")
    if limitvar == "hard" and config.user.may("general.ignore_soft_limit"):
        return config.hard_query_limit
    elif limitvar == "none" and config.user.may("general.ignore_hard_limit"):
        return None
    else:
        return config.soft_query_limit

def view_optiondial(view, option, choices, help):
    # Darn: The option "refresh" has the name "browser_reload" in the
    # view definition
    if option == "refresh":
        name = "browser_reload"
    else:
        name = option

    # Take either the first option of the choices, the view value or the
    # configured painter option.
    value = painter_options.get(option, dflt=view.get(name, choices[0][0]))

    title = dict(choices).get(value, value)
    html.begin_context_buttons() # just to be sure
    # Remove unicode strings
    choices = [ [c[0], str(c[1])] for c in choices ]
    html.open_div(id_="optiondial_%s" % option,
                  class_=["optiondial", option, "val_%s" % value],
                  title=help,
                  onclick="view_dial_option(this, \'%s\', \'%s\', %r)"
                                   % (view["name"], option, choices))
    html.div(title)
    html.close_div()
    html.final_javascript("init_optiondial('optiondial_%s');" % option)

def view_optiondial_off(option):
    html.div('', class_=["optiondial", "off", option])


# Will be called when the user presses the upper button, in order
# to persist the new setting - and to make it active before the
# browser reload of the DIV containing the actual status data is done.
@cmk.gui.pages.register("ajax_set_viewoption")
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

    po = PainterOptions()
    po.load(view_name)
    po.set(option, value)
    po.save_to_config(view_name)


def show_context_links(thisview, datasource, show_filters,
                       enable_commands, enable_checkboxes, show_checkboxes,
                       show_availability, show_combined_graphs):
    if html.output_format != "html":
        return

    html.begin_context_buttons()

    # That way if no button is painted we avoid the empty container
    if display_options.enabled(display_options.B):
        execute_hooks('buttons-begin')


    ## Small buttons
    html.open_div(class_="context_buttons_small")
    filter_isopen = html.var("filled_in") != "filter" and thisview.get("mustsearch")
    if display_options.enabled(display_options.F):
        if html.var("filled_in") == "filter":
            icon = "filters_set"
            help = _("The current data is being filtered")
        else:
            icon = "filters"
            help = _("Set a filter for refining the shown data")
        html.toggle_button("filters", filter_isopen, icon, help, disabled=not show_filters)

    if display_options.enabled(display_options.D):
        html.toggle_button("painteroptions", False, "painteroptions", _("Modify display options"),
                     disabled=not painter_options.painter_option_form_enabled())

    if display_options.enabled(display_options.C):
        html.toggle_button("commands", False, "commands", _("Execute commands on hosts, services and other objects"),
                     hidden = not enable_commands)
        html.toggle_button("commands", False, "commands", "", hidden=enable_commands, disabled=True)

        selection_enabled = enable_checkboxes if enable_commands else thisview.get('force_checkboxes')
        if not thisview.get("force_checkboxes"):
            html.toggle_button(
                id="checkbox",
                icon="checkbox",
                help=_("Enable/Disable checkboxes for selecting rows for commands"),
                onclick="location.href='%s';" % html.makeuri([('show_checkboxes', show_checkboxes and '0' or '1')]),
                isopen=show_checkboxes,
                hidden=True,
            )
        html.toggle_button("checkbox", False, "checkbox", "", hidden=not thisview.get("force_checkboxes"), disabled=True)
        html.javascript('g_selection_enabled = %s;' % ('true' if selection_enabled else 'false'))

    if display_options.enabled(display_options.O):
        if config.user.may("general.view_option_columns"):
            choices = [ [x, "%s" % x] for x in config.view_option_columns ]
            view_optiondial(thisview, "num_columns", choices, _("Change the number of display columns"))
        else:
            view_optiondial_off("num_columns")

        if display_options.enabled(display_options.R) and config.user.may("general.view_option_refresh"):
            choices = [ [x, {0:_("off")}.get(x, str(x) + "s") ] for x in config.view_option_refreshes ]
            view_optiondial(thisview, "refresh", choices, _("Change the refresh rate"))
        else:
            view_optiondial_off("refresh")
    html.close_div()

    ## Large buttons
    if display_options.enabled(display_options.B):
        import cmk.gui.watolib as watolib
        # WATO: If we have a host context, then show button to WATO, if permissions allow this
        if html.has_var("host") \
           and config.wato_enabled \
           and config.user.may("wato.use") \
           and (config.user.may("wato.hosts") or config.user.may("wato.seeall")):
            host = html.var("host")
            if host:
                url = watolib.link_to_host_by_name(host)
            else:
                url = watolib.link_to_folder_by_path(html.var("wato_folder", ""))
            html.context_button(_("WATO"), url, "wato", id="wato",
                bestof = config.context_buttons_to_show)

        # Button for creating an instant report (if reporting is available)
        if config.reporting_available() and config.user.may("general.reporting"):
            html.context_button(_("Export as PDF"), html.makeuri([], filename="report_instant.py"),
                                "report", class_="context_pdf_export")

        # Buttons to other views, dashboards, etc.
        links = visuals.collect_context_links(thisview)
        for linktitle, uri, icon, buttonid in links:
            html.context_button(linktitle, url=uri, icon=icon, id=buttonid, bestof=config.context_buttons_to_show)

    # Customize/Edit view button
    if display_options.enabled(display_options.E) and config.user.may("general.edit_views"):
        url_vars = [
            ("back", html.request.requested_url),
            ("load_name", thisview["name"]),
        ]

        if thisview["owner"] != config.user.id:
            url_vars.append(("load_user", thisview["owner"]))

        url = html.makeuri_contextless(url_vars, filename="edit_view.py")
        html.context_button(_("Edit View"), url, "edit", id="edit", bestof=config.context_buttons_to_show)

    if display_options.enabled(display_options.E):
        if show_availability:
            html.context_button(_("Availability"), html.makeuri([("mode", "availability")]), "availability")
        if show_combined_graphs and config.combined_graphs_available():
            html.context_button(_("Combined graphs"),
                                html.makeuri([
                                    ("single_infos", ",".join(thisview["single_infos"])),
                                    ("datasource", thisview["datasource"]),
                                    ("view_title", view_title(thisview)),
                                ],
                                filename="combined_graphs.py"), "pnp")


    if display_options.enabled(display_options.B):
        execute_hooks('buttons-end')

    html.end_context_buttons()


def update_context_links(enable_command_toggle, enable_checkbox_toggle):
    html.javascript("update_togglebutton('commands', %d);" % (enable_command_toggle and 1 or 0))
    html.javascript("update_togglebutton('checkbox', %d);" % (enable_command_toggle and enable_checkbox_toggle and 1 or 0, ))


@cmk.gui.pages.register("count_context_button")
def ajax_count_button():
    id = html.var("id")
    counts = config.user.load_file("buttoncounts", {})
    for i in counts:
        counts[i] *= 0.95
    counts.setdefault(id, 0)
    counts[id] += 1
    config.user.save_file("buttoncounts", counts)


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
        negate = -1 if s[1] else 1
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
            if c != 0:
                return c
        return 0 # equal

    data.sort(multisort)


def sorters_of_datasource(ds_name):
    return allowed_for_datasource(multisite_sorters, ds_name)


def painters_of_datasource(ds_name):
    return allowed_for_datasource(multisite_painters, ds_name)


def join_painters_of_datasource(ds_name):
    ds = multisite_datasources[ds_name]
    if "join" not in ds:
        return {} # no joining with this datasource

    # Get the painters allowed for the join "source" and "target"
    painters = painters_of_datasource(ds_name)
    join_painters_unfiltered = allowed_for_datasource(multisite_painters, ds['join'][0])

    # Filter out painters associated with the "join source" datasource
    join_painters = {}
    for key, val in join_painters_unfiltered.items():
        if key not in painters:
            join_painters[key] = val

    return join_painters


# Filters a list of sorters or painters and decides which of
# those are available for a certain data source
def allowed_for_datasource(collection, datasourcename):
    datasource = multisite_datasources[datasourcename]
    infos_available = set(datasource["infos"])
    add_columns = datasource.get("add_columns", [])

    allowed = {}
    for name, item in collection.items():
        infos_needed = infos_needed_by_painter(item, add_columns)
        if len(infos_needed.difference(infos_available)) == 0:
            allowed[name] = item
    return allowed


def infos_needed_by_painter(painter, add_columns=None):
    if add_columns is None:
        add_columns = []

    columns = get_painter_columns(painter)
    return set([ c.split("_", 1)[0] for c in columns if c != "site" and c not in add_columns])


def painter_choices(painters, add_params=False):
    choices = []

    for name, painter in painters.items():
        title = get_painter_title_for_choices(painter)

        # Add the optional valuespec for painter parameters
        if add_params and "params" in painter:
            vs_params = get_painter_params_valuespec(painter)
            choices.append((name, title, vs_params))
        else:
            choices.append((name, title))

    return sorted(choices, key=lambda x: x[1])


def get_painter_title_for_choices(painter):
    info_title = "/".join([ visuals.infos[info_name]["title_plural"] for info_name
                            in sorted(infos_needed_by_painter(painter)) ])

    # TODO: Cleanup the special case for sites. How? Add an info for it?
    if painter["columns"] == ["site"]:
        info_title = _("Site")

    if type(painter["title"]) in [types.FunctionType, types.MethodType]:
        title = painter["title"]()
    else:
        title = painter["title"]

    return "%s: %s" % (info_title, title)


def painter_choices_with_params(painters):
    return painter_choices(painters, add_params=True)

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

# Checks whether or not this view handles commands for the current user
# When it does not handle commands the command tab, command form, row
# selection and processing commands is disabled.
def should_show_command_form(datasource, ignore_display_option=False):
    if not ignore_display_option and display_options.disabled(display_options.C):
        return False
    if not config.user.may("general.act"):
        return False

    # What commands are available depends on the Livestatus table we
    # deal with. If a data source provides information about more
    # than one table, (like services datasource also provide host
    # information) then the first info is the primary table. So 'what'
    # will be one of "host", "service", "command" or "downtime".
    what = datasource["infos"][0]
    for command in multisite_commands:
        if what in command["tables"] and config.user.may(command["permission"]):
            return True

    return False

def show_command_form(is_open, datasource):
    # What commands are available depends on the Livestatus table we
    # deal with. If a data source provides information about more
    # than one table, (like services datasource also provide host
    # information) then the first info is the primary table. So 'what'
    # will be one of "host", "service", "command" or "downtime".
    what = datasource["infos"][0]

    html.open_div(id_="commands",
                  class_=["view_form"],
                  style="display:none;" if not is_open else None)
    html.begin_form("actions")
    html.hidden_field("_do_actions", "yes")
    html.hidden_field("actions", "yes")
    html.hidden_fields() # set all current variables, exception action vars

    # Show command forms, grouped by (optional) command group
    by_group = {}
    for command in multisite_commands:
        if what in command["tables"] and config.user.may(command["permission"]):
            # Some special commands can be shown on special views using this option.
            # It is currently only used in custom views, not shipped with check_mk.
            if command.get('only_view') and html.var('view_name') != command['only_view']:
                continue
            group = command.get("group", "various")
            by_group.setdefault(group, []).append(command)

    for group_ident, group_commands in sorted(by_group.items(),
                                    key=lambda x: multisite_command_groups[x[0]]["sort_index"]):
        forms.header(multisite_command_groups[group_ident]["title"], narrow=True)
        for command in group_commands:
            forms.section(command["title"])
            command["render"]()

    forms.end()
    html.end_form()
    html.close_div()

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
    elif what == "service":
        spec = "%s;%s" % (host, descr)
        cmdtag = "SVC"
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
        if config.user.may(cmd["permission"]):

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
    sites.live().command("[%d] %s" % (int(time.time()), command), site)

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
    if not config.user.may("general.act"):
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
            site = row.get("site") # site is missing for BI rows (aggregations can spawn several sites)
            if (site, command_entry) not in already_executed:
                # Some command functions return the information about the site per-command (e.g. for BI)
                if type(command_entry) == tuple:
                    site, command = command_entry
                else:
                    command = command_entry

                if type(command) == unicode:
                    command = command.encode("utf-8")

                executor(command, site)
                already_executed.add((site, command_entry))
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
            if html.var("_show_result") == "0":
                html.immediate_browser_redirect(0.5, backurl)
        html.message(message)

    return True


def filter_by_row_id(view, rows):
    wanted_row_id = html.var("_row_id")

    for row in rows:
        if row_id(view, row) == wanted_row_id:
            return [row]
    return []


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


@cmk.gui.pages.register("export_views")
def ajax_export():
    load_views()
    for view in available_views.itervalues():
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

def docu_link(topic, text):
    return '<a href="%s" target="_blank">%s</a>' % (config.doculink_urlformat % topic, text)

#.
#   .--Icon Selector-------------------------------------------------------.
#   |      ___                  ____       _           _                   |
#   |     |_ _|___ ___  _ __   / ___|  ___| | ___  ___| |_ ___  _ __       |
#   |      | |/ __/ _ \| '_ \  \___ \ / _ \ |/ _ \/ __| __/ _ \| '__|      |
#   |      | | (_| (_) | | | |  ___) |  __/ |  __/ (__| || (_) | |         |
#   |     |___\___\___/|_| |_| |____/ \___|_|\___|\___|\__\___/|_|         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | AJAX API call for rendering the icon selector                        |
#   '----------------------------------------------------------------------'

@cmk.gui.pages.register("ajax_popup_icon_selector")
def ajax_popup_icon_selector():
    varprefix   = html.var('varprefix')
    value       = html.var('value')
    allow_empty = html.var('allow_empty') == '1'

    vs = IconSelector(allow_empty=allow_empty)
    vs.render_popup_input(varprefix, value)

#.
#   .--Action Menu---------------------------------------------------------.
#   |          _        _   _               __  __                         |
#   |         / \   ___| |_(_) ___  _ __   |  \/  | ___ _ __  _   _        |
#   |        / _ \ / __| __| |/ _ \| '_ \  | |\/| |/ _ \ '_ \| | | |       |
#   |       / ___ \ (__| |_| | (_) | | | | | |  | |  __/ | | | |_| |       |
#   |      /_/   \_\___|\__|_|\___/|_| |_| |_|  |_|\___|_| |_|\__,_|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Realizes the popup action menu for hosts/services in views           |
#   '----------------------------------------------------------------------'

def query_action_data(what, host, site, svcdesc):
    # Now fetch the needed data from livestatus
    columns = list(iconpainter_columns(what, toplevel=False))
    try:
        columns.remove('site')
    except KeyError:
        pass

    if site:
        sites.live().set_only_sites([site])
    sites.live().set_prepend_site(True)
    query = 'GET %ss\n' \
            'Columns: %s\n' \
            'Filter: host_name = %s\n' \
           % (what, ' '.join(columns), host)
    if what == 'service':
        query += 'Filter: service_description = %s\n' % svcdesc
    row = sites.live().query_row(query)

    sites.live().set_prepend_site(False)
    sites.live().set_only_sites(None)

    return dict(zip(['site'] + columns, row))


@cmk.gui.pages.register("ajax_popup_action_menu")
def ajax_popup_action_menu():
    site    = html.var('site')
    host    = html.var('host')
    svcdesc = html.var('service')
    what    = 'service' if svcdesc else 'host'

    display_options.load_from_html()

    row = query_action_data(what, host, site, svcdesc)
    icons = get_icons(what, row, toplevel=False)

    html.open_ul()
    for icon in icons:
        if len(icon) != 4:
            html.open_li()
            html.write(icon[1])
            html.close_li()
        else:
            html.open_li()
            icon_name, title, url_spec = icon[1:]

            if url_spec:
                url, target_frame = transform_action_url(url_spec)
                url = replace_action_url_macros(url, what, row)
                onclick = None
                if url.startswith('onclick:'):
                    onclick = url[8:]
                    url = 'javascript:void(0);'
                target = None
                if target_frame and target_frame != "_self":
                    target = target_frame
                html.open_a(href=url, target=target, onclick=onclick)

            html.icon('', icon_name)
            if title:
                html.write(title)
            else:
                html.write_text(_("No title"))
            if url_spec:
                html.close_a()
            html.close_li()
    html.close_ul()


#.
#   .--Reschedule----------------------------------------------------------.
#   |          ____                _              _       _                |
#   |         |  _ \ ___  ___  ___| |__   ___  __| |_   _| | ___           |
#   |         | |_) / _ \/ __|/ __| '_ \ / _ \/ _` | | | | |/ _ \          |
#   |         |  _ <  __/\__ \ (__| | | |  __/ (_| | |_| | |  __/          |
#   |         |_| \_\___||___/\___|_| |_|\___|\__,_|\__,_|_|\___|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Ajax webservice for reschedulung host- and service checks            |
#   '----------------------------------------------------------------------'

@cmk.gui.pages.register("ajax_reschedule")
def ajax_reschedule():
    try:
        do_reschedule()
    except Exception, e:
        html.write("['ERROR', '%s']\n" % e)


def do_reschedule():
    if not config.user.may("action.reschedule"):
        raise MKGeneralException("You are not allowed to reschedule checks.")

    site = html.var("site")
    host = html.var("host", "")
    if not host:
        raise MKGeneralException("Action reschedule: missing host name")

    service  = html.get_unicode_input("service",  "")
    wait_svc = html.get_unicode_input("wait_svc", "")

    if service:
        cmd = "SVC"
        what = "service"
        spec = "%s;%s" % (host, service.encode("utf-8"))

        if wait_svc:
            wait_spec = u'%s;%s' % (host, wait_svc)
            add_filter = "Filter: service_description = %s\n" % livestatus.lqencode(wait_svc)
        else:
            wait_spec = spec
            add_filter = "Filter: service_description = %s\n" % livestatus.lqencode(service)
    else:
        cmd = "HOST"
        what = "host"
        spec = host
        wait_spec = spec
        add_filter = ""

    try:
        now = int(time.time())
        sites.live().command("[%d] SCHEDULE_FORCED_%s_CHECK;%s;%d" % (now, cmd, livestatus.lqencode(spec), now), site)
        sites.live().set_only_sites([site])
        query = u"GET %ss\n" \
                "WaitObject: %s\n" \
                "WaitCondition: last_check >= %d\n" \
                "WaitTimeout: %d\n" \
                "WaitTrigger: check\n" \
                "Columns: last_check state plugin_output\n" \
                "Filter: host_name = %s\n%s" \
                % (what, livestatus.lqencode(wait_spec), now, config.reschedule_timeout * 1000, livestatus.lqencode(host), add_filter)
        row = sites.live().query_row(query)
        sites.live().set_only_sites()
        last_check = row[0]
        if last_check < now:
            html.write("['TIMEOUT', 'Check not executed within %d seconds']\n" % (config.reschedule_timeout))
        else:
            if service == "Check_MK":
                # Passive services triggered by Check_MK often are updated
                # a few ms later. We introduce a small wait time in order
                # to increase the chance for the passive services already
                # updated also when we return.
                time.sleep(0.7)
            html.write("['OK', %d, %d, %r]\n" % (row[0], row[1], row[2].encode("utf-8")))

    except Exception, e:
        sites.live().set_only_sites()
        raise MKGeneralException(_("Cannot reschedule check: %s") % e)
