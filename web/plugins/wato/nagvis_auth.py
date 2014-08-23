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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

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

# Find all NagVis maps in the local installation to register permissions
# for each map. When no maps can be found skip this problem silently.
# This only works in OMD environments.

if defaults.omd_root:
    nagvis_maps_path = defaults.omd_root + '/etc/nagvis/maps'
    for f in os.listdir(nagvis_maps_path):
        if f[0] != '.' and f.endswith('.cfg'):
            map_name = f[:-4]

            config.declare_permission(
                'nagvis.Map_view_%s' % map_name,
                _('Map %s: view') % map_name,
                _('Grants read access to the NagVis map %s.') % map_name,
                [ 'guest' ]
            )

            config.declare_permission(
                'nagvis.Map_edit_%s' % map_name,
                _('Map %s: edit') % map_name,
                _('Grants modify access to the NagVis map %s.') % map_name,
                [ ]
            )
