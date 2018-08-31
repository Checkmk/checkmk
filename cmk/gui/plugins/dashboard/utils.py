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

import cmk.gui.plugin_registry
import cmk.gui.config as config
import cmk.gui.visuals as visuals
from cmk.gui.globals import html


builtin_dashboards = {}
# Keep this for legacy reasons until we drop the legacy plugin mechanic
dashlet_types = {}

# Declare constants to be used in the definitions of the dashboards
GROW = 0
MAX = -1

dashlet_min_size = 10, 10        # Minimum width and height of dashlets in raster units


class Dashlet(object):
    """Base class for all dashboard dashlet implementations"""
    __metaclass__ = abc.ABCMeta

    @classmethod
    @abc.abstractmethod
    def type_name(cls):
        raise NotImplementedError()


    @classmethod
    @abc.abstractmethod
    def title(cls):
        raise NotImplementedError()


    @classmethod
    @abc.abstractmethod
    def description(cls):
        raise NotImplementedError()


    @classmethod
    @abc.abstractmethod
    def sort_index(cls):
        raise NotImplementedError()


    @classmethod
    def infos(cls):
        """Return a list of the supported infos (for the visual context) of this dashlet"""
        return []


    @classmethod
    def single_infos(cls):
        """Return a list of the single infos (for the visual context) of this dashlet"""
        return []


    @classmethod
    def is_selectable(cls):
        """Whether or not the user can choose to add this dashlet in the dashboard editor"""
        return True


    @classmethod
    def is_resizable(cls):
        """Whether or not the user may resize this dashlet"""
        return True


    @classmethod
    def is_iframe_dashlet(cls):
        """Whether or not the dashlet is rendered in an iframe"""
        return False


    @classmethod
    def size(cls):
        """The initial size of dashlets when being added to the dashboard"""
        return dashlet_min_size


    @classmethod
    def vs_parameters(cls):
        """Returns a valuespec instance in case the dashlet has parameters, otherwise None"""
        # For legacy reasons this may also return a list of Dashboard() elements. (TODO: Clean this up)
        return None


    @classmethod
    def opt_parameters(cls):
        """List of optional parameters in case vs_parameters() returns a list"""
        return None


    @classmethod
    def validate_parameters_func(cls):
        """Optional validation function in case vs_parameters() returns a list"""
        return None


    @classmethod
    def refresh_interval(cls):
        return False


    @classmethod
    def styles(cls):
        """Optional registration of snapin type specific stylesheets"""
        return None


    @classmethod
    def script(cls):
        """Optional registration of snapin type specific javascript"""
        return None


    @classmethod
    def allowed_roles(cls):
        return config.builtin_role_ids


    @classmethod
    def add_url(cls):
        """The URL to open for adding a new dashlet of this type to a dashboard"""
        return html.makeuri([('type', cls.type_name()), ('back', html.makeuri([('edit', '1')]))], filename = 'edit_dashlet.py')


    def __init__(self, dashboard_name, dashboard, dashlet_id, dashlet, wato_folder):
        super(Dashlet, self).__init__()
        self._dashboard_name = dashboard_name
        self._dashboard = dashboard
        self._dashlet_id = dashlet_id
        self._dashlet = dashlet
        self._wato_folder = wato_folder


    def display_title(self):
        return self.title()


    def on_resize(self):
        """Returns either Javascript code to execute when a resize event occurs or None"""
        return None


    def on_refresh(self):
        """Returns either Javascript code to execute when a the dashlet should be refreshed or None"""
        return None


    def update(self):
        """Called by the ajax call to update dashlet contents

        This is normally equivalent to the .show() method. Differs only for iframe dashlets.
        """
        self.show()


    @abc.abstractmethod
    def show(self):
        """Produces the HTML code of the dashlet content."""
        raise NotImplementedError()


    def _show_initial_iframe_container(self):
        iframe_url = self._get_iframe_url()
        if not iframe_url:
            return

        iframe_url = self._add_wato_folder_to_url(iframe_url)

        # Fix of iPad >:-P
        html.open_div(style="width: 100%; height: 100%; -webkit-overflow-scrolling:touch;")
        html.iframe('', src="about:blank" if self._dashlet.get("reload_on_resize") else iframe_url,
                    id_="dashlet_iframe_%d" % self._dashlet_id,
                    allowTransparency="true",
                    frameborder="0",
                    width="100%",
                    height="100%")
        html.close_div()

        if self._dashlet.get("reload_on_resize"):
            html.javascript('reload_on_resize["%d"] = "%s"' % (self._dashlet_id, iframe_url))


    # TODO: Move this to Dashlet()
    def _get_iframe_url(self):
        if not self.is_iframe_dashlet():
            return

        return html.makeuri_contextless([
            ('name', self._dashboard_name),
            ('id', self._dashlet_id),
            ('mtime', self._dashboard['mtime'])] + self._get_global_context_url_vars(),
            filename = "dashboard_dashlet.py")


    # Updates the current dashlet with the current context vars maybe loaded from
    # the dashboards global configuration or HTTP vars, but also returns a list
    # of all HTTP vars which have been used
    # TODO: Cleanup the side effect of this function. It should only return the URL
    #       variables and not modify self._dashlet.
    def _get_global_context_url_vars(self):
        # Either load the single object info from the dashlet or the dashlet type
        single_infos = []
        if 'single_infos' in self._dashlet:
            single_infos = self._dashlet['single_infos']
        elif self.single_infos():
            single_infos = self.single_infos()

        global_context = self._dashboard.get('context', {})

        url_vars = []
        for info_key in single_infos:
            for param in visuals.info_params(info_key):
                if param not in self._dashlet['context']:
                    # Get the vars from the global context or http vars
                    if param in global_context:
                        self._dashlet['context'][param] = global_context[param]
                    else:
                        self._dashlet['context'][param] = html.var(param)
                        url_vars.append((param, html.var(param)))
        return url_vars


    def _add_wato_folder_to_url(self, url):
        if not self._wato_folder:
            return url
        elif '/' in url:
            return url # do not append wato_folder to non-Check_MK-urls
        elif '?' in url:
            return url + "&wato_folder=" + html.urlencode(self._wato_folder)
        else:
            return url + "?wato_folder=" + html.urlencode(self._wato_folder)


    def get_refresh_action(self):
        if not self.refresh_interval():
            return

        url = self._dashlet.get("url", "dashboard_dashlet.py?name=%s&id=%s" % (self._dashboard_name, self._dashlet_id))
        try:
            on_refresh = self.on_refresh()
            if on_refresh:
                return 'function() {%s}' % on_refresh
            else:
                return '"%s"' % self._add_wato_folder_to_url(url) # url to dashboard_dashlet.py
        except Exception:
            # Ignore the exceptions in non debug mode, assuming the exception also occures
            # while dashlet rendering, which is then shown in the dashlet itselfs.
            if config.debug:
                raise

        return None




class DashletRegistry(cmk.gui.plugin_registry.ClassRegistry):
    """The management object for all available plugins."""
    def plugin_base_class(self):
        return Dashlet


    def _register(self, plugin_class):
        snapin_id = plugin_class.type_name()
        self._entries[snapin_id] = plugin_class

dashlet_registry = DashletRegistry()
