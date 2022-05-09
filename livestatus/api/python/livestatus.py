#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""MK Livestatus Python API"""
import ast
import contextlib
import json
import os
import re
import select
import socket
import ssl
import threading
import time
from enum import Enum
from io import BytesIO
from typing import (
    Any,
    AnyStr,
    Dict,
    Iterator,
    List,
    NamedTuple,
    NewType,
    Optional,
    Pattern,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)

# TODO: Find a better solution for this issue. Astroid 2.x bug prevents us from using NewType :(
# (https://github.com/PyCQA/pylint/issues/2296)
UserId = str  # NewType("UserId", str)
SiteId = str  # NewType("SiteId", str)
SiteConfiguration = Dict[str, Any]  # NewType("SiteConfiguration", Dict[str, Any])
SiteConfigurations = Dict[
    SiteId, SiteConfiguration
]  # NewType("SiteConfigurations", Dict[SiteId, SiteConfiguration])

LivestatusColumn = Any
LivestatusRow = NewType("LivestatusRow", List[LivestatusColumn])
LivestatusResponse = NewType("LivestatusResponse", List[LivestatusRow])


# Note: If you want to use JSON as OutputFormat, then note that there are subtle differences
#       in the handling of data types between the Python and JSON formats.
#       So in general you can't transparently switch back and forth between the two.
#       It depends heavily on the queries you use to determine if this is an issue.
#       One known problem with the JSON format:
#         The mk_inventory_gz column contains a BLOB object.
#         The cmc encodes this column with latin-1 and sends it as string
#         After json.loads it needs to be encoded with latin-1 (again) to convert it to a
#         bytes like object
class LivestatusOutputFormat(Enum):
    PYTHON = "python3"
    JSON = "json"


class LivestatusTestingError(RuntimeError):
    pass


#   .--Globals-------------------------------------------------------------.
#   |                    ____ _       _           _                        |
#   |                   / ___| | ___ | |__   __ _| |___                    |
#   |                  | |  _| |/ _ \| '_ \ / _` | / __|                   |
#   |                  | |_| | | (_) | |_) | (_| | \__ \                   |
#   |                   \____|_|\___/|_.__/ \__,_|_|___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Global variables and Exception classes                              |
#   '----------------------------------------------------------------------'

# TODO: This mechanism does not take different connection options into account
# Keep a global array of persistant connections
persistent_connections: Dict[str, socket.socket] = {}

# Regular expression for removing Cache: headers if caching is not allowed
remove_cache_regex: Pattern = re.compile("\nCache:[^\n]*")


def _ensure_unicode(value: Union[str, bytes]) -> str:
    if isinstance(value, str):
        return value
    return value.decode("utf-8")


class MKLivestatusException(Exception):
    pass


class MKLivestatusSocketError(MKLivestatusException):
    pass


class MKLivestatusSocketClosed(MKLivestatusSocketError):
    pass


class MKLivestatusConfigError(MKLivestatusException):
    pass


class MKLivestatusQueryError(MKLivestatusException):
    pass


class MKLivestatusNotFoundError(MKLivestatusException):
    pass


class MKLivestatusTableNotFoundError(MKLivestatusException):
    pass


class MKLivestatusBadGatewayError(MKLivestatusException):
    """Raised when connection errors from CMC <> EC happen"""


# We need some unique value here
NO_DEFAULT = lambda: None


# Escape/strip unwanted chars from (user provided) strings to
# use them in livestatus queries. Prevent injections of livestatus
# protocol related chars or strings
def lqencode(s: AnyStr) -> str:
    # It is not enough to strip off \n\n, because one might submit "\n \n",
    # which is also interpreted as termination of the last query and beginning
    # of the next query.
    return _ensure_unicode(s).replace("\n", "")


def quote_dict(s: str) -> str:
    """Apply the quoting used for dict-valued columns (See #6972)"""
    return "'%s'" % s.replace("'", "''")


def site_local_ca_path() -> str:
    """Path to the site local CA bundle"""
    omd_root = os.getenv("OMD_ROOT")
    if not omd_root:
        raise MKLivestatusConfigError("OMD_ROOT is not set. You are not running in OMD context.")

    return os.path.join(omd_root, "var/ssl/ca-certificates.crt")


def create_client_socket(
    family: socket.AddressFamily,
    tls: bool,
    verify: bool,
    ca_file_path: Optional[str],
    do_handshake_on_connect: bool = True,
) -> socket.socket:
    """Create a client socket object for the livestatus connection"""
    sock = socket.socket(family, socket.SOCK_STREAM)

    if not tls:
        return sock

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_REQUIRED if verify else ssl.CERT_NONE
    context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1

    ca_file_path = ca_file_path if ca_file_path is not None else site_local_ca_path()
    try:
        context.load_verify_locations(ca_file_path)
    except Exception as e:
        raise MKLivestatusConfigError("Failed to load CA file '%s': %s" % (ca_file_path, e))

    return context.wrap_socket(sock, do_handshake_on_connect=do_handshake_on_connect)


# .
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   |  Helper class implementing some generic shortcut functions, e.g.     |
#   |  for fetching just one row or one single value.                      |
#   '----------------------------------------------------------------------'


