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

import abc
import time
import os
import pprint
import traceback
import json
from typing import Dict, Optional, List  # pylint: disable=unused-import

import livestatus

import cmk.utils.paths

import cmk.gui.utils as utils
import cmk.gui.config as config
import cmk.gui.weblib as weblib
import cmk.gui.forms as forms
import cmk.gui.inventory as inventory
import cmk.gui.visuals as visuals
import cmk.gui.sites as sites
import cmk.gui.i18n
import cmk.gui.pages
import cmk.gui.view_utils
from cmk.gui.display_options import display_options
from cmk.gui.valuespec import (
    DropdownChoice,
    Integer,
    ListChoice,
    Dictionary,
    FixedValue,
    IconSelector,
    ListOf,
    Tuple,
    TextUnicode,
    Alternative,
    CascadingDropdown,
)
from cmk.gui.i18n import _u, _
from cmk.gui.globals import html
from cmk.gui.exceptions import (
    HTTPRedirect,
    MKGeneralException,
    MKUserError,
    MKInternalError,
)
from cmk.gui.permissions import (
    permission_section_registry,
    PermissionSection,
    declare_permission,
)
from cmk.gui.plugins.visuals.utils import (
    visual_info_registry,
    visual_type_registry,
    VisualType,
)
from cmk.gui.plugins.views.icons.utils import (
    icon_and_action_registry,
    Icon,
)
from cmk.gui.plugins.views.utils import (
    command_registry,
    layout_registry,
    data_source_registry,
    painter_registry,
    Painter,
    sorter_registry,
    get_permitted_views,
    get_all_views,
    painter_exists,
    PainterOptions,
    get_tag_groups,
    _parse_url_sorters,
    SorterEntry,
)

# Needed for legacy (pre 1.6) plugins
from cmk.gui.htmllib import HTML  # pylint: disable=unused-import
from cmk.gui.plugins.views.utils import (  # pylint: disable=unused-import
    view_title, multisite_builtin_views, view_hooks, inventory_displayhints, register_command_group,
    transform_action_url, is_stale, paint_stalified, paint_host_list, format_plugin_output,
    link_to_view, url_to_view, row_id, group_value, view_is_enabled, paint_age, declare_1to1_sorter,
    declare_simple_sorter, cmp_simple_number, cmp_simple_string, cmp_insensitive_string,
    cmp_num_split, cmp_custom_variable, cmp_service_name_equiv, cmp_string_list, cmp_ip_address,
    get_custom_var, get_perfdata_nth_value, join_row, get_view_infos, replace_action_url_macros,
    Cell, JoinCell, register_legacy_command, register_painter, register_sorter,
)

