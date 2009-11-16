#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
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

import re, check_mk, time, socket

state_names = { 0: "OK", 1: "WARNING", 2: "CRITICAL", 3: "UNKNOWN", 4: "DEPENDENT" }
short_state_names = { 0: "OK", 1: "WARN", 2: "CRIT", 3: "UNKN", 4: "DEP" }


class MKGeneralException(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return self.reason



def find_entries(unixsocket, filt):
   services = []
   hosts = set([])

   columns = ["host_name","description","state","host_state", 
	      "plugin_output", "last_state_change", "downtimes" ] 
   svcs = query_livestatus(unixsocket, 
			   "GET services\n"
	                   "Columns: %s\n%s" % (" ".join(columns), filt))
   for line in svcs:
      services.append(dict(zip(columns, line)))
      hosts.add(line[0])
   return services, hosts


def query_livestatus(socket_path, query):
   query = query + "OutputFormat: json\n"
   try:
      s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
      s.connect(socket_path)
      s.send(query)
      s.shutdown(socket.SHUT_WR)
      answer = ""
      while True:
          r = s.recv(65536)
          if r != "":
              answer += r
          else:
              break
      try: 
          result = eval(answer)
      except:
	 raise MKGeneralException("Invalid JSON output from Livestatus. "
	       "Query was: <pre>%s</pre>. Result was: %s" % (query, answer))
      return result

   except MKGeneralException:
      raise

   except Exception, e:
      raise MKGeneralException("Cannot connect to %s: Please check if Livestatus module is correctly loaded and socket path is correct (Error: %s)" % (socket_path, e))

# Queries just a single column -> returns a list
def query_livestatus_column(socket_path, query):
   result = query_livestatus(socket_path, query)
   return [ l[0] for l in result ]

