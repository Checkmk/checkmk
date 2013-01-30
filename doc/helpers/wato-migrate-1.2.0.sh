#!/bin/bash
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

set -e

if [ ! -e main.mk -o ! -e conf.d ]
then
    echo "You are probably not in the etc/check_mk. I cannot find"
    echo "main.mk nor conf.d."
    exit 1
fi

TAR=conf.d-$(date +%s).tar.gz
echo "Making backup of conf.d into $TAR"
tar czf $TAR conf.d

cd conf.d

if which tree > /dev/null
then
    echo "Before migration:"
    echo "-----------------------------------------"
    tree
    echo "-----------------------------------------"
fi

echo
find * -name "*.mk.wato" | while read line
do
    tmpline=/$line
    thedir=${tmpline%/*}
    thedir=${thedir:1}
    thefile=${tmpline##*/}
    if [ -z "$thedir" ]; then
        newdir=wato/${thefile//.mk.wato}
    else
        newdir=wato/$thedir/${thefile//.mk.wato}
    fi

    echo "Migrating hostlist $thefile to folder $newdir..."
    mkdir -vp "$newdir"
    mv -v "$line" "$newdir/.wato"
    mv -v "${line%.wato}" "$newdir/hosts.mk"
done

# No move also the empty WATO directories
find * -name ".wato" | while read line
do
    # Skip files in wato/ directory (already migrated)
    if [ ${line:0:5} = wato/ ] ; then continue ; fi
    thedir=${line%/*}
    thefile=${line##*/}
    echo "Moving empty directory $thedir to wato/$thedir..."
    mkdir -p "wato/$thedir"
    mv -v $line "wato/$thedir"
    rmdir -v "$thedir" 2>/dev/null || true
done


if which tree > /dev/null
then
    echo "-----------------------------------------"
    echo "After migration:"
    echo "-----------------------------------------"
    tree
fi


