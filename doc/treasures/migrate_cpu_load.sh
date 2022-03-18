#!/bin/sh
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This is an example for migration of RRD data. Many things are hard
# coded here. But it might be a starting point for writing your own
# migration script.

NEU=CPU_load.rrd
ALT=CPU_load_5min.rrd

if [ ! -f $ALT ] || [ ! -f $NEU ]; then
    echo "Ausgelassen, RRDs nicht da"
    exit 0
fi

DS1=DS:1:GAUGE:8640:0:100
DS2=DS:2:GAUGE:8640:0:100
DS3=DS:3:GAUGE:8640:0:100
RRA=$(grep -v '#' </etc/nagios/rra.cfg)

printf "Sauge alte RRD-Datenbank %s aus..." "$ALT"
rrdtool dump $ALT |
    sed -n 's/<!.*\/ \(1214......\).*<v> \([^ ]*\) .*/\1:\2:\2:\2/p' |
    sort -n \
        >werte
echo OK

printf "Ermittle aeltesten Zeitstempel..."
FIRST=$(head -n1 werte | cut -d: -f1)
echo "$FIRST"

printf "Lege RRD-Datenbank %s.neu an..." "$NEU"

rrdtool create $NEU.neu -s 60 -b "$FIRST" $DS1 $DS2 $DS3 "$RRA" && echo OK || exit 1
chown nagios.nagios $NEU.neu

printf "Speise Daten aus %s ein..." "$ALT"
xargs -n 1 rrdtool update $NEU.neu <werte 2>/dev/null
rm -f werte
mv $NEU.neu $NEU
echo OK
