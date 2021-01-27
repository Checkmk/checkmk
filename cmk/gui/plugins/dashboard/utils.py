#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for module internals and the plugins"""

import time
import abc
import json
import copy
from typing import Set, Optional, Any, Dict, Union, Tuple, List, Callable, cast, Type
import urllib.parse

import cmk.utils.plugin_registry
from cmk.utils.type_defs import UserId
from cmk.gui.type_defs import HTTPVariables, VisualContext

import cmk.gui.sites as sites

from cmk.gui.figures import create_figures_response
import cmk.gui.escaping as escaping
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException, MKTimeout, MKUserError
import cmk.gui.config as config
import cmk.gui.visuals as visuals
from cmk.gui.globals import g, html, request
from cmk.gui.valuespec import (
    ValueSpec,
    ValueSpecValidateFunc,
    DictionaryEntry,
    Dictionary,
    DropdownChoice,
    FixedValue,
    Checkbox,
    TextUnicode,
)
from cmk.gui.plugins.views.utils import (
    get_permitted_views,
    get_all_views,
    transform_painter_spec,
)
from cmk.gui.metrics import translate_perf_data
from cmk.gui.plugins.metrics.rrd_fetch import merge_multicol
from cmk.gui.plugins.metrics.valuespecs import vs_title_infos, transform_graph_render_options
from cmk.gui.plugins.metrics.html_render import default_dashlet_graph_render_options
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.breadcrumb import (
    make_topic_breadcrumb,
    Breadcrumb,
    BreadcrumbItem,
)
from cmk.gui.utils.urls import makeuri, makeuri_contextless

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
DashletInputFunc = Callable[[DashletType], None]
DashletHandleInputFunc = Callable[[DashletId, DashletConfig], DashletType]

builtin_dashboards: Dict[DashboardName, DashboardConfig] = {}
# Keep this for legacy reasons until we drop the legacy plugin mechanic
dashlet_types: Dict[str, DashletType] = {}

# Declare constants to be used in the definitions of the dashboards
GROW = 0
MAX = -1


