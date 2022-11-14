#!/bin/zsh

PATH=/bin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin
export PATH

_cache=/etc/check_mk/updates_available.cache

_software_update=$(defaults read /Library/Preferences/com.apple.SoftwareUpdate.plist)
_last_full_successful_date=$(defaults read /Library/Preferences/com.apple.SoftwareUpdate.plist LastFullSuccessfulDate)
_last_full_successful_date=$(date -j -f "%Y-%m-%d %H:%M:%S %z" "${_last_full_successful_date}" +"%Y-%m-%d %H:%M:%S")

_last_updates_available=$(defaults read /Library/Preferences/com.apple.SoftwareUpdate.plist LastUpdatesAvailable)

_days_until_warn=7
_days_until_crit=14

_warn_date=$(date -j -v-${_days_until_warn}d +"%Y-%m-%d %H:%M:%S")
_crit_date=$(date -j -v-${_days_until_crit}d +"%Y-%m-%d %H:%M:%S")

#echo ${_last_full_successful_date}
#echo ${_warn_date}
#echo ${_crit_date}

if grep -qc "MSU_UPDATE_22A380_patch_13.0" <<< ${_software_update}; then
  ((_last_updates_available--))
fi

if [[ ${_last_updates_available} = 0 ]]; then
  [ -f ${_cache} ] &&  rm ${_cache}
  msg="System is up to date"
  exit_code=0
else
  if [ ! -f ${_cache} ]; then
    echo "${_last_full_successful_date}" > ${_cache}
  fi

   _updates_available_since_date=$(head -n 1 ${_cache})

  msg="New updates available"
  exit_code=0

  if [[ ${_updates_available_since_date} < ${_warn_date} ]]; then
    msg="New updates available since more than ${_days_until_warn} days"
    exit_code=1
  fi

  if [[ ${_updates_available_since_date} < ${_crit_date} ]]; then
    msg="New updates available since more than ${_days_until_crit} days"
    exit_code=2
  fi
fi

echo ${msg}
echo ${_software_update}
exit $exit_code

