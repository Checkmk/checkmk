#!/usr/bin/env python
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
"""Module to hold shared code for module internals and the plugins"""

import abc
import json
import copy
import urllib
import urlparse
from typing import (  # pylint: disable=unused-import
    Optional, Any, Dict, Union, Tuple, Text, List, Callable)

import six

import cmk.utils.plugin_registry
from cmk.utils.type_defs import UserId  # pylint: disable=unused-import

from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException
import cmk.gui.config as config
import cmk.gui.visuals as visuals
from cmk.gui.globals import g, html
from cmk.gui.valuespec import ValueSpec, ValueSpecValidateFunc, DictionaryEntry  # pylint: disable=unused-import
from cmk.gui.plugins.visuals.utils import VisualContext  # pylint: disable=unused-import
from cmk.gui.plugins.views.utils import (
    get_permitted_views,
    get_all_views,
)

DashboardName = str
DashboardConfig = Dict[str, Any]
DashletConfig = Dict[str, Any]

DashletTypeName = str
DashletType = Dict[DashletTypeName, Any]
DashletId = int
DashletRefreshInterval = Union[bool, int]
DashletRefreshAction = Optional[str]
DashletSize = Tuple[int, int]
DashletPosition = Tuple[int, int]
DashletInputFunc = Callable[["Dashlet"], None]
DashletHandleInputFunc = Callable[[DashletId, DashletConfig], None]

builtin_dashboards = {}  # type: Dict[DashboardName, DashboardConfig]
# Keep this for legacy reasons until we drop the legacy plugin mechanic
dashlet_types = {}  # type: Dict[str, DashletType]

# Declare constants to be used in the definitions of the dashboards
GROW = 0
MAX = -1


