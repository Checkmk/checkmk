#!/sbin/sh
CACHE_FILE=/tmp/XXXXX.cache
# Do not use cache file after 20 minutes
MAXAGE=1200
USE_CACHE_FILE=""
# Check if file exists and is recent enough
if [ -s $CACHE_FILE ]
then
    MTIME=$(/usr/bin/perl -e 'if (! -f $ARGV[0]){die "0000000"};$mtime=(stat($ARGV[0]))[9];print ($^T-$mtime);' $CACHE_FILE )
    if (( $MTIME < $MAXAGE )) ; then
        USE_CACHE_FILE=1
    fi
fi
if [ -s "$CACHE_FILE" ]
then
    cat $CACHE_FILE
fi
if [ -z "$USE_CACHE_FILE" -a ! -e "$CACHE_FILE.new" ]
then
    nohup sh -c "XXXXXX" > $CACHE_FILE.new 2> /dev/null && mv $CACHE_FILE.new $CACHE_FILE  &
fi
