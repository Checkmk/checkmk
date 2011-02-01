#!/bin/sh

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