@contextlib.contextmanager
def intercept_queries():
    SingleSiteConnection.collect_queries.active = True
    SingleSiteConnection.collect_queries.queries = []
    try:
        yield SingleSiteConnection.collect_queries.queries
    finally:
        SingleSiteConnection.collect_queries.active = False


class Helpers:
    def query(
        self, query: "QueryTypes", add_headers: Union[str, bytes] = ""
    ) -> "LivestatusResponse":
        raise NotImplementedError()

    def query_value(self, query: "QueryTypes", deflt: Any = NO_DEFAULT) -> LivestatusColumn:
        """Issues a query that returns exactly one line and one columns and returns
        the response as a single value"""
        normalized_query = Query(query) if not isinstance(query, Query) else query

        result = self.query(normalized_query, "ColumnHeaders: off\n")
        try:
            return result[0][0]
        except IndexError:
            if deflt == NO_DEFAULT:
                raise MKLivestatusNotFoundError(
                    "No matching entries found for query: %s" % normalized_query
                )
            return deflt

    def query_row(self, query: "QueryTypes") -> LivestatusRow:
        """Issues a query that returns one line of data and returns the elements
        of that line as list"""
        normalized_query = Query(query) if not isinstance(query, Query) else query

        result = self.query(normalized_query, "ColumnHeaders: off\n")
        try:
            return result[0]
        except IndexError:
            raise MKLivestatusNotFoundError(
                "No matching entries found for query: %s" % normalized_query
            )

    def query_row_assoc(self, query: "QueryTypes") -> Dict[str, Any]:
        """Issues a query that returns one line of data and returns the elements
        of that line as a dictionary from column names to values"""
        normalized_query = Query(query) if not isinstance(query, Query) else query

        r = self.query(normalized_query, "ColumnHeaders: on\n")[0:2]
        return dict(zip(r[0], r[1]))

    def query_column(self, query: "QueryTypes") -> List[LivestatusColumn]:
        """Issues a query that returns exactly one column and returns the values
        of all lines in that column as a single list"""
        normalized_query = Query(query) if not isinstance(query, Query) else query

        return [l[0] for l in self.query(normalized_query, "ColumnHeaders: off\n")]

    def query_column_unique(self, query: "QueryTypes") -> Set[LivestatusColumn]:
        """Issues a query that returns exactly one column and returns the values
        of all lines with duplicates removed. The "natural order" of the rows is
        not preserved."""
        normalized_query = Query(query) if not isinstance(query, Query) else query
        return {line[0] for line in self.query(normalized_query, "ColumnHeaders: off\n")}

    def query_table(self, query: "QueryTypes") -> LivestatusResponse:
        """Issues a query that may return multiple lines and columns and returns
        a list of lists"""
        normalized_query = Query(query) if not isinstance(query, Query) else query

        return self.query(normalized_query, "ColumnHeaders: off\n")

    def query_table_assoc(self, query: "QueryTypes") -> List[Dict[str, Any]]:
        """Issues a query that may return multiple lines and columns and returns
        a dictionary from column names to values for each line. This can be
        very ineffective for large response sets."""
        normalized_query = Query(query) if not isinstance(query, Query) else query

        response = self.query(normalized_query, "ColumnHeaders: on\n")
        headers = response[0]
        result = []
        for line in response[1:]:
            result.append(dict(zip(headers, line)))
        return result

    def query_summed_stats(
        self, query: "QueryTypes", add_headers: Union[str, bytes] = ""
    ) -> List[int]:
        """Convenience function for adding up numbers from Stats queries
        Adds up results column-wise. This is useful for multisite queries."""
        normalized_query = Query(query) if not isinstance(query, Query) else query

        data = self.query(normalized_query, add_headers)
        if not data:
            raise MKLivestatusNotFoundError(
                "No matching entries found for query: Empty result to Stats-Query"
            )
        return [sum(column) for column in zip(*data)]


class QuerySpecification(NamedTuple):
    table: str
    columns: Sequence[LivestatusColumn]
    headers: str

    def __str__(self) -> str:
        # TODO: later commit
        pass


# TODO: Add more functionality to the Query class:
# - set_prepend_site
# - set_only_sites
# - set_auth_domain
# All these are mostly set for a single query and reset back to another
# value after the query. But nearly all of these usages does not care
# about resetting the option in case of an exception. This could be
# handled better using the query class
class Query:
    """This object can be passed to all livestatus methods accepting a livestatus
    query. The object can be used to hand over the handling code some flags, for
    example to influence the error handling during query processing."""

    default_suppressed_exceptions: Tuple[Type[Exception], ...] = (MKLivestatusTableNotFoundError,)

    def __init__(
        self,
        query: Union[str, bytes, QuerySpecification],
        suppress_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    ) -> None:
        self._query = query
        if suppress_exceptions is None:
            self.suppress_exceptions = self.default_suppressed_exceptions
        else:
            self.suppress_exceptions = suppress_exceptions

    def __str__(self) -> str:
        if isinstance(self._query, QuerySpecification):
            return str(self._query)
        return _ensure_unicode(self._query)

    def supports_json_format(self) -> bool:
        return False


QueryTypes = Union[str, bytes, Query]
OnlySites = Optional[List[SiteId]]
DeadSite = Dict[str, Union[str, int, Exception, SiteConfiguration]]

