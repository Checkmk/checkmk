#!/bin/sh
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# EXAMPLE

# This script is called by the Checkmk ORACLE plugin in order to
# execute an SQL query.

# It is your task to adapt this script so that the ORACLE environment
# is setup and the correct user chosen to execute sqlplus.

# The script will get the query on stdin and shall output the
# result on stdout. Error messages goes to stderr.

ORACLE_SID=$1
if [ -z "$ORACLE_SID" ]; then
    echo "Usage: $0 ORACLE_SID" >&2
    exit 1
fi

su nagios -c "
ORACLE_SID=$ORACLE_SID
ORAENV_ASK=NO
. /usr/local/bin/oraenv
sqlplus -s /"
