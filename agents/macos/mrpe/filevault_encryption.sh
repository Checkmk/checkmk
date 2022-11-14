#! /bin/sh 

PATH=/bin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin
export PATH

_is_filevault_encryption_active=$(fdesetup isactive)

if [ "${_is_filevault_encryption_active}" == "true" ]; then
  echo "FileVault is active"
  exit 0
else 
  echo "FileVault is inactive"
  exit 1
fi

