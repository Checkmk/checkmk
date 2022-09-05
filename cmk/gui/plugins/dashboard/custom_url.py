#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.dashboard.utils import dashlet_registry, DashletConfig, IFrameDashlet
from cmk.gui.valuespec import Checkbox, TextInput


class URLDashletConfig(DashletConfig):
    url: str
    show_in_iframe: bool


@dashlet_registry.register
class URLDashlet(IFrameDashlet[URLDashletConfig]):
    """Dashlet that displays a custom webpage"""

    @classmethod
    def type_name(cls):
        return "url"

    @classmethod
    def title(cls):
        return _("Custom URL")

    @classmethod
    def description(cls):
        return _("Displays the content of a custom website.")

    @classmethod
    def sort_index(cls) -> int:
        return 80

    @classmethod
    def initial_size(cls):
        return (30, 10)

    @classmethod
    def vs_parameters(cls):
        return [
            (
                "url",
                TextInput(
                    title=_("URL"),
                    size=50,
                    allow_empty=False,
                ),
            ),
            (
                "show_in_iframe",
                Checkbox(
                    title=_("Render in iframe"),
                    label=_("Render URL contents in own frame"),
                    default_value=True,
                ),
            ),
        ]

    def update(self):
        pass  # Not called at all. This dashlet always opens configured pages (see below)

    def _get_refresh_url(self) -> str:
        """Returns the URL to be used for loading the dashlet contents"""
        dashlet_url = self._get_dashlet_url_from_urlfunc()
        if dashlet_url is not None:
            return dashlet_url

        if self._dashlet_spec.get("url"):
            return self._dashlet_spec["url"]

        return super()._get_refresh_url()

    def _get_dashlet_url_from_urlfunc(self) -> str | None:
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

        urlfunc = self._dashlet_spec["urlfunc"]
        if hasattr(urlfunc, "__call__"):
            return urlfunc()

        if "." in urlfunc:
            module_name, func_name = urlfunc.split(".", 1)
            module = __import__(module_name)
            return module.__dict__[func_name]()

        return globals()[urlfunc]()

    def _get_iframe_url(self):
        if not self._dashlet_spec.get("show_in_iframe", True):
            return None

        # Previous to 1.6 the url was optional and a urlfunc was allowed. The
        # later option has been removed and url is now mandatory. In case you
        # need to calculate an own dynamic function you will have to subclass
        # this dashlet and implement your own _get_iframe_url() method
        if "url" not in self._dashlet_spec:
            raise MKUserError(None, _("You need to specify a URL in the element properties"))

        return self._dashlet_spec["url"]