# .
#   .--SingleSiteConn------------------------------------------------------.
#   |  ____  _             _      ____  _ _        ____                    |
#   | / ___|(_)_ __   __ _| | ___/ ___|(_) |_ ___ / ___|___  _ __  _ __    |
#   | \___ \| | '_ \ / _` | |/ _ \___ \| | __/ _ \ |   / _ \| '_ \| '_ \   |
#   |  ___) | | | | | (_| | |  __/___) | | ||  __/ |__| (_) | | | | | | |  |
#   | |____/|_|_| |_|\__, |_|\___|____/|_|\__\___|\____\___/|_| |_|_| |_|  |
#   |                |___/                                                 |
#   +----------------------------------------------------------------------+
#   |  Connections to one local Unix or remote TCP socket.                 |
#   '----------------------------------------------------------------------'


def _parse_socket_url(url: str) -> Tuple[socket.AddressFamily, Union[str, tuple]]:
    """Parses a Livestatus socket URL to address family and address

    Examples:

        >>> _parse_socket_url('unix:/tmp/sock')
        (<AddressFamily.AF_UNIX: 1>, '/tmp/sock')

        >>> _parse_socket_url('tcp:192.168.0.1:8080')
        (<AddressFamily.AF_INET: 2>, ('192.168.0.1', 8080))

        >>> _parse_socket_url('tcp6:::1:8080')
        (<AddressFamily.AF_INET6: 10>, ('::1', 8080))

        >>> _parse_socket_url('Hallo Welt!')
        Traceback (most recent call last):
        ...
        livestatus.MKLivestatusConfigError: Invalid livestatus URL 'Hallo Welt!'. Must begin with \
'tcp:', 'tcp6:' or 'unix:'

    """
    if ":" in url:
        family_txt, url = url.split(":", 1)
        if family_txt == "unix":
            return socket.AF_UNIX, url

        if family_txt in ["tcp", "tcp6"]:
            try:
                host, port_txt = url.rsplit(":", 1)
                port = int(port_txt)
            except ValueError:
                raise MKLivestatusConfigError(
                    "Invalid livestatus tcp URL '%s'. "
                    "Correct example is 'tcp:somehost:6557' or 'tcp6:somehost:6557'" % url
                )
            address_family = socket.AF_INET if family_txt == "tcp" else socket.AF_INET6
            return address_family, (host, port)

    raise MKLivestatusConfigError(
        "Invalid livestatus URL '%s'. " "Must begin with 'tcp:', 'tcp6:' or 'unix:'" % url
    )


