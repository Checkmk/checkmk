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
import copy
import json
from typing import (  # pylint: disable=unused-import
    Any, Dict, Optional,
)

import cmk.gui.pages
import cmk.gui.notify as notify
import cmk.gui.config as config
import cmk.gui.visuals as visuals
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
import cmk.gui.utils as utils
from cmk.gui.valuespec import (
    Transform,
    Dictionary,
    TextUnicode,
    DropdownChoice,
    Checkbox,
    FixedValue,
)
import cmk.gui.i18n
from cmk.gui.i18n import _u, _
from cmk.gui.log import logger
from cmk.gui.globals import html

from cmk.gui.exceptions import (
    HTTPRedirect,
    MKGeneralException,
    MKAuthException,
    MKUserError,
)
from cmk.gui.permissions import (
    declare_permission,
    permission_section_registry,
    PermissionSection,
)
from cmk.gui.plugins.visuals.utils import (
    visual_info_registry,
    visual_type_registry,
    VisualType,
)

import cmk.gui.plugins.dashboard

if not cmk.is_raw_edition():
    import cmk.gui.cee.plugins.dashboard

if cmk.is_managed_edition():
    import cmk.gui.cme.plugins.dashboard

from cmk.gui.plugins.views.utils import (
    data_source_registry,
    get_permitted_views,
    get_all_views,
)
from cmk.gui.plugins.dashboard.utils import (
    builtin_dashboards,
    GROW,
    MAX,
    dashlet_types,
    dashlet_registry,
    Dashlet,
)

loaded_with_language = False
builtin_dashboards_transformed = False

# These settings might go into the config module, sometime in future,
# in order to allow the user to customize this.

screen_margin = 5  # Distance from the left border of the main-frame to the dashboard area
dashlet_padding = 34, 4, -2, 4, 4  # Margin (N, E, S, W, N w/o title) between outer border of dashlet and its content
#dashlet_padding  = 23, 2, 2, 2, 2 # Margin (N, E, S, W, N w/o title) between outer border of dashlet and its content
raster = 10  # Raster the dashlet coords are measured in (px)


@visual_type_registry.register
class VisualTypeDashboards(VisualType):
    @property
    def ident(self):
        return "dashboards"

    @property
    def title(self):
        return _("dashboard")

    @property
    def plural_title(self):
        return _("dashboards")

    @property
    def ident_attr(self):
        return "name"

    @property
    def multicontext_links(self):
        return False

    @property
    def show_url(self):
        return "dashboard.py"

    def popup_add_handler(self, add_type):
        if not config.user.may("general.edit_dashboards"):
            return []

        if add_type in ["availability", "graph_collection"]:
            return

        load_dashboards()
        return [(name, board["title"]) for (name, board) in available_dashboards.items()]

    def add_visual_handler(self, target_visual_name, add_type, context, parameters):
        if not config.user.may("general.edit_dashboards"):
            # Exceptions do not work here.
            return

        if add_type == "pnpgraph" and context is None:
            # Raw Edition graphs are added correctly by htdocs/js/checkmk.js create_pnp_graph().
            # Enterprise Edition graphs:
            #
            # Context will always be None here, but the specification (in parameters)
            # will contain it. Transform the data to the format needed by the dashlets.
            #
            # Example:
            # parameters = [ 'template', {'service_description': 'CPU load', 'site': 'mysite',
            #                         'graph_index': 0, 'host_name': 'server123'}])
            specification = parameters["definition"]["specification"]
            if specification[0] == "template":
                context = {"host": specification[1]["host_name"]}
                if specification[1].get("service_description") != "_HOST_":
                    context["service"] = specification[1]["service_description"]
                parameters = {"source": specification[1]["graph_index"] + 1}

            elif specification[0] == "custom":
                # Override the dashlet type here. It would be better to get the
                # correct dashlet type from the menu. But this does not seem to
                # be a trivial change.
                add_type = "custom_graph"
                context = {}
                parameters = {
                    "custom_graph": specification[1],
                }

            else:
                raise MKGeneralException(_("Invalid graph type '%s'") % specification[0])

        load_dashboards(lock=True)

        if target_visual_name not in available_dashboards:
            return
        dashboard = load_dashboard_with_cloning(target_visual_name)

        dashlet = default_dashlet_definition(add_type)

        dashlet["context"] = context
        if add_type == 'view':
            view_name = parameters['name']
        else:
            dashlet.update(parameters)

        # When a view shal be added to the dashboard, load the view and put it into the dashlet
        # FIXME: Mave this to the dashlet plugins
        if add_type == 'view':
            # save the original context and override the context provided by the view
            context = dashlet['context']
            load_view_into_dashlet(dashlet,
                                   len(dashboard['dashlets']),
                                   view_name,
                                   add_context=context)

        elif add_type in ["pnpgraph", "custom_graph"]:
            # The "add to visual" popup does not provide a timerange information,
            # but this is not an optional value. Set it to 25h initially.
            dashlet.setdefault("timerange", "1")

        add_dashlet(dashlet, dashboard)

        # Directly go to the dashboard in edit mode. We send the URL as an answer
        # to the AJAX request
        html.write('OK dashboard.py?name=' + target_visual_name + '&edit=1')

    def load_handler(self):
        load_dashboards()

    @property
    def permitted_visuals(self):
        return permitted_dashboards()


