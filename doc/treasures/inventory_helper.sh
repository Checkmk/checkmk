#!/bin/sh



# A script to get systems where the inventory check has fired
# then output those including the services they'll add
# then reinventorize them
# then reschedule the inventory check to clean up


reinventory()
{

check_mk --automation inventory new $HOST
 
echo "COMMAND [`date +%s`] SCHEDULE_FORCED_SVC_CHECK;$HOST;Check_MK inventory;`date +%s`" | lq 

}

INVENTORY_INFO=`echo "GET services
Columns: host_name long_plugin_output
Filter: description = Check_MK inventory
Filter: plugin_output !~~ no unchecked" | lq`

if [ $INVENTORY_INFO != "" ]; then
    HOSTS=`echo "$INVENTORY_INFO" | cut -f1 -d\;`
    echo "$INVENTORY_INFO"
    for HOST in "$HOSTS" ; do
       reinventory
    done
fi