# Needed for legacy (pre 1.6) plugins
from cmk.gui.plugins.views.icons import (  # pylint: disable=unused-import
    multisite_icons_and_actions, get_multisite_icons, get_icons, iconpainter_columns,
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

# TODO: Kept for compatibility with pre 1.6 plugins. Plugins will not be used anymore, but an error
# will be displayed.
multisite_painter_options = {}
multisite_layouts = {}
multisite_commands = {}
multisite_datasources = {}
multisite_painters = {}
multisite_sorters = {}


@visual_type_registry.register
class VisualTypeViews(VisualType):
    """Register the views as a visual type"""
    @property
    def ident(self):
        return "views"

    @property
    def title(self):
        return _("view")

    @property
    def plural_title(self):
        return _("views")

    @property
    def ident_attr(self):
        return "view_name"

    @property
    def multicontext_links(self):
        return False

    @property
    def show_url(self):
        return "view.py"

    def popup_add_handler(self, add_type):
        return []

    def add_visual_handler(self, target_visual_name, add_type, context, parameters):
        return None

    def load_handler(self):
        pass

    @property
    def permitted_visuals(self):
        return get_permitted_views()

    def is_enabled_for(self, this_visual, visual, context_vars):
        if visual["name"] not in view_is_enabled:
            return True  # Not registered are always visible!

        return view_is_enabled[visual["name"]](this_visual, visual, context_vars)


@permission_section_registry.register
class PermissionSectionViews(PermissionSection):
    @property
    def name(self):
        return "view"

    @property
    def title(self):
        return _("Views")

    @property
    def do_sort(self):
        return True


class View(object):
    """Manages processing of a single view, e.g. during rendering"""
    def __init__(self, view_name, view_spec):
        # type: (str, Dict) -> None
        super(View, self).__init__()
        self.name = view_name
        self.spec = view_spec
        self._row_limit = None  # type: Optional[int]
        self._only_sites = None  # type: Optional[List[str]]
        self._user_sorters = None  # type: Optional[Tuple]

    @property
    def datasource(self):
        try:
            return data_source_registry[self.spec["datasource"]]()
        except KeyError:
            if self.spec["datasource"].startswith("mkeventd_"):
                raise MKUserError(
                    None,
                    _("The Event Console view '%s' can not be rendered. The Event Console is possibly "
                      "disabled.") % self.name)
            else:
                raise MKUserError(
                    None,
                    _("The view '%s' using the datasource '%s' can not be rendered "
                      "because the datasource does not exist.") % (self.name, self.datasource))

    @property
    def row_cells(self):
        # type: () -> List[Cell]
        """Regular cells are displaying information about the rows of the type the view is about"""
        cells = []
        for e in self.spec["painters"]:
            if not painter_exists(e):
                continue

            if Cell.is_join_cell(e):
                cells.append(JoinCell(self, e))
            else:
                cells.append(Cell(self, e))

        return cells

    @property
    def group_cells(self):
        # type: () -> List[Cell]
        """Group cells are displayed as titles of grouped rows"""
        return [Cell(self, e) for e in self.spec["group_painters"] if painter_exists(e)]

    @property
    def join_cells(self):
        """Join cells are displaying information of a joined source (e.g.service data on host views)"""
        return [x for x in self.row_cells if isinstance(x, JoinCell)]

    @property
    def sorters(self):
        """Returns the list of effective sorters to be used to sort the rows of this view"""
        return self._get_sorter_entries(
            self.user_sorters if self.user_sorters else self.spec["sorters"])

    def _get_sorter_entries(self, sorter_list):
        sorters = []
        for entry in sorter_list:
            if not isinstance(entry, SorterEntry):
                entry = SorterEntry(*entry)

            sorter_name = entry.sorter
            hash_id = None
            if ":" in entry.sorter:
                sorter_name, hash_id = entry.sorter.split(':', 1)

            sorter = sorter_registry.get(sorter_name, None)

            if sorter is None:
                continue  # Skip removed sorters

            sorter = sorter()
            if hasattr(sorter, 'derived_columns'):
                sorter.derived_columns(self, hash_id)

            sorters.append(SorterEntry(sorter=sorter, negate=entry.negate, join_key=entry.join_key))
        return sorters

    @property
    def row_limit(self):
        if self.datasource.ignore_limit:
            return None

        return self._row_limit

    @row_limit.setter
    def row_limit(self, row_limit):
        self._row_limit = row_limit

    @property
    def only_sites(self):
        """Optional list of sites to query instead of all sites

        This is a performance feature. It is highly recommended to set the only_sites attribute
        whenever it is possible. In the moment it is set a livestatus query is not sent to all
        sites anymore but only to the given list of sites."""
        return self._only_sites

    @only_sites.setter
    def only_sites(self, only_sites):
        self._only_sites = only_sites

    @property
    def user_sorters(self):
        """Optional list of sorters to use for rendering the view

        The user may click on the headers of tables to change the default view sorting. In the
        moment the user overrides the sorting configured for the view in self.spec"""
        # TODO: Only process in case the view is user sortable
        return self._user_sorters

    @user_sorters.setter
    def user_sorters(self, user_sorters):
        self._user_sorters = user_sorters


class ViewRenderer(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, view):
        super(ViewRenderer, self).__init__()
        self.view = view

    @abc.abstractmethod
    def render(self, rows, group_cells, cells, show_checkboxes, layout, num_columns, show_filters):
        raise NotImplementedError()


class GUIViewRenderer(ViewRenderer):
    def __init__(self, view, show_buttons):
        super(GUIViewRenderer, self).__init__(view)
        self._show_buttons = show_buttons

    def render(self, rows, group_cells, cells, show_checkboxes, layout, num_columns, show_filters):
        view_spec = self.view.spec

        if html.transaction_valid() and html.do_actions():
            html.set_browser_reload(0)

        # Show/Hide the header with page title, MK logo, etc.
        if display_options.enabled(display_options.H):
            html.body_start(view_title(view_spec))

        if display_options.enabled(display_options.T):
            html.top_heading(view_title(view_spec))

        has_done_actions = False
        row_count = len(rows)

        # This is a general flag which makes the command form render when the current
        # view might be able to handle commands. When no commands are possible due missing
        # permissions or datasources without commands, the form is not rendered
        command_form = should_show_command_form(self.view.datasource)

        if command_form:
            weblib.init_selection()

        if self._show_buttons:
            _show_context_links(
                self.view,
                show_filters,
                # Take into account: permissions, display_options
                row_count > 0 and command_form,
                # Take into account: layout capabilities
                layout.can_display_checkboxes and not view_spec.get("force_checkboxes"),
                show_checkboxes,
            )
        # User errors in filters
        html.show_user_errors()

        # Filter form
        filter_isopen = view_spec.get("mustsearch") and not html.request.var("filled_in")
        if display_options.enabled(display_options.F) and len(show_filters) > 0:
            show_filter_form(filter_isopen, show_filters)

        # Actions
        if command_form:
            # If we are currently within an action (confirming or executing), then
            # we display only the selected rows (if checkbox mode is active)
            if show_checkboxes and html.do_actions():
                rows = filter_selected_rows(view_spec, rows,
                                            weblib.get_rowselection('view-' + view_spec['name']))

            # There are one shot actions which only want to affect one row, filter the rows
            # by this id during actions
            if html.request.has_var("_row_id") and html.do_actions():
                rows = filter_by_row_id(view_spec, rows)

            if html.do_actions() and html.transaction_valid():  # submit button pressed, no reload
                try:
                    # Create URI with all actions variables removed
                    backurl = html.makeuri([], delvars=['filled_in', 'actions'])
                    has_done_actions = do_actions(view_spec, self.view.datasource.infos[0], rows,
                                                  backurl)
                except MKUserError as e:
                    html.show_error(e)
                    html.add_user_error(e.varname, e)
                    if display_options.enabled(display_options.C):
                        show_command_form(True, self.view.datasource)

            elif display_options.enabled(
                    display_options.C):  # (*not* display open, if checkboxes are currently shown)
                show_command_form(False, self.view.datasource)

        # Also execute commands in cases without command form (needed for Python-
        # web service e.g. for NagStaMon)
        elif row_count > 0 and config.user.may("general.act") \
             and html.do_actions() and html.transaction_valid():

            # There are one shot actions which only want to affect one row, filter the rows
            # by this id during actions
            if html.request.has_var("_row_id") and html.do_actions():
                rows = filter_by_row_id(view_spec, rows)

            try:
                do_actions(view_spec, self.view.datasource.infos[0], rows, '')
            except Exception:
                pass  # currently no feed back on webservice

        painter_options = PainterOptions.get_instance()
        painter_options.show_form(self.view)

        # The refreshing content container
        if display_options.enabled(display_options.R):
            html.open_div(id_="data_container")

        if not has_done_actions:
            if display_options.enabled(display_options.W):
                if cmk.gui.view_utils.row_limit_exceeded(rows, self.view.row_limit):
                    del rows[self.view.row_limit:]
            layout.render(rows, view_spec, group_cells, cells, num_columns, show_checkboxes and
                          not html.do_actions())
            headinfo = "%d %s" % (row_count, _("row") if row_count == 1 else _("rows"))
            if show_checkboxes:
                selected = filter_selected_rows(
                    view_spec, rows, weblib.get_rowselection('view-' + view_spec['name']))
                headinfo = "%d/%s" % (len(selected), headinfo)

            if html.output_format == "html":
                html.javascript("cmk.utils.update_header_info(%s);" % json.dumps(headinfo))

                # The number of rows might have changed to enable/disable actions and checkboxes
                if self._show_buttons:
                    update_context_links(
                        # don't take display_options into account here ('c' is set during reload)
                        row_count > 0 and
                        should_show_command_form(self.view.datasource, ignore_display_option=True),
                        # and not html.do_actions(),
                        layout.can_display_checkboxes)

            # Play alarm sounds, if critical events have been displayed
            if display_options.enabled(display_options.S) and view_spec.get("play_sounds"):
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

        pid = os.getpid()
        if sites.live().successfully_persisted():
            html.add_status_icon(
                "persist",
                _("Reused persistent livestatus connection from earlier request (PID %d)") % pid)

        html.bottom_focuscode()
        if display_options.enabled(display_options.Z):
            html.bottom_footer()

        if display_options.enabled(display_options.H):
            html.body_end()


# Load all view plugins
def load_plugins(force):
    global loaded_with_language

    if loaded_with_language == cmk.gui.i18n.get_current_language() and not force:
        clear_alarm_sound_states()
        return

    utils.load_web_plugins("views", globals())
    utils.load_web_plugins('icons', globals())
    clear_alarm_sound_states()

    transform_old_dict_based_icons()

    # TODO: Kept for compatibility with pre 1.6 plugins. Plugins will not be used anymore, but an error
    # will be displayed.
    if multisite_painter_options:
        raise MKGeneralException("Found legacy painter option plugins: %s. You will either have to "
                                 "remove or migrate them." %
                                 ", ".join(multisite_painter_options.keys()))
    if multisite_layouts:
        raise MKGeneralException("Found legacy layout plugins: %s. You will either have to "
                                 "remove or migrate them." % ", ".join(multisite_layouts.keys()))
    if multisite_datasources:
        raise MKGeneralException("Found legacy data source plugins: %s. You will either have to "
                                 "remove or migrate them." %
                                 ", ".join(multisite_datasources.keys()))

    # TODO: Kept for compatibility with pre 1.6 plugins
    for cmd_spec in multisite_commands:
        register_legacy_command(cmd_spec)

    cmk.gui.plugins.views.inventory.declare_inventory_columns()

    # TODO: Kept for compatibility with pre 1.6 plugins
    for ident, spec in multisite_painters.items():
        register_painter(ident, spec)

    # TODO: Kept for compatibility with pre 1.6 plugins
    for ident, spec in multisite_sorters.items():
        register_sorter(ident, spec)

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = cmk.gui.i18n.get_current_language()

    visuals.declare_visual_permissions('views', _("views"))

    # Declare permissions for builtin views
    for name, view_spec in multisite_builtin_views.items():
        declare_permission("view.%s" % name, format_view_title(name, view_spec),
                           "%s - %s" % (name, _u(view_spec["description"])),
                           config.builtin_role_ids)

    # Make sure that custom views also have permissions
    config.declare_dynamic_permissions(lambda: visuals.declare_custom_permissions('views'))


# Transform pre 1.6 icon plugins. Deprecate this one day.
def transform_old_dict_based_icons():
    for icon_id, icon in multisite_icons_and_actions.items():
        icon_class = type(
            "LegacyIcon%s" % icon_id.title(), (Icon,), {
                "_ident": icon_id,
                "_icon_spec": icon,
                "ident": classmethod(lambda cls: cls._ident),
                "sort_index": lambda self: self._icon_spec.get("sort_index", 30),
                "toplevel": lambda self: self._icon_spec.get("toplevel", False),
                "render": lambda self, *args: self._icon_spec["paint"](*args),
                "columns": lambda self: self._icon_spec.get("columns", []),
                "host_columns": lambda self: self._icon_spec.get("host_columns", []),
                "service_columns": lambda self: self._icon_spec.get("service_columns", []),
            })

        icon_and_action_registry.register(icon_class)


def _register_tag_plugins():
    _register_host_tag_painters()
    _register_host_tag_sorters()


config.register_post_config_load_hook(_register_tag_plugins)


def _register_host_tag_painters():
    # first remove all old painters to reflect delted painters during runtime
    for key in list(painter_registry.keys()):
        if key.startswith('host_tag_'):
            del painter_registry[key]

    for tag_group in config.tags.tag_groups:
        if tag_group.topic:
            long_title = tag_group.topic + ' / ' + tag_group.title
        else:
            long_title = tag_group.title

        ident = "host_tag_" + tag_group.id
        spec = {
            "title": _("Host tag:") + ' ' + long_title,
            "short": tag_group.title,
            "columns": ["host_custom_variables"],
        }
        cls = type(
            "HostTagPainter%s" % str(tag_group.id).title(),
            (Painter,),
            {
                "_ident": ident,
                "_spec": spec,
                "_tag_group_id": tag_group.id,
                "ident": property(lambda self: self._ident),
                "title": property(lambda self: self._spec["title"]),
                "columns": property(lambda self: self._spec["columns"]),
                "render": lambda self, row, cell: _paint_host_tag(row, self._tag_group_id),
                "short_title": property(lambda self: self._spec["short"]),
                # Use title of the tag value for grouping, not the complete
                # dictionary of custom variables!
                "group_by": lambda self, row: _paint_host_tag(row, self._tag_group_id)[1],
            })
        painter_registry.register(cls)


def _paint_host_tag(row, tgid):
    return "", _get_tag_group_value(row, "host", tgid)


def _register_host_tag_sorters():
    for tag_group in config.tags.tag_groups:
        register_sorter(
            "host_tag_" + str(tag_group.id), {
                "_tag_group_id": tag_group.id,
                "title": _("Host tag:") + ' ' + tag_group.title,
                "columns": ["host_custom_variables"],
                "cmp": lambda self, r1, r2: _cmp_host_tag(r1, r2, self._spec["_tag_group_id"]),
            })


def _cmp_host_tag(r1, r2, tgid):
    return cmp(_get_tag_group_value(r1, "host", tgid), _get_tag_group_value(r2, "host", tgid))


def _get_tag_group_value(row, what, tag_group_id):
    tag_id = get_tag_groups(row, "host").get(tag_group_id)

    tag_group = config.tags.get_tag_group(tag_group_id)
    if tag_group:
        label = dict(tag_group.get_tag_choices()).get(tag_id, _("N/A"))
    else:
        label = tag_id

    return label or _("N/A")


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
    cols = [(_('Datasource'), lambda v: data_source_registry[v["datasource"]]().title)]
    visuals.page_list('views', _("Edit Views"), get_all_views(), cols)


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


def DatasourceSelection():
    """Create datasource selection valuespec, also for other modules"""
    return DropdownChoice(
        title=_('Datasource'),
        help=_('The datasources define which type of objects should be displayed with this view.'),
        choices=data_source_registry.data_source_choices(),
        columns=1,
        default_value='services',
    )


@cmk.gui.pages.register("create_view")
def page_create_view(next_url=None):

    vs_ds = DatasourceSelection()

    ds = 'services'  # Default selection

    html.header(_('Create View'))
    html.begin_context_buttons()
    html.context_button(_("Back"), html.get_url_input("back", "edit_views.py"), "back")
    html.end_context_buttons()

    if html.request.var('save') and html.check_transaction():
        try:
            ds = vs_ds.from_html_vars('ds')
            vs_ds.validate_value(ds, 'ds')

            if not next_url:
                next_url = html.makeuri([('datasource', ds)], filename="create_view_infos.py")
            else:
                next_url = next_url + '&datasource=%s' % ds
            raise HTTPRedirect(next_url)
        except MKUserError as e:
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
    ds_class, ds_name = html.get_item_input("datasource", data_source_registry)
    visuals.page_create_visual('views',
                               ds_class().infos,
                               next_url='edit_view.py?mode=create&datasource=%s&single_infos=%%s' %
                               ds_name)


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
    visuals.page_edit_visual(
        'views',
        get_all_views(),
        custom_field_handler=render_view_config,
        load_handler=transform_view_to_valuespec_value,
        create_handler=create_view_from_valuespec,
        info_handler=get_view_infos,
    )


def view_choices(only_with_hidden=False):
    choices = [("", "")]
    for name, view in get_permitted_views().items():
        if not only_with_hidden or view['single_infos']:
            title = format_view_title(name, view)
            choices.append(("%s" % name, title))
    return choices


def format_view_title(name, view):
    title_parts = []

    if view.get('mobile', False):
        title_parts.append(_('Mobile'))

    # Don't use the data source title because it does not really look good here
    datasource = data_source_registry[view["datasource"]]()
    infos = datasource.infos
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
        ('mobile', _('Show this view in the Mobile GUI')),
        ('mustsearch', _('Show data only on search')),
        ('force_checkboxes', _('Always show the checkboxes')),
        ('user_sortable', _('Make view sortable by user')),
        ('play_sounds', _('Play alarm sounds')),
    ]


