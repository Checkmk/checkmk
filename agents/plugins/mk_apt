#!/bin/bash
# Check for APT updates (Debian, Ubuntu)
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

# TODO:
# Einstellungen:
# - upgrade oder dist-upgrade
# - vorher ein update machen
# Bakery:
# - Bakelet anlegen
# - Async-Zeit einstellbar machen und das Ding immer async laufen lassen
# Check programmieren:
#   * Schwellwerte auf Anzahlen
#   * Regexen auf Pakete, die zu CRIT/WARN führen
# - Graph malen mit zwei Kurven

# This variable can either be "upgrade" or "dist-upgrade"
UPGRADE=upgrade
DO_UPDATE=yes


function check_apt_update {
    if [ "$DO_UPDATE" = yes ] ; then
        # NOTE: Even with -qq, apt-get update can output several lines to
        # stderr, e.g.:
        #
        # W: There is no public key available for the following key IDs:
        # 1397BC53640DB551
        apt-get update -qq 2> /dev/null
    fi
    apt-get -o 'Debug::NoLocking=true' -o 'APT::Get::Show-User-Simulation-Note=false' -s -qq "$UPGRADE" | grep -v '^Conf'
}


if type apt-get > /dev/null ; then
    echo '<<<apt:sep(0)>>>'
    out=$(check_apt_update)
    if [ -z "$out" ]; then
        echo "No updates pending for installation"
    else
        echo "$out"
    fi
fi
