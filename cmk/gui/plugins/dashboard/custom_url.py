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

from cmk.gui.i18n import _
from cmk.gui.exceptions import MKUserError
from cmk.gui.valuespec import (
    TextAscii,
    Checkbox,
)

from cmk.gui.plugins.dashboard import (
    IFrameDashlet,
    dashlet_registry,
)


@dashlet_registry.register
class URLDashlet(IFrameDashlet):
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
    def sort_index(cls):
        return 80

    @classmethod
    def initial_size(cls):
        return (30, 10)

    @classmethod
    def vs_parameters(cls):
        return [
            ("url", TextAscii(
                title=_('URL'),
                size=50,
                allow_empty=False,
            )),
            ("show_in_iframe",
             Checkbox(
                 title=_('Render in iframe'),
                 label=_('Render URL contents in own frame'),
                 default_value=True,
             )),
        ]

    def update(self):
        pass  # Not called at all. This dashlet always opens configured pages (see below)

    def _get_iframe_url(self):
        if not self._dashlet_spec.get('show_in_iframe', True):
            return

        # Previous to 1.6 the url was optional and a urlfunc was allowed. The
        # later option has been removed and url is now mandatory. In case you
        # need to calculate an own dynamic function you will have to subclass
        # this dashlet and implement your own _get_iframe_url() method
        if "url" not in self._dashlet_spec:
            raise MKUserError(None, _("You need to specify a URL in the dashlet properties"))

        return self._dashlet_spec['url']