def view_editor_specs(ds_name, general_properties=True):
    specs = []
    if general_properties:
        specs.append(('view',
                      Dictionary(
                          title=_('View Properties'),
                          render='form',
                          optional_keys=None,
                          elements=[
                              ('datasource',
                               FixedValue(
                                   ds_name,
                                   title=_('Datasource'),
                                   totext=data_source_registry[ds_name]().title,
                                   help=_('The datasource of a view cannot be changed.'),
                               )),
                              ('options',
                               ListChoice(
                                   title=_('Options'),
                                   choices=view_editor_options(),
                                   default_value=['user_sortable'],
                               )),
                              ('browser_reload',
                               Integer(
                                   title=_('Automatic page reload'),
                                   unit=_('seconds'),
                                   minvalue=0,
                                   help=_('Leave this empty or at 0 for no automatic reload.'),
                               )),
                              ('layout',
                               DropdownChoice(
                                   title=_('Basic Layout'),
                                   choices=layout_registry.get_choices(),
                                   default_value='table',
                                   sorted=True,
                               )),
                              ('num_columns',
                               Integer(
                                   title=_('Number of Columns'),
                                   default_value=1,
                                   minvalue=1,
                                   maxvalue=50,
                               )),
                              ('column_headers',
                               DropdownChoice(
                                   title=_('Column Headers'),
                                   choices=[
                                       ("off", _("off")),
                                       ("pergroup", _("once per group")),
                                       ("repeat", _("repeat every 20'th row")),
                                   ],
                                   default_value='pergroup',
                               )),
                          ],
                      )))

    def column_spec(ident, title, ds_name):
        painters = painters_of_datasource(ds_name)

        allow_empty = True
        empty_text = None
        if ident == 'columns':
            allow_empty = False
            empty_text = _("Please add at least one column to your view.")

        vs_column = Tuple(
            title=_('Column'),
            elements=[
                CascadingDropdown(
                    title=_('Column'),
                    choices=painter_choices_with_params(painters),
                    no_preselect=True,
                ),
                DropdownChoice(
                    title=_('Link'),
                    choices=view_choices,
                    sorted=True,
                ),
                DropdownChoice(
                    title=_('Tooltip'),
                    choices=[(None, "")] + painter_choices(painters),
                ),
            ],
        )

        join_painters = join_painters_of_datasource(ds_name)
        if ident == 'columns' and join_painters:
            join_painters = join_painters_of_datasource(ds_name)

            vs_column = Alternative(
                elements=[
                    vs_column,
                    Tuple(
                        title=_('Joined column'),
                        help=_(
                            "A joined column can display information about specific services for "
                            "host objects in a view showing host objects. You need to specify the "
                            "service description of the service you like to show the data for."),
                        elements=[
                            CascadingDropdown(
                                title=_('Column'),
                                choices=painter_choices_with_params(join_painters),
                                no_preselect=True,
                            ),
                            TextUnicode(
                                title=_('of Service'),
                                allow_empty=False,
                            ),
                            DropdownChoice(
                                title=_('Link'),
                                choices=view_choices,
                                sorted=True,
                            ),
                            DropdownChoice(
                                title=_('Tooltip'),
                                choices=[(None, "")] + painter_choices(join_painters),
                            ),
                            TextUnicode(title=_('Title'),),
                        ],
                    ),
                ],
                style='dropdown',
                match=lambda x: 1 * (x is not None and len(x) == 5),
            )

        return (ident,
                Dictionary(
                    title=title,
                    render='form',
                    optional_keys=None,
                    elements=[
                        (ident,
                         ListOf(
                             vs_column,
                             title=title,
                             add_label=_('Add column'),
                             allow_empty=allow_empty,
                             empty_text=empty_text,
                         )),
                    ],
                ))

    specs.append(column_spec('columns', _('Columns'), ds_name))

    specs.append(
        ('sorting',
         Dictionary(
             title=_('Sorting'),
             render='form',
             optional_keys=None,
             elements=[
                 ('sorters',
                  ListOf(
                      Tuple(
                          elements=[
                              DropdownChoice(
                                  title=_('Column'),
                                  choices=[(name, get_painter_title_for_choices(p))
                                           for name, p in sorters_of_datasource(ds_name).items()],
                                  sorted=True,
                                  no_preselect=True,
                              ),
                              DropdownChoice(
                                  title=_('Order'),
                                  choices=[(False, _("Ascending")), (True, _("Descending"))],
                              ),
                          ],
                          orientation='horizontal',
                      ),
                      title=_('Sorting'),
                      add_label=_('Add sorter'),
                  )),
             ],
         )),)

    specs.append(column_spec('grouping', _('Grouping'), ds_name))

    return specs


