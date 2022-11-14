#!/bin/zsh 

PATH=/bin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin
export PATH

days=7

_details=$(defaults read /Library/Preferences/com.apple.SoftwareUpdate.plist)
_last_full_successful_date=$(defaults read /Library/Preferences/com.apple.SoftwareUpdate.plist LastFullSuccessfulDate)
_last_full_successful_date=$(date -j -f "%Y-%m-%d %H:%M:%S %z" "${_last_full_successful_date}" +"%Y-%m-%d %H:%M:%S")

_seven_days_ago_date=$(date -j -v-${days}d +"%Y-%m-%d %H:%M:%S")

#echo ${_last_full_successful_date}
#echo ${_seven_days_ago_date}

if [[ ${_last_full_successful_date} > ${_seven_days_ago_date} ]]; then
  echo "Last check: ${_last_full_successful_date}"
  exit 0
else 
  echo "Last check is older than ${days} days: ${_last_full_successful_date}"
  exit 2
fi


