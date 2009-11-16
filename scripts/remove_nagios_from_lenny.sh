#!/bin/bash
# +------------------------------------------------------------------+
# |                     _           _           _                    |
# |                  __| |_  ___ __| |__  _ __ | |__                 |
# |                 / _| ' \/ -_) _| / / | '  \| / /                 |
# |                 \__|_||_\___\__|_\_\_|_|_|_|_\_\                 |
# |                                   |___|                          |
# |              _   _   __  _         _        _ ____               |
# |             / | / | /  \| |__  ___| |_ __ _/ |__  |              |
# |             | |_| || () | '_ \/ -_)  _/ _` | | / /               |
# |             |_(_)_(_)__/|_.__/\___|\__\__,_|_|/_/                |
# |                                            check_mk 1.1.0beta17  |
# |                                                                  |
# | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
# 
# This file is part of check_mk 1.1.0beta17.
# The official homepage is at http://mathias-kettner.de/check_mk.
# 
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

#!/bin/bash
set -e
killall nagios
if [ -n "$DESTDIR" ] ; then cd $DESTDIR ; else cd / ; fi
rm -vrf \
  etc/nagios \
  usr/local/bin/nagios* \
  usr/local/share/nagios \
  usr/local/lib/nagios \
  var/lib/nagios \
  var/log/nagios \
  var/cache/nagios \
  var/spool/nagios \
  var/run/nagios* \
  etc/init.d/nagios \
  etc/apache2/conf.d/nagios.* \
  usr/local/bin/npcd* \
  etc/check_mk \
  usr/share/check_mk \
  var/lib/check_mk \
  etc/xinetd.d/check_mk \
  usr/bin/check_mk* \
  usr/share/doc/check_mk \
  usr/lib/check_mk_agent

if [ -n "$DESTDIR" ] ; then
  find "$DESTDIR" -type d | sort -r | xargs rmdir -v
fi

userdel nagios || true
groupdel nagios || true