def render_view_config(view, general_properties=True):
    ds_name = view.get("datasource", html.request.var("datasource"))
    if not ds_name:
        raise MKInternalError(_("No datasource defined."))
    if ds_name not in data_source_registry:
        raise MKInternalError(_('The given datasource is not supported.'))

    view['datasource'] = ds_name

    for ident, vs in view_editor_specs(ds_name, general_properties):
        vs.render_input(ident, view.get(ident))


# Is used to change the view structure to be compatible to
# the valuespec This needs to perform the inverted steps of the
# transform_valuespec_value_to_view() function. FIXME: One day we should
# rewrite this to make no transform needed anymore
def transform_view_to_valuespec_value(view):
    view["view"] = {}  # Several global variables are put into a sub-dict
    # Only copy our known keys. Reporting element, etc. might have their own keys as well
    for key in ["datasource", "browser_reload", "layout", "num_columns", "column_headers"]:
        if key in view:
            view["view"][key] = view[key]

    view["view"]['options'] = []
    for key, _title in view_editor_options():
        if view.get(key):
            view['view']['options'].append(key)

    view['visibility'] = {}
    for key in ['hidden', 'hidebutton', 'public']:
        if view.get(key):
            view['visibility'][key] = view[key]

    view['grouping'] = {"grouping": view.get('group_painters', [])}
    view['sorting'] = {"sorters": view.get('sorters', {})}

    columns = []
    view['columns'] = {"columns": columns}
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
    ds_name = old_view.get('datasource', html.request.var('datasource'))
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
    html.open_div(id_="filters",
                  class_=["view_form"],
                  style="display: none;" if not is_open else None)

    html.begin_form("filter")
    html.open_table(class_=["filterform"], cellpadding="0", cellspacing="0", border="0")
    html.open_tr()
    html.open_td()

    # sort filters according to title
    s = sorted([(f.sort_index, f.title, f) for f in filters if f.available()])

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
    view_spec, view_name = html.get_item_input("view_name", get_permitted_views())

    view = View(view_name, view_spec)
    view.row_limit = get_limit()
    view.only_sites = get_only_sites()
    view.user_sorters = get_user_sorters()

    # Gather the page context which is needed for the "add to visual" popup menu
    # to add e.g. views to dashboards or reports
    context = visuals.get_context_from_uri_vars(view.datasource.infos)
    context.update(visuals.get_singlecontext_html_vars(view.spec))
    html.set_page_context(context)

    painter_options = PainterOptions.get_instance()
    painter_options.load(view.name)
    painter_options.update_from_url(view)

    view_renderer = GUIViewRenderer(view, show_buttons=True)
    show_view(view, view_renderer)


