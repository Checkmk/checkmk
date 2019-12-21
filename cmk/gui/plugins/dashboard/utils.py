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
from typing import (  # pylint: disable=unused-import
    Optional, Any, Dict, Union, Tuple, Text, List, Callable)

import six

import cmk.utils.plugin_registry

import cmk.gui.config as config
import cmk.gui.visuals as visuals
from cmk.gui.globals import html
from cmk.gui.valuespec import ValueSpec, ValueSpecValidateFunc, DictionaryEntry  # pylint: disable=unused-import

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
    def infos(cls):
        # type: () -> List[str]
        """Return a list of the supported infos (for the visual context) of this dashlet"""
        return []

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

    def __init__(self, dashboard_name, dashboard, dashlet_id, dashlet, wato_folder):
        # type: (DashboardName, DashboardConfig, DashletId, DashletConfig, Optional[str]) -> None
        super(Dashlet, self).__init__()
        self._dashboard_name = dashboard_name
        self._dashboard = dashboard
        self._dashlet_id = dashlet_id
        self._dashlet_spec = dashlet
        self._wato_folder = wato_folder

    @property
    def dashlet_id(self):
        # type: () -> DashletId
        return self._dashlet_id

    @property
    def dashlet_spec(self):
        # type: () -> DashletConfig
        return self._dashlet_spec

    @property
    def wato_folder(self):
        # type: () -> Optional[str]
        return self._wato_folder

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

    # Updates the current dashlet with the current context vars maybe loaded from
    # the dashboards global configuration or HTTP vars, but also returns a list
    # of all HTTP vars which have been used
    # TODO: Cleanup the side effect of this function. It should only return the URL
    #       variables and not modify self._dashlet.
    def _get_global_context_url_vars(self):
        # type: () -> List[Tuple[str, str]]
        # Either load the single object info from the dashlet or the dashlet type
        single_infos = []
        if 'single_infos' in self._dashlet_spec:
            single_infos = self._dashlet_spec['single_infos']
        elif self.single_infos():
            single_infos = self.single_infos()

        global_context = self._dashboard.get('context', {})

        url_vars = []
        for info_key in single_infos:
            for param in visuals.info_params(info_key):
                if param not in self._dashlet_spec['context']:
                    # Get the vars from the global context or http vars
                    if param in global_context:
                        self._dashlet_spec['context'][param] = global_context[param]
                    else:
                        self._dashlet_spec['context'][param] = html.request.var(param)
                        url_vars.append((param, html.request.var(param)))
        return url_vars

    def _add_wato_folder_to_url(self, url):
        # type: (str) -> str
        if not self._wato_folder:
            return url
        if '/' in url:
            return url  # do not append wato_folder to non-Check_MK-urls
        if '?' in url:
            return url + "&wato_folder=" + html.urlencode(self._wato_folder)
        return url + "?wato_folder=" + html.urlencode(self._wato_folder)

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

        url = self._dashlet_spec.get(
            "url", "dashboard_dashlet.py?name=%s&id=%s" % (self._dashboard_name, self._dashlet_id))
        try:
            on_refresh = self.on_refresh()
            if on_refresh:
                return '(function() {%s})' % on_refresh
            return '"%s"' % self._add_wato_folder_to_url(url)  # url to dashboard_dashlet.py
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

        return html.makeuri_contextless([
            ("name", self._dashboard_name),
            ("id", self._dashlet_id),
        ],
                                        filename="dashboard_dashlet.py")

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

        iframe_url = self._add_wato_folder_to_url(iframe_url)

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

        return html.makeuri_contextless([('name', self._dashboard_name), ('id', self._dashlet_id),
                                         ('mtime', self._dashboard['mtime'])] +
                                        self._get_global_context_url_vars(),
                                        filename="dashboard_dashlet.py")

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
