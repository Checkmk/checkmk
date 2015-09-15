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

# EXAMPLE

# This script is called by the Check_MK ORACLE plugin in order to
# execute an SQL query.

# It is your task to adapt this script so that the ORACLE environment
# is setup and the correct user chosen to execute sqlplus.

# The script will get the query on stdin and shall output the
# result on stdout. Error messages goes to stderr.

ORACLE_SID=$1
if [ -z "$ORACLE_SID" ] ; then
    echo "Usage: $0 ORACLE_SID" >&2
    exit 1
fi

su nagios -c "
ORACLE_SID=$ORACLE_SID
ORAENV_ASK=NO
. /usr/local/bin/oraenv
sqlplus -s /"
