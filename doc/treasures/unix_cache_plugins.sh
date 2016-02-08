#!/bin/sh
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

CACHE_FILE=/tmp/XXXXX.cache
# Do not use cache file after 20 minutes
MAXAGE=1200
USE_CACHE_FILE=""
# Check if file exists and is recent enough
if [ -s $CACHE_FILE ]
then
    MTIME=$(/usr/bin/perl -e 'if (! -f $ARGV[0]){die "0000000"};$mtime=(stat($ARGV[0]))[9];print ($^T-$mtime);' $CACHE_FILE )
    if (( $MTIME < $MAXAGE )) ; then
        USE_CACHE_FILE=1
    fi
fi
if [ -s "$CACHE_FILE" ]
then
    cat $CACHE_FILE
fi
if [ -z "$USE_CACHE_FILE" -a ! -e "$CACHE_FILE.new" ]
then
    nohup sh -c "XXXXXX" > $CACHE_FILE.new 2> /dev/null && mv $CACHE_FILE.new $CACHE_FILE  &
fi
