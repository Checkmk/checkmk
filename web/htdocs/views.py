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

import config, time, os, re, pprint
import weblib, traceback, forms, valuespec, inventory, visuals, metrics
import sites
import bi
import inspect
from lib import *

import cmk.paths

# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False
display_options      = None

# Load all view plugins
def load_plugins(force):
    global loaded_with_language

    if loaded_with_language == current_language and not force:
        # always reload the hosttag painters, because new hosttags might have been
        # added during runtime
        load_host_tag_painters()
        clear_alarm_sound_states()
        return

    global multisite_datasources     ; multisite_datasources      = {}
    global multisite_layouts         ; multisite_layouts          = {}
    global multisite_painters        ; multisite_painters         = {}
    global multisite_sorters         ; multisite_sorters          = {}
    global multisite_builtin_views   ; multisite_builtin_views    = {}
    global multisite_painter_options ; multisite_painter_options  = {}
    global multisite_commands        ; multisite_commands         = []
    global multisite_command_groups  ; multisite_command_groups   = {}
    global view_hooks                ; view_hooks                 = {}
    global inventory_displayhints    ; inventory_displayhints     = {}

    config.declare_permission_section("action", _("Commands on host and services"), do_sort = True)

    load_web_plugins("views", globals())
    load_host_tag_painters()
    clear_alarm_sound_states()

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = current_language

    # Declare permissions for builtin views
    config.declare_permission_section("view", _("Multisite Views"), do_sort = True)
    for name, view in multisite_builtin_views.items():
        config.declare_permission("view.%s" % name,
                format_view_title(name, view),
                "%s - %s" % (name, _u(view["description"])),
                config.builtin_role_ids)

    # Make sure that custom views also have permissions
    config.declare_dynamic_permissions(lambda: visuals.declare_custom_permissions('views'))

    declare_inventory_columns()


# Load all views - users or builtins
def load_views():
    global multisite_views, available_views
    # Skip views which do not belong to known datasources
    multisite_views = visuals.load('views', multisite_builtin_views,
                    skip_func = lambda v: v['datasource'] not in multisite_datasources)
    available_views = visuals.available('views', multisite_views)
    transform_old_views()

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
                elif 'aggr_group' in hide_filters:
                    view['single_infos'] = ['aggr_group']
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


# For each view a function can be registered that has to return either True
# or False to show a view as context link
view_is_enabled = {}

def is_enabled_for(linking_view, view, context_vars):
    if view["name"] not in view_is_enabled:
        return True # Not registered are always visible!

    return view_is_enabled[view["name"]](linking_view, view, context_vars)

#.
#   .--PainterOptions------------------------------------------------------.
#   |  ____       _       _             ___        _   _                   |
#   | |  _ \ __ _(_)_ __ | |_ ___ _ __ / _ \ _ __ | |_(_) ___  _ __  ___   |
#   | | |_) / _` | | '_ \| __/ _ \ '__| | | | '_ \| __| |/ _ \| '_ \/ __|  |
#   | |  __/ (_| | | | | | ||  __/ |  | |_| | |_) | |_| | (_) | | | \__ \  |
#   | |_|   \__,_|_|_| |_|\__\___|_|   \___/| .__/ \__|_|\___/|_| |_|___/  |
#   |                                       |_|                            |
#   +----------------------------------------------------------------------+
#   | Painter options are settings that can be changed per user per view.  |
#   | These options are controlled throught the painter options form which |
#   | is accessible through the small monitor icon on the top left of the  |
#   | views.                                                               |
#   '----------------------------------------------------------------------'

