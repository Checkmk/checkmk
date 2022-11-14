#! /bin/sh 

PATH=/bin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin
export PATH

#  get the last known encryption state of the TimeMachine Backup Disk 
_last_known_encryption_state=$(defaults read /Library/Preferences/com.apple.TimeMachine.plist | sed -n 's/.*LastKnownEncryptionState = \(.*\);/\1/p')

if [ "${_last_known_encryption_state}" == "Encrypted" ]; then
  echo "Backup disk is encrypted"
  exit 0
else 
  echo "Backup disk is not encrypted"
  exit 1
fi

