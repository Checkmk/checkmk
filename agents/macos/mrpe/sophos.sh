#! /bin/sh

PATH=/bin:/usr/bin:/usr/sbin
export PATH

log="/Library/Logs/Sophos Anti-Virus.log"

# Use these strings to filter out virus reports from today and yesterday
today=`date "+%Y-%m-%e"`
yesterday=`date -v -1d "+%Y-%m-%e"`

# Is Sophos running?

if ( ps aux | grep Sophos | grep -vq grep ); then
    running=yes
    output="Sophos is running"
    ret=0
else
    running=no
    output="Sophos is not running!"
    ret=2
fi



# Look for reports of viruses being detected today and yesterday

virus="`grep -i detected "/Library/Logs/Sophos Anti-Virus.log" | grep -e $today -e $yesterday | sed -E 's/.* (....-..-..).*Threat: (.+) detected .*/\1 - \2/g'`"

if [ -n "$virus" ]; then
    output="$output; Virus(es) detected recently!\\n$virus"
#    output="$output; Virus(es) detected!"
#    output="$virus"
    ret=2
fi

# Get version information

version=`egrep "(Product Version|Engine Version|Threat Data Version)" "$log" | grep -v AAFollowUpController | tail -3 | sed "s/com.sophos.oas: //"`
output="$output
$version"

echo "$output"
    
exit $ret