# TODO: Better name it PainterOptions or DisplayOptions? There are options which only affect
# painters, but some which affect generic behaviour of the views, so DisplayOptions might
# be better.
class PainterOptions(object):
    def __init__(self, view_name=None):
        self._view_name         = view_name
        # The names of the painter options used by the current view
        self._used_option_names = None
        # The effective options for this view
        self._options           = {}


    def load(self):
        self._load_from_config()


    # Load the options to be used for this view
    def _load_used_options(self, view):
        if self._used_option_names != None:
            return # only load once per request

        options = set([])

        for cell in get_group_cells(view) + get_cells(view):
            options.update(cell.painter_options())

        # Also layouts can register painter options
        layout_name = view.get("layout")
        if layout_name != None:
            options.update(multisite_layouts[layout_name].get("options", []))

        # TODO: Improve sorting. Add a sort index?
        self._used_option_names = sorted(options)


    def _load_from_config(self):
        if self._is_anonymous_view():
            return # never has options

        if not self.painter_options_permitted():
            return

        # Options are stored per view. Get all options for all views
        vo = config.user.load_file("viewoptions", {})
        self._options = vo.get(self._view_name, {})


    def save_to_config(self):
        vo = config.user.load_file("viewoptions", {}, lock=True)
        vo[self._view_name] = self._options
        config.user.save_file("viewoptions", vo)


    def update_from_url(self, view):
        self._load_used_options(view)

        if not self.painter_option_form_enabled():
            return

        if html.has_var("_reset_painter_options"):
            self._clear_painter_options()
            return

        elif html.has_var("_update_painter_options"):
            self._set_from_submitted_form()


    def _set_from_submitted_form(self):
        # TODO: Remove all keys that are in multisite_painter_options
        # but not in self._used_option_names

        modified = False
        for option_name in self._used_option_names:
            # Get new value for the option from the value spec
            vs = self.get_valuespec_of(option_name)
            value = vs.from_html_vars("po_%s" % option_name)

            if not self._is_set(option_name) or self.get(option_name) != value:
                modified = True

            self.set(option_name, value)

        if modified:
            self.save_to_config()


    def _clear_painter_options(self):
        # TODO: This never removes options that are not existant anymore
        modified = False
        for name in multisite_painter_options.keys():
            try:
                del self._options[name]
                modified = True
            except KeyError:
                pass

        if modified:
            self.save_to_config()

        # Also remove the options from current html vars. Otherwise the
        # painter option form will display the just removed options as
        # defaults of the painter option form.
        for varname in html.all_varnames_with_prefix("po_"):
            html.del_var(varname)


    def get_valuespec_of(self, name):
        opt = multisite_painter_options[name]
        if type(lambda: None) == type(opt["valuespec"]):
            return opt["valuespec"]()
        else:
            return opt["valuespec"]


    def _is_set(self, name):
        return name in self._options


    # Sets a painter option value (only for this request). Is not persisted!
    def set(self, name, value):
        self._options[name] = value


    # Returns either the set value, the provided default value or if none
    # provided, it returns the default value of the valuespec.
    def get(self, name, dflt=None):
        if dflt == None:
            try:
                dflt = self.get_valuespec_of(name).default_value()
            except KeyError:
                # Some view options (that are not declared as display options)
                # like "refresh" don't have a valuespec. So they need to default
                # to None.
                # TODO: Find all occurences and simply declare them as "invisible"
                # painter options.
                pass
        return self._options.get(name, dflt)


    # Not falling back to a default value, simply returning None in case
    # the option is not set.
    def get_without_default(self, name):
        return self._options.get(name)


    def get_all(self):
        return self._options


    def _is_anonymous_view(self):
        return self._view_name == None


    def painter_options_permitted(self):
        return config.user.may("general.painter_options")


    def painter_option_form_enabled(self):
        return self._used_option_names and self.painter_options_permitted()


    def show_form(self, view):
        self._load_used_options(view)

        if not display_options.enabled(display_options.D) or not self.painter_option_form_enabled():
            return

        html.open_div(id_="painteroptions", class_=["view_form"], style="display: none;")
        html.begin_form("painteroptions")
        forms.header(_("Display Options"))
        for name in self._used_option_names:
            vs = self.get_valuespec_of(name)
            forms.section(vs.title())
            # TODO: Possible improvement for vars which default is specified
            # by the view: Don't just default to the valuespecs default. Better
            # use the view default value here to get the user the current view
            # settings reflected.
            vs.render_input("po_%s" % name, self.get(name))
        forms.end()

        html.button("_update_painter_options", _("Submit"), "submit")
        html.button("_reset_painter_options", _("Reset"), "submit")

        html.hidden_fields()
        html.end_form()
        html.close_div()



def prepare_painter_options(view_name=None):
    global painter_options
    painter_options = PainterOptions(view_name)
    painter_options.load()


#.
#   .--Cells---------------------------------------------------------------.
#   |                           ____     _ _                               |
#   |                          / ___|___| | |___                           |
#   |                         | |   / _ \ | / __|                          |
#   |                         | |__|  __/ | \__ \                          |
#   |                          \____\___|_|_|___/                          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | View cell handling classes. Each cell instanciates a multisite       |
#   | painter to render a table cell.                                      |
#   '----------------------------------------------------------------------'