# Display view with real data
# TODO: Disentangle logic and presentation like this:
# - Move logic stuff to View class
# - Move rendering specific stuff to the fitting ViewRenderer
# - Find the right place for the availability / SLA hacks here
def show_view(view, view_renderer, only_count=False):
    display_options.load_from_html()

    # Load from hard painter options > view > hard coded default
    painter_options = PainterOptions.get_instance()
    num_columns = painter_options.get("num_columns", view.spec.get("num_columns", 1))
    browser_reload = painter_options.get("refresh", view.spec.get("browser_reload", None))

    force_checkboxes = view.spec.get("force_checkboxes", False)
    show_checkboxes = force_checkboxes or html.request.var('show_checkboxes', '0') == '1'

    # Not all filters are really shown later in show_filter_form(), because filters which
    # have a hardcoded value are not changeable by the user
    show_filters = visuals.filters_of_visual(view.spec,
                                             view.datasource.infos,
                                             link_filters=view.datasource.link_filters)
    show_filters = visuals.visible_filters_of_visual(view.spec, show_filters)

    # FIXME TODO HACK to make grouping single contextes possible on host/service infos
    # Is hopefully cleaned up soon.
    if view.datasource.ident in ['hosts', 'services']:
        if html.request.has_var('hostgroup') and not html.request.has_var("opthost_group"):
            html.request.set_var("opthost_group", html.request.var("hostgroup"))
        if html.request.has_var('servicegroup') and not html.request.has_var("optservice_group"):
            html.request.set_var("optservice_group", html.request.var("servicegroup"))

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
    if _is_ec_unrelated_host_view(view):
        # Set the value for the event host filter
        if not html.request.has_var("event_host"):
            html.request.set_var("event_host", html.request.var("host"))

    # Now populate the HTML vars with context vars from the view definition. Hard
    # coded default values are treated differently:
    #
    # a) single context vars of the view are enforced
    # b) multi context vars can be overwritten by existing HTML vars
    visuals.add_context_to_uri_vars(view.spec, only_count)

    # Check that all needed information for configured single contexts are available
    visuals.verify_single_contexts('views', view.spec, view.datasource.link_filters)

    all_active_filters = _get_all_active_filters(view)
    filterheaders = _get_livestatus_filter_headers(view, all_active_filters)

    # Fork to availability view. We just need the filter headers, since we do not query the normal
    # hosts and service table, but "statehist". This is *not* true for BI availability, though (see later)
    if html.request.var("mode") == "availability" and ("aggr" not in view.datasource.infos or
                                                       html.request.var("timeline_aggr")):

        context = visuals.get_context_from_uri_vars(view.datasource.infos)
        context.update(visuals.get_singlecontext_html_vars(view.spec))

        return cmk.gui.plugins.views.availability.render_availability_page(
            view, context, filterheaders)

    headers = filterheaders + view.spec.get("add_headers", "")

    # Sorting - use view sorters and URL supplied sorters
    if only_count:
        sorters = []
    else:
        sorters = view.sorters

    # Prepare cells of the view
    group_cells = view.group_cells
    cells = view.row_cells

    # Now compute the list of all columns we need to query via Livestatus.
    # Those are: (1) columns used by the sorters in use, (2) columns use by
    # column- and group-painters in use and - note - (3) columns used to
    # satisfy external references (filters) of views we link to. The last bit
    # is the trickiest. Also compute this list of view options use by the
    # painters
    columns = _get_needed_regular_columns(group_cells + cells, sorters, view.datasource)

    # Fetch data. Some views show data only after pressing [Search]
    if (only_count or (not view.spec.get("mustsearch")) or
            html.request.var("filled_in") in ["filter", 'actions', 'confirm', 'painteroptions']):
        rows = view.datasource.table.query(view, columns, headers, view.only_sites, view.row_limit,
                                           all_active_filters)

        # Now add join information, if there are join columns
        if view.join_cells:
            _do_table_join(view, rows, filterheaders, sorters)

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
                sla_configurations_container = sla.SLAConfigurationsContainerFactory.create_from_cells(
                    sla_params, rows)
                sla.SLAProcessor(sla_configurations_container).add_sla_data_to_rows(rows)

        sort_data(rows, sorters)
    else:
        rows = []

    if display_options.enabled(display_options.W):
        cmk.gui.view_utils.query_limit_exceeded_with_warn(rows, view.row_limit, config.user)

    # Apply non-Livestatus filters
    for filter_ in all_active_filters:
        rows = filter_.filter_table(rows)

    if html.request.var("mode") == "availability":
        cmk.gui.plugins.views.availability.render_bi_availability(view_title(view.spec), rows)
        return

    # TODO: Use livestatus Stats: instead of fetching rows!
    if only_count:
        for filter_vars in view.spec["context"].itervalues():
            for varname in filter_vars.iterkeys():
                html.request.del_var(varname)
        return len(rows)

    # The layout of the view: it can be overridden by several specifying
    # an output format (like json or python). Note: the layout is not
    # always needed. In case of an embedded view in the reporting this
    # field is simply missing, because the rendering is done by the
    # report itself.
    # TODO: CSV export should be handled by the layouts. It cannot
    # be done generic in most cases
    if "layout" in view.spec:
        layout = layout_registry[view.spec["layout"]]()
    else:
        layout = None

    if html.output_format != "html":
        if layout and layout.has_individual_csv_export:
            layout.csv_export(rows, view.spec, group_cells, cells)
            return

        # Generic layout of export
        layout_class = layout_registry.get(html.output_format)
        if not layout_class:
            raise MKUserError("output_format",
                              _("Output format '%s' not supported") % html.output_format)

        layout = layout_class()

    # Set browser reload
    if browser_reload and display_options.enabled(display_options.R) and not only_count:
        html.set_browser_reload(browser_reload)

    if config.enable_sounds and config.sounds and html.output_format == "html":
        for row in rows:
            save_state_for_playing_alarm_sounds(row)

    # Until now no single byte of HTML code has been output.
    # Now let's render the view
    view_renderer.render(rows, group_cells, cells, show_checkboxes, layout, num_columns,
                         show_filters)


def _get_all_active_filters(view):
    # Always allow the users to specify all allowed filters using the URL
    use_filters = visuals.filters_allowed_for_infos(view.datasource.infos).values()

    # See show_view() for more information about this hack
    if _is_ec_unrelated_host_view(view):
        # Remove the original host name filter
        use_filters = [f for f in use_filters if f.ident != "host"]

    use_filters = [f for f in use_filters if f.available()]

    for filt in use_filters:
        if hasattr(filt, 'derived_columns'):
            filt.derived_columns(view)

    return use_filters


def _is_ec_unrelated_host_view(view):
    return view.datasource.ident in [ "mkeventd_events", "mkeventd_history" ] \
       and "host" in view.spec["single_infos"] and view.spec["name"] != "ec_events_of_monhost"


def _get_needed_regular_columns(cells, sorters, datasource):
    # BI availability needs aggr_tree
    # TODO: wtf? a full reset of the list? Move this far away to a special place!
    if html.request.var("mode") == "availability" and "aggr" in datasource.infos:
        return ["aggr_tree", "aggr_name", "aggr_group"]

    columns = columns_of_cells(cells)

    # Columns needed for sorters
    # TODO: Move sorter parsing and logic to something like Cells()
    for entry in sorters:
        columns.update(entry.sorter.columns)

    # Add key columns, needed for executing commands
    columns.update(datasource.keys)

    # Add idkey columns, needed for identifying the row
    columns.update(datasource.id_keys)

    # Remove (implicit) site column
    try:
        columns.remove("site")
    except KeyError:
        pass

    return list(columns)