class Dashlet(six.with_metaclass(abc.ABCMeta, object)):
    """Base class for all dashboard dashlet implementations"""

    # Minimum width and height of dashlets in raster units
    minimum_size = (10, 5)  # type: DashletSize

    @classmethod
    @abc.abstractmethod
    def type_name(cls):
        # type: () -> str
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def title(cls):
        # type: () -> Text
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def description(cls):
        # type: () -> Text
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def sort_index(cls):
        # type: () -> int
        raise NotImplementedError()

    @classmethod
    def has_context(cls):
        # type: () -> bool
        """Whether or not this dashlet is context sensitive."""
        return False

    @classmethod
    def single_infos(cls):
        # type: () -> List[str]
        """Return a list of the single infos (for the visual context) of this dashlet"""
        return []

    @classmethod
    def is_selectable(cls):
        # type: () -> bool
        """Whether or not the user can choose to add this dashlet in the dashboard editor"""
        return True

    @classmethod
    def is_resizable(cls):
        # type: () -> bool
        """Whether or not the user may resize this dashlet"""
        return True

    @classmethod
    def is_iframe_dashlet(cls):
        # type: () -> bool
        """Whether or not the dashlet is rendered in an iframe"""
        return False

    @classmethod
    def initial_size(cls):
        # type: () -> DashletSize
        """The initial size of dashlets when being added to the dashboard"""
        return cls.minimum_size

    @classmethod
    def initial_position(cls):
        # type: () -> DashletPosition
        """The initial position of dashlets when being added to the dashboard"""
        return (1, 1)

    @classmethod
    def initial_refresh_interval(cls):
        # type: () -> DashletRefreshInterval
        return False

    @classmethod
    def vs_parameters(cls):
        # type: () -> Optional[Union[List[DictionaryEntry], ValueSpec, Tuple[DashletInputFunc, DashletHandleInputFunc]]]
        """Returns a valuespec instance in case the dashlet has parameters, otherwise None"""
        # For legacy reasons this may also return a list of Dashboard() elements. (TODO: Clean this up)
        return None

    @classmethod
    def opt_parameters(cls):
        # type: () -> Optional[List[DictionaryEntry]]
        """List of optional parameters in case vs_parameters() returns a list"""
        return None

    @classmethod
    def validate_parameters_func(cls):
        # type: () -> Optional[ValueSpecValidateFunc]
        """Optional validation function in case vs_parameters() returns a list"""
        return None

    @classmethod
    def styles(cls):
        # type: () -> Optional[str]
        """Optional registration of snapin type specific stylesheets"""
        return None

    @classmethod
    def script(cls):
        # type: () -> Optional[str]
        """Optional registration of snapin type specific javascript"""
        return None

    @classmethod
    def allowed_roles(cls):
        # type: () -> List[str]
        return config.builtin_role_ids

    @classmethod
    def add_url(cls):
        # type: () -> str
        """The URL to open for adding a new dashlet of this type to a dashboard"""
        return html.makeuri([('type', cls.type_name()), ('back', html.makeuri([('edit', '1')]))],
                            filename='edit_dashlet.py')

    def __init__(self, dashboard_name, dashboard, dashlet_id, dashlet):
        # type: (DashboardName, DashboardConfig, DashletId, DashletConfig) -> None
        super(Dashlet, self).__init__()
        self._dashboard_name = dashboard_name
        self._dashboard = dashboard
        self._dashlet_id = dashlet_id
        self._dashlet_spec = dashlet
        self._context = self._get_context()  # type: Optional[Dict]

    def infos(self):
        # type: () -> List[str]
        """Return a list of the supported infos (for the visual context) of this dashlet"""
        return []

    def _get_context(self):
        # type: () -> Optional[Dict]
        if not self.has_context():
            return None

        return visuals.get_merged_context(
            visuals.get_context_from_uri_vars(self.infos(), self.single_infos()),
            self._dashboard["context"],
            self._dashlet_spec["context"],
        )

    @property
    def context(self):
        # type: () -> Dict
        if self._context is None:
            raise Exception("Missing context")
        return self._context

    @property
    def dashlet_id(self):
        # type: () -> DashletId
        return self._dashlet_id

    @property
    def dashlet_spec(self):
        # type: () -> DashletConfig
        return self._dashlet_spec

    @property
    def dashboard_name(self):
        # type: () -> str
        return self._dashboard_name

    def display_title(self):
        # type: () -> Text
        return self._dashlet_spec.get("title", self.title())

    def show_title(self):
        # type: () -> bool
        return self._dashlet_spec.get("show_title", True)

    def title_url(self):
        # type: () -> Optional[str]
        return self._dashlet_spec.get("title_url")

    def show_background(self):
        # type: () -> bool
        return self._dashlet_spec.get("background", True)

    def on_resize(self):
        # type: () -> Optional[str]
        """Returns either Javascript code to execute when a resize event occurs or None"""
        return None

    def on_refresh(self):
        # type: () -> Optional[str]
        """Returns either Javascript code to execute when a the dashlet should be refreshed or None"""
        return None

    def update(self):
        # type: () -> None
        """Called by the ajax call to update dashlet contents

        This is normally equivalent to the .show() method. Differs only for iframe dashlets.
        """
        self.show()

    @abc.abstractmethod
    def show(self):
        # type: () -> None
        """Produces the HTML code of the dashlet content."""
        raise NotImplementedError()

    def _add_context_vars_to_url(self, url):
        # type: (str) -> str
        """Adds missing context variables to the given URL"""
        if not self.has_context():
            return url

        context_vars = self._dashlet_context_vars()

        parts = urlparse.urlparse(url)
        url_vars = dict(urlparse.parse_qsl(parts.query, keep_blank_values=True))
        url_vars.update(context_vars)

        new_qs = urllib.urlencode(url_vars)
        return urlparse.urlunparse(tuple(parts[:4] + (new_qs,) + parts[5:]))

    def _dashlet_context_vars(self):
        # type: () -> Dict[str, str]
        return dict(visuals.get_context_uri_vars(self.context, self.single_infos()))

    def size(self):
        # type: () -> DashletSize
        if self.is_resizable():
            return self._dashlet_spec.get("size", self.initial_size())
        return self.initial_size()

    def position(self):
        # type: () -> DashletPosition
        return self._dashlet_spec.get("position", self.initial_position())

    def refresh_interval(self):
        # type: () -> DashletRefreshInterval
        return self._dashlet_spec.get("refresh", self.initial_refresh_interval())

    def get_refresh_action(self):
        # type: () -> DashletRefreshAction
        if not self.refresh_interval():
            return None

        url = self._get_refresh_url()
        try:
            on_refresh = self.on_refresh()
            if on_refresh:
                return '(function() {%s})' % on_refresh
            return '"%s"' % self._add_context_vars_to_url(url)  # url to dashboard_dashlet.py
        except Exception:
            # Ignore the exceptions in non debug mode, assuming the exception also occures
            # while dashlet rendering, which is then shown in the dashlet itselfs.
            if config.debug:
                raise

        return None

    def _get_refresh_url(self):
        # type: () -> str
        """Returns the URL to be used for loading the dashlet contents"""
        dashlet_url = self._get_dashlet_url_from_urlfunc()
        if dashlet_url is not None:
            return dashlet_url

        if self._dashlet_spec.get("url"):
            return self._dashlet_spec["url"]

        return html.makeuri_contextless(
            [
                ('name', self._dashboard_name),
                ('id', self._dashlet_id),
                ('mtime', self._dashboard['mtime']),
            ],
            filename="dashboard_dashlet.py",
        )

    # TODO: This is specific for the 'url' dashlet type. Move it to that
    # dashlets class once it has been refactored to a class
    def _get_dashlet_url_from_urlfunc(self):
        # type: () -> Optional[str]
        """Use the URL returned by urlfunc as dashlet URL

        Dashlets using the 'urlfunc' method will dynamically compute
        an url (using HTML context variables at their wish).

        We need to support function pointers to be compatible to old dashboard plugin
        based definitions. The new dashboards use strings to reference functions within
        the global context or functions of a module. An example would be:

        urlfunc: "my_custom_url_rendering_function"

        or within a module:

        urlfunc: "my_module.render_my_url"
        """
        if "urlfunc" not in self._dashlet_spec:
            return None

        urlfunc = self._dashlet_spec['urlfunc']
        if hasattr(urlfunc, '__call__'):
            return urlfunc()

        if '.' in urlfunc:
            module_name, func_name = urlfunc.split('.', 1)
            module = __import__(module_name)
            return module.__dict__[func_name]()

        return globals()[urlfunc]()