# A cell is an instance of a painter in a view (-> a cell or a grouping cell)
class Cell(object):
    # Wanted to have the "parse painter spec logic" in one place (The Cell() class)
    # but this should be cleaned up more. TODO: Move this to another place
    @staticmethod
    def painter_exists(painter_spec):
        if type(painter_spec[0]) == tuple:
            painter_name = painter_spec[0][0]
        else:
            painter_name = painter_spec[0]

        return painter_name in multisite_painters


    # Wanted to have the "parse painter spec logic" in one place (The Cell() class)
    # but this should be cleaned up more. TODO: Move this to another place
    @staticmethod
    def is_join_cell(painter_spec):
        return len(painter_spec) >= 4


    def __init__(self, view, painter_spec=None):
        self._view               = view
        self._painter_name       = None
        self._painter_params     = None
        self._link_view_name     = None
        self._tooltip_painter_name = None

        if painter_spec:
            self._from_view(painter_spec)

    # In views the painters are saved as tuples of the following formats:
    #
    # Painter name, Link view name
    # ('service_discovery_service', None),
    #
    # Painter name,  Link view name, Hover painter name
    # ('host_plugin_output', None, None),
    #
    # Join column: Painter name, Link view name, hover painter name, Join service description
    # ('service_description', None, None, u'CPU load')
    #
    # Join column: Painter name, Link view name, hover painter name, Join service description, custom title
    # ('service_description', None, None, u'CPU load')
    #
    # Parameterized painters:
    # Same as above but instead of the "Painter name" a two element tuple with the painter name as
    # first element and a dictionary of parameters as second element is set.
    def _from_view(self, painter_spec):
        if type(painter_spec[0]) == tuple:
            self._painter_name, self._painter_params = painter_spec[0]
        else:
            self._painter_name = painter_spec[0]

        if painter_spec[1] != None:
            self._link_view_name = painter_spec[1]

        # Clean this call to Cell.painter_exists() up!
        if len(painter_spec) >= 3 and Cell.painter_exists((painter_spec[2], None)):
            self._tooltip_painter_name = painter_spec[2]


    # Get a list of columns we need to fetch in order to render this cell
    def needed_columns(self):
        columns = set(get_painter_columns(self.painter()))

        if self._link_view_name:
            # Make sure that the information about the available views is present. If
            # called via the reporting, then this might not be the case
            # TODO: Move this to some better place.
            views = permitted_views()

            if self._has_link():
                link_view = self._link_view()
                if link_view:
                    # TODO: Clean this up here
                    for filt in [ visuals.get_filter(fn) for fn in visuals.get_single_info_keys(link_view) ]:
                        columns.update(filt.link_columns)

        if self.has_tooltip():
            columns.update(get_painter_columns(self.tooltip_painter()))

        return columns


    def is_joined(self):
        return False


    def join_service(self):
        return None


    def _has_link(self):
        return self._link_view_name != None


    def _link_view(self):
        try:
            return get_view_by_name(self._link_view_name)
        except KeyError:
            return None


    def painter(self):
        return multisite_painters[self._painter_name]


    def painter_name(self):
        return self._painter_name


    def export_title(self):
        return self._painter_name


    def painter_options(self):
        return self.painter().get("options", [])


    # The parameters configured in the view for this painter. In case the
    # painter has params, it defaults to the valuespec default value and
    # in case the painter has no params, it returns None.
    def painter_parameters(self):
        vs_painter_params = get_painter_params_valuespec(self.painter())
        if not vs_painter_params:
            return

        if vs_painter_params and self._painter_params == None:
            return vs_painter_params.default_value()
        else:
            return self._painter_params


    def title(self, use_short=True):
        painter = self.painter()
        if use_short:
            return self._get_short_title(painter)
        else:
            return self._get_long_title(painter)


    def _get_short_title(self, painter):
        if type(painter.get("short")) in [types.FunctionType, types.MethodType]:
            return painter["short"](self.painter_parameters())
        else:
            return painter.get("short", self._get_long_title(painter))


    def _get_long_title(self, painter):
        if type(painter.get("title")) in [types.FunctionType, types.MethodType]:
            return painter["title"](self.painter_parameters())
        else:
            return painter["title"]


    # Can either be:
    # True       : Is printable in PDF
    # False      : Is not printable at all
    # "<string>" : ID of a painter_printer (Reporting module)
    def printable(self):
        return self.painter().get("printable", True)


    def has_tooltip(self):
        return self._tooltip_painter_name != None


    def tooltip_painter_name(self):
        return self._tooltip_painter_name


    def tooltip_painter(self):
        return multisite_painters[self._tooltip_painter_name]


    def paint_as_header(self, is_last_column_header=False):
        # Optional: Sort link in title cell
        # Use explicit defined sorter or implicit the sorter with the painter name
        # Important for links:
        # - Add the display options (Keeping the same display options as current)
        # - Link to _self (Always link to the current frame)
        classes = []
        onclick = ''
        title = ''
        if display_options.enabled(display_options.L) \
           and self._view.get('user_sortable', False) \
           and get_sorter_name_of_painter(self.painter_name()) is not None:
            params = [
                ('sort', self._sort_url()),
            ]
            if display_options.title_options:
                params.append(('display_options', display_options.title_options))

            classes += [ "sort", get_primary_sorter_order(self._view, self.painter_name()) ]
            onclick = "location.href=\'%s\'" % html.makeuri(params, 'sort')
            title   = _('Sort by %s') % self.title()

        if is_last_column_header:
            classes.append("last_col")

        html.open_th(class_=classes, onclick=onclick, title=title)
        html.write(self.title())
        html.close_th()
        #html.guitest_record_output("view", ("header", title))


    def _sort_url(self):
        """
        The following sorters need to be handled in this order:

        1. group by sorter (needed in grouped views)
        2. user defined sorters (url sorter)
        3. configured view sorters
        """
        sorter = []

        group_sort, user_sort, view_sort = get_separated_sorters(self._view)

        sorter = group_sort + user_sort + view_sort

        # Now apply the sorter of the current column:
        # - Negate/Disable when at first position
        # - Move to the first position when already in sorters
        # - Add in the front of the user sorters when not set
        sorter_name = get_sorter_name_of_painter(self.painter_name())
        if self.is_joined():
            # TODO: Clean this up and then remove Cell.join_service()
            this_asc_sorter  = (sorter_name, False, self.join_service())
            this_desc_sorter = (sorter_name, True, self.join_service())
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



    def render(self, row):
        row = join_row(row, self)

        try:
            tdclass, content = self.render_content(row)
        except:
            log_exception("Failed to render painter '%s' (Row: %r)" %
                                        (self._painter_name, row))
            raise

        if tdclass == None:
            tdclass = ""

        if tdclass == "" and content == "":
            return "", ""

        # Add the optional link to another view
        if content and self._has_link():
            content = link_to_view(content, row, self._link_view_name)

        # Add the optional mouseover tooltip
        if content and self.has_tooltip():
            tooltip_cell = Cell(self._view, (self.tooltip_painter_name(), None))
            tooltip_tdclass, tooltip_content = tooltip_cell.render_content(row)
            tooltip_text = html.strip_tags(tooltip_content)
            content = '<span title="%s">%s</span>' % (tooltip_text, content)

        return tdclass, content


    # Same as self.render() for HTML output: Gets a painter and a data
    # row and creates the text for being painted.
    def render_for_pdf(self, row, time_range):
        # TODO: Move this somewhere else!
        def find_htdocs_image_path(filename):
            dirs = [
                cmk.paths.local_web_dir + "/htdocs/",
                cmk.paths.web_dir + "/htdocs/",
            ]
            for d in dirs:
                if os.path.exists(d + filename):
                    return d + filename

        try:
            row = join_row(row, self)
            css_classes, txt = self.render_content(row)
            if txt is None:
                return css_classes, ""
            txt = txt.strip()

            # Handle <img...>. Our PDF writer cannot draw arbitrary
            # images, but all that we need for showing simple icons.
            # Current limitation: *one* image
            if txt.lower().startswith("<img"):
                img_filename = re.sub('.*src=["\']([^\'"]*)["\'].*', "\\1", str(txt))
                img_path = find_htdocs_image_path(img_filename)
                if img_path:
                    txt = ("icon", img_path)
                else:
                    txt = img_filename

            if isinstance(txt, HTML):
                txt = html.strip_tags("%s" % txt)

            elif not isinstance(txt, tuple):
                txt = html.escaper.unescape_attributes(txt)
                txt = html.strip_tags(txt)

            return css_classes, txt
        except Exception:
            raise MKGeneralException('Failed to paint "%s": %s' %
                                    (self.painter_name(), traceback.format_exc()))



    def render_content(self, row):
        if not row:
            return "", "" # nothing to paint


        painter = self.painter()
        paint_func = painter["paint"]

        # Painters can request to get the cell object handed over.
        # Detect that and give the painter this argument.
        arg_names = inspect.getargspec(paint_func)[0]
        painter_args = []
        for arg_name in arg_names:
            if arg_name == "row":
                painter_args.append(row)
            elif arg_name == "cell":
                painter_args.append(self)

        # Add optional painter arguments from painter specification
        if "args" in painter:
            painter_args += painter["args"]

        return painter["paint"](*painter_args)


    def paint(self, row, tdattrs="", is_last_cell=False):
        tdclass, content = self.render(row)
        has_content = content != ""

        if is_last_cell:
            if tdclass == None:
                tdclass = "last_col"
            else:
                tdclass += " last_col"

        if tdclass:
            html.write("<td %s class=\"%s\">" % (tdattrs, tdclass))
            html.write(content)
            html.close_td()
        else:
            html.write("<td %s>" % (tdattrs))
            html.write(content)
            html.close_td()
        #html.guitest_record_output("view", ("cell", content))

        return has_content