class Dashlet(metaclass=abc.ABCMeta):
    """Base class for all dashboard dashlet implementations"""

    # Minimum width and height of dashlets in raster units
    minimum_size: DashletSize = (12, 10)

    @classmethod
    @abc.abstractmethod
    def type_name(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def title(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def description(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def sort_index(cls) -> int:
        raise NotImplementedError()

    @classmethod
    def has_context(cls) -> bool:
        """Whether or not this dashlet is context sensitive."""
        return False

    @classmethod
    def single_infos(cls) -> List[str]:
        """Return a list of the single infos (for the visual context) of this dashlet"""
        return []

    @classmethod
    def is_selectable(cls) -> bool:
        """Whether or not the user can choose to add this dashlet in the dashboard editor"""
        return True

    @classmethod
    def is_resizable(cls) -> bool:
        """Whether or not the user may resize this dashlet"""
        return True

    @classmethod
    def is_iframe_dashlet(cls) -> bool:
        """Whether or not the dashlet is rendered in an iframe"""
        return False

    @classmethod
    def initial_size(cls) -> DashletSize:
        """The initial size of dashlets when being added to the dashboard"""
        return cls.minimum_size

    @classmethod
    def initial_position(cls) -> DashletPosition:
        """The initial position of dashlets when being added to the dashboard"""
        return (1, 1)

    @classmethod
    def initial_refresh_interval(cls) -> DashletRefreshInterval:
        return False

    @classmethod
    def vs_parameters(
        cls
    ) -> Union[None, List[DictionaryEntry], ValueSpec, Tuple[DashletInputFunc,
                                                             DashletHandleInputFunc]]:
        """Returns a valuespec instance in case the dashlet has parameters, otherwise None"""
        # For legacy reasons this may also return a list of Dashboard() elements. (TODO: Clean this up)
        return None

    @classmethod
    def opt_parameters(cls) -> Union[bool, List[str]]:
        """List of optional parameters in case vs_parameters() returns a list"""
        return False

    @classmethod
    def validate_parameters_func(cls) -> Optional[ValueSpecValidateFunc]:
        """Optional validation function in case vs_parameters() returns a list"""
        return None

    @classmethod
    def styles(cls) -> Optional[str]:
        """Optional registration of snapin type specific stylesheets"""
        return None

    @classmethod
    def script(cls) -> Optional[str]:
        """Optional registration of snapin type specific javascript"""
        return None

    @classmethod
    def allowed_roles(cls) -> List[str]:
        return config.builtin_role_ids

    @classmethod
    def add_url(cls) -> str:
        """The URL to open for adding a new dashlet of this type to a dashboard"""
        return makeuri(
            request,
            [('type', cls.type_name()), ('back', makeuri(request, [('edit', '1')]))],
            filename='edit_dashlet.py',
        )

    @classmethod
    def default_settings(cls):
        """Overwrite specific default settings for dashlets by returning a dict
            return { key: default_value, ... }
        e.g. to have a dashlet default to not showing its title
            return { "show_title": False }
        """
        return {}

    def __init__(self, dashboard_name: DashboardName, dashboard: DashboardConfig,
                 dashlet_id: DashletId, dashlet: DashletConfig) -> None:
        super(Dashlet, self).__init__()
        self._dashboard_name = dashboard_name
        self._dashboard = dashboard
        self._dashlet_id = dashlet_id
        self._dashlet_spec = dashlet
        self._context: Optional[Dict] = self._get_context()

    def infos(self) -> List[str]:
        """Return a list of the supported infos (for the visual context) of this dashlet"""
        return []

    def _get_context(self) -> Optional[Dict]:
        if not self.has_context():
            return None

        return visuals.get_merged_context(
            visuals.get_context_from_uri_vars(self.infos(), self.single_infos()),
            self._dashboard["context"],
            self._dashlet_spec["context"],
        )

    @property
    def context(self) -> Dict:
        if self._context is None:
            raise Exception("Missing context")
        return self._context

    @property
    def dashlet_id(self) -> DashletId:
        return self._dashlet_id

    @property
    def dashlet_spec(self) -> DashletConfig:
        return self._dashlet_spec

    @property
    def dashboard_name(self) -> str:
        return self._dashboard_name

    def display_title(self) -> str:
        return self._dashlet_spec.get("title", self.title())

    def show_title(self) -> bool:
        return self._dashlet_spec.get("show_title", True)

    def title_url(self) -> Optional[str]:
        return self._dashlet_spec.get("title_url")

    def show_background(self) -> bool:
        return self._dashlet_spec.get("background", True)

    def on_resize(self) -> Optional[str]:
        """Returns either Javascript code to execute when a resize event occurs or None"""
        return None

    def on_refresh(self) -> Optional[str]:
        """Returns either Javascript code to execute when a the dashlet should be refreshed or None"""
        return None

    def update(self) -> None:
        """Called by the ajax call to update dashlet contents

        This is normally equivalent to the .show() method. Differs only for
        iframe and single metric dashlets.
        """
        self.show()

    @abc.abstractmethod
    def show(self) -> None:
        """Produces the HTML code of the dashlet content."""
        raise NotImplementedError()

    def _add_context_vars_to_url(self, url: str) -> str:
        """Adds missing context variables to the given URL"""
        if not self.has_context():
            return url

        context_vars = {
            k: "%s" % v  #
            for k, v in self._dashlet_context_vars()
            if v is not None
        }

        parts = urllib.parse.urlparse(url)
        url_vars = dict(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
        url_vars.update(context_vars)

        new_qs = urllib.parse.urlencode(url_vars)
        return urllib.parse.urlunparse(tuple(parts[:4] + (new_qs,) + parts[5:]))

    def _dashlet_context_vars(self) -> HTTPVariables:
        return visuals.get_context_uri_vars(self.context, self.single_infos())

    def unconfigured_single_infos(self) -> Set[str]:
        """Returns infos that are not set by the dashlet config"""
        if not self.has_context():
            return set()
        return visuals.get_missing_single_infos(self.single_infos(), self._dashlet_spec["context"])

    def missing_single_infos(self) -> Set[str]:
        """Returns infos that are neither configured nor available through HTTP variables"""
        if not self.has_context():
            return set()
        return visuals.get_missing_single_infos(self.single_infos(), self.context)

    def size(self) -> DashletSize:
        if self.is_resizable():
            return self._dashlet_spec.get("size", self.initial_size())
        return self.initial_size()

    def position(self) -> DashletPosition:
        return self._dashlet_spec.get("position", self.initial_position())

    def refresh_interval(self) -> DashletRefreshInterval:
        return self._dashlet_spec.get("refresh", self.initial_refresh_interval())

    def get_refresh_action(self) -> DashletRefreshAction:
        if not self.refresh_interval():
            return None

        url = self._get_refresh_url()
        try:
            # pylint is just too stupid, see e.g. https://github.com/PyCQA/pylint/issues/2332
            # or https://github.com/PyCQA/pylint/issues/2559 plus a dozen other issues...
            on_refresh = self.on_refresh()  # pylint: disable=assignment-from-none
            if on_refresh:
                return '(function() {%s})' % on_refresh
            return '"%s"' % self._add_context_vars_to_url(url)  # url to dashboard_dashlet.py
        except Exception:
            # Ignore the exceptions in non debug mode, assuming the exception also occures
            # while dashlet rendering, which is then shown in the dashlet itselfs.
            if config.debug:
                raise

        return None

    def _get_refresh_url(self) -> str:
        """Returns the URL to be used for loading the dashlet contents"""
        dashlet_url = self._get_dashlet_url_from_urlfunc()
        if dashlet_url is not None:
            return dashlet_url

        if self._dashlet_spec.get("url"):
            return self._dashlet_spec["url"]

        return makeuri_contextless(
            request,
            [
                ('name', self._dashboard_name),
                ('id', self._dashlet_id),
                ('mtime', self._dashboard['mtime']),
            ],
            filename="dashboard_dashlet.py",
        )

    # TODO: This is specific for the 'url' dashlet type. Move it to that
    # dashlets class once it has been refactored to a class
    def _get_dashlet_url_from_urlfunc(self) -> Optional[str]:
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


def dashlet_vs_general_settings(dashlet: Dashlet, single_infos: List[str]):
    return Dictionary(
        title=_('General Settings'),
        render='form',
        optional_keys=['title', 'title_url'],
        elements=[
            ('type',
             FixedValue(
                 dashlet.type_name(),
                 totext=dashlet.title(),
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
             DropdownChoice(
                 title=_("Show title header"),
                 help=_('Render the titlebar including title and link above the dashlet.'),
                 choices=[
                     (False, _("Don't show any header")),
                     (True, _("Show header with highlighted background")),
                     ("transparent", _("Show title without any background")),
                 ],
                 default_value=True,
             )),
            ('title',
             TextUnicode(
                 title=_('Custom Title') + '<sup>*</sup>',
                 help=_('Most dashlets have a hard coded static title and some are aware of '
                        'its content and set the title dynamically, like the view snapin, which '
                        'displays the title of the view. If you like to use any other title, '
                        'set it here.'),
                 size=50,
             )),
            ("title_format", vs_title_infos()),
            ('title_url',
             TextUnicode(
                 title=_('Link of Title'),
                 help=_('The URL of the target page the link of the dashlet should link to.'),
                 size=50,
             )),
        ],
    )


class IFrameDashlet(Dashlet, metaclass=abc.ABCMeta):
    """Base class for all dashlet using an iframe"""
    @classmethod
    def is_iframe_dashlet(cls) -> bool:
        """Whether or not the dashlet is rendered in an iframe"""
        return True

    def show(self) -> None:
        self._show_initial_iframe_container()

    def reload_on_resize(self) -> bool:
        """Whether or not the page should be reloaded when the dashlet is resized"""
        return self._dashlet_spec.get("reload_on_resize", False)

    def _show_initial_iframe_container(self) -> None:
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

    def _get_iframe_url(self) -> Optional[str]:
        if not self.is_iframe_dashlet():
            return None

        return self._add_context_vars_to_url(self._get_refresh_url())

    @abc.abstractmethod
    def update(self) -> None:
        raise NotImplementedError()


class DashletRegistry(cmk.utils.plugin_registry.Registry[Type[Dashlet]]):
    """The management object for all available plugins."""
    def plugin_name(self, instance):
        return instance.type_name()


dashlet_registry = DashletRegistry()


class ABCDataGenerator(metaclass=abc.ABCMeta):
    def vs_parameters(self):
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def generate_response_data(cls, properties, context, settings):
        raise NotImplementedError()

    def generate_response_from_request(self):
        settings = json.loads(html.request.get_str_input_mandatory("settings"))

        try:
            dashlet_type = cast(Dashlet, dashlet_registry[settings.get("type")])
        except KeyError:
            raise MKUserError("type", _('The requested dashlet type does not exist.'))

        settings = dashlet_vs_general_settings(
            dashlet_type, dashlet_type.single_infos()).value_from_json(settings)

        raw_properties = html.request.get_str_input_mandatory("properties")
        properties = self.vs_parameters().value_from_json(json.loads(raw_properties))
        context = json.loads(html.request.get_str_input_mandatory("context", "{}"))
        response_data = self.generate_response_data(properties, context, settings)
        return create_figures_response(response_data)


def dashlet_http_variables(dashlet: Dashlet) -> HTTPVariables:
    vs_general_settings = dashlet_vs_general_settings(dashlet, dashlet.single_infos())
    dashlet_settings = vs_general_settings.value_to_json(dashlet._dashlet_spec)
    dashlet_params = dashlet.vs_parameters()
    assert isinstance(dashlet_params, ValueSpec)  # help mypy
    dashlet_properties = dashlet_params.value_to_json(dashlet._dashlet_spec)

    context = visuals.get_merged_context(
        visuals.get_context_from_uri_vars(["host", "service"], dashlet.single_infos()),
        dashlet._dashlet_spec["context"])

    args: HTTPVariables = []
    args.append(("settings", json.dumps(dashlet_settings)))
    args.append(("context", json.dumps(context)))
    args.append(("properties", json.dumps(dashlet_properties)))

    return args


class ABCFigureDashlet(Dashlet, metaclass=abc.ABCMeta):
    """ Base class for cmk_figures based graphs
        Only contains the dashlet spec, the data generation is handled in the
        DataGenerator classes, to split visualization and data
    """
    @classmethod
    def type_name(cls):
        return "figure_dashlet"

    @classmethod
    def sort_index(cls):
        return 95

    @classmethod
    def initial_refresh_interval(cls):
        return False

    @classmethod
    def initial_size(cls):
        return (56, 40)

    @classmethod
    def infos(cls):
        return ["host", "service"]

    @classmethod
    def single_infos(cls):
        return []

    @classmethod
    def has_context(cls):
        return True

    @property
    def instance_name(self):
        # Note: This introduces the restriction one graph type per dashlet
        return "%s_%s" % (self.type_name(), self._dashlet_id)

    @classmethod
    def vs_parameters(cls):
        return cls.data_generator().vs_parameters()

    @classmethod
    @abc.abstractmethod
    def data_generator(cls) -> ABCDataGenerator:
        raise NotImplementedError()

    @property
    def update_interval(self) -> int:
        return 60

    def on_resize(self):
        return ("if (typeof %(instance)s != 'undefined') {"
                "%(instance)s.update_gui();"
                "}") % {
                    "instance": self.instance_name
                }

    def js_dashlet(self, fetch_url: str):
        div_id = "%s_dashlet_%d" % (self.type_name(), self._dashlet_id)
        html.div("", id_=div_id)

        args = dashlet_http_variables(self)
        body = html.urlencode_vars(args)

        html.javascript(
            """
            let %(type_name)s_class_%(dashlet_id)d = cmk.figures.figure_registry.get_figure("%(type_name)s");
            let %(instance_name)s = new %(type_name)s_class_%(dashlet_id)d(%(div_selector)s);
            %(instance_name)s.set_post_url_and_body(%(url)s, %(body)s);
            %(instance_name)s.initialize();
            %(instance_name)s.scheduler.set_update_interval(%(update)d);
            %(instance_name)s.scheduler.enable();
            """ % {
                "type_name": self.type_name(),
                "dashlet_id": self._dashlet_id,
                "instance_name": self.instance_name,
                "div_selector": json.dumps("#%s" % div_id),
                "url": json.dumps(fetch_url),
                "body": json.dumps(body),
                "update": self.update_interval,
            })


# TODO: Same as in cmk.gui.plugins.views.utils.ViewStore, centralize implementation?
class DashboardStore:
    @classmethod
    def get_instance(cls):
        """Use the request globals to prevent multiple instances during a request"""
        if 'dashboard_store' not in g:
            g.dashboard_store = cls()
        return g.dashboard_store

    def __init__(self):
        self.all = self._load_all()
        self.permitted = self._load_permitted(self.all)

    def _load_all(self) -> Dict[Tuple[UserId, DashboardName], DashboardConfig]:
        """Loads all definitions from disk and returns them"""
        _transform_builtin_dashboards()
        return _transform_dashboards(visuals.load('dashboards', builtin_dashboards))

    def _load_permitted(
        self, all_dashboards: Dict[Tuple[UserId, DashboardName], DashboardConfig]
    ) -> Dict[DashboardName, DashboardConfig]:
        """Returns all defitions that a user is allowed to use"""
        return visuals.available('dashboards', all_dashboards)


def save_all_dashboards() -> None:
    visuals.save('dashboards', get_all_dashboards())


def get_all_dashboards() -> Dict[Tuple[Optional[UserId], DashboardName], DashboardConfig]:
    return DashboardStore.get_instance().all


def get_permitted_dashboards() -> Dict[DashboardName, DashboardConfig]:
    return DashboardStore.get_instance().permitted


# During implementation of the dashboard editor and recode of the visuals
# we had serveral different data structures, for example one where the
# views in user dashlets were stored with a context_type instead of the
# "single_info" key, which is the currently correct one.
#
# This code transforms views from user_dashboards.mk which have been
# migrated/created with daily snapshots from 2014-08 till beginning 2014-10.
# FIXME: Can be removed one day. Mark as incompatible change or similar.
# Also this method transforms network topology dashlets to custom url ones
def _transform_dashboards(
    boards: Dict[Tuple[UserId, DashboardName], DashboardConfig]
) -> Dict[Tuple[UserId, DashboardName], DashboardConfig]:
    for dashboard in boards.values():
        visuals.transform_old_visual(dashboard)
        for dashlet in dashboard['dashlets']:
            visuals.transform_old_visual(dashlet)
            _transform_dashlets_mut(dashlet)

    return boards


def _transform_dashlets_mut(dashlet_spec: DashletConfig) -> DashletConfig:
    # abusing pass by reference to mutate dashlet
    if dashlet_spec['type'] == 'view':
        transform_painter_spec(dashlet_spec)

    # ->2014-10
    if dashlet_spec['type'] == 'pnpgraph':
        if 'service' not in dashlet_spec['single_infos']:
            dashlet_spec['single_infos'].append('service')
        if 'host' not in dashlet_spec['single_infos']:
            dashlet_spec['single_infos'].append('host')

    if dashlet_spec['type'] in ['pnpgraph', 'custom_graph']:
        # -> 1.5.0i2
        if "graph_render_options" not in dashlet_spec:
            dashlet_spec["graph_render_options"] = {
                "show_legend": dashlet_spec.pop("show_legend", False),
                "show_service": dashlet_spec.pop("show_service", True),
            }
        # -> 2.0.0i1
        dashlet_spec["graph_render_options"].setdefault(
            "title_format", default_dashlet_graph_render_options["title_format"])
        transform_graph_render_options(dashlet_spec["graph_render_options"])
        title_format = dashlet_spec["graph_render_options"].pop("title_format")
        dashlet_spec.setdefault(
            "title_format", title_format or dashlet_spec["graph_render_options"]["title_format"])
        dashlet_spec["graph_render_options"].pop("show_title", None)

    if dashlet_spec["type"] == "network_topology":
        # -> 2.0.0i Removed network topology dashlet type
        transform_topology_dashlet(dashlet_spec)

    # -> 2.0.0i1 All dashlets have new mandatory title_format
    dashlet_spec.setdefault("title_format", ['plain'])

    return dashlet_spec


def transform_topology_dashlet(dashlet_spec: DashletConfig,
                               filter_group: str = "") -> DashletConfig:
    site_id = dashlet_spec["context"].get("site", config.omd_site())

    dashlet_spec.update({
        "type": "url",
        "title": _("Network topology of site %s") % site_id,
        "url": "../nagvis/frontend/nagvis-js/index.php?mod=Map&header_template="
               "on-demand-filter&header_menu=1&label_show=1&sources=automap&act=view"
               "&backend_id=%s&render_mode=undirected&url_target=main&filter_group=%s" %
               (site_id, filter_group),
        "show_in_iframe": True,
    })

    return dashlet_spec


# be compatible to old definitions, where even internal dashlets were
# referenced by url, e.g. dashboard['url'] = 'hoststats.py'
# FIXME: can be removed one day. Mark as incompatible change or similar.
def _transform_builtin_dashboards() -> None:
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
                    (nr, name, escaping.escape_attribute(dashlet)))

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


def copy_view_into_dashlet(dashlet: DashletConfig,
                           nr: DashletId,
                           view_name: str,
                           add_context: Optional[VisualContext] = None,
                           load_from_all_views: bool = False) -> None:
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
        for (_u, n), this_view in get_all_views().items():
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
    dashlet['title'] = visuals.visual_title('view', view, dashlet['context'])
    # TODO: Shouldn't we use the self._dashlet_context_vars() here?
    name_part: HTTPVariables = [('view_name', view_name)]
    singlecontext_vars = cast(
        HTTPVariables,
        list(visuals.get_singlecontext_vars(
            view["context"],
            view["single_infos"],
        ).items()))
    dashlet['title_url'] = makeuri_contextless(
        request,
        name_part + singlecontext_vars,
        filename='view.py',
    )

    dashlet['type'] = 'view'
    dashlet['name'] = 'dashlet_%d' % nr
    dashlet['show_title'] = True
    dashlet['mustsearch'] = False


class site_query:
    def __init__(self, f):
        self.f = f

    def __call__(self, cls, properties, context):
        filter_headers, only_sites = visuals.get_filter_headers("log", ["host", "service"], context)
        columns = self.f(cls, properties, context)

        query = ("GET services\n"
                 "Columns: %(cols)s\n"
                 "%(filter)s" % {
                     "cols": " ".join(columns),
                     "filter": filter_headers,
                 })

        with sites.only_sites(only_sites), sites.prepend_site():
            try:
                rows = sites.live().query(query)
            except MKTimeout:
                raise
            except Exception:
                raise MKGeneralException(_("The query returned no data."))

        return ['site'] + columns, rows


def create_data_for_single_metric(cls, properties, context):
    columns, data_rows = cls._get_data(properties, context)

    data = []
    used_metrics = []

    for idx, row in enumerate(data_rows):
        d_row = dict(zip(columns, row))
        translated_metrics = translate_perf_data(d_row["service_perf_data"],
                                                 d_row["service_check_command"])
        metric = translated_metrics.get(properties['metric'])

        if metric is None:
            continue

        series = merge_multicol(d_row, columns, properties)
        site = d_row['site']
        host = d_row["host_name"]
        svc_url = makeuri(
            request,
            [("view_name", "service"), ("site", site), ("host", host),
             ("service", d_row['service_description'])],
            filename="view.py",
        )

        row_id = "row_%d" % idx

        # Historic values
        for ts, elem in series.time_data_pairs():
            if elem:
                data.append({
                    "tag": row_id,
                    "timestamp": ts,
                    "value": elem,
                    "label": host,
                })

        # Live value
        data.append({
            "tag": row_id,
            "timestamp": int(time.time()),
            "value": metric['value'],
            "label": host,
            "url": svc_url,
        })

        used_metrics.append((row_id, metric, d_row))

    return data, used_metrics


def dashboard_breadcrumb(name: str, board: DashboardConfig, title: str) -> Breadcrumb:
    breadcrumb = make_topic_breadcrumb(mega_menu_registry.menu_monitoring(),
                                       PagetypeTopics.get_topic(board["topic"]))
    breadcrumb.append(BreadcrumbItem(title, makeuri_contextless(request, [("name", name)])))
    return breadcrumb
