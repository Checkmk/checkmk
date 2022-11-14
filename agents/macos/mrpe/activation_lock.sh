#! /bin/bash

# query activation lock status
activation_lock_status=$(system_profiler SPHardwareDataType | grep 'Activation Lock' | tr -s ' ' | cut -d ' ' -f 5)


# on older macbooks (macbooks without T2 chip, or without Apple Silicon CPU) the function "activation lock" is not available.
# in this case we are fine
if [ -z "$activation_lock_status" ]; then
  echo "Activation Lock is not available for this MacBook"
  exit 0
fi


# if the function "activation lock" is available for this macbook (T2 chip, or M1 CPU, M2 CPU,..)
# it should be enabled.
if [ "$activation_lock_status" == "Disabled" ]; then
  echo "Activation Lock is disabled"
  exit 0
fi

# at this point we know that "activation lock" is enabled
# now we have to check that it is enabled by using appleid.abu@physik.uni-freiburg.de for Admin Account

apple_id_for_admin=$(defaults read /Users/admin/Library/Preferences/MobileMeAccounts.plist Accounts | grep AccountID | tr -s ' ' | cut -d ' ' -f 4 | sed 's/"\(.*\)";/\1/')
is_find_my_mac_enabled_for_apple_id=$(defaults read /Users/admin/Library/Preferences/MobileMeAccounts.plist Accounts | grep -B1 'FIND_MY_MAC' | grep Enabled | tr -s ' ' | cut -d ' ' -f 4 | cut -c1)
account=admin

if [ "$is_find_my_mac_enabled_for_apple_id" != "1" ]; then
  apple_id_for_admin=$(defaults read /Users/markus/Library/Preferences/MobileMeAccounts.plist Accounts | grep AccountID | tr -s ' ' | cut -d ' ' -f 4 | sed 's/"\(.*\)";/\1/')
  is_find_my_mac_enabled_for_apple_id=$(defaults read /Users/markus/Library/Preferences/MobileMeAccounts.plist Accounts | grep -B1 'FIND_MY_MAC' | grep Enabled | tr -s ' ' | cut -d ' ' -f 4 | cut -c1)
  account=markus
fi

if [ "$apple_id_for_admin" == "appleid.abu@physik.uni-freiburg.de" ] && [ "$is_find_my_mac_enabled_for_apple_id" == "1" ]; then
  echo "Find My Mac is enabled for Apple ID: $apple_id_for_admin, Account: ($account)"
  exit 0
else
  echo "Find My Mac is Enabled, but NOT for Apple ID: $apple_id_for_admin"
  exit 1
fi



echo "Activation Lock Status: $activation_lock_status"

echo "Apple ID used in Admin Account: $apple_id_for_admin"

echo "Is Find My Mac enabled for $apple_id_for_admin: $is_find_my_mac_enabled_for_apple_id"