# TODO: When this is used by the reporting then *all* filters are active.
# That way the inventory data will always be loaded. When we convert this to the
# visuals principle the we need to optimize this.
def _get_livestatus_filter_headers(view, all_active_filters):
    """Prepare Filter headers for Livestatus"""
    filterheaders = ""
    for filt in all_active_filters:
        try:
            header = filt.filter(view.datasource.table)
        except MKUserError as e:
            html.add_user_error(e.varname, e)
            continue
        filterheaders += header
    return filterheaders


def _get_needed_join_columns(join_cells, sorters):
    join_columns = columns_of_cells(join_cells)

    # Columns needed for sorters
    # TODO: Move sorter parsing and logic to something like Cells()
    for entry in sorters:
        join_columns.update(entry.sorter.columns)

    # Remove (implicit) site column
    try:
        join_columns.remove("site")
    except KeyError:
        pass

    return list(join_columns)


def is_sla_data_needed(group_cells, cells, sorters, all_active_filters):
    pass


def is_inventory_data_needed(group_cells, cells, sorters, all_active_filters):
    for cell in cells:
        if cell.has_tooltip():
            if cell.tooltip_painter_name().startswith("inv_"):
                return True

    for entry in sorters:
        if entry.sorter.load_inv:
            return True

    for cell in group_cells + cells:
        if cell.painter().load_inv:
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


def _do_table_join(view, master_rows, master_filters, sorters):
    join_table, join_master_column = view.datasource.join
    slave_ds = data_source_registry[join_table]()
    join_slave_column = slave_ds.join_key
    join_cells = view.join_cells
    join_columns = _get_needed_join_columns(join_cells, sorters)

    # Create additional filters
    join_filters = []
    for cell in join_cells:
        join_filters.append(cell.livestatus_filter(join_slave_column))

    join_filters.append("Or: %d" % len(join_filters))
    headers = "%s%s\n" % (master_filters, "\n".join(join_filters))
    rows = slave_ds.table.query(view,
                                columns=list(
                                    set([join_master_column, join_slave_column] + join_columns)),
                                headers=headers,
                                only_sites=view.only_sites,
                                limit=None,
                                all_active_filters=None)
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
    host_state_map = {0: "up", 1: "down", 2: "unreachable"}
    service_state_map = {0: "up", 1: "warning", 2: "critical", 3: "unknown"}

    for state_map, state in [(host_state_map, row.get("host_hard_state", row.get("host_state"))),
                             (service_state_map,
                              row.get("service_last_hard_state", row.get("service_state")))]:
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
            break  # only one sound at one time


def get_user_sorters():
    """Returns a list of optionally set sort parameters from HTTP request"""
    return _parse_url_sorters(html.request.var("sort"))


def get_only_sites():
    # type: () -> Optional[List[str]]
    """Is the view limited to specific sites by request?"""
    if html.request.var("site"):
        return [html.request.var("site")]
    return None


def get_limit():
    """How many data rows may the user query?"""
    limitvar = html.request.var("limit", "soft")
    if limitvar == "hard" and config.user.may("general.ignore_soft_limit"):
        return config.hard_query_limit
    elif limitvar == "none" and config.user.may("general.ignore_hard_limit"):
        return None
    return config.soft_query_limit


def view_optiondial(view, option, choices, help_txt):
    # Darn: The option "refresh" has the name "browser_reload" in the
    # view definition
    if option == "refresh":
        name = "browser_reload"
    else:
        name = option

    # Take either the first option of the choices, the view value or the
    # configured painter option.
    painter_options = PainterOptions.get_instance()
    value = painter_options.get(option, dflt=view.get(name, choices[0][0]))

    title = dict(choices).get(value, value)
    html.begin_context_buttons()  # just to be sure
    html.open_div(id_="optiondial_%s" % option,
                  class_=["optiondial", option, "val_%s" % value],
                  title=help_txt,
                  onclick="cmk.views.dial_option(this, %s, %s, %s)" %
                  (json.dumps(view["name"]), json.dumps(option), json.dumps(choices)))
    html.div(title)
    html.close_div()
    html.final_javascript("cmk.views.init_optiondial('optiondial_%s');" % option)


def view_optiondial_off(option):
    html.div('', class_=["optiondial", "off", option])


# Will be called when the user presses the upper button, in order
# to persist the new setting - and to make it active before the
# browser reload of the DIV containing the actual status data is done.
@cmk.gui.pages.register("ajax_set_viewoption")
def ajax_set_viewoption():
    view_name = html.request.var("view_name")
    option = html.request.var("option")
    value = html.request.var("value")
    value = {'true': True, 'false': False}.get(value, value)
    if isinstance(value, str) and value[0].isdigit():
        try:
            value = int(value)
        except ValueError:
            pass

    painter_options = PainterOptions.get_instance()
    painter_options.load(view_name)
    painter_options.set(option, value)
    painter_options.save_to_config(view_name)


