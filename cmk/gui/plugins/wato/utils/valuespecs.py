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
import time

import cmk.gui.config as config
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    TextAreaUnicode,
    TextAscii,
)


class RuleComment(TextAreaUnicode):
    def __init__(self, **kwargs):
        kwargs.setdefault("title", _("Comment"))
        kwargs.setdefault("help", _("An optional comment that explains the purpose of this rule."))
        kwargs.setdefault("rows", 4)
        kwargs.setdefault("cols", 80)
        super(RuleComment, self).__init__(**kwargs)

    def render_input(self, varprefix, value):
        html.open_div(style="white-space: nowrap;")

        super(RuleComment, self).render_input(varprefix, value)

        date_and_user = "%s %s: " % (time.strftime("%F", time.localtime()), config.user.id)

        html.nbsp()
        html.icon_button(None,
                         title=_("Prefix date and your name to the comment"),
                         icon="insertdate",
                         onclick="cmk.valuespecs.rule_comment_prefix_date_and_user(this, '%s');" %
                         date_and_user)
        html.close_div()


def DocumentationURL():
    return TextAscii(
        title=_("Documentation URL"),
        help=HTML(
            _("An optional URL pointing to documentation or any other page. This will be displayed "
              "as an icon %s and open a new page when clicked. "
              "You can use either global URLs (beginning with <tt>http://</tt>), absolute local urls "
              "(beginning with <tt>/</tt>) or relative URLs (that are relative to <tt>check_mk/</tt>)."
             ) % html.render_icon("url")),
        size=80,
    )
