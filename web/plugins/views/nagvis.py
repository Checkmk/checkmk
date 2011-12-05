#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

# Vorgehen:
#
# Es gibt eine Sektion mit NagVis spezifischen Berechtigungen. Die meißten NagVis
# internen Rechte wirken implizit.
#
# Im Multisite gibt es zwei Wege Nutzer zu berechtigen. Zunächst können pro Rolle
# die allgemeinen Rechte gesetzt werden. Das ist z.B. Full Access auf alles.
#
# Dann gibt es noch die Berechtigungen, die sich auf die WATO Folder Maps beziehen.
# Wir nehmn dazu einfach die Berechtigungen, die eh schon auf dem Folder liegen.
# Im Folder sind die Contactgroups definiert. Aus diesen wird dann die Berechtigung
# auf dem Folder abgeleitet.
#
# Auf WATO Ebene bedeutet die Zuordnung eine Contactgroup, dass diese Nutzer die
# Hosts via WATO editieren können. Also kann man daraus auch ableten, dass diese
# Nutzer die Maps in diesem Folder editieren dürfen.
#
# Wie werden die Anzeige-Berechtigungen geregelt?

config.declare_permission_section('nagvis', _('NagVis'))

config.declare_permission(
    'nagvis.*_*_*',
    _('Full access'),
    _('This permission grants full access to NagVis.'),
    [ 'admin' ]
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

# FIXME: Weitere permissions ergänzen