class SingleSiteConnection(Helpers):

    # So we only collect in a specific thread, and not in all of them. We also use
    # a class-variable for this case, so we activate this across all sites at once.
    collect_queries = threading.local()

    def __init__(
        self,
        socketurl: str,
        site_name: Optional[str] = None,
        persist: bool = False,
        allow_cache: bool = False,
        tls: bool = False,
        verify: bool = True,
        ca_file_path: Optional[str] = None,
    ) -> None:
        """Create a new connection to a MK Livestatus socket"""
        super().__init__()
        self.prepend_site = False
        self.site_name = site_name
        self.auth_users: Dict[str, UserId] = {}
        # never filled, just to have the same API as MultiSiteConnection (TODO: Cleanup)
        self.deadsites: Dict[SiteId, DeadSite] = {}
        self.limit: Optional[int] = None
        self.add_headers = ""
        self.auth_header = ""
        self.persist = persist
        self.allow_cache = allow_cache
        self.socketurl = socketurl
        self.socket: Optional[socket.socket] = None
        self.timeout: Optional[int] = None
        self.successful_persistence = False
        self._output_format = LivestatusOutputFormat.PYTHON

        # Whether to establish an encrypted connection
        self.tls = tls
        # Whether to accept any certificate or to verify it
        self.tls_verify = verify
        self._tls_ca_file_path = ca_file_path

    @property
    def tls_ca_file_path(self) -> str:
        """CA file bundle to use for certificate verification"""
        if self._tls_ca_file_path is None:
            return site_local_ca_path()
        return self._tls_ca_file_path

    def successfully_persisted(self) -> bool:
        return self.successful_persistence

    def add_header(self, header: str) -> None:
        self.add_headers += header + "\n"

    def set_timeout(self, timeout: int) -> None:
        self.timeout = timeout
        if self.socket:
            self.socket.settimeout(float(timeout))

    def _try_get_persisted_connection(self) -> Optional[socket.socket]:
        if self.persist and self.socketurl in persistent_connections:
            self.successful_persistence = True
            return persistent_connections[self.socketurl]
        return None

    def connect(self) -> None:
        if (site_socket := self._try_get_persisted_connection()) is None:
            site_socket = self._create_new_socket_connection()
            if self.persist:
                persistent_connections[self.socketurl] = site_socket
        self.socket = site_socket

    def _create_new_socket_connection(self) -> socket.socket:
        self.successful_persistence = False
        family, address = _parse_socket_url(self.socketurl)
        site_socket = self._create_socket(family, self.site_name)

        # If a timeout is set, then we retry after a failure with mild
        # a binary backoff.
        sleep_interval = 0.0
        before = 0.0
        if self.timeout:
            before = time.time()
            sleep_interval = 0.1

        while True:
            try:
                if self.timeout:
                    site_socket.settimeout(sleep_interval)

                # In case of TLS it may happen that we are retrying after the connect succeeded
                # and the handshake failed. In this case do not retry the connect.
                try:
                    site_socket.connect(address)
                except ValueError as e:
                    if "attempt to connect already-connected SSLSocket" not in str(e):
                        raise

                if self.tls:
                    # Mypy does not understand the SSL socket wrapping
                    site_socket.do_handshake()  # type: ignore[attr-defined]

                break
            except Exception as e:
                if self.timeout:
                    time_left = self.timeout - (time.time() - before)
                    # only try again, if there is substantial time left
                    if time_left > sleep_interval:
                        time.sleep(sleep_interval)
                        sleep_interval *= 1.5
                        continue

                try:
                    site_socket.close()
                except OSError:
                    pass
                raise MKLivestatusSocketError("Cannot connect to '%s': %s" % (self.socketurl, e))

        return site_socket

    # NOTE:
    # The site_name parameter is here to be able to create a mocked socket in the testing
    # framework which fakes the correct site connection. It is never used at runtime here, but
    # will break a lot of tests if removed.
    # Its optional because some parts of the code instantiate a SingleSiteConnection directly
    # without being able to pass a site_name parameter.
    def _create_socket(
        self,
        family: socket.AddressFamily,
        site_name: Optional[SiteId] = None,
    ) -> socket.socket:
        """Creates the Livestatus client socket

        It ensures that either a TLS secured socket or a plain text socket
        is being created."""
        return create_client_socket(
            family, self.tls, self.tls_verify, self._tls_ca_file_path, do_handshake_on_connect=False
        )

    def disconnect(self) -> None:
        self._close_socket()

    def _close_socket(self) -> None:
        if self.socket is not None:
            try:
                self.socket.close()
            except OSError:
                pass

            self.socket = None

        if self.persist:
            self.successful_persistence = False
            try:
                del persistent_connections[self.socketurl]
            except KeyError:
                pass

    def receive_data(self, size: int, timeout: Optional[float] = None) -> bytes:
        if self.socket is None:
            raise MKLivestatusSocketError("Socket to '%s' is not connected" % self.socketurl)

        data = BytesIO()
        self.socket.settimeout(timeout)
        receive_start = time.time()
        while size > 0:
            if is_socket_readable(self.socket, 0.1):
                packet = self.socket.recv(size)
                if not packet:
                    raise MKLivestatusSocketClosed(
                        "Read zero data from socket, remote peer closed connection."
                    )
                size -= len(packet)
                data.write(packet)
            if timeout is not None and (time.time() - receive_start) > timeout:
                raise MKLivestatusSocketError(
                    f"{timeout}s while reading data from socket. "
                    "Received data: {data.getbuffer().nbytes}/{size} bytes"
                )

        return data.getvalue()

    def do_query(self, query_obj: Query, add_headers: str = "") -> LivestatusResponse:
        with _livestatus_output_format_switcher(query_obj, self):
            query = self.build_query(query_obj, add_headers)
            self.send_query(query)
            try:
                return self.parse_raw_response(
                    self.receive_raw_response(query, query_obj.suppress_exceptions)
                )
            except MKLivestatusQueryError:
                self.disconnect()
                raise

    def build_query(self, query_obj: Query, add_headers: str) -> str:
        query = str(query_obj)
        if not self.allow_cache:
            query = remove_cache_regex.sub("", query)

        headers = [
            self.auth_header,
            self.add_headers,
            f"Localtime: {int(time.time()):d}",
            "OutputFormat: %s" % self._output_format.value,
            "KeepAlive: on",
            "ResponseHeader: fixed16",
            add_headers,
        ]

        return _combine_query(query, headers)

    def send_query(self, query: str, do_reconnect: bool = True) -> None:
        if self.socket is None:
            self.connect()

        if self.socket is None:
            raise MKLivestatusSocketError("Socket to '%s' is not connected" % self.socketurl)

        try:
            self.socket.sendall(query.encode("utf-8") + b"\n\n")
            if getattr(self.collect_queries, "active", False):
                self.collect_queries.queries.append(query)
        except IOError as e:
            self._close_socket()

            if do_reconnect:
                # Automatically try to reconnect in case of an error, but only once.
                self.connect()
                self.send_query(query, False)
                return

            raise MKLivestatusSocketError("RC1:" + str(e))

    # Reads a response from the livestatus socket. If the socket is closed
    # by the livestatus server, we automatically make a reconnect and send
    # the query again (once). This is due to timeouts during keepalive.
    def receive_raw_response(
        self,
        query: str,
        suppress_exceptions: Tuple[Type[Exception], ...],
        timeout_at: Optional[float] = None,
    ) -> bytes:
        try:
            # Headers are always ASCII encoded
            resp = self.receive_data(16)
            code = resp[0:3].decode("ascii")
            try:
                length = int(resp[4:15].lstrip())
            except Exception:
                self.disconnect()
                raise MKLivestatusSocketError(
                    "Malformed output. Livestatus TCP socket might be unreachable or wrong"
                    "encryption settings are used."
                )

            # Apply a lower timeout for the content because the data is already available
            # in the socket. The liveproxyd (same system) has the complete data available
            # while the data from a standard connection can still take some time.
            # 30 seconds should be more than enough for the maximum telegram size of 100MB
            data = self.receive_data(length, 30)

            if code == "200":
                return data

            error_info = data.decode("utf-8")
            if code == "404":
                raise MKLivestatusTableNotFoundError("Not Found (%s): %r" % (code, error_info))

            if code == "502":
                raise MKLivestatusBadGatewayError(error_info)

            raise MKLivestatusQueryError("%s: %s" % (code, error_info))

        except (MKLivestatusSocketClosed, IOError) as e:
            # In case of an IO error or the other side having
            # closed the socket do a reconnect and try again
            self.disconnect()

            # In case of unix socket connections, do not start any reconnection attempts
            # The other side (liveproxyd) might have had a good reason to disconnect
            # Note: In most scenarios the liveproxyd still tries to send back a reasonable
            # error response back to the client
            if self.socket and self.socket.family == socket.AF_UNIX:
                raise MKLivestatusSocketError("Unix socket was closed by peer")

            now = time.time()
            if not timeout_at or timeout_at > now:
                if timeout_at is None:
                    # Try until timeout reached in case there was a timeout configured.
                    # Otherwise only retry once.
                    timeout_at = now
                    if self.timeout:
                        timeout_at += self.timeout

                time.sleep(0.1)
                self.connect()
                self.send_query(query)
                # do not send query again -> danger of infinite loop
                return self.receive_raw_response(query, suppress_exceptions, timeout_at)
            raise MKLivestatusSocketError(str(e))

        except suppress_exceptions:
            raise

        except Exception as e:
            # Catches
            # MKLivestatusQueryError
            # MKLivestatusSocketError
            # FIXME: ? self.disconnect()
            raise MKLivestatusSocketError("Unhandled exception: %s" % e)

    def parse_raw_response(self, raw_response: bytes) -> LivestatusResponse:
        data = raw_response.decode("utf-8")
        try:
            if self._output_format == LivestatusOutputFormat.PYTHON:
                return ast.literal_eval(data)

            if self._output_format == LivestatusOutputFormat.JSON:
                return json.loads(data)

            raise MKLivestatusQueryError("Unknown OutputFormat %r" % self._output_format)
        except (ValueError, SyntaxError):
            raise MKLivestatusQueryError("Malformed raw response output")

    def set_prepend_site(self, p: bool) -> None:
        self.prepend_site = p

    def set_only_sites(self, sites: Optional[List[SiteId]] = None) -> None:
        pass

    def set_output_format(self, output_format: LivestatusOutputFormat) -> None:
        self._output_format = output_format

    def get_output_format(self) -> LivestatusOutputFormat:
        return self._output_format

    def set_limit(self, limit: Optional[int] = None) -> None:
        self.limit = limit

    def query(self, query: "QueryTypes", add_headers: Union[str, bytes] = "") -> LivestatusResponse:
        # Normalize argument types
        normalized_add_headers = _ensure_unicode(add_headers)
        normalized_query = Query(query) if not isinstance(query, Query) else query

        if self.limit is not None:
            normalized_query = Query(
                "%sLimit: %d\n" % (normalized_query, self.limit),
                normalized_query.suppress_exceptions,
            )

        response = self.do_query(normalized_query, normalized_add_headers)
        if self.prepend_site:
            for row in response:
                row.insert(0, b"")
        return response

    # TODO: Cleanup all call sites to hand over str types
    def command(self, command: AnyStr, site: Optional[SiteId] = None) -> None:
        command_str = _ensure_unicode(command).rstrip("\n")
        if not command_str.startswith("["):
            command_str = f"[{int(time.time())}] {command_str}"
        self.send_command(f"COMMAND {command_str}")

    def send_command(self, command: str) -> None:
        if self.socket is None:
            self.connect()

        assert self.socket is not None  # TODO: refactor to avoid assert

        try:
            self.socket.sendall(command.encode("utf-8") + b"\n\n")
        except IOError as e:
            self._close_socket()
            raise MKLivestatusSocketError(str(e))

    # Set user to be used in certain authorization domain
    def set_auth_user(self, domain: str, user: UserId) -> None:
        if user:
            self.auth_users[domain] = user
        elif domain in self.auth_users:
            del self.auth_users[domain]

    # Switch future request to new authorization domain
    def set_auth_domain(self, domain: str) -> None:
        auth_user = self.auth_users.get(domain)
        if auth_user:
            self.auth_header = "AuthUser: %s\n" % auth_user
        else:
            self.auth_header = ""


