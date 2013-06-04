#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

import socket, time

# Python 2.3 does not have 'set' in normal namespace.
# But it can be imported from 'sets'
try:
    set()
except NameError:
    from sets import Set as set

"""MK Livestatus Python API

This module allows easy access to Nagios via MK Livestatus.
It supports persistent connections via the connection class.
If you want single-shot connections, just initialize a
connection object on-the-fly, e.g.:

r = connection("/var/lib/nagios/rw/live").query_table_assoc("GET hosts")

For persistent connections create and keep an object:

conn = connection("/var/lib/nagios/rw/live")
r1 = conn.query_table_assoc("GET hosts")
r2 = conn.query_row("GET status")
"""

# Keep a global array of persistant connections
persistent_connections = {}

# DEBUGGING PERSISTENT CONNECTIONS
# import os
# hirn_debug = file("/tmp/live.log", "a")
# def hirn(x):
#     pid = os.getpid()
#     hirn_debug.write("[\033[1;3%d;4%dm%d\033[0m] %s\n" % (pid%7+1, (pid/7)%7+1, pid, x))
#     hirn_debug.flush()

class MKLivestatusException(Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return str(self.parameter)

class MKLivestatusSocketError(MKLivestatusException):
    def __init__(self, reason):
        MKLivestatusException.__init__(self, reason)

class MKLivestatusSocketClosed(MKLivestatusSocketError):
    def __init__(self, reason):
        MKLivestatusSocketError.__init__(self, reason)

class MKLivestatusConfigError(MKLivestatusException):
    def __init__(self, reason):
        MKLivestatusException.__init__(self, reason)

class MKLivestatusQueryError(MKLivestatusException):
    def __init__(self, code, reason):
        MKLivestatusException.__init__(self, "%s: %s" % (code, reason))
        self.code = code

class MKLivestatusNotFoundError(MKLivestatusException):
    def __init__(self, query):
        MKLivestatusException.__init__(self, query)
        self.query = query

# We need some unique value here
NO_DEFAULT = lambda: None
class Helpers:
    def query_value(self, query, deflt = NO_DEFAULT):
        """Issues a query that returns exactly one line and one columns and returns
           the response as a single value"""
        result = self.query(query, "ColumnHeaders: off\n")
        try:
            return result[0][0]
        except:
            if deflt == NO_DEFAULT:
                raise MKLivestatusNotFoundError(query)
            else:
                return deflt

    def query_row(self, query):
        """Issues a query that returns one line of data and returns the elements
           of that line as list"""
        return self.query(query, "ColumnHeaders: off\n")[0]

    def query_row_assoc(self, query):
        """Issues a query that returns one line of data and returns the elements
           of that line as a dictionary from column names to values"""
        r = self.query(query, "ColumnHeaders: on\n")[0:2]
        return dict(zip(r[0], r[1]))

    def query_column(self, query):
        """Issues a query that returns exactly one column and returns the values
           of all lines in that column as a single list"""
        return [ l[0] for l in self.query(query, "ColumnHeaders: off\n") ]

    def query_column_unique(self, query):
        """Issues a query that returns exactly one column and returns the values
           of all lines with duplicates removed"""
        result = []
        for line in self.query(query, "ColumnHeaders: off\n"):
            if line[0] not in result:
                result.append(line[0])
        return result

    def query_table(self, query):
        """Issues a query that may return multiple lines and columns and returns
           a list of lists"""
        return self.query(query, "ColumnHeaders: off\n")

    def query_table_assoc(self, query):
        """Issues a query that may return multiple lines and columns and returns
           a dictionary from column names to values for each line. This can be
           very ineffective for large response sets."""
        response = self.query(query, "ColumnHeaders: on\n")
        headers = response[0]
        result = []
        for line in response[1:]:
            result.append(dict(zip(headers, line)))
        return result

    def query_summed_stats(self, query, add_headers = ""):
        """Conveniance function for adding up numbers from Stats queries
        Adds up results column-wise. This is useful for multisite queries."""
        data = self.query(query, add_headers)
        if len(data) == 1:
            return data[0]
        elif len(data) == 0:
            raise MKLivestatusNotFoundError("Empty result to Stats-Query")

        result = []
        for x in range(0, len(data[0])):
            result.append(sum([row[x] for row in data]))
        return result


class BaseConnection:
    def __init__(self, socketurl, persist = False):
        """Create a new connection to a MK Livestatus socket"""
        self.add_headers = ""
        self.persist = persist
        self.socketurl = socketurl
        self.socket = None
        self.timeout = None
        self.successful_persistence = False

    def successfully_persisted(self):
        return self.successful_persistence

    def add_header(self, header):
        self.add_headers += header + "\n"

    def set_timeout(self, timeout):
        self.timeout = timeout
        if self.socket:
            self.socket.settimeout(float(timeout))

    def connect(self):
        if self.persist and self.socketurl in persistent_connections:
            self.socket = persistent_connections[self.socketurl]
            self.successful_persistence = True
            return

        self.successful_persistence = False

        # Create new socket
        self.socket = None
        url = self.socketurl
        parts = url.split(":")
        if parts[0] == "unix":
            if len(parts) != 2:
                raise MKLivestatusConfigError("Invalid livestatus unix URL: %s. "
                        "Correct example is 'unix:/var/run/nagios/rw/live'" % url)
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            target = parts[1]

        elif parts[0] == "tcp":
            try:
                host = parts[1]
                port = int(parts[2])
            except:
                raise MKLivestatusConfigError("Invalid livestatus tcp URL '%s'. "
                        "Correct example is 'tcp:somehost:6557'" % url)
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target = (host, port)
        else:
            raise MKLivestatusConfigError("Invalid livestatus URL '%s'. "
                    "Must begin with 'tcp:' or 'unix:'" % url)

        # If a timeout is set, then we retry after a failure with mild
        # a binary backoff.
        if self.timeout:
            before = time.time()
            sleep_interval = 0.1

        while True:
            try:
                if self.timeout:
                    self.socket.settimeout(float(sleep_interval))
                self.socket.connect(target)
                break
            except Exception, e:
                if self.timeout:
                    time_left = self.timeout - (time.time() - before)
                    # only try again, if there is substantial time left
                    if time_left > sleep_interval:
                        time.sleep(sleep_interval)
                        sleep_interval *= 1.5
                        continue

                self.socket = None
                raise MKLivestatusSocketError("Cannot connect to '%s': %s" % (self.socketurl, e))

        if self.persist:
            persistent_connections[self.socketurl] = self.socket

    def disconnect(self):
        self.socket = None
        if self.persist:
            del persistent_connections[self.socketurl]

    def receive_data(self, size):
        result = ""
        # Timeout is only honored when connecting
        self.socket.settimeout(None)
        while size > 0:
            packet = self.socket.recv(size)
            if len(packet) == 0:
                raise MKLivestatusSocketClosed("Read zero data from socket, nagios server closed connection")
            size -= len(packet)
            result += packet
        return result

    def do_query(self, query, add_headers = ""):
        self.send_query(query, add_headers)
        return self.recv_response(query, add_headers)

    def send_query(self, query, add_headers = "", do_reconnect=True):
        orig_query = query
        if self.socket == None:
            self.connect()
        if not query.endswith("\n"):
            query += "\n"
        query += self.auth_header + self.add_headers
        query += "Localtime: %d\nOutputFormat: python\nKeepAlive: on\nResponseHeader: fixed16\n" % int(time.time())
        query += add_headers
        if not query.endswith("\n"):
            query += "\n"
        query += "\n"

        try:
            # socket.send() will implicitely cast to str(), we need ot
            # convert to UTF-8 in order to avoid exceptions
            if type(query) == unicode:
                query = query.encode("utf-8")
            self.socket.send(query)
        except IOError, e:
            if self.persist:
                del persistent_connections[self.socketurl]
                self.successful_persistence = False
            self.socket = None

            if do_reconnect:
                # Automatically try to reconnect in case of an error, but
                # only once.
                self.connect()
                self.send_query(orig_query, add_headers, False)
                return

            raise MKLivestatusSocketError("RC1:" + str(e))

    # Reads a response from the livestatus socket. If the socket is closed
    # by the livestatus server, we automatically make a reconnect and send
    # the query again (once). This is due to timeouts during keepalive.
    def recv_response(self, query = None, add_headers = "", timeout_at = None):
        try:
            resp = self.receive_data(16)
            code = resp[0:3]
            try:
                length = int(resp[4:15].lstrip())
            except:
                raise MKLivestatusSocketError("Malformed output. Livestatus TCP socket might be unreachable.")
            data = self.receive_data(length)
            if code == "200":
                try:
                    return eval(data)
                except:
                    raise MKLivestatusSocketError("Malformed output")
            else:
                raise MKLivestatusQueryError(code, data.strip())

        # In case of an IO error or the other side having
        # closed the socket do a reconnect and try again, but
        # only once
        except (MKLivestatusSocketClosed, IOError), e:
            self.disconnect()
            now = time.time()
            if query and (not timeout_at or timeout_at > now):
                if timeout_at == None:
                    timeout_at = now + self.timeout
                time.sleep(0.1)
                self.connect()
                self.send_query(query, add_headers)
                return self.recv_response(query, add_headers, timeout_at) # do not send query again -> danger of infinite loop
            else:
                raise MKLivestatusSocketError(str(e))

        except Exception, e:
            raise MKLivestatusSocketError("Unhandled exception: %s" % e)


    def do_command(self, command):
        if self.socket == None:
            self.connect()
        if not command.endswith("\n"):
            command += "\n"
        try:
            self.socket.send("COMMAND " + command + "\n")
        except IOError, e:
            self.socket = None
            if self.persist:
                del persistent_connections[self.socketurl]
            raise MKLivestatusSocketError(str(e))


class SingleSiteConnection(BaseConnection, Helpers):
    def __init__(self, socketurl, persist = False):
        BaseConnection.__init__(self, socketurl, persist)
        self.prepend_site = False
        self.auth_users = {}
        self.deadsites = {} # never filled, just for compatibility
        self.auth_header = ""
        self.limit = None

    def set_prepend_site(self, p):
        self.prepend_site = p

    def set_only_sites(self, os = None):
        pass

    def set_limit(self, limit = None):
        self.limit = limit

    def query(self, query, add_headers = ""):
        if self.limit != None:
            query += "Limit: %d\n" % self.limit
        data = self.do_query(query, add_headers)
        if self.prepend_site:
            return [ [''] + line for line in data ]
        else:
            return data

    def command(self, command, site = None):
        self.do_command(command)

    # Set user to be used in certain authorization domain
    def set_auth_user(self, domain, user):
        if user:
            self.auth_users[domain] = user
        else:
            del self.auth_users[domain]

    # Switch future request to new authorization domain
    def set_auth_domain(self, domain):
        auth_user = self.auth_users.get(domain)
        if auth_user:
            self.auth_header = "AuthUser: %s\n" % auth_user
        else:
            self.auth_header = ""


# sites is a dictionary from site name to a dict.
# Keys in the dictionary:
# socket:   socketurl (obligatory)
# timeout:  timeout for tcp/unix in seconds

class MultiSiteConnection(Helpers):
    def __init__(self, sites, disabled_sites = []):
        self.sites = sites
        self.connections = []
        self.deadsites = {}
        self.prepend_site = False
        self.only_sites = None
        self.limit = None
        self.parallelize = True

        # Helper function for connecting to a site
        def connect_to_site(sitename, site, temporary=False):
            try:
                url = site["socket"]
                persist = not temporary and site.get("persist", False)
                connection = SingleSiteConnection(url, persist)
                if "timeout" in site:
                    connection.set_timeout(int(site["timeout"]))
                connection.connect()
                self.connections.append((sitename, site, connection))

            except Exception, e:
                self.deadsites[sitename] = {
                    "exception" : e,
                    "site"      : site,
                }

        # Needed for temporary connection for status_hosts in disabled sites
        def disconnect_site(sitename):
            i = 0
            for name, site, connection in self.connections:
                if name == sitename:
                    del self.connections[i]
		    return
                i += 1


        # Status host: A status host helps to prevent trying to connect
        # to a remote site which is unreachable. This is done by looking
        # at the current state of a certain host on a local site that is
        # representing the connection to the remote site. The status host
        # is specified as an optional pair of (site, host) in the entry
        # "status_host". We first connect to all sites without a status_host
        # entry, then retrieve the host states of the status hosts and then
        # connect to the remote site which are reachable

        # Tackle very special problem: If the user disables a site which
        # provides status_host information for other sites, the dead-detection
        # would not work. For that cases we make a temporary connection just
        # to fetch the status information
        extra_status_sites = {}
        if len(disabled_sites) > 0:
            status_sitenames = set([])
            for sitename, site in sites.items():
                try:
                    s, h = site.get("status_host")
                    status_sitenames.add(s)
                except:
                    continue
            for sitename in status_sitenames:
                site = disabled_sites.get(sitename)
                if site:
                    extra_status_sites[sitename] = site


        # First connect to sites without status host. Collect status
        # hosts at the same time.

        status_hosts = {} # dict from site to list of status_hosts
        for sitename, site in sites.items() + extra_status_sites.items():
            status_host = site.get("status_host")
            if status_host:
                if type(status_host) != tuple or len(status_host) != 2:
                    raise MKLivestatusConfigError("Status host of site %s is %r, but must be pair of site and host" %
                            (sitename, status_host))
                s, h = status_host
                status_hosts[s] = status_hosts.get(s, []) + [h]
            else:
                connect_to_site(sitename, site)

        # Now learn current states of status hosts and store it in a dictionary
        # from (local_site, host) => state
        status_host_states = {}
        for sitename, hosts in status_hosts.items():
            # Fetch all the states of status hosts of this local site in one query
            query = "GET hosts\nColumns: name state has_been_checked last_time_up\n"
            for host in hosts:
                query += "Filter: name = %s\n" % host
            query += "Or: %d\n" % len(hosts)
            self.set_only_sites([sitename]) # only connect one site
            try:
                result = self.query_table(query)
                # raise MKLivestatusConfigError("TRESulT: %s" % (result,))
                for host, state, has_been_checked, lastup in result:
                    if has_been_checked == 0:
                        state = 3
                    status_host_states[(sitename, host)] = (state, lastup)
            except Exception, e:
                raise MKLivestatusConfigError(e)
                status_host_states[(sitename, host)] = (str(e), None)
        self.set_only_sites() # clear site filter

        # Disconnect from disabled sites that we connected to only to
        # get status information from
        for sitename, site in extra_status_sites.items():
            disconnect_site(sitename)

        # Now loop over all sites having a status_host and take that state
        # of that into consideration

        for sitename, site in sites.items():
            status_host = site.get("status_host")
            if status_host:
                now = time.time()
                shs, lastup = status_host_states.get(status_host, (4, now)) # None => Status host not existing
                deltatime = now - lastup
                if shs == 0 or shs == None:
                    connect_to_site(sitename, site)
                else:
                    if shs == 1:
                        ex = "The remote monitoring host is down"
                    elif shs == 2:
                        ex = "The remote monitoring host is unreachable"
                    elif shs == 3:
                        ex = "The remote monitoring host's state it not yet determined"
                    elif shs == 4:
                        ex = "Invalid status host: site %s has no host %s" % (status_host[0], status_host[1])
                    else:
                        ex = "Error determining state of remote monitoring host: %s" % shs
                    self.deadsites[sitename] = {
                        "site" : site,
                        "status_host_state" : shs,
                        "exception" : ex,
                    }

    def add_header(self, header):
        for sitename, site, connection in self.connections:
            connection.add_header(header)

    def set_prepend_site(self, p):
        self.prepend_site = p

    def set_only_sites(self, os = None):
        self.only_sites = os

    # Impose Limit on number of returned datasets (distributed amoung sites)
    def set_limit(self, limit = None):
        self.limit = limit

    def dead_sites(self):
        return self.deadsites

    def alive_sites(self):
        return self.connections.keys()

    def successfully_persisted(self):
        for sitename, site, connection in self.connections:
            if connection.successfully_persisted():
                return True
        return False

    def set_auth_user(self, domain, user):
        for sitename, site, connection in self.connections:
            connection.set_auth_user(domain, user)

    def set_auth_domain(self, domain):
        for sitename, site, connection in self.connections:
            connection.set_auth_domain(domain)

    def query(self, query, add_headers = ""):
        if self.parallelize:
            return self.query_parallel(query, add_headers)
        else:
            return self.query_non_parallel(query, add_headers)

    def query_non_parallel(self, query, add_headers = ""):
        result = []
        stillalive = []
        limit = self.limit
        for sitename, site, connection in self.connections:
            if self.only_sites != None and sitename not in self.only_sites:
                stillalive.append( (sitename, site, connection) ) # state unknown, assume still alive
                continue
            try:
                if limit != None:
                    limit_header = "Limit: %d\n" % limit
                else:
                    limit_header = ""
                r = connection.query(query, add_headers + limit_header)
                if self.prepend_site:
                    r = [ [sitename] + l for l in r ]
                if limit != None:
                    limit -= len(r) # Account for portion of limit used by this site
                result += r
                stillalive.append( (sitename, site, connection) )
            except Exception, e:
                self.deadsites[sitename] = {
                    "exception" : e,
                    "site" : site,
                }
        self.connections = stillalive
        return result

    # New parallelized version of query(). The semantics differs in the handling
    # of Limit: since all sites are queried in parallel, the Limit: is simply
    # applied to all sites - resulting in possibly more results then Limit requests.
    def query_parallel(self, query, add_headers = ""):
        if self.only_sites != None:
            active_sites = [ c for c in self.connections if c[0] in self.only_sites ]
        else:
            active_sites = self.connections

        start_time = time.time()
        stillalive = []
        limit = self.limit
        if limit != None:
            limit_header = "Limit: %d\n" % limit
        else:
            limit_header = ""

        # First send all queries
        for sitename, site, connection in active_sites:
            try:
                connection.send_query(query, add_headers + limit_header)
            except Exception, e:
                self.deadsites[sitename] = {
                    "exception" : e,
                    "site" : site,
                }

        # Then retrieve all answers. We will be as slow as the slowest of all
        # connections.
        result = []
        for sitename, site, connection in self.connections:
            if self.only_sites != None and sitename not in self.only_sites:
                stillalive.append( (sitename, site, connection) ) # state unknown, assume still alive
                continue

            try:
                r = connection.recv_response(query, add_headers + limit_header)
                stillalive.append( (sitename, site, connection) )
                if self.prepend_site:
                    r = [ [sitename] + l for l in r ]
                result += r
            except Exception, e:
                self.deadsites[sitename] = {
                    "exception" : e,
                    "site" : site,
                }


        self.connections = stillalive
        return result

    def command(self, command, sitename = "local"):
        if sitename in self.deadsites:
            raise MKLivestatusSocketError("Connection to site %s is dead: %s" % \
                    (sitename, self.deadsites[sitename]["exception"]))
        conn = [t[2] for t in self.connections if t[0] == sitename]
        if len(conn) == 0:
            raise MKLivestatusConfigError("Cannot send command to unconfigured site '%s'" % sitename)
        conn[0].do_command(command)

    # Return connection to localhost (UNIX), if available
    def local_connection(self):
        for sitename, site, connection in self.connections:
            if site["socket"].startswith("unix:"):
                return connection
        raise MKLivestatusConfigError("No livestatus connection to local host")

# Examle for forcing local connection:
# live.local_connection().query_single_value(...)
