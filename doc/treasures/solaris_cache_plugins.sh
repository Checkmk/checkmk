#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

MK_CONFDIR=/etc/check_mk
CACHE_FILE=$MK_CONFDIR/db2-logs.cache
if [ ! -d $MK_CONFDIR ]; then
    mkdir -p $MK_CONFDIR
fi

# Do not use cache file after 20 minutes
MAXAGE=1200

# Check if file exists and is recent enough
if [ -s $CACHE_FILE ]
then
    MTIME=$(perl -e 'if (! -f $ARGV[0]){die "0000000"};$mtime=(stat($ARGV[0]))[9];print ($^T-$mtime);' $CACHE_FILE )
    if [ $MTIME -le $MAXAGE ] ; then 
        USE_CACHE_FILE=1
    fi 
fi

if [ -s "$CACHE_FILE" ]
then
    cat $CACHE_FILE
fi

if [ -z "$USE_CACHE_FILE" -a ! -e "$CACHE_FILE.new" ]
then
    nohup bash -c "COMMAND | grep -v 'mail'" > $CACHE_FILE.new 2> /dev/null && mv $CACHE_FILE.new $CACHE_FILE  &
fi

