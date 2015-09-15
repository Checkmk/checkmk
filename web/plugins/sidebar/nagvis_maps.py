#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
# Check_MK is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.
#
# Check_MK is  distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY;  without even the implied warranty of
# MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have  received  a copy of the  GNU  General Public
# License along with Check_MK.  If  not, email to mk@mathias-kettner.de
# or write to the postal address provided at www.mathias-kettner.de

# +------------------------------------------------------------------+
# | This file has been contributed and is copyrighted by:            |
# |                                                                  |
# | Lars Michelsen <lm@mathias-kettner.de>            Copyright 2010 |
# +------------------------------------------------------------------+

import views, defaults

def render_nagvis_maps():
    refresh_url = "%snagvis/server/core/ajax_handler.php?mod=Multisite&act=getMaps" % (defaults.url_prefix)
    return refresh_url

sidebar_snapins["nagvis_maps"] = {
    "title":       _("NagVis Maps"),
    "description": _("List of available NagVis maps. This only works with NagVis 1.5 and above. " \
                   "At the moment it is neccessarry to authenticate with NagVis first by opening " \
                   "a NagVis map in the browser. After this the maplist should be filled."),
    "render":      render_nagvis_maps,
    "allowed":     [ "user", "admin", "guest" ],
    "refresh":     True,
    "styles":      """
div.state1.statea {
    border-color: #ff0;
}
div.state2.statea {
    border-color: #f00;
}
div.statea {
    background-color: #0b3;
}
div.state1.stated {
    border-color: #ff0;
}
div.state2.stated {
    border-color: #f00;
}
div.stated {
    background-color: #0b3;
}
"""
}