def _show_context_links(view, show_filters, enable_commands, enable_checkboxes, show_checkboxes):
    if html.output_format != "html":
        return

    # TODO: Clean this up
    thisview = view.spec

    html.begin_context_buttons()

    # That way if no button is painted we avoid the empty container
    if display_options.enabled(display_options.B):
        execute_hooks('buttons-begin')

    ## Small buttons
    html.open_div(class_="context_buttons_small")
    filter_isopen = html.request.var("filled_in") != "filter" and thisview.get("mustsearch")
    if display_options.enabled(display_options.F):
        if html.request.var("filled_in") == "filter":
            icon = "filters_set"
            help_txt = _("The current data is being filtered")
        else:
            icon = "filters"
            help_txt = _("Set a filter for refining the shown data")
        html.toggle_button("filters", filter_isopen, icon, help_txt, disabled=not show_filters)

    if display_options.enabled(display_options.D):
        painter_options = PainterOptions.get_instance()
        html.toggle_button("painteroptions",
                           False,
                           "painteroptions",
                           _("Modify display options"),
                           disabled=not painter_options.painter_option_form_enabled())

    if display_options.enabled(display_options.C):
        html.toggle_button("commands",
                           False,
                           "commands",
                           _("Execute commands on hosts, services and other objects"),
                           hidden=not enable_commands)
        html.toggle_button("commands", False, "commands", "", hidden=enable_commands, disabled=True)

        selection_enabled = enable_checkboxes if enable_commands else thisview.get(
            'force_checkboxes')
        if not thisview.get("force_checkboxes"):
            html.toggle_button(
                id_="checkbox",
                icon="checkbox",
                title=_("Enable/Disable checkboxes for selecting rows for commands"),
                onclick="location.href='%s';" %
                html.makeuri([('show_checkboxes', show_checkboxes and '0' or '1')]),
                isopen=show_checkboxes,
                hidden=True,
            )
        html.toggle_button("checkbox",
                           False,
                           "checkbox",
                           "",
                           hidden=not thisview.get("force_checkboxes"),
                           disabled=True)
        html.javascript('cmk.selection.set_selection_enabled(%s);' % json.dumps(selection_enabled))

    if display_options.enabled(display_options.O):
        if config.user.may("general.view_option_columns"):
            choices = [[x, "%s" % x] for x in config.view_option_columns]
            view_optiondial(thisview, "num_columns", choices,
                            _("Change the number of display columns"))
        else:
            view_optiondial_off("num_columns")

        if display_options.enabled(
                display_options.R) and config.user.may("general.view_option_refresh"):
            choices = [[x, {
                0: _("off")
            }.get(x,
                  str(x) + "s")] for x in config.view_option_refreshes]
            view_optiondial(thisview, "refresh", choices, _("Change the refresh rate"))
        else:
            view_optiondial_off("refresh")
    html.close_div()

    ## Large buttons
    if display_options.enabled(display_options.B):
        # WATO: If we have a host context, then show button to WATO, if permissions allow this
        if html.request.has_var("host") \
           and config.wato_enabled \
           and config.user.may("wato.use") \
           and (config.user.may("wato.hosts") or config.user.may("wato.seeall")):
            host = html.request.var("host")
            if host:
                url = _link_to_host_by_name(host)
            else:
                url = _link_to_folder_by_path(html.request.var("wato_folder", ""))
            html.context_button(_("WATO"),
                                url,
                                "wato",
                                id_="wato",
                                bestof=config.context_buttons_to_show)

        # Button for creating an instant report (if reporting is available)
        if config.reporting_available() and config.user.may("general.reporting"):
            html.context_button(_("Export as PDF"),
                                html.makeuri([], filename="report_instant.py"),
                                "report",
                                class_="context_pdf_export")

        # Buttons to other views, dashboards, etc.
        links = visuals.collect_context_links(thisview)
        for linktitle, uri, icon, buttonid in links:
            html.context_button(linktitle,
                                url=uri,
                                icon=icon,
                                id_=buttonid,
                                bestof=config.context_buttons_to_show)

    # Customize/Edit view button
    if display_options.enabled(display_options.E) and config.user.may("general.edit_views"):
        url_vars = [
            ("back", html.request.requested_url),
            ("load_name", thisview["name"]),
        ]

        if thisview["owner"] != config.user.id:
            url_vars.append(("load_user", thisview["owner"]))

        url = html.makeuri_contextless(url_vars, filename="edit_view.py")
        html.context_button(_("Edit View"),
                            url,
                            "edit",
                            id_="edit",
                            bestof=config.context_buttons_to_show)

    if display_options.enabled(display_options.E):
        if _show_availability_context_button(view):
            html.context_button(_("Availability"), html.makeuri([("mode", "availability")]),
                                "availability")

        if _show_combined_graphs_context_button(view):
            html.context_button(
                _("Combined graphs"),
                html.makeuri(
                    [
                        ("single_infos", ",".join(thisview["single_infos"])),
                        ("datasource", thisview["datasource"]),
                        ("view_title", view_title(thisview)),
                    ],
                    filename="combined_graphs.py",
                ), "pnp")

    if display_options.enabled(display_options.B):
        execute_hooks('buttons-end')

    html.end_context_buttons()


def _show_availability_context_button(view):
    if not config.user.may("general.see_availability"):
        return False

    if "aggr" in view.datasource.infos:
        return True

    return view.datasource.ident in ["hosts", "services"]


def _show_combined_graphs_context_button(view):
    if not config.combined_graphs_available():
        return False

    return view.datasource.ident in ["hosts", "services", "hostsbygroup", "servicesbygroup"]


def _link_to_folder_by_path(path):
    # type: (str) -> str
    """Return an URL to a certain WATO folder when we just know its path"""
    return html.makeuri_contextless([("mode", "folder"), ("folder", path)], filename="wato.py")


def _link_to_host_by_name(host_name):
    # type: (str) -> str
    """Return an URL to the edit-properties of a host when we just know its name"""
    return html.makeuri_contextless([("mode", "edit_host"), ("host", host_name)],
                                    filename="wato.py")


def update_context_links(enable_command_toggle, enable_checkbox_toggle):
    html.javascript("cmk.views.update_togglebutton('commands', %d);" %
                    (enable_command_toggle and 1 or 0))
    html.javascript("cmk.views.update_togglebutton('checkbox', %d);" %
                    (enable_command_toggle and enable_checkbox_toggle and 1 or 0,))


@cmk.gui.pages.register("count_context_button")
def ajax_count_button():
    id_ = html.request.var("id")
    counts = config.user.load_file("buttoncounts", {})
    for i in counts:
        counts[i] *= 0.95
    counts.setdefault(id_, 0)
    counts[id_] += 1
    config.user.save_file("buttoncounts", counts)


# Sort data according to list of sorters. The tablename
# is needed in order to handle different column names
# for same objects (e.g. host_name in table services and
# simply name in table hosts)
def sort_data(data, sorters):
    if not sorters:
        return

    # Handle case where join columns are not present for all rows
    def safe_compare(compfunc, row1, row2):
        if row1 is None and row2 is None:
            return 0
        elif row1 is None:
            return -1
        elif row2 is None:
            return 1

        return compfunc(row1, row2)

    def multisort(e1, e2):
        for entry in sorters:
            neg = -1 if entry.negate else 1

            if entry.join_key:  # Sorter for join column, use JOIN info
                c = neg * safe_compare(entry.sorter.cmp, e1["JOIN"].get(entry.join_key),
                                       e2["JOIN"].get(entry.join_key))
            else:
                c = neg * entry.sorter.cmp(e1, e2)

            if c != 0:
                return c
        return 0  # equal

    data.sort(multisort)


def sorters_of_datasource(ds_name):
    return _allowed_for_datasource(sorter_registry, ds_name)


def painters_of_datasource(ds_name):
    return _allowed_for_datasource(painter_registry, ds_name)


def join_painters_of_datasource(ds_name):
    datasource = data_source_registry[ds_name]()
    if datasource.join is None:
        return {}  # no joining with this datasource

    # Get the painters allowed for the join "source" and "target"
    painters = painters_of_datasource(ds_name)
    join_painters_unfiltered = _allowed_for_datasource(painter_registry, datasource.join[0])

    # Filter out painters associated with the "join source" datasource
    join_painters = {}
    for key, val in join_painters_unfiltered.items():
        if key not in painters:
            join_painters[key] = val

    return join_painters


# Filters a list of sorters or painters and decides which of
# those are available for a certain data source
def _allowed_for_datasource(collection, ds_name):
    datasource = data_source_registry[ds_name]()
    infos_available = set(datasource.infos)
    add_columns = datasource.add_columns

    allowed = {}
    for name, plugin_class in collection.items():
        plugin = plugin_class()
        infos_needed = infos_needed_by_painter(plugin, add_columns)
        if len(infos_needed.difference(infos_available)) == 0:
            allowed[name] = plugin
    return allowed


def infos_needed_by_painter(painter, add_columns=None):
    if add_columns is None:
        add_columns = []

    return {c.split("_", 1)[0] for c in painter.columns if c != "site" and c not in add_columns}