class JoinCell(Cell):
    def __init__(self, view, painter_spec):
        self._join_service_descr = None
        self._custom_title       = None
        super(JoinCell, self).__init__(view, painter_spec)


    def _from_view(self, painter_spec):
        super(JoinCell, self)._from_view(painter_spec)

        if len(painter_spec) >= 4:
            self._join_service_descr = painter_spec[3]

        if len(painter_spec) == 5:
            self._custom_title = painter_spec[4]


    def is_joined(self):
        return True


    def join_service(self):
        return self._join_service_descr


    def livestatus_filter(self, join_column_name):
        return "Filter: %s = %s" % \
            (lqencode(join_column_name), lqencode(self._join_service_descr))


    def title(self, use_short=True):
        if self._custom_title:
            return self._custom_title
        else:
            return self._join_service_descr


    def export_title(self):
        return "%s.%s" % (self._painter_name, self.join_service())




class EmptyCell(Cell):
    def __init__(self, view):
        super(EmptyCell, self).__init__(view)


    def render(self, row):
        return "", ""


    def paint(self, row):
        return False




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
    if not is_allowed_url(back_url):
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
            html.http_redirect(next_url)
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
    )

def view_choices(only_with_hidden = False):
    choices = [("", "")]
    for name, view in available_views.items():
        if not only_with_hidden or view['single_infos']:
            title = format_view_title(name, view)
            choices.append(("%s" % name, title))
    return choices

