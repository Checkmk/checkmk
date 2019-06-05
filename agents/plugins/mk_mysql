#!/bin/bash
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# gets optional socket as argument
function do_query() {

  # we use the sockets full name as instance name:
  INSTANCE_HEADER="[[$1]]"

  # Check if mysqld is running and root password setup
  echo "<<<mysql_ping>>>"
  echo "$INSTANCE_HEADER"
  mysqladmin --defaults-extra-file="$MK_CONFDIR"/mysql.cfg ${1:+--socket="$1"} ping 2>&1 || return

  echo "<<<mysql>>>"
  echo "$INSTANCE_HEADER"
  mysql --defaults-extra-file="$MK_CONFDIR"/mysql.cfg ${1:+--socket="$1"} -sN \
     -e "show global status ; show global variables ;"

  echo "<<<mysql_capacity>>>"
  echo "$INSTANCE_HEADER"
  mysql --defaults-extra-file="$MK_CONFDIR"/mysql.cfg ${1:+--socket="$1"} -sN \
      -e "SELECT table_schema, sum(data_length + index_length), sum(data_free)
         FROM information_schema.TABLES GROUP BY table_schema"

  echo "<<<mysql_slave>>>"
  echo "$INSTANCE_HEADER"
  mysql --defaults-extra-file="$MK_CONFDIR"/mysql.cfg ${1:+--socket="$1"} -s \
     -e "show slave status\G"

}

if type mysqladmin >/dev/null
then
  mysql_sockets=$(fgrep -h socket "$MK_CONFDIR"/mysql{.local,}.cfg | sed -ne 's/.*socket=\([^ ]*\).*/\1/p')
  if [ -z "$mysql_sockets" ] ; then
    mysql_sockets=$(ps -fww -C mysqld | grep "socket" | sed -ne 's/.*socket=\([^ ]*\).*/\1/p')
  fi
  if [ -z "$mysql_sockets" ] ; then
    do_query ""
  else
    for socket in $mysql_sockets ; do
      do_query "$socket"
    done
  fi

fi