def painter_choices(painters, add_params=False):
    choices = []

    for name, painter in painters.items():
        title = get_painter_title_for_choices(painter)

        # Add the optional valuespec for painter parameters
        if add_params and painter.parameters:
            choices.append((name, title, painter.parameters))
        else:
            choices.append((name, title))

    return sorted(choices, key=lambda x: x[1])


def get_painter_title_for_choices(painter):
    info_title = "/".join([
        visual_info_registry[info_name]().title_plural
        for info_name in sorted(infos_needed_by_painter(painter))
    ])

    # TODO: Cleanup the special case for sites. How? Add an info for it?
    if painter.columns == ["site"]:
        info_title = _("Site")

    if callable(painter.title):
        title = painter.title()
    else:
        title = painter.title

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
    what = datasource.infos[0]
    for command_class in command_registry.values():
        command = command_class()
        if what in command.tables and config.user.may(command.permission().name):
            return True

    return False


def show_command_form(is_open, datasource):
    # What commands are available depends on the Livestatus table we
    # deal with. If a data source provides information about more
    # than one table, (like services datasource also provide host
    # information) then the first info is the primary table. So 'what'
    # will be one of "host", "service", "command" or "downtime".
    what = datasource.infos[0]

    html.open_div(id_="commands",
                  class_=["view_form"],
                  style="display:none;" if not is_open else None)
    html.begin_form("actions")
    html.hidden_field("_do_actions", "yes")
    html.hidden_field("actions", "yes")
    html.hidden_fields()  # set all current variables, exception action vars

    # Show command forms, grouped by (optional) command group
    by_group = {}
    for command_class in command_registry.values():
        command = command_class()
        if what in command.tables and config.user.may(command.permission().name):
            # Some special commands can be shown on special views using this option.
            # It is currently only used in custom views, not shipped with check_mk.
            if command.only_view and html.request.var('view_name') != command.only_view:
                continue
            by_group.setdefault(command.group, []).append(command)

    for group_class, group_commands in sorted(by_group.items(), key=lambda x: x[0]().sort_index):
        forms.header(group_class().title, narrow=True)
        for command in group_commands:
            forms.section(command.title)
            command.render(what)

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
    for cmd_class in command_registry.values():
        cmd = cmd_class()
        if config.user.may(cmd.permission().name):
            result = cmd.action(cmdtag, spec, row, row_nr, total_rows)
            if result:
                executor = cmd.executor
                commands, title = result
                break

    # Use the title attribute to determine if a command exists, since the list
    # of commands might be empty (e.g. in case of "remove all downtimes" where)
    # no downtime exists in a selection of rows.
    if not title:
        raise MKUserError(None, _("Sorry. This command is not implemented."))

    # Some commands return lists of commands, others
    # just return one basic command. Convert those
    if not isinstance(commands, list):
        commands = [commands]

    return commands, title, executor


# Returns:
# True -> Actions have been done
# False -> No actions done because now rows selected
# [...] new rows -> Rows actions (shall/have) be performed on
def do_actions(view, what, action_rows, backurl):
    if not config.user.may("general.act"):
        html.show_error(
            _("You are not allowed to perform actions. "
              "If you think this is an error, please ask "
              "your administrator grant you the permission to do so."))
        return False  # no actions done

    if not action_rows:
        message = _("No rows selected to perform actions for.")
        if html.output_format == "html":  # sorry for this hack
            message += '<br><a href="%s">%s</a>' % (backurl, _('Back to view'))
        html.show_error(message)
        return False  # no actions done

    command = None
    title, executor = core_command(what, action_rows[0], 0,
                                   len(action_rows))[1:3]  # just get the title and executor
    if not html.confirm(_("Do you really want to %(title)s the following %(count)d %(what)s?") % {
            "title": title,
            "count": len(action_rows),
            "what": visual_info_registry[what]().title_plural,
    },
                        method='GET'):
        return False

    count = 0
    already_executed = set([])
    for nr, row in enumerate(action_rows):
        core_commands, title, executor = core_command(what, row, nr, len(action_rows))
        for command_entry in core_commands:
            site = row.get(
                "site")  # site is missing for BI rows (aggregations can spawn several sites)
            if (site, command_entry) not in already_executed:
                # Some command functions return the information about the site per-command (e.g. for BI)
                if isinstance(command_entry, tuple):
                    site, command = command_entry
                else:
                    command = command_entry

                if isinstance(command, unicode):
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
        if html.output_format == "html":  # sorry for this hack
            backurl += "&filled_in=filter"
            message += '<br><a href="%s">%s</a>' % (backurl, _('Back to view'))
            if html.request.var("show_checkboxes") == "1":
                html.request.del_var("selection")
                weblib.selection_id()
                backurl += "&selection=" + html.request.var("selection")
                message += '<br><a href="%s">%s</a>' % (backurl,
                                                        _('Back to view with checkboxes reset'))
            if html.request.var("_show_result") == "0":
                html.immediate_browser_redirect(0.5, backurl)
        html.message(message)

    return True


def filter_by_row_id(view, rows):
    wanted_row_id = html.request.var("_row_id")

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
    if viewname in get_permitted_views():
        return "view.py?view_name=%s" % viewname
    return None


@cmk.gui.pages.register("export_views")
def ajax_export():
    for view in get_permitted_views().itervalues():
        view["owner"] = ''
        view["public"] = True
    html.write(pprint.pformat(get_permitted_views()))


def get_view_by_name(view_name):
    return get_permitted_views()[view_name]


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
        except Exception:
            if config.debug:
                raise MKGeneralException(
                    _('Problem while executing hook function %s in hook %s: %s') %
                    (hook_func.__name__, hook, traceback.format_exc()))
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
    varprefix = html.request.var('varprefix')
    value = html.request.var('value')
    allow_empty = html.request.var('allow_empty') == '1'

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
    site = html.request.var('site')
    host = html.request.var('host')
    svcdesc = html.get_unicode_input('service')
    what = 'service' if svcdesc else 'host'

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
    except Exception as e:
        html.write("['ERROR', '%s']\n" % e)


def do_reschedule():
    if not config.user.may("action.reschedule"):
        raise MKGeneralException("You are not allowed to reschedule checks.")

    site = html.request.var("site")
    host = html.request.var("host", "")
    if not host:
        raise MKGeneralException("Action reschedule: missing host name")

    service = html.get_unicode_input("service", "")
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
        sites.live().command(
            "[%d] SCHEDULE_FORCED_%s_CHECK;%s;%d" % (now, cmd, livestatus.lqencode(spec), now),
            site)
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
            html.write("['TIMEOUT', 'Check not executed within %d seconds']\n" %
                       (config.reschedule_timeout))
        else:
            if service == "Check_MK":
                # Passive services triggered by Check_MK often are updated
                # a few ms later. We introduce a small wait time in order
                # to increase the chance for the passive services already
                # updated also when we return.
                time.sleep(0.7)
            html.write("['OK', %d, %d, %r]\n" % (row[0], row[1], row[2].encode("utf-8")))

    except Exception as e:
        sites.live().set_only_sites()
        raise MKGeneralException(_("Cannot reschedule check: %s") % e)