@permission_section_registry.register
class PermissionSectionDashboard(PermissionSection):
    @property
    def name(self):
        return "dashboard"

    @property
    def title(self):
        return _("Dashboards")

    @property
    def do_sort(self):
        return True


# Load plugins in web/plugins/dashboard and declare permissions,
# note: these operations produce language-specific results and
# thus must be reinitialized everytime a language-change has
# been detected.
def load_plugins(force):
    global loaded_with_language, dashboards, builtin_dashboards_transformed
    if loaded_with_language == cmk.gui.i18n.get_current_language() and not force:
        return

    # Load plugins for dashboards. Currently these files
    # just may add custom dashboards by adding to builtin_dashboards.
    builtin_dashboards_transformed = False
    utils.load_web_plugins("dashboard", globals())

    _transform_old_dict_based_dashlets()

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = cmk.gui.i18n.get_current_language()

    # Clear this structure to prevent users accessing dashboard structures created
    # by other users, make them see these dashboards
    dashboards = {}

    visuals.declare_visual_permissions('dashboards', _("dashboards"))

    # Declare permissions for all dashboards
    for name, board in builtin_dashboards.items():
        declare_permission(
            "dashboard.%s" % name,
            board["title"],
            board.get("description", ""),
            config.builtin_role_ids,
        )

    # Make sure that custom views also have permissions
    config.declare_dynamic_permissions(lambda: visuals.declare_custom_permissions('dashboards'))


class LegacyDashlet(cmk.gui.plugins.dashboard.IFrameDashlet):
    """Helper to be able to handle pre 1.6 dashlet_type declared dashlets"""
    _type_name = ""
    _spec = {}  # type: Dict[str, Any]

    @classmethod
    def type_name(cls):
        return cls._type_name

    @classmethod
    def title(cls):
        return cls._spec["title"]

    @classmethod
    def description(cls):
        return cls._spec["description"]

    @classmethod
    def sort_index(cls):
        return cls._spec["sort_index"]

    @classmethod
    def infos(cls):
        return cls._spec.get("infos", [])

    @classmethod
    def single_infos(cls):
        return cls._spec.get("single_infos", [])

    @classmethod
    def is_selectable(cls):
        return cls._spec.get("selectable", True)

    @classmethod
    def is_resizable(cls):
        return cls._spec.get("resizable", True)

    @classmethod
    def is_iframe_dashlet(cls):
        return "iframe_render" in cls._spec or "iframe_urlfunc" in cls._spec

    @classmethod
    def initial_size(cls):
        return cls._spec.get("size", Dashlet.minimum_size)

    @classmethod
    def vs_parameters(cls):
        return cls._spec.get("parameters", None)

    @classmethod
    def opt_parameters(cls):
        """List of optional parameters in case vs_parameters() returns a list"""
        return cls._spec.get("opt_params")

    @classmethod
    def validate_parameters_func(cls):
        """Optional validation function in case vs_parameters() returns a list"""
        return cls._spec.get("validate_params")

    @classmethod
    def initial_refresh_interval(cls):
        return cls._spec.get("refresh", False)

    @classmethod
    def allowed_roles(cls):
        return cls._spec.get("allowed", config.builtin_role_ids)

    @classmethod
    def styles(cls):
        return cls._spec.get("styles")

    @classmethod
    def script(cls):
        return cls._spec.get("script")

    @classmethod
    def add_url(cls):
        if "add_urlfunc" in cls._spec:
            return cls._spec["add_urlfunc"]()
        return super(LegacyDashlet, cls).add_url()

    def display_title(self):
        title_func = self._spec.get("title_func")
        if title_func:
            return title_func(self._dashlet_spec)
        return self.title()

    def on_resize(self):
        on_resize_func = self._spec.get("on_resize")
        if on_resize_func:
            return on_resize_func(self._dashlet_id, self._dashlet_spec)
        return None

    def on_refresh(self):
        on_refresh_func = self._spec.get("on_refresh")
        if on_refresh_func:
            return on_refresh_func(self._dashlet_id, self._dashlet_spec)
        return None

    def update(self):
        if self.is_iframe_dashlet():
            self._spec['iframe_render'](self._dashlet_id, self._dashlet_spec)
        else:
            self._spec['render'](self._dashlet_id, self._dashlet_spec)

    def show(self):
        if "render" in self._spec:
            self._spec['render'](self._dashlet_id, self._dashlet_spec)

        elif self.is_iframe_dashlet():
            self._show_initial_iframe_container()

    def _get_iframe_url(self):
        # type: () -> Optional[str]
        if not self.is_iframe_dashlet():
            return None

        if "iframe_urlfunc" in self._spec:
            # Optional way to render a dynamic iframe URL
            url = self._spec["iframe_urlfunc"](self._dashlet_spec)
            return url

        return super(LegacyDashlet, self)._get_iframe_url()


