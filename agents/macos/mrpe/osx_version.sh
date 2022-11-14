#! /bin/bash

osx_version=$(sw_vers | sed 1d | tr "\n" " " | awk -F" " '{print $2" ("$4")"}')
echo $osx_version
exit 0

