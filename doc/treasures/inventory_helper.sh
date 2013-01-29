#!/bin/sh
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

# A script to 
# * identify systems where the inventory check has fired
# * output their list including the services that are unmonitored add
# * then reinventorize them
# * reschedule the inventory check to clean up
# The script does not remove any services!

# this works as intended. If you have a flaky enviroment, you
# might want to filter for hosts that are in state up before the
# inventory goes looking for them.


reinventory()
{

now=`date +%s`

# Use the automation API to run an inventory, only for new objects.
check_mk --automation inventory new $HOST >/dev/null

# Then reschedule the inventory check right now to clear up.
# (currently we're running it just once a day at the same time on all hosts)
echo "COMMAND [$now] SCHEDULE_FORCED_SVC_CHECK;$HOST;Check_MK inventory;$now" | lq 

}

# Here we grab the hosts where the inventory check found something.
# we look at the check output because we don't know what serverity
# is configured for the inventory check by a user.
# The only info we store is the host name and the list of detected services.
# (so you can log the info)

INVENTORY_INFO=`echo "GET services
Columns: host_name long_plugin_output
Filter: description = Check_MK inventory
Filter: plugin_output !~~ no unchecked" | lq`

if [ "$INVENTORY_INFO" != "" ]; then
    HOSTS=`echo "$INVENTORY_INFO" | cut -f1 -d\;`
    echo "$INVENTORY_INFO"
    for HOST in $HOSTS ; do
       reinventory
    done
fi