def format_view_title(name, view):
    title_parts = []

    if view.get('mobile', False):
        title_parts.append(_('Mobile'))

    # Don't use the data source title because it does not really look good here
    datasource = multisite_datasources[view["datasource"]]
    infos = datasource["infos"]
    if "event" in infos:
        title_parts.append(_("Event Console"))
    elif view["datasource"].startswith("inv"):
        title_parts.append(_("HW/SW inventory"))
    elif "aggr" in infos:
        title_parts.append(_("BI"))
    elif "log" in infos:
        title_parts.append(_("Log"))
    elif "service" in infos:
        title_parts.append(_("Services"))
    elif "host" in infos:
        title_parts.append(_("Hosts"))
    elif "hostgroup" in infos:
        title_parts.append(_("Hostgroups"))
    elif "servicegroup" in infos:
        title_parts.append(_("Servicegroups"))

    title_parts.append("%s (%s)" % (_u(view["title"]), name))

    return " - ".join(title_parts)

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
    for key, title in view_editor_options():
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
                for option in dict(view_editor_options()).keys():
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
    for sort_index, title, f in s:
        if f.double_height():
            show_filter(f)

    # Now single height filters
    for sort_index, title, f in s:
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

    prepare_painter_options(view_name)
    painter_options.update_from_url(view)

    show_view(view, True, True, True)


def get_painter_columns(painter):
    if type(lambda: None) == type(painter["columns"]):
        return painter["columns"]()
    else:
        return painter["columns"]


# Display view with real data. This is *the* function everying
# is about.
def show_view(view, show_heading = False, show_buttons = True,
              show_footer = True, render_function = None, only_count=False,
              all_filters_active=False, limit=None):

    weblib.prepare_display_options(globals())

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
    visuals.add_context_to_uri_vars(view, datasource["infos"], only_count)

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

        return render_availability_page(view, datasource, context, filterheaders, only_sites, limit)

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
    regular_cells = get_regular_cells(cells)
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
            import sla
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
        render_bi_availability(view_title(view), rows)
        return


    # TODO: Use livestatus Stats: instead of fetching rows!
    if only_count:
        for fname, filter_vars in view["context"].items():
            for varname, value in filter_vars.items():
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

    # Until now no single byte of HTML code has been output.
    # Now let's render the view. The render_function will be
    # replaced by the mobile interface for an own version.
    if not render_function:
        render_function = render_view

    render_function(view, rows, datasource, group_cells, cells,
                show_heading, show_buttons,
                show_checkboxes, layout, num_columns, show_filters, show_footer,
                browser_reload)


def get_group_cells(view):
    return [ Cell(view, e) for e in view["group_painters"]
             if Cell.painter_exists(e) ]