class IFrameDashlet(six.with_metaclass(abc.ABCMeta, Dashlet)):
    """Base class for all dashlet using an iframe"""
    @classmethod
    def is_iframe_dashlet(cls):
        # type: () -> bool
        """Whether or not the dashlet is rendered in an iframe"""
        return True

    def show(self):
        # type: () -> None
        self._show_initial_iframe_container()

    def reload_on_resize(self):
        # type: () -> bool
        """Whether or not the page should be reloaded when the dashlet is resized"""
        return self._dashlet_spec.get("reload_on_resize", False)

    def _show_initial_iframe_container(self):
        # type: () -> None
        iframe_url = self._get_iframe_url()
        if not iframe_url:
            return

        # Fix of iPad >:-P
        html.open_div(style="width: 100%; height: 100%; -webkit-overflow-scrolling:touch;")
        html.iframe('',
                    src="about:blank" if self.reload_on_resize() else iframe_url,
                    id_="dashlet_iframe_%d" % self._dashlet_id,
                    allowTransparency="true",
                    frameborder="0",
                    width="100%",
                    height="100%")
        html.close_div()

        if self.reload_on_resize():
            html.javascript('cmk.dashboard.set_reload_on_resize(%s, %s);' %
                            (json.dumps(self._dashlet_id), json.dumps(iframe_url)))

    def _get_iframe_url(self):
        # type: () -> Optional[str]
        if not self.is_iframe_dashlet():
            return None

        return self._add_context_vars_to_url(self._get_refresh_url())

    @abc.abstractmethod
    def update(self):
        # type: () -> None
        raise NotImplementedError()


class DashletRegistry(cmk.utils.plugin_registry.ClassRegistry):
    """The management object for all available plugins."""
    def plugin_base_class(self):
        return Dashlet

    def plugin_name(self, plugin_class):
        return plugin_class.type_name()


dashlet_registry = DashletRegistry()


# TODO: Same as in cmk.gui.plugins.views.utils.ViewStore, centralize implementation?
class DashboardStore(object):
    @classmethod
    def get_instance(cls):
        """Use the request globals to prevent multiple instances during a request"""
        if 'dashboard_store' not in g:
            g.dashboard_store = cls()
        return g.dashboard_store

    def __init__(self):
        self.all = self._load_all()
        self.permitted = self._load_permitted(self.all)

    def _load_all(self):
        # type: () -> Dict[Tuple[UserId, DashboardName], DashboardConfig]
        """Loads all definitions from disk and returns them"""
        _transform_builtin_dashboards()
        return _transform_dashboards(visuals.load('dashboards', builtin_dashboards))

    def _load_permitted(self, all_dashboards):
        # type: (Dict[Tuple[UserId, DashboardName], DashboardConfig]) -> Dict[DashboardName, DashboardConfig]
        """Returns all defitions that a user is allowed to use"""
        return visuals.available('dashboards', all_dashboards)


def save_all_dashboards():
    # type: () -> None
    visuals.save('dashboards', get_all_dashboards())


def get_all_dashboards():
    # type: () -> Dict[Tuple[UserId, DashboardName], DashboardConfig]
    return DashboardStore.get_instance().all


def get_permitted_dashboards():
    # type: () -> Dict[DashboardName, DashboardConfig]
    return DashboardStore.get_instance().permitted


# During implementation of the dashboard editor and recode of the visuals
# we had serveral different data structures, for example one where the
# views in user dashlets were stored with a context_type instead of the
# "single_info" key, which is the currently correct one.
#
# This code transforms views from user_dashboards.mk which have been
# migrated/created with daily snapshots from 2014-08 till beginning 2014-10.
# FIXME: Can be removed one day. Mark as incompatible change or similar.
def _transform_dashboards(boards):
    # type: (Dict[Tuple[UserId, DashboardName], DashboardConfig]) -> Dict[Tuple[UserId, DashboardName], DashboardConfig]
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

    return boards


# be compatible to old definitions, where even internal dashlets were
# referenced by url, e.g. dashboard['url'] = 'hoststats.py'
# FIXME: can be removed one day. Mark as incompatible change or similar.
def _transform_builtin_dashboards():
    # type: () -> None
    if 'builtin_dashboards_transformed' in g:
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
                copy_view_into_dashlet(dashlet, nr, view_name, load_from_all_views=True)
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
    g.builtin_dashboards_transformed = True


def copy_view_into_dashlet(dashlet, nr, view_name, add_context=None, load_from_all_views=False):
    # type: (DashletConfig, DashletId, str, VisualContext, bool) -> None
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
    # TODO: Shouldn't we use the self._dashlet_context_vars() here?
    dashlet['title_url'] = html.makeuri_contextless(
        [('view_name', view_name)] +
        visuals.get_singlecontext_vars(view["context"], view["single_infos"]).items(),
        filename='view.py')

    dashlet['type'] = 'view'
    dashlet['name'] = 'dashlet_%d' % nr
    dashlet['show_title'] = True
    dashlet['mustsearch'] = False