# Pre Check_MK 1.6 the dashlets were declared with dictionaries like this:
#
# dashlet_types["hoststats"] = {
#     "title"       : _("Host Statistics"),
#     "sort_index"  : 45,
#     "description" : _("Displays statistics about host states as globe and a table."),
#     "render"      : dashlet_hoststats,
#     "refresh"     : 60,
#     "allowed"     : config.builtin_role_ids,
#     "size"        : (30, 18),
#     "resizable"   : False,
# }
#
# Convert it to objects to be compatible
# TODO: Deprecate this one day.
def _transform_old_dict_based_dashlets():
    for dashlet_type_id, dashlet_spec in dashlet_types.items():

        @dashlet_registry.register
        class LegacyDashletType(LegacyDashlet):
            _type_name = dashlet_type_id
            _spec = dashlet_spec

        _it_is_really_used = LegacyDashletType  # help pylint


dashboards = {}  # type: Dict
available_dashboards = {}  # type: Dict


def load_dashboards(lock=False):
    global dashboards, available_dashboards
    transform_builtin_dashboards()
    dashboards = visuals.load('dashboards', builtin_dashboards, lock=lock)
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
def transform_dashboards(boards):
    for dashboard in boards.itervalues():
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
        return  # Only do this once
    for name, dashboard in builtin_dashboards.items():
        # Do not transform dashboards which are already in the new format
        if 'context' in dashboard:
            continue

        # Transform the dashlets
        for nr, dashlet in enumerate(dashboard['dashlets']):
            dashlet.setdefault('show_title', True)

            if dashlet.get('url', '').startswith('dashlet_hoststats') or \
                dashlet.get('url', '').startswith('dashlet_servicestats'):

                # hoststats and servicestats
                dashlet['type'] = dashlet['url'][8:].split('.', 1)[0]

                if '?' in dashlet['url']:
                    # Transform old parameters:
                    # wato_folder
                    # host_contact_group
                    # service_contact_group
                    paramstr = dashlet['url'].split('?', 1)[1]
                    dashlet['context'] = {}
                    for key, val in [p.split('=', 1) for p in paramstr.split('&')]:
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

            elif dashlet.get('urlfunc') and not isinstance(dashlet['urlfunc'], str):
                raise MKGeneralException(
                    _('Unable to transform dashlet %d of dashboard %s: '
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
                load_view_into_dashlet(dashlet, nr, view_name, load_from_all_views=True)
                del dashlet['view']

            else:
                raise MKGeneralException(
                    _('Unable to transform dashlet %d of dashboard %s. '
                      'You will need to migrate it on your own. Definition: %r') %
                    (nr, name, html.attrencode(dashlet)))

            dashlet.setdefault('context', {})
            dashlet.setdefault('single_infos', [])

        # the modification time of builtin dashboards can not be checked as on user specific
        # dashboards. Set it to 0 to disable the modification chech.
        dashboard.setdefault('mtime', 0)

        dashboard.setdefault('show_title', True)
        if dashboard['title'] is None:
            dashboard['title'] = _('No title')
            dashboard['show_title'] = False

        dashboard.setdefault('single_infos', [])
        dashboard.setdefault('context', {})
        dashboard.setdefault('topic', _('Overview'))
        dashboard.setdefault('description', dashboard.get('title', ''))
    builtin_dashboards_transformed = True


def load_view_into_dashlet(dashlet, nr, view_name, add_context=None, load_from_all_views=False):
    permitted_views = get_permitted_views()

    # it is random which user is first accessing
    # an apache python process, initializing the dashboard loading and conversion of
    # old dashboards. In case of the conversion we really try hard to make the conversion
    # work in all cases. So we need all views instead of the views of the user.
    if load_from_all_views and view_name not in permitted_views:
        # This is not really 100% correct according to the logic of visuals.available(),
        # but we do this for the rare edge case during legacy dashboard conversion, so
        # this should be sufficient
        view = None
        for (_u, n), this_view in get_all_views().iteritems():
            # take the first view with a matching name
            if view_name == n:
                view = this_view
                break

        if not view:
            raise MKGeneralException(
                _("Failed to convert a builtin dashboard which is referencing "
                  "the view \"%s\". You will have to migrate it to the new "
                  "dashboard format on your own to work properly.") % view_name)
    else:
        view = permitted_views[view_name]

    view = copy.deepcopy(view)  # Clone the view
    dashlet.update(view)
    if add_context:
        dashlet['context'].update(add_context)

    # Overwrite the views default title with the context specific title
    dashlet['title'] = visuals.visual_title('view', view)
    dashlet['title_url'] = html.makeuri_contextless([('view_name', view_name)] +
                                                    visuals.get_singlecontext_vars(view).items(),
                                                    filename='view.py')

    dashlet['type'] = 'view'
    dashlet['name'] = 'dashlet_%d' % nr
    dashlet['show_title'] = True
    dashlet['mustsearch'] = False


def save_dashboards(us):
    visuals.save('dashboards', dashboards)


def permitted_dashboards():
    return available_dashboards


# HTML page handler for generating the (a) dashboard. The name
# of the dashboard to render is given in the HTML variable 'name'.
# This defaults to "main".
@cmk.gui.pages.register("dashboard")
def page_dashboard():
    load_dashboards()

    name = html.request.var("name")
    if not name:
        name = "main"
        html.request.set_var("name", name)  # make sure that URL context is always complete
    if name not in available_dashboards:
        raise MKUserError("name", _('The requested dashboard does not exist.'))

    draw_dashboard(name)


def load_dashboard_with_cloning(name, edit=True):
    board = available_dashboards[name]
    if edit and board['owner'] != config.user.id:
        # This dashboard which does not belong to the current user is about to
        # be edited. In order to make this possible, the dashboard is being
        # cloned now!
        board = copy.deepcopy(board)
        board['owner'] = config.user.id
        board['public'] = False

        dashboards[(config.user.id, name)] = board
        available_dashboards[name] = board
        visuals.save('dashboards', dashboards)

    return board


# Actual rendering function
def draw_dashboard(name):
    mode = 'display'
    if html.request.var('edit') == '1':
        mode = 'edit'

    if mode == 'edit' and not config.user.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = load_dashboard_with_cloning(name, edit=mode == 'edit')

    # The dashboard may be called with "wato_folder" set. In that case
    # the dashboard is assumed to restrict the shown data to a specific
    # WATO subfolder or file. This could be a configurable feature in
    # future, but currently we assume, that *all* dashboards are filename
    # sensitive.
    wato_folder = html.request.var("wato_folder")

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
        title = watolib.get_folder_title(wato_folder) + " - " + title

    html.add_body_css_class("dashboard")
    html.header(title)

    html.open_div(class_=["dashboard_%s" % name], id_="dashboard")  # Container of all dashlets

    dashlet_javascripts(board)
    dashlet_styles(board)

    refresh_dashlets = []  # Dashlets with automatic refresh, for Javascript
    dashlet_coords = []  # Dimensions and positions of dashlet
    on_resize_dashlets = {}  # javascript function to execute after ressizing the dashlet
    for nr, dashlet in enumerate(board["dashlets"]):
        dashlet_content_html = ""
        dashlet_title_html = ""
        try:
            dashlet_type = get_dashlet_type(dashlet)
            dashlet_instance = dashlet_type(name, board, nr, dashlet, wato_folder)

            refresh = get_dashlet_refresh(dashlet_instance)
            if refresh:
                refresh_dashlets.append(refresh)

            on_resize = get_dashlet_on_resize(dashlet_instance)
            if on_resize:
                on_resize_dashlets[nr] = on_resize

            dashlet_title_html = render_dashlet_title_html(dashlet_instance)
            dashlet_content_html = render_dashlet_content(dashlet_instance, is_update=False)

        except Exception as e:
            dashlet_content_html = render_dashlet_exception_content(dashlet_instance, nr, e)

        # Now after the dashlet content has been calculated render the whole dashlet
        dashlet_container_begin(nr, dashlet)
        draw_dashlet(dashlet_instance, dashlet_content_html, dashlet_title_html)
        dashlet_container_end()
        dashlet_coords.append(get_dashlet_dimensions(dashlet_instance))

    dashboard_edit_controls(name, board)

    dashboard_properties = {
        "MAX": MAX,
        "GROW": GROW,
        "grid_size": raster,
        "header_height": header_height,
        "screen_margin": screen_margin,
        "dashlet_padding": dashlet_padding,
        "dashlet_min_size": Dashlet.minimum_size,
        "refresh_dashlets": refresh_dashlets,
        "on_resize_dashlets": on_resize_dashlets,
        "dashboard_name": name,
        "dashboard_mtime": board['mtime'],
        "dashlets": dashlet_coords,
    }

    html.javascript("""
cmk.dashboard.set_dashboard_properties(%s);
cmk.dashboard.calculate_dashboard();
window.onresize = function () { cmk.dashboard.calculate_dashboard(); }
cmk.dashboard.execute_dashboard_scheduler(1);
cmk.dashboard.register_event_handlers();
    """ % json.dumps(dashboard_properties))

    if mode == 'edit':
        html.javascript('cmk.dashboard.toggle_dashboard_edit(true)')

    html.body_end()  # omit regular footer with status icons, etc.


def dashlet_container_begin(nr, dashlet):
    dashlet_type = get_dashlet_type(dashlet)

    classes = ['dashlet', dashlet['type']]
    if dashlet_type.is_resizable():
        classes.append('resizable')

    html.open_div(id_="dashlet_%d" % nr, class_=classes)


def dashlet_container_end():
    html.close_div()


def render_dashlet_title_html(dashlet_instance):
    title = dashlet_instance.display_title()
    if title is not None and dashlet_instance.show_title():
        url = dashlet_instance.title_url()
        if url:
            title = html.render_a(_u(title), url)
        else:
            title = _u(title)
    return title


def render_dashlet_content(dashlet_instance, is_update, stash_html_vars=True):
    def update_or_show():
        visuals.add_context_to_uri_vars(dashlet_instance.dashlet_spec)
        if dashlet_instance.wato_folder is not None:
            html.request.set_var("wato_folder", dashlet_instance.wato_folder)
        with html.plugged():
            if is_update:
                dashlet_instance.update()
            else:
                dashlet_instance.show()
            return html.drain()

    if stash_html_vars:
        with html.stashed_vars():
            html.request.del_vars()
            html.request.set_var("name", dashlet_instance.dashboard_name)
            return update_or_show()
    else:
        return update_or_show()


def render_dashlet_exception_content(dashlet_instance, nr, e):
    logger.exception("Problem while rendering dashlet %d of type %s" %
                     (nr, dashlet_instance.type_name()))

    # Unify different string types from exception messages to a unicode string
    try:
        exc_txt = unicode(e)
    except UnicodeDecodeError:
        exc_txt = str(e).decode("utf-8")

    return html.render_error(
        _("Problem while rendering dashlet %d of type %s: %s. Have a look at <tt>var/log/web.log</tt> for "
          "further information.") % (nr, dashlet_instance.type_name(), exc_txt))


def dashboard_edit_controls(name, board):
    # Show the edit menu to all users which are allowed to edit dashboards
    if not config.user.may("general.edit_dashboards"):
        return

    html.open_ul(style="display:none;", class_=["menu"], id_="controls")

    if board['owner'] != config.user.id:
        # Not owned dashboards must be cloned before being able to edit. Do not switch to
        # edit mode using javascript, use the URL with edit=1. When this URL is opened,
        # the dashboard will be cloned for this user
        html.li(html.render_a(_("Edit Dashboard"), href=html.makeuri([("edit", 1)])))

    else:
        #
        # Add dashlet menu
        #
        html.open_li(class_=["sublink"],
                     id_="control_add",
                     style="display:%s;" % ("block" if html.request.var("edit") == '1' else "none"),
                     onmouseover="cmk.dashboard.show_submenu(\'control_add\');")
        html.open_a(href="javascript:void(0)")
        html.icon(title=_("Add dashlet"), icon="dashboard_menuarrow")
        html.write_text(_("Add dashlet"))
        html.close_a()

        # The dashlet types which can be added to the view
        html.open_ul(style="display:none", class_=["menu", "sub"], id_="control_add_sub")

        # TODO: Why is this done like this? Looks like a dirty hack.
        # - Mypy does not understand this. We could probably use type(..., ..., ...) here instead.
        # - Or event better: Just produce a new menu entry below without registering something new
        #   to the dashlet registry.
        class ExistingView(dashlet_registry['view']):  # type: ignore
            @classmethod
            def title(cls):
                return _('Existing View')

            @classmethod
            def add_url(cls):
                return 'create_view_dashlet.py?name=%s&create=0&back=%s' % \
                            (html.urlencode(name), html.urlencode(html.makeuri([('edit', '1')])))

        dashlet_registry.register(ExistingView)

        for ty, dashlet_type in sorted(dashlet_registry.items(), key=lambda x: x[1].sort_index()):
            if dashlet_type.is_selectable():
                url = dashlet_type.add_url()
                html.open_li()
                html.open_a(href=url)
                html.icon(title=dashlet_type.title(), icon="dashlet_%s" % ty)
                html.write(dashlet_type.title())
                html.close_a()
                html.close_li()
        html.close_ul()

        html.close_li()

        #
        # Properties link
        #
        html.open_li()
        html.open_a(href="edit_dashboard.py?load_name=%s&back=%s" %
                    (name, html.urlencode(html.makeuri([]))),
                    onmouseover="cmk.dashboard.hide_submenus();")
        html.icon(title="", icon="trans")
        html.write(_('Properties'))
        html.close_a()
        html.close_li()

        #
        # Stop editing
        #
        html.open_li(style="display:%s;" % ("block" if html.request.var("edit") == '1' else "none"),
                     id_="control_view")
        html.open_a(href="javascript:void(0)",
                    onclick="cmk.dashboard.toggle_dashboard_edit(false)",
                    onmouseover="cmk.dashboard.hide_submenus();")
        html.icon(title="", icon="trans")
        html.write(_('Stop Editing'))
        html.close_a()
        html.close_li()

        #
        # Enable editing link
        #
        html.open_li(style="display:%s;" % ("none" if html.request.var("edit") == '1' else "block"),
                     id_="control_edit")
        html.open_a(href="javascript:void(0)", onclick="cmk.dashboard.toggle_dashboard_edit(true);")
        html.icon(title="", icon="trans")
        html.write(_('Edit Dashboard'))
        html.close_a()
        html.close_li()

    html.close_ul()

    html.icon_button(None,
                     _('Edit the Dashboard'),
                     'dashboard_controls',
                     'controls_toggle',
                     onclick='void(0)')

    html.close_div()


# Render dashlet custom scripts
def dashlet_javascripts(board):
    scripts = '\n'.join([ty.script() for ty in used_dashlet_types(board) if ty.script()])
    if scripts:
        html.javascript(scripts)


# Render dashlet custom styles
def dashlet_styles(board):
    styles = '\n'.join([ty.styles() for ty in used_dashlet_types(board) if ty.styles()])
    if styles:
        html.style(styles)


def used_dashlet_types(board):
    type_names = list(set([d['type'] for d in board['dashlets']]))
    return [dashlet_registry[ty] for ty in type_names]


# dashlets using the 'url' method will be refreshed by us. Those
# dashlets using static content (such as an iframe) will not be
# refreshed by us but need to do that themselves.
# TODO: Refactor this to Dashlet or later Dashboard class
def get_dashlet_refresh(dashlet_instance):
    if dashlet_instance.type_name() == "url" or (not dashlet_instance.is_iframe_dashlet() and
                                                 dashlet_instance.refresh_interval()):
        refresh = dashlet_instance.refresh_interval()
        if not refresh:
            return

        action = dashlet_instance.get_refresh_action()
        if action:
            return [dashlet_instance.dashlet_id, refresh, action]
    return None


# TODO: Refactor this to Dashlet or later Dashboard class
def get_dashlet_on_resize(dashlet_instance):
    on_resize = dashlet_instance.on_resize()
    if on_resize:
        return '(function() {%s})' % on_resize
    return None


# TODO: Refactor this to Dashlet or later Dashboard class
def get_dashlet_dimensions(dashlet_instance):
    dimensions = {}
    dimensions['x'], dimensions['y'] = dashlet_instance.position()
    dimensions['w'], dimensions['h'] = dashlet_instance.size()
    return dimensions


def get_dashlet_type(dashlet):
    return dashlet_registry[dashlet["type"]]


def get_dashlet(board, ident):
    if board not in available_dashboards:
        raise MKUserError("name", _('The requested dashboard does not exist.'))
    dashboard = available_dashboards[board]

    try:
        return dashboard['dashlets'][ident]
    except IndexError:
        raise MKGeneralException(_('The dashlet does not exist.'))


def draw_dashlet(dashlet_instance, dashlet_content_html, dashlet_title_html):
    """Draws the initial HTML code for one dashlet

    Each dashlet has an id "dashlet_%d", where %d is its index (in
    board["dashlets"]).  Javascript uses that id for the resizing. Within that
    div there is an inner div containing the actual dashlet content. This content
    is updated later using the dashboard_dashlet.py ajax call.
    """
    if dashlet_title_html is not None and dashlet_instance.show_title():
        html.div(html.render_span(dashlet_title_html),
                 id_="dashlet_title_%d" % dashlet_instance.dashlet_id,
                 class_=["title"])

    css = ["dashlet_inner"]
    if dashlet_instance.show_background():
        css.append("background")

    html.open_div(id_="dashlet_inner_%d" % dashlet_instance.dashlet_id, class_=css)
    html.write_html(dashlet_content_html)
    html.close_div()


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


@cmk.gui.pages.register("dashboard_dashlet")
def ajax_dashlet():
    name = html.request.var('name')
    if not name:
        raise MKUserError("name", _('The name of the dashboard is missing.'))

    ident = html.get_integer_input("id")

    load_dashboards()

    if name not in available_dashboards:
        raise MKUserError("name", _('The requested dashboard does not exist.'))
    board = available_dashboards[name]

    mtime = html.get_integer_input('mtime', 0)
    if mtime < board['mtime']:
        # prevent reloading on the dashboard which already has the current mtime,
        # this is normally the user editing this dashboard. All others: reload
        # the whole dashboard once.
        html.javascript('if (cmk.dashboard.dashboard_properties.dashboard_mtime < %d) {\n'
                        '    parent.location.reload();\n'
                        '}' % board['mtime'])

    the_dashlet = None
    for nr, dashlet in enumerate(board['dashlets']):
        if nr == ident:
            the_dashlet = dashlet
            break

    if not the_dashlet:
        raise MKUserError("id", _('The dashlet can not be found on the dashboard.'))

    if the_dashlet['type'] not in dashlet_registry:
        raise MKUserError("id", _('The requested dashlet type does not exist.'))

    wato_folder = html.request.var("wato_folder")

    dashlet_type = get_dashlet_type(the_dashlet)
    dashlet_instance = dashlet_type(name, board, ident, the_dashlet, wato_folder)

    try:
        dashlet_content_html = render_dashlet_content(dashlet_instance,
                                                      stash_html_vars=False,
                                                      is_update=True)
    except Exception as e:
        dashlet_content_html = render_dashlet_exception_content(dashlet_instance, ident, e)

    html.write_html(dashlet_content_html)


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


@cmk.gui.pages.register("edit_dashboards")
def page_edit_dashboards():
    load_dashboards(lock=html.is_transaction())
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


@cmk.gui.pages.register("create_dashboard")
def page_create_dashboard():
    visuals.page_create_visual('dashboards', visual_info_registry.keys())


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

vs_dashboard = None


@cmk.gui.pages.register("edit_dashboard")
def page_edit_dashboard():
    global vs_dashboard
    load_dashboards(lock=html.is_transaction())

    # This is not defined here in the function in order to be l10n'able
    vs_dashboard = Dictionary(
        title=_('Dashboard Properties'),
        render='form',
        optional_keys=None,
        elements=[
            ('show_title',
             Checkbox(
                 title=_('Display dashboard title'),
                 label=_('Show the header of the dashboard with the configured title.'),
                 default_value=True,
             )),
        ],
    )

    visuals.page_edit_visual('dashboards',
                             dashboards,
                             create_handler=create_dashboard,
                             custom_field_handler=custom_field_handler)


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


@cmk.gui.pages.register("create_view_dashlet")
def page_create_view_dashlet():
    create = html.request.var('create', '1') == '1'
    name = html.request.var('name')

    if create:
        import cmk.gui.views as views
        url = html.makeuri([('back', html.makeuri([]))], filename="create_view_dashlet_infos.py")
        views.page_create_view(next_url=url)

    else:
        # Choose an existing view from the list of available views
        choose_view(name)


@cmk.gui.pages.register("create_view_dashlet_infos")
def page_create_view_dashlet_infos():
    ds_name = html.request.var('datasource')
    if ds_name not in data_source_registry:
        raise MKUserError("datasource", _('The given datasource is not supported'))

    # Create a new view by choosing the datasource and the single object types
    visuals.page_create_visual('views',
                               data_source_registry[ds_name]().infos,
                               next_url=html.makeuri_contextless([
                                   ('name', html.request.var('name')),
                                   ('type', 'view'),
                                   ('datasource', ds_name),
                                   ('back', html.makeuri([])),
                                   ('next',
                                    html.makeuri_contextless([('name', html.request.var('name')),
                                                              ('edit', '1')], 'dashboard.py')),
                               ],
                                                                 filename='edit_dashlet.py'))


def choose_view(name):
    import cmk.gui.views as views
    vs_view = DropdownChoice(
        title=_('View Name'),
        choices=views.view_choices,
        sorted=True,
    )

    html.header(_('Create Dashlet from existing View'))
    html.begin_context_buttons()
    back_url = html.get_url_input(
        "back", "dashboard.py?edit=1&name=%s" % html.urlencode(html.request.var('name')))
    html.context_button(_("Back"), back_url, "back")
    html.end_context_buttons()

    if html.request.var('save') and html.check_transaction():
        try:
            view_name = vs_view.from_html_vars('view')
            vs_view.validate_value(view_name, 'view')

            load_dashboards(lock=True)
            dashboard = available_dashboards[name]

            # Add the dashlet!
            dashlet = default_dashlet_definition('view')

            # save the original context and override the context provided by the view
            dashlet_id = len(dashboard['dashlets'])
            load_view_into_dashlet(dashlet, dashlet_id, view_name)
            add_dashlet(dashlet, dashboard)

            raise HTTPRedirect('edit_dashlet.py?name=%s&id=%d' % (name, dashlet_id))
        except MKUserError as e:
            html.user_error(e)

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


@cmk.gui.pages.register("edit_dashlet")
def page_edit_dashlet():
    if not config.user.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = html.request.var('name')
    if not board:
        raise MKUserError("name", _('The name of the dashboard is missing.'))

    ty = html.request.var('type')

    if html.request.has_var('id'):
        ident = html.get_integer_input("id")
    else:
        ident = None

    if ident is None and not ty:
        raise MKUserError("id", _('The ID of the dashlet is missing.'))

    load_dashboards(lock=html.is_transaction())

    if board not in available_dashboards:
        raise MKUserError("name", _('The requested dashboard does not exist.'))
    dashboard = available_dashboards[board]

    if ident is None:
        mode = 'add'
        title = _('Add Dashlet')

        try:
            dashlet_type = dashlet_registry[ty]
        except KeyError:
            raise MKUserError("type", _('The requested dashlet type does not exist.'))

        # Initial configuration
        dashlet = {
            'position': dashlet_type.initial_position(),
            'size': dashlet_type.initial_size(),
            'single_infos': dashlet_type.single_infos(),
            'type': ty,
        }
        ident = len(dashboard['dashlets'])

        single_infos_raw = html.request.var('single_infos')
        single_infos = []
        if single_infos_raw:
            single_infos = single_infos_raw.split(',')
            for key in single_infos:
                if key not in visual_info_registry:
                    raise MKUserError('single_infos', _('The info %s does not exist.') % key)

        if not single_infos:
            single_infos = dashlet_type.single_infos()

        dashlet['single_infos'] = single_infos
    else:
        mode = 'edit'
        title = _('Edit Dashlet')

        try:
            dashlet = dashboard['dashlets'][ident]
        except IndexError:
            raise MKUserError("id", _('The dashlet does not exist.'))

        ty = dashlet['type']
        dashlet_type = dashlet_registry[ty]
        single_infos = dashlet['single_infos']

    html.header(title)

    html.begin_context_buttons()
    back_url = html.get_url_input('back', 'dashboard.py?name=%s&edit=1' % board)
    next_url = html.get_url_input('next', back_url)
    html.context_button(_('Back'), back_url, 'back')
    html.context_button(_('All Dashboards'), 'edit_dashboards.py', 'dashboard')
    html.end_context_buttons()

    vs_general = Dictionary(
        title=_('General Settings'),
        render='form',
        optional_keys=['title', 'title_url'],
        elements=[
            ('type', FixedValue(
                ty,
                totext=dashlet_type.title(),
                title=_('Dashlet Type'),
            )),
            visuals.single_infos_spec(single_infos),
            ('background',
             Checkbox(
                 title=_('Colored Background'),
                 label=_('Render background'),
                 help=_('Render gray background color behind the dashlets content.'),
                 default_value=True,
             )),
            ('show_title',
             Checkbox(
                 title=_('Show Title'),
                 label=_('Render the titlebar above the dashlet'),
                 help=_('Render the titlebar including title and link above the dashlet.'),
                 default_value=True,
             )),
            ('title',
             TextUnicode(
                 title=_('Custom Title') + '<sup>*</sup>',
                 help=_(
                     'Most dashlets have a hard coded default title. For example the view snapin '
                     'has even a dynamic title which defaults to the real title of the view. If you '
                     'like to use another title, set it here.'),
                 size=50,
             )),
            ('title_url',
             TextUnicode(
                 title=_('Link of Title'),
                 help=_('The URL of the target page the link of the dashlet should link to.'),
                 size=50,
             )),
        ],
    )

    def dashlet_info_handler(dashlet):
        if dashlet['type'] == 'view':
            import cmk.gui.views as views
            return views.get_view_infos(dashlet)
        return dashlet_registry[dashlet['type']].infos()

    context_specs = visuals.get_context_specs(dashlet, info_handler=dashlet_info_handler)

    vs_type = None
    params = dashlet_type.vs_parameters()
    render_input_func = None
    handle_input_func = None
    if isinstance(params, list):
        # TODO: Refactor all params to be a Dictionary() and remove this special case
        vs_type = Dictionary(
            title=_('Properties'),
            render='form',
            optional_keys=dashlet_type.opt_parameters(),
            validate=dashlet_type.validate_parameters_func(),
            elements=params,
        )

    elif isinstance(params, (Dictionary, Transform)):
        vs_type = params

    elif callable(params):
        # It's a tuple of functions which should be used to render and parse the params
        render_input_func, handle_input_func = params()

    if html.request.var('save') and html.transaction_valid():
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
                # The returned dashlet must be equal to the parameter! It is not replaced/re-added
                # to the dashboard object. FIXME TODO: Clean this up!
                dashlet = handle_input_func(ident, dashlet)

            if context_specs:
                dashlet['context'] = visuals.process_context_specs(context_specs)

            if mode == "add":
                dashboard['dashlets'].append(dashlet)

            visuals.save('dashboards', dashboards)

            html.immediate_browser_redirect(1, next_url)
            if mode == 'edit':
                html.message(_('The dashlet has been saved.'))
            else:
                html.message(_('The dashlet has been added to the dashboard.'))
            html.reload_sidebar()
            html.footer()
            return

        except MKUserError as e:
            html.user_error(e)

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


@cmk.gui.pages.register("delete_dashlet")
def page_delete_dashlet():
    if not config.user.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = html.request.var('name')
    if not board:
        raise MKUserError("name", _('The name of the dashboard is missing.'))

    ident = html.get_integer_input("id")

    load_dashboards(lock=True)

    if board not in available_dashboards:
        raise MKUserError("name", _('The requested dashboard does not exist.'))
    dashboard = available_dashboards[board]

    try:
        _dashlet = dashboard['dashlets'][ident]
    except IndexError:
        raise MKUserError("id", _('The dashlet does not exist.'))

    html.header(_('Confirm Dashlet Deletion'))

    html.begin_context_buttons()
    back_url = html.get_url_input('back', 'dashboard.py?name=%s&edit=1' % board)
    html.context_button(_('Back'), back_url, 'back')
    html.end_context_buttons()

    result = html.confirm(_('Do you really want to delete this dashlet?'),
                          method='GET',
                          add_transid=True)
    if result is False:
        html.footer()
        return  # confirm dialog shown
    elif result is True:  # do it!
        try:
            dashboard['dashlets'].pop(ident)
            dashboard['mtime'] = int(time.time())
            visuals.save('dashboards', dashboards)

            html.message(_('The dashlet has been deleted.'))
        except MKUserError as e:
            html.div(e.message, class_="error")
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
    if not config.user.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = html.request.var('name')
    if not board:
        raise MKUserError("name", _('The name of the dashboard is missing.'))

    ident = html.get_integer_input("id")

    load_dashboards(lock=True)

    if board not in available_dashboards:
        raise MKUserError("name", _('The requested dashboard does not exist.'))
    dashboard = available_dashboards[board]

    try:
        dashlet = dashboard['dashlets'][ident]
    except IndexError:
        raise MKUserError("id", _('The dashlet does not exist.'))

    return dashlet, dashboard


@cmk.gui.pages.register("ajax_dashlet_pos")
def ajax_dashlet_pos():
    dashlet, board = check_ajax_update()

    board['mtime'] = int(time.time())

    dashlet['position'] = int(html.request.var('x')), int(html.request.var('y'))
    dashlet['size'] = int(html.request.var('w')), int(html.request.var('h'))
    visuals.save('dashboards', dashboards)
    html.write('OK %d' % board['mtime'])


@cmk.gui.pages.register("ajax_delete_user_notification")
def ajax_delete_user_notification():
    msg_id = html.request.var("id")
    notify.delete_gui_message(msg_id)


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


# TODO: Move this to the Dashlet class
def default_dashlet_definition(ty):
    return {
        'type': ty,
        'position': dashlet_registry[ty].initial_position(),
        'size': dashlet_registry[ty].initial_size(),
        'show_title': True,
    }


def add_dashlet(dashlet, dashboard):
    dashboard['dashlets'].append(dashlet)
    dashboard['mtime'] = int(time.time())
    visuals.save('dashboards', dashboards)