# .
#   .--MultiSiteConn-------------------------------------------------------.
#   |     __  __       _ _   _ ____  _ _        ____                       |
#   |    |  \/  |_   _| | |_(_) ___|(_) |_ ___ / ___|___  _ __  _ __       |
#   |    | |\/| | | | | | __| \___ \| | __/ _ \ |   / _ \| '_ \| '_ \      |
#   |    | |  | | |_| | | |_| |___) | | ||  __/ |__| (_) | | | | | | |     |
#   |    |_|  |_|\__,_|_|\__|_|____/|_|\__\___|\____\___/|_| |_|_| |_|     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Connections to a list of local and remote sites.                    |
#   '----------------------------------------------------------------------'

# sites is a dictionary from site name to a dict.
# Keys in the dictionary:
# socket:   socketurl (obligatory)
# timeout:  timeout for tcp/unix in seconds

# TODO: Move the connect/disconnect stuff to separate methods. Then make
# it possible to connect/disconnect while an object is instantiated.


class ConnectedSite(NamedTuple):
    id: SiteId
    config: SiteConfiguration
    connection: SingleSiteConnection


ConnectedSites = List[ConnectedSite]


class MultiSiteConnection(Helpers):
    def __init__(
        self, sites: SiteConfigurations, disabled_sites: Optional[SiteConfigurations] = None
    ) -> None:
        if disabled_sites is None:
            disabled_sites = {}

        self.sites = sites
        self.connections: ConnectedSites = []
        self.deadsites: Dict[SiteId, DeadSite] = {}
        self.prepend_site = False
        self.only_sites: OnlySites = None
        self.limit: Optional[int] = None
        self.parallelize = True

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
            status_sitenames = set()
            for sitename, site in sites.items():
                status_host = site.get("status_host")
                if status_host is None:
                    continue

                s, h = status_host
                status_sitenames.add(s)

            for sitename in status_sitenames:
                status_site = disabled_sites.get(sitename)
                if status_site:
                    extra_status_sites[sitename] = status_site

        # First connect to sites without status host. Collect status
        # hosts at the same time.

        # dict from site to list of status_hosts
        status_hosts: Dict[SiteId, List[bytes]] = {}
        sites_dict = sites.copy()
        sites_dict.update(extra_status_sites)
        for sitename, site in sites_dict.items():
            status_host = site.get("status_host")
            if status_host:
                if not isinstance(status_host, tuple) or len(status_host) != 2:
                    raise MKLivestatusConfigError(
                        "Status host of site %s is %r, but must be pair of site and host"
                        % (sitename, status_host)
                    )
                s, h = status_host
                status_hosts[s] = status_hosts.get(s, []) + [h]
            else:
                try:
                    connection = self.connect_to_site(sitename, site)
                    self.connections.append(ConnectedSite(sitename, site, connection))
                except Exception as e:
                    self.deadsites[sitename] = {
                        "exception": e,
                        "site": site,
                    }

        # Now learn current states of status hosts and store it in a dictionary
        # from (local_site, host) => state
        status_host_states = {}
        for sitename, hosts in status_hosts.items():
            # Fetch all the states of status hosts of this local site in one query
            query = "GET hosts\nColumns: name state has_been_checked last_time_up\n"
            for host in hosts:
                query += "Filter: name = %s\n" % str(host)
            query += "Or: %d\n" % len(hosts)
            self.set_only_sites([sitename])  # only connect one site
            try:
                result = self.query_table(query)
                # raise MKLivestatusConfigError("TRESulT: %s" % (result,))
                for host, state, has_been_checked, lastup in result:
                    if has_been_checked == 0:
                        state = 3
                    status_host_states[(sitename, host)] = (state, lastup)
            except Exception as e:
                raise MKLivestatusConfigError(e)
        self.set_only_sites()  # clear site filter

        # Disconnect from disabled sites that we connected to only to
        # get status information from
        for sitename, site in extra_status_sites.items():
            self._disconnect_site(sitename)

        # Now loop over all sites having a status_host and take that state
        # of that into consideration
        for sitename, site in sites.items():
            status_host = site.get("status_host")
            if status_host:
                now = time.time()
                shs, lastup = status_host_states.get(
                    status_host, (4, now)
                )  # None => Status host not existing
                if shs == 0 or shs is None:
                    try:
                        connection = self.connect_to_site(sitename, site)
                        self.connections.append(ConnectedSite(sitename, site, connection))
                    except Exception as e:
                        self.deadsites[sitename] = {
                            "exception": e,
                            "site": site,
                        }
                else:
                    if shs == 1:
                        ex = "The remote monitoring host is down"
                    elif shs == 2:
                        ex = "The remote monitoring host is unreachable"
                    elif shs == 3:
                        ex = "The remote monitoring host's state it not yet determined"
                    elif shs == 4:
                        ex = "Invalid status host: site %s has no host %s" % (
                            status_host[0],
                            status_host[1],
                        )
                    else:
                        ex = "Error determining state of remote monitoring host: %s" % shs
                    self.deadsites[sitename] = {
                        "site": site,
                        "status_host_state": shs,
                        "exception": ex,
                    }

    def connect_to_site(
        self, site_name: SiteId, site: SiteConfiguration, temporary: bool = False
    ) -> SingleSiteConnection:
        """Helper function for connecting to a site"""
        url = site["socket"]
        persist = not temporary and site.get("persist", False)
        tls_type, tls_params = site.get("tls", ("plain_text", {}))

        connection = SingleSiteConnection(
            socketurl=url,
            site_name=site_name,
            persist=persist,
            allow_cache=site.get("cache", False),
            tls=tls_type != "plain_text",
            verify=tls_params.get("verify", True),
            ca_file_path=tls_params.get("ca_file_path", None),
        )

        if "timeout" in site:
            connection.set_timeout(int(site["timeout"]))
        connection.connect()
        return connection

    def disconnect(self) -> None:
        for connected_site in self.connections:
            connected_site.connection.disconnect()
        self.connections.clear()

    # Needed for temporary connection for status_hosts in disabled sites
    def _disconnect_site(self, sitename: SiteId) -> None:
        i = 0
        for connected_site in self.connections:
            if connected_site.id == sitename:
                del self.connections[i]
                return
            i += 1

    def add_header(self, header: str) -> None:
        for connected_site in self.connections:
            connected_site.connection.add_header(header)

    def set_prepend_site(self, p: bool) -> None:
        self.prepend_site = p

    def set_only_sites(self, sites: Optional[OnlySites] = None) -> None:
        """Make future queries only contact the given sites.

        Provide a list of site IDs to not contact all configured sites, but only the listed
        site IDs. In case None is given, the limitation is removed.
        """
        self.only_sites = sites

    def set_limit(self, limit: Optional[int] = None) -> None:
        """Impose Limit on number of returned datasets (distributed among sites)"""
        self.limit = limit

    def dead_sites(self) -> Dict[SiteId, DeadSite]:
        return self.deadsites

    def alive_sites(self) -> List[SiteId]:
        return [s.id for s in self.connections]

    def successfully_persisted(self) -> bool:
        for connected_site in self.connections:
            if connected_site.connection.successfully_persisted():
                return True
        return False

    def set_output_format(self, output_format: LivestatusOutputFormat):
        for connected_site in self.connections:
            connected_site.connection.set_output_format(output_format)

    def get_output_format(self) -> LivestatusOutputFormat:
        # Since all connections share the same output format, simple return the first connection
        if not self.connections:
            return LivestatusOutputFormat.PYTHON
        return self.connections[0].connection.get_output_format()

    def set_auth_user(self, domain: str, user: UserId) -> None:
        for connected_site in self.connections:
            connected_site.connection.set_auth_user(domain, user)

    def set_auth_domain(self, domain: str) -> None:
        for connected_site in self.connections:
            connected_site.connection.set_auth_domain(domain)

    def query(self, query: "QueryTypes", add_headers: Union[str, bytes] = "") -> LivestatusResponse:
        # Normalize argument types
        normalized_add_headers = _ensure_unicode(add_headers)
        normalized_query = Query(query) if not isinstance(query, Query) else query

        with _livestatus_output_format_switcher(normalized_query, self):
            if self.parallelize:
                return self.query_parallel(normalized_query, normalized_add_headers)
            return self.query_non_parallel(normalized_query, normalized_add_headers)

    def query_non_parallel(self, query: Query, add_headers: str = "") -> LivestatusResponse:
        result = LivestatusResponse([])
        stillalive = []
        limit = self.limit
        for connected_site in self.connections:
            if self.only_sites is not None and connected_site.id not in self.only_sites:
                stillalive.append(connected_site)  # state unknown, assume still alive
                continue
            try:
                if limit is not None:
                    limit_header = "Limit: %d\n" % limit
                else:
                    limit_header = ""
                r = connected_site.connection.query(query, add_headers + limit_header)
                if self.prepend_site:
                    for row in r:
                        row.insert(0, connected_site.id)
                if limit is not None:
                    limit -= len(r)  # Account for portion of limit used by this site
                result += r
                stillalive.append(connected_site)
            except LivestatusTestingError:
                raise
            except Exception as e:
                connected_site.connection.disconnect()
                self.deadsites[connected_site.id] = {
                    "exception": e,
                    "site": connected_site.config,
                }
        self.connections = stillalive
        return result

    # New parallelized version of query(). The semantics differs in the handling
    # of Limit: since all sites are queried in parallel, the Limit: is simply
    # applied to all sites - resulting in possibly more results then Limit requests.
    def query_parallel(self, query: Query, add_headers: str = "") -> LivestatusResponse:
        stillalive = []
        if self.only_sites is not None:
            connect_to_sites = [c for c in self.connections if c[0] in self.only_sites]
            # Unused sites are assumed to be alive
            stillalive.extend([c for c in self.connections if c[0] not in self.only_sites])
        else:
            connect_to_sites = self.connections

        limit = self.limit
        if limit is not None:
            limit_header = "Limit: %d\n" % limit
        else:
            limit_header = ""

        # First send all queries
        for connected_site in connect_to_sites:
            try:
                str_query = connected_site.connection.build_query(query, add_headers + limit_header)
                connected_site.connection.send_query(str_query)
            except LivestatusTestingError:
                raise
            except Exception as e:
                self.deadsites[connected_site.id] = {
                    "exception": e,
                    "site": connected_site.config,
                }

        # Then retrieve all raw responses. We will be as slow as the slowest of all connections.
        site_responses: List[Tuple[ConnectedSite, bytes]] = []
        for connected_site in connect_to_sites:
            try:
                site_responses.append(
                    (
                        connected_site,
                        connected_site.connection.receive_raw_response(
                            str_query, query.suppress_exceptions
                        ),
                    )
                )
            except query.suppress_exceptions:
                # Mostly handles exception types MKLivestatusTableNotFoundError
                stillalive.append(connected_site)
                continue
            except LivestatusTestingError:
                raise
            except Exception as e:
                connected_site.connection.disconnect()
                self.deadsites[connected_site.id] = {
                    "exception": e,
                    "site": connected_site.config,
                }

        # Convert responses to python format
        result = LivestatusResponse([])
        for connected_site, raw_response in site_responses:
            try:
                rows = connected_site.connection.parse_raw_response(raw_response)
                stillalive.append(connected_site)
                if self.prepend_site:
                    for row in rows:
                        row.insert(0, connected_site.id)
                result.extend(rows)
            except query.suppress_exceptions:
                stillalive.append(connected_site)
                continue
            except LivestatusTestingError:
                raise
            except Exception as e:
                connected_site.connection.disconnect()
                self.deadsites[connected_site.id] = {
                    "exception": e,
                    "site": connected_site.config,
                }

        self.connections = stillalive
        return result

    # TODO: Is this SiteId(...) the way to go? Without this mypy complains about incompatible bytes
    # vs. Optional[SiteId]
    def command(self, command: AnyStr, sitename: Optional[SiteId] = SiteId("local")) -> None:
        if sitename in self.deadsites:
            raise MKLivestatusSocketError(
                "Connection to site %s is dead: %s"
                % (sitename, self.deadsites[sitename]["exception"])
            )
        conn = [t[2] for t in self.connections if t[0] == sitename]
        if len(conn) == 0:
            raise MKLivestatusConfigError(
                "Cannot send command to unconfigured site '%s'" % sitename
            )
        conn[0].command(command)

    # Return connection to localhost (UNIX), if available
    def local_connection(self) -> SingleSiteConnection:
        for _sitename, site, connection in self.connections:
            if site["socket"].startswith("unix:") and "liveproxy" not in site["socket"]:
                return connection
        raise MKLivestatusConfigError("No livestatus connection to local host")

    def get_connection(self, site_id: SiteId) -> SingleSiteConnection:
        for this_site_id, _site, connection in self.connections:
            if this_site_id == site_id:
                return connection
        raise KeyError("Connection does not exist")


