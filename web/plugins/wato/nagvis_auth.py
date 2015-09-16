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

# Register general nagvis permissions

config.declare_permission_section('nagvis', _('NagVis'))

config.declare_permission(
    'nagvis.*_*_*',
    _('Full access'),
    _('This permission grants full access to NagVis.'),
    [ 'admin' ]
)

config.declare_permission(
    'nagvis.Rotation_view_*',
    _('Use all map rotations'),
    _('Grants read access to all rotations.'),
    [ 'guest' ]
)

config.declare_permission(
    'nagvis.Map_view_*',
    _('View all maps'),
    _('Grants read access to all maps.'),
    [ 'guest' ]
)

config.declare_permission(
    'nagvis.Map_edit_*',
    _('Edit all maps'),
    _('Grants modify access to all maps.'),
    []
)

config.declare_permission(
    'nagvis.Map_delete_*',
    _('Delete all maps'),
    _('Permits to delete all maps.'),
    []
)

config.declare_permission(
    'nagvis.Map_view',
    _('View permitted maps'),
    _('Grants read access to all maps the user is a contact for.'),
    ['user']
)

config.declare_permission(
    'nagvis.Map_edit',
    _('Edit permitted maps'),
    _('Grants modify access to all maps the user is contact for.'),
    ['user']
)

config.declare_permission(
    'nagvis.Map_delete',
    _('Delete permitted maps'),
    _('Permits to delete all maps the user is contact for.'),
    ['user']
)