def get_cells(view):
    cells = []
    for e in view["painters"]:
        if not Cell.painter_exists(e):
            continue

        if Cell.is_join_cell(e):
            cells.append(JoinCell(view, e))

        else:
            cells.append(Cell(view, e))

    return cells


def get_join_cells(cell_list):
    return filter(lambda x: type(x) == JoinCell, cell_list)


def get_regular_cells(cell_list):
    return filter(lambda x: type(x) == Cell, cell_list)


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
            check_limit(rows, get_limit())
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
        for sitename, info in sites.live().dead_sites().items():
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


def check_limit(rows, limit):
    count = len(rows)
    if limit != None and count >= limit + 1:
        text = _("Your query produced more than %d results. ") % limit

        if html.var("limit", "soft") == "soft" and config.user.may("general.ignore_soft_limit"):
            text += html.render_a(_('Repeat query and allow more results.'),
                                  target="_self",
                                  href=html.makeuri([("limit", "hard")]))
        elif html.var("limit") == "hard" and config.user.may("general.ignore_hard_limit"):
            text += html.render_a(_('Repeat query without limit.'),
                                  target="_self",
                                  href=html.makeuri([("limit", "none")]))

        text += " " + _("<b>Note:</b> the shown results are incomplete and do not reflect the sort order.")
        html.show_warning(text)
        del rows[limit:]
        return False
    return True


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

def view_title(view):
    return visuals.visual_title('view', view)

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

# FIXME: Consolidate with html.toggle_button() rendering functions
# TODO: Replace hard coded icon path with dynamic path to old or new theme
def toggler(id, icon, help, onclick, value, hidden = False):
    html.begin_context_buttons() # just to be sure
    hide = ' style="display:none"' if hidden else ''
    html.write('<div id="%s_on" title="%s" class="togglebutton %s %s" %s>'
               '<a href="javascript:void(0)" onclick="%s"><img src="images/icon_%s.png"></a></div>' % (
        id, help, icon, value and "down" or "up", hide, onclick, icon))


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

    po = PainterOptions(view_name)
    po.load()
    po.set(option, value)
    po.save_to_config()


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

        selection_enabled = (enable_commands and enable_checkboxes) or thisview.get("force_checkboxes")
        if not thisview.get("force_checkboxes"):
            toggler("checkbox", "checkbox", _("Enable/Disable checkboxes for selecting rows for commands"),
                    "location.href='%s';" % html.makeuri([('show_checkboxes', show_checkboxes and '0' or '1')]),
                    show_checkboxes, hidden = True) # not selection_enabled)
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
        # WATO: If we have a host context, then show button to WATO, if permissions allow this
        if html.has_var("host") \
           and config.wato_enabled \
           and config.user.may("wato.use") \
           and (config.user.may("wato.hosts") or config.user.may("wato.seeall")):
            host = html.var("host")
            if host:
                url = wato.link_to_host_by_name(host)
            else:
                url = wato.link_to_folder_by_path(html.var("wato_folder", ""))
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
            ("back", html.requested_url()),
            ("load_name", thisview["name"]),
        ]

        if thisview["owner"] != config.user.id:
            url_vars.append(("load_user", thisview["owner"]))

        url = html.makeuri_contextless(url_vars, filename="edit_view.py")
        html.context_button(_("Edit View"), url, "edit", id="edit", bestof=config.context_buttons_to_show)

    if display_options.enabled(display_options.E):
        if show_availability and config.user.may("general.see_availability"):
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


def ajax_count_button():
    id = html.var("id")
    counts = config.user.load_file("buttoncounts", {})
    for i in counts:
        counts[i] *= 0.95
    counts.setdefault(id, 0)
    counts[id] += 1
    config.user.save_file("buttoncounts", counts)


# Retrieve data via livestatus, convert into list of dicts,
# prepare row-function needed for painters
# datasource: the datasource object as defined in plugins/views/datasources.py
# columns: the list of livestatus columns to query
# add_columns: list of columns the datasource is known to add itself
#  (couldn't we get rid of this parameter by looking that up ourselves?)
# add_headers: additional livestatus headers to add
# only_sites: list of sites the query is limited to
# limit: maximum number of data rows to query
def query_data(datasource, columns, add_columns, add_headers,
               only_sites = None, limit = None, tablename=None):
    if only_sites is None:
        only_sites = []

    if tablename == None:
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

    auth_domain = datasource.get("auth_domain", "read")

    # Remove columns which are implicitely added by the datasource
    columns = [ c for c in columns if c not in add_columns ]
    query = "GET %s\n" % tablename
    rows = do_query_data(query, columns, add_columns, merge_column,
                         add_headers, only_sites, limit, auth_domain)

    # Datasource may have optional post processing function to filter out rows
    post_process_func = datasource.get("post_process")
    if post_process_func:
        return post_process_func(rows)
    else:
        return rows