@contextlib.contextmanager
def _livestatus_output_format_switcher(
    query: Query, connection: Union[MultiSiteConnection, SingleSiteConnection]
) -> Iterator[None]:
    previous_format = connection.get_output_format()
    try:
        if query.supports_json_format():
            connection.set_output_format(LivestatusOutputFormat.JSON)
        yield
    finally:
        connection.set_output_format(previous_format)


# .
#   .--LocalConn-----------------------------------------------------------.
#   |            _                    _  ____                              |
#   |           | |    ___   ___ __ _| |/ ___|___  _ __  _ __              |
#   |           | |   / _ \ / __/ _` | | |   / _ \| '_ \| '_ \             |
#   |           | |__| (_) | (_| (_| | | |__| (_) | | | | | | |            |
#   |           |_____\___/ \___\__,_|_|\____\___/|_| |_|_| |_|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  LocalConnection is a convenience class for connecting to the        |
#   |  local Livestatus socket within an OMD site. It only works within    |
#   |  OMD context.                                                        |
#   '----------------------------------------------------------------------'


class LocalConnection(SingleSiteConnection):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        omd_root = os.getenv("OMD_ROOT")
        if not omd_root:
            raise MKLivestatusConfigError(
                "OMD_ROOT is not set. You are not running in OMD context."
            )
        super().__init__("unix:" + omd_root + "/tmp/run/live", "local", *args, **kwargs)


