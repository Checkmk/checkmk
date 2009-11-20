#!/usr/bin/python


import livestatus

socket_path = "/var/lib/nagios/rw/live"

try:
   # Make a single connection for each query
   print "\nPerformance:"
   for key, value in livestatus.connection(socket_path).query_line_assoc("GET status").items():
      print "%-20s: %10.3f" % (key, value)
   print "\nHosts:"
   hosts = livestatus.connection(socket_path).query_table("GET hosts\nColumns: name alias address")
   for name, alias, address in hosts:
      print "%-14s %-16s %s" % (name, address, alias)

   # Do several queries in one connection
   conn = livestatus.connection(socket_path)
   num_up = conn.query_value("GET hosts\nStats: hard_state = 0")
   print "\nHosts up: %d" % num_up

   stats = conn.query_line(
	 "GET services\n"
	 "Stats: state = 0\n"
	 "Stats: state = 1\n"
	 "Stats: state = 2\n"
	 "Stats: state = 3\n")
   print "Service stats: %d/%d/%d/%d" % tuple(stats)

   print "List of commands: %s" % \
      ", ".join(conn.query_column("GET commands\nColumns: name"))

   print "Query error:"
   conn.query_value("GET hosts\nColumns: hirni")


except livestatus.MKLivestatusException, e:
   print "Livestatus error: %s" % str(e)

