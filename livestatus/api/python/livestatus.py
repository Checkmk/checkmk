#!/usr/bin/python

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

class MKLivestatusQueryError(MKLivestatusException):
   def __init__(self, reason):
      MKLivestatusException.__init__(self, reason)

class connection:
   """A connection to MK Livestatus. The connection to the socket 
      is either created by calling connect() or by issuing a query().
      The connection is closed if the object is destroyed or if a
      socket error occurs. 
   """

   def __init__(self, socketpath):
      """Create a new connection to a MK Livestatus socket"""
      self.socketpath = socketpath
      self.socket_state = DOWN

   def connect(self):
      """Does the actual connect to the UNIX socket"""
      import socket
      try:
	 self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	 self.socket.connect(self.socketpath)
	 self.socket_state = UP
      except Exception, e:
         self.socket_state = DOWN
	 raise MKLivestatusSocketError(str(e))

   def query(self, query, add_headers = ""):
      """Private function for querying Livestatus. Better use the
	 other variants of query_...()"""
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
      except e:
	  self.socket_state = DOWN
	  raise MKLivestatusSocketError(str(e))

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
	 raise MKLivestatusQueryError(data.strip())

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

   def receive_data(self, size):
      try:
	 result = ""
	 while size > 0:
	    packet = self.socket.recv(size)
	    size -= len(packet)
	    result += packet
	 return result
      except Exception, e:
	 self.socket_state = DOWN
	 raise MKLivestatusSocketError(str(e))