def _combine_query(query: str, headers: Union[str, List[str]]):
    """Combine a query with additional headers

    Examples:

        Combining supports either strings or list-of-strings:

            >>> _combine_query("GET tables", "Filter: name = heute")
            'GET tables\\nFilter: name = heute'

            >>> _combine_query("GET tables", ["Filter: name = heute"])
            'GET tables\\nFilter: name = heute'

        Empty headers are treated correctly:

            >>> _combine_query("GET tables", "")
            'GET tables'

        Trailing whitespaces are stripped:

            >>> _combine_query("GET tables \\n", "")
            'GET tables'

            >>> _combine_query("GET tables \\n", "\\n")
            'GET tables'

            >>> _combine_query("GET tables \\n", ["\\n", " \\n"])
            'GET tables'

        Weird headers are also merged like they should:

            >>> _combine_query("GET tables", ["Filter: name = heute\\n", "", "\\n "])
            'GET tables\\nFilter: name = heute'

    Args:
        query:
            A livestatus query as a text.
        headers:
            Either a list of strings or a simple string, containing additional filter-headers.

    Returns:

    """
    query = query.rstrip("\n ")

    if isinstance(headers, list):
        # We filter out all headers which are either empty or only contain whitespaces.
        headers = "\n".join([head.rstrip("\n ") for head in headers if head.strip()])

    headers = headers.strip("\n ")

    if not headers:
        return query

    return query + "\n" + headers


def is_socket_readable(sock: socket.socket, select_timeout: float = 1.0) -> bool:
    # SSL sockets may not return any fileno in the select, since the data lingers around in pending
    # https://stackoverflow.com/questions/3187565/select-and-ssl-in-python
    # https://stackoverflow.com/questions/40346619/behavior-of-pythons-select-with-partial-recv-on-ssl-socket/40347469#40347469
    if isinstance(sock, ssl.SSLSocket) and sock.pending():
        return True
    fd_sets = select.select([sock], [], [], select_timeout)
    return sock in fd_sets[0]