def do_query_data(query, columns, add_columns, merge_column,
                  add_headers, only_sites, limit, auth_domain):
    query += "Columns: %s\n" % " ".join(columns)
    query += add_headers
    sites.live().set_prepend_site(True)

    if limit != None:
        sites.live().set_limit(limit + 1) # + 1: We need to know, if limit is exceeded
    else:
        sites.live().set_limit(None)

    if config.debug_livestatus_queries \
            and html.output_format == "html" and display_options.enabled(display_options.W):
        html.open_div(class_=["livestatus", "message"])
        html.tt(query.replace('\n', '<br>\n'))
        html.close_div()


    if only_sites:
        sites.live().set_only_sites(only_sites)
    sites.live().set_auth_domain(auth_domain)
    data = sites.live().query(query)
    sites.live().set_auth_domain("read")
    sites.live().set_only_sites(None)
    sites.live().set_prepend_site(False)
    sites.live().set_limit() # removes limit

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
            if c != 0: return c
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


# Returns either the valuespec of the painter parameters or None
def get_painter_params_valuespec(painter):
    if "params" not in painter:
        return


#    if type(lambda: None) == type(painter["params"]):
    if isinstance(painter["params"], (types.FunctionType, types.MethodType)):
        return painter["params"]()
    else:
        return painter["params"]


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
            backurl += "&filled_in=filter"
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


def register_command_group(ident, title, sort_index):
    multisite_command_groups[ident] = {
        "title"      : title,
        "sort_index" : sort_index,
    }


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

def join_row(row, cell):
    if type(cell) == JoinCell:
        return row.get("JOIN", {}).get(cell.join_service())
    else:
        return row

# TODO: There is duplicated logic with visuals.collect_context_links_of()
def url_to_view(row, view_name):
    if display_options.disabled(display_options.I):
        return None

    view = permitted_views().get(view_name)
    if view:
        # Get the context type of the view to link to, then get the parameters of this
        # context type and try to construct the context from the data of the row
        url_vars = []
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
                    url_vars += new_vars

        # See get_link_filter_names() comment for details
        for src_key, dst_key in visuals.get_link_filter_names(view, datasource['infos'],
                                                datasource.get('link_filters', {})):
            try:
                url_vars += visuals.get_filter(src_key).variable_settings(row)
            except KeyError:
                pass

            try:
                url_vars += visuals.get_filter(dst_key).variable_settings(row)
            except KeyError:
                pass

        add_site_hint = visuals.may_add_site_hint(view_name, info_keys=datasource["infos"],
                                                  single_info_keys=view["single_infos"], filter_names=dict(url_vars).keys())
        if add_site_hint and row.get('site'):
            url_vars.append(('site', row['site']))

        do = html.var("display_options")
        if do:
            url_vars.append(("display_options", do))

        filename = "mobile_view.py" if html.mobile else "view.py"
        return filename + "?" + html.urlencode_vars([("view_name", view_name)] + url_vars)

def link_to_view(content, row, view_name):
    if display_options.disabled(display_options.I):
        return content

    url = url_to_view(row, view_name)
    if url:
        return "<a href=\"%s\">%s</a>" % (url, content)
    else:
        return content

def docu_link(topic, text):
    return '<a href="%s" target="_blank">%s</a>' % (config.doculink_urlformat % topic, text)

# Calculates a uniq id for each data row which identifies the current
# row accross different page loadings.
def row_id(view, row):
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


def get_sorter_name_of_painter(painter_name):
    painter = multisite_painters[painter_name]
    if 'sorter' in painter:
        return painter['sorter']

    elif painter_name in multisite_sorters:
        return painter_name


def get_primary_sorter_order(view, painter_name):
    sorter_name = get_sorter_name_of_painter(painter_name)
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
    group_sort = [ (get_sorter_name_of_painter(p[0]), False)
                   for p in view['group_painters']
                   if p[0] in multisite_painters
                      and get_sorter_name_of_painter(p[0]) is not None ]
    view_sort  = [ s for s in view['sorters'] if not s[0] in group_sort ]

    # Get current url individual sorters. Parse the "sort" url parameter,
    # then remove the group sorters. The left sorters must be the user
    # individual sorters for this view.
    # Then remove the user sorters from the view sorters
    user_sort = parse_url_sorters(html.var('sort'))

    substract_sorters(user_sort, group_sort)
    substract_sorters(view_sort, user_sort)

    return group_sort, user_sort, view_sort

