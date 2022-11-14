#! /bin/sh 

PATH=/bin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin
export PATH

# get the latest snapshot dates form 
_snapshot_dates=$(defaults read /Library/Preferences/com.apple.TimeMachine.plist | awk '/SnapshotDates/,/\)/' | awk '{ sub(/^[ \t]+/, ""); print }')
_timemachine_details=$(defaults read /Library/Preferences/com.apple.TimeMachine.plist)

# if the latest backup is older than ${_days} the service becomes critical
_days=7

# check if a backup has been performed in the last ${_days}
for idx in $(seq 0 $((_days-1))); do
  # date_str looks like: 2022-02-20, 2022-02-19, 2022-02-18, ...
  _date_str=$(date -v-${idx}d +%F)

  # check if a snapshot has been made at ${_date_str}
  if [[ $_snapshot_dates =~ .*${_date_str}.* ]]; then
    echo "Last time machine backup date: ${_date_str}"; 
    echo "${_timemachiine_details}"
    exit 0
  fi
done

# if we get so far no backup has been perfomed in the last ${_days} days
echo "Last time machine backup is older than $_days days"
echo "${_timemachine_details}"
exit 2

