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

# This module is needed only for SNMP based checks

def strip_snmp_value(value):
   v = value.strip()
   if v.startswith('"'): v = v[1:]
   if v.endswith('"'): v = v[:-1]
   return v.strip()

# Fetch single values via SNMP. This function is only used by snmp_info_single,
# which is only rarely used. Most checks use snmp_info, which is handled by
# get_snmp_table. 
def get_snmp_explicit(hostname, ipaddress, community, mib, baseoid, suffixes):
    if opt_verbose:
        sys.stderr.write('Fetching misc values from OID %s%s%s%s from IP %s\n' % \
                         (tty_bold, tty_green, baseoid, tty_normal, ipaddress))

    info = []
    if is_bulkwalk_host(hostname):
        cmd = "snmpbulkwalk -v2c"
    else:
        cmd = "snmpwalk -v1"
    for suffix in suffixes:
        if mib:
            mibinfo = " -m %s" % mib
        else:
            mibinfo = ""
        command = cmd + "%s -OQ -Oe -c %s %s %s.%s 2>/dev/null" % \
                  (mibinfo, community, ipaddress, baseoid, suffix)
        if opt_verbose:
            sys.stderr.write('   Running %s...' % (command,))
        num_found = 0
        snmp_process = os.popen(command, "r")
        for line in snmp_process.readlines():
	   if not '=' in line: # TODO: join onto previous line
	      continue
           item, value = line.split("=")
           value_text = strip_snmp_value(value)
           # try to remove text, only keep number
           value_num = value_text.split(" ")[0]
           value_num = value_num.lstrip("+")
           value_num = value_num.rstrip("%")
           item = strip_snmp_value(item.split(":")[-1])
           if item.endswith(".0"):
              item = item[:-2]
           info.append( [ item, value_num, value_text ] )
           num_found += 1
        exitstatus = snmp_process.close()
        if exitstatus:
            if opt_verbose:
                sys.stderr.write(tty_red + tty_bold + "ERROR: " + tty_normal + "SNMP error\n")
            return None
        if opt_verbose:
               sys.stderr.write(' %d items found\n' % num_found)
    return info