# The Group-value of a row is used for deciding whether
# two rows are in the same group or not
def group_value(row, group_cells):
    group = []
    for cell in group_cells:
        painter = cell.painter()

        groupvalfunc = painter.get("groupby")
        if groupvalfunc:
            if "args" in painter:
                group.append(groupvalfunc(row, *painter["args"]))
            else:
                group.append(groupvalfunc(row))

        else:
            for c in get_painter_columns(painter):
                if c in row:
                    group.append(row[c])

    return create_dict_key(group)


def create_dict_key(value):
    if type(value) in (list, tuple):
        return tuple(map(create_dict_key, value))
    elif type(value) == dict:
        return tuple([ (k, create_dict_key(v)) for (k, v) in sorted(value.items()) ])
    else:
        return value


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
        for entry in config.host_tag_groups():
            g_taggroups_by_id[entry[0]] = (entry[1], entry[2])

    return g_taggroups_by_id.get(tgid, (_("N/A"), []))

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
    c1 = num_split(r1[column].lower())
    c2 = num_split(r2[column].lower())
    return cmp(c1, c2)

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
    site_id = html.var("site")
    hostname = html.var("host")
    invpath = html.var("path")
    tree_id = html.var("treeid", "")
    if html.var("show_internal_tree_paths"):
        show_internal_tree_paths = True
    else:
        show_internal_tree_paths = False

    if tree_id:
        struct_tree = inventory.load_delta_tree(hostname, int(tree_id[1:]))
        tree_renderer = DeltaNodeRenderer(site_id, hostname, tree_id, invpath)
    else:
        row = inventory.get_status_data_via_livestatus(site_id, hostname)
        struct_tree = inventory.load_filtered_and_merged_tree(row)
        tree_renderer = AttributeRenderer(site_id, hostname, "", invpath,
                        show_internal_tree_paths=show_internal_tree_paths)

    if struct_tree is None:
        html.show_error(_("No such inventory tree."))

    parsed_path, _attribute_keys = inventory.parse_tree_path(invpath)
    if parsed_path:
        children = struct_tree.get_sub_children(parsed_path)
    else:
        children = [struct_tree.get_root_container()]

    if children is None:
        html.show_error(_("Invalid path in inventory tree: '%s' >> %s") % (invpath, repr(parsed_path)))
    else:
        for child in inventory.sort_children(children):
            child.show(tree_renderer, path=invpath)


def output_csv_headers(view):
    filename = '%s-%s.csv' % (view['name'], time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(time.time())))
    if type(filename) == unicode:
        filename = filename.encode("utf-8")
    html.req.headers_out['Content-Disposition'] = 'Attachment; filename="%s"' % filename

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


def ajax_popup_action_menu():
    site    = html.var('site')
    host    = html.var('host')
    svcdesc = html.get_unicode_input('service')
    what    = 'service' if svcdesc else 'host'

    weblib.prepare_display_options(globals())

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
                url, target_frame = sanitize_action_url(url_spec)
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


def sanitize_action_url(url_spec):
    if type(url_spec) == tuple:
        return url_spec
    else:
        return (url_spec, None)


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
            add_filter = "Filter: service_description = %s\n" % lqencode(wait_svc)
        else:
            wait_spec = spec
            add_filter = "Filter: service_description = %s\n" % lqencode(service)
    else:
        cmd = "HOST"
        what = "host"
        spec = host
        wait_spec = spec
        add_filter = ""

    try:
        now = int(time.time())
        sites.live().command("[%d] SCHEDULE_FORCED_%s_CHECK;%s;%d" % (now, cmd, lqencode(spec), now), site)
        sites.live().set_only_sites([site])
        query = u"GET %ss\n" \
                "WaitObject: %s\n" \
                "WaitCondition: last_check >= %d\n" \
                "WaitTimeout: %d\n" \
                "WaitTrigger: check\n" \
                "Columns: last_check state plugin_output\n" \
                "Filter: host_name = %s\n%s" \
                % (what, lqencode(wait_spec), now, config.reschedule_timeout * 1000, lqencode(host), add_filter)
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
                time.sleep(0.7);
            html.write("['OK', %d, %d, %r]\n" % (row[0], row[1], row[2].encode("utf-8")))

    except Exception, e:
        sites.live().set_only_sites()
        raise MKGeneralException(_("Cannot reschedule check: %s") % e)
