#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import re, check_mk, time, socket
from lib import *

state_names = { 0: "OK", 1: "WARNING", 2: "CRITICAL", 3: "UNKNOWN", 4: "DEPENDENT" }
short_state_names = { 0: "OK", 1: "WARN", 2: "CRIT", 3: "UNKN", 4: "DEP" }


class MKGeneralException(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return self.reason



def find_entries(filt, enabled_sites = None):
   services = []
   hosts = set([])

   columns = ["host_name","description","state","host_state", 
	      "plugin_output", "last_state_change", "downtimes" ] 
   svcs = query_livestatus("GET services\n"
	                   "Columns: %s\n%s" % (" ".join(columns), filt), enabled_sites)
   for line in svcs:
      services.append(dict(zip(columns, line)))
      hosts.add(line[0])
   return services, hosts

def query_livestatus(query, enabled_sites = None):
    result = []
    exceptions = []
    sites = [ s for s in check_mk.sites() if enabled_sites == None or s in enabled_sites ]

    if len(sites) == 0:
	raise MKGeneralException("No site selected")

    for site_name in sites:
       site = check_mk.site(site_name)
       # TODO: The queries should not be sent one after another,
       # but all sites should be connected in parallel (multithreaded?)
       try:
           result += query_livestatus_url(site["socket"], query)
       except Exception, e:
           exceptions.append("%s: %s" % (site["alias"], e))
    if len(exceptions) > 0 and len(exceptions) == len(sites): # no site worked...
        raise MKGeneralException("Cannot connect to any site: %s" % ", ".join([str(e) for e in exceptions]))
    return result

def query_livestatus_url(url, query):
    parts = url.split(":")
    if parts[0] == "unix":
	return query_livestatus_unix(parts[1], query)
    elif parts[0] == "tcp":
	try:
	    host = parts[1]
	    port = int(parts[2])
	except:
	    raise MKConfigError("Invalid livestatus tcp url '%s'. Correct example is 'tcp:somehost:6557'" % url)
	return query_livestatus_tcp(host, port, query)
    else:
	raise MKConfigError("Invalid livestatus url '%s'" % url)

def query_livestatus_unix(socket_path, query):
   s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
   s.connect(socket_path)
   return query_livestatus_socket(s, query)

def query_livestatus_tcp(ipaddress, port, query):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect( (ipaddress, port) )
    return query_livestatus_socket(s, query)
   
def query_livestatus_socket(s, query):
   query = query + "OutputFormat: json\n"
   try:
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
def query_livestatus_column(query):
   result = query_livestatus(query)
   return [ l[0] for l in result ]

def query_livestatus_column_unique(query):
   r = []
   for e in query_livestatus_column(query):
       if e not in r:
           r.append(e)
   return r