def get_snmp_table(hostname, ip, community, oid_info):
    # oid_info is either ( oid, columns ) or
    # ( oid, suboids, columns )
    # suboids is a list if OID-infixes that are put between baseoid
    # and the columns and also prefixed to the index column. This
    # allows to merge distinct SNMP subtrees with a similar structure
    # to one virtual new tree (look into cmctc_temp for an example)
    if is_bulkwalk_host(hostname):
        cmd = "snmpbulkwalk -v2c"
    else:
        cmd = "snmpwalk -v1"
    
    if len(oid_info) == 2:
      oid, columns = oid_info
      suboids = [None]
    else:
      oid, suboids, columns = oid_info

    if opt_verbose:
       sys.stderr.write('Fetching OID %s%s%s%s from IP %s with %s\n' % (tty_bold, tty_green, oid, tty_normal, ip, cmd))

    all_values = []
    index_column = -1
    number_rows = -1
    info = []
    for suboid in suboids:
       colno = -1
       values = []
       for column in columns:
            # column may be integer or string like "1.5.4.2.3"
            colno += 1
            # if column is 0, we do not fetch any data from snmp, but use
            # a running counter as index. If the index column is the first one,
            # we do not know the number of entries right now. We need to fill
            # in later.
            if column == 0:
               index_column = colno
               values.append([])
               continue
            
            fetchoid = oid
            if suboid:
               fetchoid += "." + str(suboid)
            
            command = cmd + " -OQ -Ov -c %s %s %s.%s 2>/dev/null" % \
                (community, ip, fetchoid, str(column))
            snmp_process = os.popen(command, "r").xreadlines()
	    
	    # Ugly(1): in some cases snmpwalk inserts line feed within one
	    # dataset. This happens for example on hexdump outputs longer
	    # than a few bytes. Those dumps are enclose in double quotes.
	    # So if the value begins with a double quote, but the line
	    # does not end with a double quote, we take the next line(s) as
	    # a continuation line.
	    rowinfo = []
	    try:
	        while True: # walk through all lines
		    line = snmp_process.next().strip()
		    if len(line) > 0 and line[0] == '"' and line[-1] != '"': # to be continued
			while True: # scan for end of this dataset
			    nextline = snmp_process.next().strip()
			    line += " " + nextline
			    if line[-1] == '"':
				break
		    rowinfo.append(strip_snmp_value(line))
		    
	    except StopIteration:
		pass

            exitstatus = snmp_process.close()
            if exitstatus:
                if opt_verbose:
                    sys.stderr.write(tty_red + tty_bold + "ERROR: " + tty_normal + "SNMP error\n")
                return None

            # Ugly(2): snmpbulkwalk outputs 'No more variables left in this MIB
            # View (It is past the end of the MIB tree)' if part of tree is
            # not available -- on stdout >:-P
            if len(rowinfo) == 1 and ( \
		rowinfo[0].startswith('No more variables') or \
		rowinfo[0].startswith('End of MIB') or \
		rowinfo[0].startswith('No Such Object available') or \
		rowinfo[0].startswith('No Such Instance currently exists'):
                rowinfo = []
            if len(rowinfo) > 0:
               # if we are working with suboids, we need to prefix them
               # to the index in order to make the index unique
               values.append(rowinfo)
               number_rows = len(rowinfo)

       if index_column != -1:
          index_rows = []
          x = 1
          while x <= number_rows:
             index_rows.append(x)
             x += 1
          values[index_column] = index_rows
       
       # prepend suboid to first column
       if suboid and len(values) > 0:
          first_column = values[0]
          new_first_column = []
          for x in first_column:
             new_first_column.append(str(suboid) + "." + str(x))
          values[0] = new_first_column

       # swap X and Y axis of table (we want one list of columns per item)
       new_info = []
       index = 0
       if len(values) > 0:
          for item in values[0]:
             new_info.append([ c[index] for c in values ])
             index += 1
          info += new_info

    return info

# SNMP-Helper functions used in various checks

def check_snmp_misc(item, params, info):
   for line in info:
      if item == line[0]:
         value = float(line[1])
         text = line[2]
         crit_low, warn_low, warn_high, crit_high = params
         # if value is negative, we have to swap >= and <=!
         perfdata=[ (item, line[1]) ]
         if not within_range(value, crit_low, crit_high):
            return (2, "CRIT - %.2f value out of crit range (%.2f .. %.2f)" % \
                    (value, crit_low, crit_high), perfdata)
         elif not within_range(value, warn_low, warn_high):
            return (2, "WARNING - %.2f value out of warning range (%.2f .. %.2f)" % \
                    (value, warn_low, warn_high), perfdata)
         else:
            return (0, "OK = %s (OK within %.2f .. %.2f)" % (text, warn_low, warn_high), perfdata) 
   return (3, "Missing item %s in SNMP data" % item)

def inventory_snmp_misc(checkname, info):
   inventory = []
   for line in info:
      value = float(line[1])
      params = "(%.1f, %.1f, %.1f, %.1f)" % (value*.8, value*.9, value*1.1, value*1.2)
      inventory.append( (line[0], line[2], params ) )
   return inventory
                        
# Version with simple handling of target parameters: only
# the current value is OK, all other values are CRIT
def inventory_snmp_fixed(checkname, info):
   inventory = []
   for line in info:
      value = line[1]
      params = '"%s"' % (value,)
      inventory.append( (line[0], line[2], params ) )
   return inventory

def check_snmp_fixed(item, targetvalue, info):
   for line in info:
      if item == line[0]:
         value = line[1]
         text = line[2]
         if value != targetvalue:
             return (2, "CRIT - %s (should be %s)" % (value, targetvalue))
         else:
             return (0, "OK - %s" % (value,))
   return (3, "Missing item %s in SNMP data" % item)


