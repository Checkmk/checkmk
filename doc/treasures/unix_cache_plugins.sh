#!/bin/sh
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
