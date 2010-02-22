#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

import socket

"""MK Livestatus Python API

This module allows easy access to Nagios via MK Livestatus.
It supports persistent connections via the connection class.
If you want single-shot connections, just initialize a 
connection object on-the-fly, e.g.:

r = connection("/var/lib/nagios/rw/live").query_table_assoc("GET hosts")

For persistent connections create and keep an object:

conn = connection("/var/lib/nagios/rw/live")
r1 = conn.query_table_assoc("GET hosts")
r2 = conn.query_line("GET status")
"""

DOWN = 0
UP   = 1

class MKLivestatusException(Exception):
   def __init__(self, value):
      self.parameter = value
   def __str__(self):
      return str(self.parameter)

class MKLivestatusSocketError(MKLivestatusException):
   def __init__(self, reason):
      MKLivestatusException.__init__(self, reason)

class MKLivestatusConfigError(MKLivestatusException):
   def __init__(self, reason):
      MKLivestatusException.__init__(self, reason)

class MKLivestatusQueryError(MKLivestatusException):
   def __init__(self, code, reason):
      MKLivestatusException.__init__(self, "%s: %s" % (code, reason))
      self.code = code

class Helpers:
   def query_value(self, query):
      """Issues a query that returns exactly one line and one columns and returns 
	 the response as a single value"""
      return self.query(query, "ColumnHeaders: off")[0][0]
   
   def query_line(self, query):
      """Issues a query that returns one line of data and returns the elements
	 of that line as list"""
      return self.query(query, "ColumnHeaders: off")[0]

   def query_line_assoc(self, query):
      """Issues a query that returns one line of data and returns the elements
	 of that line as a dictionary from column names to values"""
      r = self.query(query, "ColumnHeaders: on")[0:2]
      return dict(zip(r[0], r[1]))

   def query_column(self, query):
      """Issues a query that returns exactly one column and returns the values 
	 of all lines in that column as a single list"""
      return [ l[0] for l in self.query(query, "ColumnHeaders: off") ]

   def query_table(self, query):
      """Issues a query that may return multiple lines and columns and returns 
	 a list of lists"""
      return self.query(query, "ColumnHeaders: off")

   def query_table_assoc(self, query):
      """Issues a query that may return multiple lines and columns and returns
	 a dictionary from column names to values for each line. This can be
	 very ineffective for large response sets."""
      response = self.query(query, "ColumnHeaders: on")
      headers = response[0]
      result = []
      for line in response[1:]:
	 result.append(dict(zip(headers, line)))
      return result

class BaseConnection:
    def __init__(self, socketurl):
	"""Create a new connection to a MK Livestatus socket"""
	self.socketurl = socketurl
	self.socket_state = DOWN
	self.socket_target = None
	self.create_socket(socketurl)

    def set_timeout(self, timeout):
	self.socket.settimeout(timeout)
 
    def create_socket(self, url):
	parts = url.split(":")
	if parts[0] == "unix":
	    if len(parts) != 2:
		raise MKLivestatusConfigError("Invalid livestatus unix url: %s. Correct example is 'unix:/var/run/nagios/rw/live'" % url)
	    self.socket_target = parts[1]
	    self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

	elif parts[0] == "tcp":
	    try:
		host = parts[1]
		port = int(parts[2])
	    except:
		raise MKLivestatusConfigError("Invalid livestatus tcp url '%s'. Correct example is 'tcp:somehost:6557'" % url)
	    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	    self.socket_target = ( host, port )

    def connect(self):
	if self.socket_state == DOWN:
	    try:
		self.socket.connect(self.socket_target)
	        self.socket_state = UP
	    except Exception, e:
		raise MKLivestatusSocketError("Cannot connect to '%s': %s" % (self.socketurl, e))

    def receive_data(self, size):
	result = ""
	while size > 0:
	    packet = self.socket.recv(size)
	    size -= len(packet)
	    result += packet
	return result

    def query(self, query, add_headers = ""):
        if self.socket_state != UP:
	    self.connect()
        if not query.endswith("\n"):
	    query += "\n"
        query += add_headers
        if not query.endswith("\n"):
	    query += "\n"
        query += "OutputFormat: json\nKeepAlive: on\nResponseHeader: fixed16\n\n"

        try:
	    self.socket.send(query)
	    resp = self.receive_data(16)
	    code = resp[0:3]
	    length = int(resp[4:15].lstrip())
	    data = self.receive_data(length)
	    if code == "200":
		try:
		    return eval(data)
		except:
		    raise MKLivestatusQueryError("Invalid response from Livestatus")
	    else:
	       raise MKLivestatusQueryError(code, data.strip())
        except 1: # Exception, e:
	    self.socket_state = DOWN
	    raise MKLivestatusSocketError(str(e))

class SingleSiteConnection(BaseConnection, Helpers):
    def __init__(self, unixsocketpath):
	BaseConnection.__init__(self, "unix:" + unixsocketpath)

# sites is a dictionary from site name to a dict.
# Keys in the dictionary:
# socket:   socketurl (obligatory)
# timeout:  timeout for tcp/unix in seconds

class MultiSiteConnection(Helpers):
    def __init__(self, sites):
	self.sites = sites
	self.connections = []
	self.deadsites = {}
	self.prepend_site = False
	for sitename, site in sites.items():
	    try:
		url = site["socket"]
	        connection = BaseConnection(url)
		if "timeout" in site:
		   connection.set_timeout(int(site["timeout"]))
		connection.connect()
	        self.connections.append((sitename, site, connection))

	    except Exception, e:
		self.deadsites[sitename] = {
		    "exception" : e,
		    "site"      : site,
		}

    def set_prepend_site(self, p):
	self.prepend_site = p

    def dead_sites(self):
	return self.deadsites

    def alive_sites(self):
	return self.connections.keys()

    def query(self, query, add_headers = ""):
	result = []
	stillalive = []
	for sitename, site, connection in self.connections:
	    try:
		r = connection.query(query, add_headers)
		if self.prepend_site:
		    r = [ [sitename] + l for l in r ]
		result += r
		stillalive.append( (sitename, site, connection) )
	    except Exception, e:
		self.deadsites[sitename] = {
		    "exception" : e,
		    "site" : site,
		}
	self.alive_sites = stillalive
	return result

