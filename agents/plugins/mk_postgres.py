#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
r"""Check_MK Agent Plugin: mk_postgres

This is a Check_MK Agent plugin. If configured, it will be called by the
agent without any arguments.
"""

__version__ = "2.0.0p25"

import io
import subprocess
import re
import os
import abc
import platform
import sys
import logging
# optparse exist in python2.6 up to python 3.8. Do not use argparse, because it will not run with python2.6
import optparse  # pylint: disable=W0402

try:
    from typing import Any, Dict, List, Optional, Tuple
except ImportError:
    # We need typing only for testing
    pass

# For Python 3 sys.stdout creates \r\n as newline for Windows.
# Checkmk can't handle this therefore we rewrite sys.stdout to a new_stdout function.
# If you want to use the old behaviour just use old_stdout.
if sys.version_info[0] >= 3:
    new_stdout = io.TextIOWrapper(sys.stdout.buffer,
                                  newline='\n',
                                  encoding=sys.stdout.encoding,
                                  errors=sys.stdout.errors)
    old_stdout, sys.stdout = sys.stdout, new_stdout

OS = platform.system()
IS_LINUX = OS == "Linux"
IS_WINDOWS = OS == "Windows"
LOGGER = logging.getLogger(__name__)

if IS_LINUX:
    import resource
elif IS_WINDOWS:
    import time
else:
    raise NotImplementedError("The OS type(%s) is not yet implemented." % platform.system())


# for compatibility with python 2.6
def subprocess_check_output(args):
    return subprocess.Popen(args, stdout=subprocess.PIPE).communicate()[0]


# Borrowed from six
def ensure_str(s):
    if sys.version_info[0] >= 3:
        if isinstance(s, bytes):
            return s.decode("utf-8")
    else:
        if isinstance(s, unicode):  # pylint: disable=undefined-variable
            return s.encode("utf-8")
    return s


class PostgresPsqlError(RuntimeError):
    pass


class PostgresBase:
    """
    Base class for x-plattform postgres queries
    :param db_user: The postgres db user
    :param instance: Pass an instance, in case of monitoring a server with multiple instances

    All abstract methods must have individual implementation depending on the OS type
    which runs postgres.
    All non-abstract methods are meant to work on all OS types which were subclassed.
    """
    __metaclass__ = abc.ABCMeta
    _supported_pg_versions = ["12"]

    def __init__(self, db_user, instance):
        # type: (str, Dict) -> None
        self.db_user = db_user
        self.name = instance["name"]
        self.pg_user = instance["pg_user"]
        self.pg_port = instance["pg_port"]
        self.pg_database = instance["pg_database"]
        self.pg_passfile = instance.get("pg_passfile", "")
        self.my_env = os.environ.copy()
        self.my_env["PGPASSFILE"] = instance.get("pg_passfile", "")
        self.sep = os.sep
        self.psql, self.bin_path = self.get_psql_and_bin_path()
        self.conn_time = ""  # For caching as conn_time and version are in one query

    @abc.abstractmethod
    def run_sql_as_db_user(self,
                           sql_cmd,
                           extra_args="",
                           field_sep=";",
                           quiet=True,
                           rows_only=True,
                           mixed_cmd=False):
        # type: (str, str, str, bool, bool, bool) -> str
        """This method implements the system specific way to call the psql interface"""

    @abc.abstractmethod
    def get_psql_and_bin_path(self):
        """This method returns the system specific psql binary and its path"""

    @abc.abstractmethod
    def get_instances(self):
        """Gets all instances"""

    @abc.abstractmethod
    def get_stats(self, databases):
        """Get the stats"""

    @abc.abstractmethod
    def get_version_and_connection_time(self):
        """Get the pg version and the time for the query connection"""

    @abc.abstractmethod
    def get_bloat(self, databases, numeric_version):
        """Get the db bloats"""

    def get_databases(self):
        """Gets all non template databases"""
        sql_cmd = "SELECT datname FROM pg_database WHERE datistemplate = false;"
        out = self.run_sql_as_db_user(sql_cmd)
        return out.replace("\r", "").split("\n")

    def get_server_version(self):
        """Gets the server version"""
        out = self.run_sql_as_db_user('SHOW server_version;')
        if out == "":
            raise PostgresPsqlError("psql connection returned with no data")
        version_as_string = out.split()[0]
        # Use Major and Minor version for float casting: "12.6.4" -> 12.6
        return float(".".join(version_as_string.split(".")[0:2]))

    def get_condition_vars(self, numeric_version):
        """Gets condition variables for other queries"""
        if numeric_version > 9.2:
            return "state", "'idle'"
        return "current_query", "'<IDLE>'"

    def get_connections(self):
        """Gets the the idle and active connections"""
        connection_sql_cmd = ("SELECT datname, "
                              "(SELECT setting AS mc FROM pg_settings "
                              "WHERE name = 'max_connections') AS mc, "
                              "COUNT(state) FILTER (WHERE state='idle') AS idle, "
                              "COUNT(state) FILTER (WHERE state='active') AS active "
                              "FROM pg_stat_activity group by 1;")

        return self.run_sql_as_db_user(connection_sql_cmd,
                                       rows_only=False,
                                       extra_args="-P footer=off")

    def get_sessions(self, row, idle):
        """Gets idle and open sessions"""
        condition = "%s = %s" % (row, idle)

        sql_cmd = ("SELECT %s, count(*) FROM pg_stat_activity "
                   "WHERE %s IS NOT NULL GROUP BY (%s);") % (condition, row, condition)

        out = self.run_sql_as_db_user(sql_cmd,
                                      quiet=False,
                                      extra_args="--variable ON_ERROR_STOP=1",
                                      field_sep=" ")

        # line with number of idle sessions is sometimes missing on Postgres 8.x. This can lead
        # to an altogether empty section and thus the check disappearing.
        if not out.startswith("t"):
            out += "\nt 0"
        return out

    def get_query_duration(self, numeric_version):
        """Gets the query duration"""
        # Previously part of simple_queries

        if numeric_version > 9.2:
            querytime_sql_cmd = ("SELECT datname, datid, usename, client_addr, state AS state, "
                                 "COALESCE(ROUND(EXTRACT(epoch FROM now()-query_start)),0) "
                                 "AS seconds, pid, "
                                 "regexp_replace(query, E'[\\n\\r\\u2028]+', ' ', 'g' ) "
                                 "AS current_query FROM pg_stat_activity "
                                 "WHERE (query_start IS NOT NULL AND "
                                 "(state NOT LIKE 'idle%' OR state IS NULL)) "
                                 "ORDER BY query_start, pid DESC;")

        else:
            querytime_sql_cmd = ("SELECT datname, datid, usename, client_addr, '' AS state,"
                                 " COALESCE(ROUND(EXTRACT(epoch FROM now()-query_start)),0) "
                                 "AS seconds, procpid as pid, regexp_replace(current_query, "
                                 "E'[\\n\\r\\u2028]+', ' ', 'g' ) AS current_query "
                                 "FROM pg_stat_activity WHERE "
                                 "(query_start IS NOT NULL AND current_query NOT LIKE '<IDLE>%') "
                                 "ORDER BY query_start, procpid DESC;")

        return self.run_sql_as_db_user(querytime_sql_cmd,
                                       rows_only=False,
                                       extra_args="-P footer=off")

    def get_stat_database(self):
        """Gets the database stats"""
        # Previously part of simple_queries
        sql_cmd = ("SELECT datid, datname, numbackends, xact_commit, xact_rollback, blks_read, "
                   "blks_hit, tup_returned, tup_fetched, tup_inserted, tup_updated, tup_deleted, "
                   "pg_database_size(datname) AS datsize FROM pg_stat_database;")
        return self.run_sql_as_db_user(sql_cmd, rows_only=False, extra_args="-P footer=off")

    def get_locks(self):
        """Get the locks"""
        # Previously part of simple_queries
        sql_cmd = ("SELECT datname, granted, mode FROM pg_locks l RIGHT "
                   "JOIN pg_database d ON (d.oid=l.database) WHERE d.datallowconn;")
        return self.run_sql_as_db_user(sql_cmd, rows_only=False, extra_args="-P footer=off")

    def get_version(self):
        """Wrapper around get_version_conn_time"""
        version, self.conn_time = self.get_version_and_connection_time()
        return version

    def get_connection_time(self):
        """
        Wrapper around get_version_conn time.
        Execute query only if conn_time wasn't already set
        """
        if self.conn_time == "":
            _, self.conn_time = self.get_version_and_connection_time()
        return self.conn_time

    def is_pg_ready(self):
        """Executes pg_isready.
        pg_isready is a utility for checking the connection status of a PostgreSQL database server.
        """

        out = subprocess_check_output(
            ["%s%spg_isready" % (self.bin_path, self.sep), "-p", self.pg_port],)

        sys.stdout.write("%s\n" % ensure_str(out))

    def execute_all_queries(self):
        """Executes all queries and writes the output formatted to stdout"""
        instance = "\n[[[%s]]]" % self.name

        try:
            databases = self.get_databases()
            database_text = "\n[databases_start]\n%s\n[databases_end]" % "\n".join(databases)
            version = self.get_server_version()
            row, idle = self.get_condition_vars(version)
        except PostgresPsqlError:
            # if tcp connection to db instance failed variables are empty
            databases = ""
            database_text = ""
            version = None
            row, idle = "", ""

        out = "<<<postgres_instances>>>"
        out += instance
        out += "\n%s" % self.get_instances()
        sys.stdout.write("%s\n" % out)

        out = "<<<postgres_sessions>>>"
        if row and idle:
            out += instance
            out += "\n%s" % self.get_sessions(row, idle)
            sys.stdout.write("%s\n" % out)

        out = "<<<postgres_stat_database:sep(59)>>>"
        out += instance
        out += "\n%s" % self.get_stat_database()
        sys.stdout.write("%s\n" % out)

        out = "<<<postgres_locks:sep(59)>>>"
        if database_text:
            out += instance
            out += database_text
            out += "\n%s" % self.get_locks()
            sys.stdout.write("%s\n" % out)

        out = "<<<postgres_query_duration:sep(59)>>>"
        if version:
            out += instance
            out += database_text
            out += "\n%s" % self.get_query_duration(version)
            sys.stdout.write("%s\n" % out)

        out = "<<<postgres_connections:sep(59)>>>"
        if database_text:
            out += instance
            out += database_text
            out += "\n%s" % self.get_connections()
            sys.stdout.write("%s\n" % out)

        out = "<<<postgres_stats:sep(59)>>>"
        if databases:
            out += instance
            out += database_text
            out += "\n%s" % self.get_stats(databases)
            sys.stdout.write("%s\n" % out)

        out = "<<<postgres_version:sep(1)>>>"
        out += instance
        out += "\n%s" % self.get_version()
        sys.stdout.write("%s\n" % out)

        out = "<<<postgres_conn_time>>>"
        out += instance
        out += "\n%s" % self.get_connection_time()
        sys.stdout.write("%s\n" % out)

        out = "<<<postgres_bloat:sep(59)>>>"
        if databases and version:
            out += instance
            out += database_text
            out += "\n%s" % self.get_bloat(databases, version)
            sys.stdout.write("%s\n" % out)


class PostgresWin(PostgresBase):
    def run_sql_as_db_user(self,
                           sql_cmd,
                           extra_args="",
                           field_sep=";",
                           quiet=True,
                           rows_only=True,
                           mixed_cmd=False):
        # type: (str, str, str, Optional[bool], Optional[bool],Optional[bool]) -> str
        """This method implements the system specific way to call the psql interface"""
        extra_args += " -U %s" % self.pg_user
        extra_args += " -d %s" % self.pg_database
        extra_args += " -p %s" % self.pg_port

        if quiet:
            extra_args += " -q"
        if rows_only:
            extra_args += " -t"

        if mixed_cmd:
            cmd_str = "cmd /c echo %s | cmd /c \"\"%s\" -X %s -A -F\"%s\" -U %s\"" % (
                sql_cmd, self.psql, extra_args, field_sep, self.db_user)

        else:
            cmd_str = "cmd /c \"\"%s\" -X %s -A -F\"%s\" -U %s -c \"%s\"\" " % (
                self.psql, extra_args, field_sep, self.db_user, sql_cmd)

        proc = subprocess.Popen(
            cmd_str,
            env=self.my_env,
            stdout=subprocess.PIPE,
        )
        out = ensure_str(proc.communicate()[0])
        return out.rstrip()

    def get_psql_and_bin_path(self):
        # type: () -> Tuple[str, str]
        """This method returns the system specific psql interface binary as callable string"""

        # TODO: Make this more clever...
        for pg_ver in self._supported_pg_versions:
            bin_path = "C:\\Program Files\\PostgreSQL\\%s\\bin" % pg_ver
            psql_path = "%s\\psql.exe" % bin_path
            if os.path.isfile(psql_path):
                return psql_path, bin_path

        raise IOError("Could not determine psql bin and its path.")

    def get_instances(self):
        # type: () -> str
        """Gets all instances"""

        procs_to_match = [
            re.compile(pattern) for pattern in
            [r"(.*)bin\\postgres(.*)", r"(.*)bin\\postmaster(.*)", r"(.*)bin\\edb-postgres(.*)"]
        ]

        taskslist = ensure_str(
            subprocess_check_output(
                ["wmic", "process", "get", "processid,commandline",
                 "/format:list"])).split("\r\r\n\r\r\n\r\r\n")

        out = ""
        for task in taskslist:
            task = task.lstrip().rstrip()
            if len(task) == 0:
                continue
            cmd_line, PID = task.split("\r\r\n")
            cmd_line = cmd_line.split("CommandLine=")[1]
            PID = PID.split("ProcessId=")[1]
            if any(pat.search(cmd_line) for pat in procs_to_match):
                if task.find(self.name) != -1:
                    out += "%s %s\n" % (PID, cmd_line)
        return out.rstrip()

    def get_stats(self, databases):
        # type: (List[str]) -> str
        """Get the stats"""
        # The next query had to be slightly modified:
        # As cmd.exe interprets > as redirect and we need <> as "not equal", this was changed to
        # != as it has the same SQL implementation
        sql_cmd_lastvacuum = ("SELECT "
                              "current_database() AS datname, nspname AS sname, "
                              "relname AS tname, CASE WHEN v IS NULL THEN -1 "
                              "ELSE round(extract(epoch FROM v)) END AS vtime, "
                              "CASE WHEN g IS NULL THEN -1 ELSE round(extract(epoch FROM g)) "
                              "END AS atime FROM (SELECT nspname, relname, "
                              "GREATEST(pg_stat_get_last_vacuum_time(c.oid), "
                              "pg_stat_get_last_autovacuum_time(c.oid)) AS v, "
                              "GREATEST(pg_stat_get_last_analyze_time(c.oid), "
                              "pg_stat_get_last_autoanalyze_time(c.oid)) AS g "
                              "FROM pg_class c, pg_namespace n WHERE relkind = 'r' "
                              "AND n.oid = c.relnamespace AND n.nspname != 'information_schema' "
                              "ORDER BY 3) AS foo;")

        query = "\\pset footer off \\\\ BEGIN;SET statement_timeout=30000;COMMIT;"

        cur_rows_only = False
        for cnt, database in enumerate(databases):

            query = "%s \\c %s \\\\ %s" % (query, database, sql_cmd_lastvacuum)
            if cnt == 0:
                query = "%s \\pset tuples_only on" % query

        return self.run_sql_as_db_user(query, mixed_cmd=True, rows_only=cur_rows_only)

    def get_version_and_connection_time(self):
        # type: () -> Tuple[str, str]
        """Get the pg version and the time for the query connection"""
        cmd = "SELECT version() AS v"

        # TODO: Verify this time measurement
        start_time = time.time()
        out = self.run_sql_as_db_user(cmd)
        diff = time.time() - start_time
        return out, '%.3f' % diff

    def get_bloat(self, databases, numeric_version):
        # type: (List[Any], float) -> str
        """Get the db bloats"""
        # Bloat index and tables
        # Supports versions <9.0, >=9.0
        # This huge query has been gratefully taken from Greg Sabino Mullane's check_postgres.pl
        if numeric_version > 9.0:
            # TODO: Reformat query in a more readable way
            # Here as well: "<" and ">" must be escaped. As we're using meta-command + SQL in one
            # query, we need to use pipe. Due to Window's cmd behaviour, we need to escape those
            # symbols with 3 (!) carets. See https://ss64.com/nt/syntax-redirection.html
            bloat_query = (
                "SELECT current_database() AS db, "
                "schemaname, tablename, reltuples::bigint "
                "AS tups, relpages::bigint AS pages, otta, "
                "ROUND(CASE WHEN sml.relpages=0 "
                "OR sml.relpages=otta THEN 0.0 "
                "ELSE (sml.relpages-otta::numeric)/sml.relpages END,3) AS tbloat, "
                "CASE WHEN relpages ^^^< otta THEN 0 "
                "ELSE relpages::bigint - otta END AS wastedpages, "
                "CASE WHEN relpages ^^^< otta THEN 0 ELSE bs*(sml.relpages-otta)::bigint END "
                "AS wastedbytes, CASE WHEN relpages ^^^< otta THEN 0 "
                "ELSE (bs*(relpages-otta))::bigint END "
                "AS wastedsize, iname, ituples::bigint AS itups, ipages::bigint "
                "AS ipages, iotta, ROUND(CASE WHEN ipages=0 OR ipages^^^<=iotta THEN 0.0 "
                "ELSE (ipages-iotta::numeric)/ipages END,3) AS ibloat, "
                "CASE WHEN ipages ^^^< iotta THEN 0 ELSE ipages::bigint - iotta END "
                "AS wastedipages, CASE WHEN ipages ^^^< iotta THEN 0 ELSE bs*(ipages-iotta) "
                "END AS wastedibytes, CASE WHEN ipages ^^^< iotta THEN 0 "
                "ELSE (bs*(ipages-iotta))::bigint END AS wastedisize, "
                "CASE WHEN relpages ^^^< otta THEN CASE WHEN ipages ^^^< iotta THEN 0 "
                "ELSE bs*(ipages-iotta::bigint) END ELSE CASE WHEN ipages ^^^< iotta "
                "THEN bs*(relpages-otta::bigint) "
                "ELSE bs*(relpages-otta::bigint + ipages-iotta::bigint) "
                "END END AS totalwastedbytes "
                "FROM ( SELECT nn.nspname AS schemaname, cc.relname AS tablename, "
                "COALESCE(cc.reltuples,0) AS reltuples, COALESCE(cc.relpages,0) "
                "AS relpages, COALESCE(bs,0) AS bs, "
                "COALESCE(CEIL((cc.reltuples*((datahdr+ma- (CASE WHEN datahdr%ma=0 "
                "THEN ma ELSE datahdr%ma END))+nullhdr2+4))/(bs-20::float)),0) "
                "AS otta, COALESCE(c2.relname,'?') AS iname, COALESCE(c2.reltuples,0) "
                "AS ituples, COALESCE(c2.relpages,0) "
                "AS ipages, COALESCE(CEIL((c2.reltuples*(datahdr-12))/(bs-20::float)),0) "
                "AS iotta FROM pg_class cc "
                "JOIN pg_namespace nn ON cc.relnamespace = nn.oid "
                "AND nn.nspname != 'information_schema' LEFT JOIN "
                "( SELECT ma,bs,foo.nspname,foo.relname, "
                "(datawidth+(hdr+ma-(case when hdr%ma=0 "
                "THEN ma ELSE hdr%ma END)))::numeric AS datahdr, "
                "(maxfracsum*(nullhdr+ma-(case when nullhdr%ma=0 THEN ma "
                "ELSE nullhdr%ma END))) AS nullhdr2 "
                "FROM ( SELECT ns.nspname, tbl.relname, hdr, ma, bs, "
                "SUM((1-coalesce(null_frac,0))*coalesce(avg_width, 2048)) AS datawidth, "
                "MAX(coalesce(null_frac,0)) AS maxfracsum, hdr+( SELECT 1+count(*)/8 "
                "FROM pg_stats s2 WHERE null_frac != 0 AND s2.schemaname = ns.nspname "
                "AND s2.tablename = tbl.relname ) AS nullhdr FROM pg_attribute att "
                "JOIN pg_class tbl ON att.attrelid = tbl.oid JOIN pg_namespace ns "
                "ON ns.oid = tbl.relnamespace LEFT JOIN pg_stats s "
                "ON s.schemaname=ns.nspname AND s.tablename = tbl.relname AND "
                "s.inherited=false AND s.attname=att.attname, "
                "( SELECT (SELECT current_setting('block_size')::numeric) AS bs, CASE WHEN "
                "SUBSTRING(SPLIT_PART(v, ' ', 2) FROM '#\\[0-9]+.[0-9]+#\\%' for '#') "
                "IN ('8.0','8.1','8.2') THEN 27 ELSE 23 END AS hdr, CASE "
                "WHEN v ~ 'mingw32' OR v ~ '64-bit' THEN 8 ELSE 4 END AS ma "
                "FROM (SELECT version() AS v) AS foo ) AS constants WHERE att.attnum ^^^> 0 "
                "AND tbl.relkind='r' GROUP BY 1,2,3,4,5 ) AS foo ) AS rs "
                "ON cc.relname = rs.relname AND nn.nspname = rs.nspname LEFT "
                "JOIN pg_index i ON indrelid = cc.oid LEFT JOIN pg_class c2 "
                "ON c2.oid = i.indexrelid ) AS sml WHERE sml.relpages - otta ^^^> 0 "
                "OR ipages - iotta ^^^> 10 ORDER BY totalwastedbytes DESC LIMIT 10;")

        else:
            bloat_query = (
                "SELECT "
                "current_database() AS db, schemaname, tablename, "
                "reltuples::bigint AS tups, relpages::bigint AS pages, otta, "
                "ROUND(CASE WHEN sml.relpages=0 OR sml.relpages=otta THEN 0.0 "
                "ELSE (sml.relpages-otta::numeric)/sml.relpages END,3) AS tbloat, "
                "CASE WHEN relpages ^^^< otta THEN 0 ELSE relpages::bigint - otta END "
                "AS wastedpages, CASE WHEN relpages ^^^< otta THEN 0 "
                "ELSE bs*(sml.relpages-otta)::bigint END AS wastedbytes, "
                "CASE WHEN relpages ^^^< otta THEN '0 bytes'::text "
                "ELSE (bs*(relpages-otta))::bigint || ' bytes' END AS wastedsize, "
                "iname, ituples::bigint AS itups, ipages::bigint AS ipages, iotta, "
                "ROUND(CASE WHEN ipages=0 OR ipages^^^<=iotta THEN 0.0 ELSE "
                "(ipages-iotta::numeric)/ipages END,3) AS ibloat, "
                "CASE WHEN ipages ^^^< iotta THEN 0 ELSE ipages::bigint - iotta END "
                "AS wastedipages, CASE WHEN ipages ^^^< iotta THEN 0 "
                "ELSE bs*(ipages-iotta) END AS wastedibytes, "
                "CASE WHEN ipages ^^^< iotta THEN '0 bytes' ELSE "
                "(bs*(ipages-iotta))::bigint || ' bytes' END AS wastedisize, CASE "
                "WHEN relpages ^^^< otta THEN CASE WHEN ipages ^^^< iotta THEN 0 "
                "ELSE bs*(ipages-iotta::bigint) END ELSE CASE WHEN ipages ^^^< iotta "
                "THEN bs*(relpages-otta::bigint) "
                "ELSE bs*(relpages-otta::bigint + ipages-iotta::bigint) END "
                "END AS totalwastedbytes FROM (SELECT nn.nspname AS schemaname, "
                "cc.relname AS tablename, COALESCE(cc.reltuples,0) AS reltuples, "
                "COALESCE(cc.relpages,0) AS relpages, COALESCE(bs,0) AS bs, "
                "COALESCE(CEIL((cc.reltuples*((datahdr+ma-(CASE WHEN datahdr%ma=0 "
                "THEN ma ELSE datahdr%ma END))+nullhdr2+4))/(bs-20::float)),0) AS otta, "
                "COALESCE(c2.relname,'?') AS iname, COALESCE(c2.reltuples,0) AS ituples, "
                "COALESCE(c2.relpages,0) AS ipages, "
                "COALESCE(CEIL((c2.reltuples*(datahdr-12))/(bs-20::float)),0) AS iotta "
                "FROM pg_class cc JOIN pg_namespace nn ON cc.relnamespace = nn.oid "
                "AND nn.nspname ^^^<^^^> 'information_schema' LEFT "
                "JOIN(SELECT ma,bs,foo.nspname,foo.relname, "
                "(datawidth+(hdr+ma-(case when hdr%ma=0 THEN ma "
                "ELSE hdr%ma END)))::numeric AS datahdr, "
                "(maxfracsum*(nullhdr+ma-(case when nullhdr%ma=0 THEN ma "
                "ELSE nullhdr%ma END))) AS nullhdr2 "
                "FROM (SELECT ns.nspname, tbl.relname, hdr, ma, bs, "
                "SUM((1-coalesce(null_frac,0))*coalesce(avg_width, 2048)) "
                "AS datawidth, MAX(coalesce(null_frac,0)) AS maxfracsum, hdr+("
                "SELECT 1+count(*)/8 FROM pg_stats s2 WHERE null_frac^^^<^^^>0 "
                "AND s2.schemaname = ns.nspname AND s2.tablename = tbl.relname) "
                "AS nullhdr FROM pg_attribute att JOIN pg_class tbl "
                "ON att.attrelid = tbl.oid JOIN pg_namespace ns ON "
                "ns.oid = tbl.relnamespace LEFT JOIN pg_stats s "
                "ON s.schemaname=ns.nspname AND s.tablename = tbl.relname "
                "AND s.attname=att.attname, (SELECT ("
                "SELECT current_setting('block_size')::numeric) AS bs, CASE WHEN "
                "SUBSTRING(SPLIT_PART(v, ' ', 2) FROM '#\"[0-9]+.[0-9]+#\"%' for '#') "
                "IN ('8.0','8.1','8.2') THEN 27 ELSE 23 END AS hdr, CASE "
                "WHEN v ~ 'mingw32' OR v ~ '64-bit' THEN 8 ELSE 4 END AS ma "
                "FROM (SELECT version() AS v) AS foo) AS constants WHERE att.attnum ^^^> 0 "
                "AND tbl.relkind='r' GROUP BY 1,2,3,4,5) AS foo) AS rs ON "
                "cc.relname = rs.relname AND nn.nspname = rs.nspname LEFT JOIN pg_index i "
                "ON indrelid = cc.oid LEFT JOIN pg_class c2 ON c2.oid = i.indexrelid) "
                "AS sml WHERE sml.relpages - otta ^^^> 0 OR ipages - iotta ^^^> 10 ORDER "
                "BY totalwastedbytes DESC LIMIT 10;")

        query = "\\pset footer off \\\\"

        cur_rows_only = False
        for idx, database in enumerate(databases):

            query = "%s \\c %s \\\\ %s" % (query, database, bloat_query)
            if idx == 0:
                query = "%s \\pset tuples_only on" % query

        return self.run_sql_as_db_user(query, mixed_cmd=True, rows_only=cur_rows_only)


class PostgresLinux(PostgresBase):
    def run_sql_as_db_user(self,
                           sql_cmd,
                           extra_args="",
                           field_sep=";",
                           quiet=True,
                           rows_only=True,
                           mixed_cmd=False):
        # type: (str, str, str, bool, bool, bool) -> str
        base_cmd_list = ["su", "-", self.db_user, "-c", r"""PGPASSFILE=%s %s -X %s -A -F'%s'%s"""]
        extra_args += " -U %s" % self.pg_user
        extra_args += " -d %s" % self.pg_database
        extra_args += " -p %s" % self.pg_port

        if quiet:
            extra_args += " -q"
        if rows_only:
            extra_args += " -t"

        # In case we want to use postgres meta commands AND SQL queries in one call, we need to pipe
        # the full cmd string into psql executable
        # see https://www.postgresql.org/docs/9.2/app-psql.html
        if mixed_cmd:
            cmd_to_pipe = subprocess.Popen(["echo", sql_cmd], stdout=subprocess.PIPE)
            base_cmd_list[-1] = base_cmd_list[-1] % (self.pg_passfile, self.psql, extra_args,
                                                     field_sep, "")

            receiving_pipe = subprocess.Popen(base_cmd_list,
                                              stdin=cmd_to_pipe.stdout,
                                              stdout=subprocess.PIPE,
                                              env=self.my_env)
            out = ensure_str(receiving_pipe.communicate()[0])

        else:
            base_cmd_list[-1] = base_cmd_list[-1] % (self.pg_passfile, self.psql, extra_args,
                                                     field_sep, " -c \"%s\" " % sql_cmd)
            proc = subprocess.Popen(base_cmd_list, env=self.my_env, stdout=subprocess.PIPE)
            out = ensure_str(proc.communicate()[0])

        return out.rstrip()

    def get_psql_and_bin_path(self):
        # type: () -> Tuple[str, str]
        try:
            proc = subprocess.Popen(["which", "psql"], stdout=subprocess.PIPE)
            out = ensure_str(proc.communicate()[0])
        except subprocess.CalledProcessError:
            raise RuntimeError("Could not determine psql executable.")

        return out.split("/")[-1].rstrip(), out.replace("psql", "").rstrip()

    def get_instances(self):
        # type: () -> str

        procs_to_match = [
            re.compile(pattern) for pattern in
            ["(.*)bin/postgres(.*)", "(.*)bin/postmaster(.*)", "(.*)bin/edb-postgres(.*)"]
        ]

        procs_list = ensure_str(subprocess_check_output(["ps", "h", "-eo",
                                                         "pid:1,command:1"])).split("\n")
        out = ""
        for proc in procs_list:
            if any(pat.search(proc) for pat in procs_to_match):
                # the data directory for the instance "main" is not called "main" but "data" on some platforms
                if self.name in proc or (self.name == 'main' and 'data' in proc):
                    out += proc + "\n"
        return out.rstrip()

    def get_query_duration(self, numeric_version):
        # type: (float) -> str
        # Previously part of simple_queries

        if numeric_version > 9.2:
            querytime_sql_cmd = ("SELECT datname, datid, usename, client_addr, state AS state, "
                                 "COALESCE(ROUND(EXTRACT(epoch FROM now()-query_start)),0) "
                                 "AS seconds, pid, "
                                 "regexp_replace(query, E'[\\n\\r\\u2028]+', ' ', 'g' ) AS "
                                 "current_query FROM pg_stat_activity "
                                 "WHERE (query_start IS NOT NULL AND "
                                 "(state NOT LIKE 'idle%' OR state IS NULL)) "
                                 "ORDER BY query_start, pid DESC;")

        else:
            querytime_sql_cmd = ("SELECT datname, datid, usename, client_addr, '' AS state, "
                                 "COALESCE(ROUND(EXTRACT(epoch FROM now()-query_start)),0) "
                                 "AS seconds, procpid as pid, "
                                 "regexp_replace(current_query, E'[\\n\\r\\u2028]+', ' ', 'g' ) "
                                 "AS current_query FROM pg_stat_activity WHERE "
                                 "(query_start IS NOT NULL AND current_query NOT LIKE '<IDLE>%') "
                                 "ORDER BY query_start, procpid DESC;")

        return self.run_sql_as_db_user(querytime_sql_cmd,
                                       rows_only=False,
                                       extra_args="-P footer=off")

    def get_stats(self, databases):
        # type: (List[str]) -> str
        sql_cmd_lastvacuum = ("SELECT "
                              "current_database() AS datname, nspname AS sname, "
                              "relname AS tname, CASE WHEN v IS NULL THEN -1 "
                              "ELSE round(extract(epoch FROM v)) END AS vtime, "
                              "CASE WHEN g IS NULL THEN -1 ELSE round(extract(epoch FROM v)) "
                              "END AS atime FROM (SELECT nspname, relname, "
                              "GREATEST(pg_stat_get_last_vacuum_time(c.oid), "
                              "pg_stat_get_last_autovacuum_time(c.oid)) AS v, "
                              "GREATEST(pg_stat_get_last_analyze_time(c.oid), "
                              "pg_stat_get_last_autoanalyze_time(c.oid)) AS g "
                              "FROM pg_class c, pg_namespace n WHERE relkind = 'r' "
                              "AND n.oid = c.relnamespace AND n.nspname <> 'information_schema' "
                              "ORDER BY 3) AS foo;")

        query = "\\pset footer off\nBEGIN;\nSET statement_timeout=30000;\nCOMMIT;"

        cur_rows_only = False
        for cnt, database in enumerate(databases):

            query = "%s\n\\c %s\n%s" % (query, database, sql_cmd_lastvacuum)
            if cnt == 0:
                query = "%s\n\\pset tuples_only on" % query

        return self.run_sql_as_db_user(query, mixed_cmd=True, rows_only=cur_rows_only)

    def get_version_and_connection_time(self):
        # type: () -> Tuple[str, str]
        cmd = "SELECT version() AS v"
        usage_start = resource.getrusage(resource.RUSAGE_CHILDREN)
        out = self.run_sql_as_db_user(cmd)
        usage_end = resource.getrusage(resource.RUSAGE_CHILDREN)

        sys_time = usage_end.ru_stime - usage_start.ru_stime
        usr_time = usage_end.ru_utime - usage_start.ru_utime
        real = sys_time + usr_time

        return out, '%.3f' % real

    def get_bloat(self, databases, numeric_version):
        # type: (List[Any], float) -> str
        # Bloat index and tables
        # Supports versions <9.0, >=9.0
        # This huge query has been gratefully taken from Greg Sabino Mullane's check_postgres.pl
        if numeric_version > 9.0:
            # TODO: Reformat query in a more readable way
            bloat_query = (
                "SELECT current_database() AS db, schemaname, tablename, reltuples::bigint "
                "AS tups, relpages::bigint AS pages, otta, ROUND(CASE WHEN sml.relpages=0 "
                "OR sml.relpages=otta THEN 0.0 "
                "ELSE (sml.relpages-otta::numeric)/sml.relpages END,3) AS tbloat, "
                "CASE WHEN relpages < otta THEN 0 "
                "ELSE relpages::bigint - otta END AS wastedpages, "
                "CASE WHEN relpages < otta THEN 0 ELSE bs*(sml.relpages-otta)::bigint END "
                "AS wastedbytes, CASE WHEN relpages < otta THEN 0 "
                "ELSE (bs*(relpages-otta))::bigint END "
                "AS wastedsize, iname, ituples::bigint AS itups, ipages::bigint "
                "AS ipages, iotta, ROUND(CASE WHEN ipages=0 OR ipages<=iotta THEN 0.0 "
                "ELSE (ipages-iotta::numeric)/ipages END,3) AS ibloat, "
                "CASE WHEN ipages < iotta THEN 0 ELSE ipages::bigint - iotta END "
                "AS wastedipages, CASE WHEN ipages < iotta THEN 0 ELSE bs*(ipages-iotta) "
                "END AS wastedibytes, CASE WHEN ipages < iotta THEN 0 "
                "ELSE (bs*(ipages-iotta))::bigint END AS wastedisize, "
                "CASE WHEN relpages < otta THEN CASE WHEN ipages < iotta THEN 0 "
                "ELSE bs*(ipages-iotta::bigint) END ELSE CASE WHEN ipages < iotta "
                "THEN bs*(relpages-otta::bigint) "
                "ELSE bs*(relpages-otta::bigint + ipages-iotta::bigint) "
                "END END AS totalwastedbytes "
                "FROM ( SELECT nn.nspname AS schemaname, cc.relname AS tablename, "
                "COALESCE(cc.reltuples,0) AS reltuples, COALESCE(cc.relpages,0) "
                "AS relpages, COALESCE(bs,0) AS bs, "
                "COALESCE(CEIL((cc.reltuples*((datahdr+ma- (CASE WHEN datahdr%ma=0 "
                "THEN ma ELSE datahdr%ma END))+nullhdr2+4))/(bs-20::float)),0) "
                "AS otta, COALESCE(c2.relname,'?') AS iname, COALESCE(c2.reltuples,0) "
                "AS ituples, COALESCE(c2.relpages,0) "
                "AS ipages, COALESCE(CEIL((c2.reltuples*(datahdr-12))/(bs-20::float)),0) "
                "AS iotta FROM pg_class cc "
                "JOIN pg_namespace nn ON cc.relnamespace = nn.oid "
                "AND nn.nspname <> 'information_schema' LEFT JOIN "
                "( SELECT ma,bs,foo.nspname,foo.relname, "
                "(datawidth+(hdr+ma-(case when hdr%ma=0 "
                "THEN ma ELSE hdr%ma END)))::numeric AS datahdr, "
                "(maxfracsum*(nullhdr+ma-(case when nullhdr%ma=0 THEN ma "
                "ELSE nullhdr%ma END))) AS nullhdr2 "
                "FROM ( SELECT ns.nspname, tbl.relname, hdr, ma, bs, "
                "SUM((1-coalesce(null_frac,0))*coalesce(avg_width, 2048)) AS datawidth, "
                "MAX(coalesce(null_frac,0)) AS maxfracsum, hdr+( SELECT 1+count(*)/8 "
                "FROM pg_stats s2 WHERE null_frac<>0 AND s2.schemaname = ns.nspname "
                "AND s2.tablename = tbl.relname ) AS nullhdr FROM pg_attribute att "
                "JOIN pg_class tbl ON att.attrelid = tbl.oid JOIN pg_namespace ns "
                "ON ns.oid = tbl.relnamespace LEFT JOIN pg_stats s "
                "ON s.schemaname=ns.nspname AND s.tablename = tbl.relname AND "
                "s.inherited=false AND s.attname=att.attname, "
                "( SELECT (SELECT current_setting('block_size')::numeric) AS bs, CASE WHEN "
                "SUBSTRING(SPLIT_PART(v, ' ', 2) FROM '#\\[0-9]+.[0-9]+#\\%' for '#') "
                "IN ('8.0','8.1','8.2') THEN 27 ELSE 23 END AS hdr, CASE "
                "WHEN v ~ 'mingw32' OR v ~ '64-bit' THEN 8 ELSE 4 END AS ma "
                "FROM (SELECT version() AS v) AS foo ) AS constants WHERE att.attnum > 0 "
                "AND tbl.relkind='r' GROUP BY 1,2,3,4,5 ) AS foo ) AS rs "
                "ON cc.relname = rs.relname AND nn.nspname = rs.nspname LEFT JOIN pg_index i "
                "ON indrelid = cc.oid LEFT JOIN pg_class c2 ON c2.oid = i.indexrelid ) "
                "AS sml WHERE sml.relpages - otta > 0 OR ipages - iotta > 10 ORDER "
                "BY totalwastedbytes DESC LIMIT 10;")
        else:
            bloat_query = (
                "SELECT "
                "current_database() AS db, schemaname, tablename, "
                "reltuples::bigint AS tups, relpages::bigint AS pages, otta, "
                "ROUND(CASE WHEN sml.relpages=0 OR sml.relpages=otta THEN 0.0 "
                "ELSE (sml.relpages-otta::numeric)/sml.relpages END,3) AS tbloat, "
                "CASE WHEN relpages < otta THEN 0 ELSE relpages::bigint - otta END "
                "AS wastedpages, CASE WHEN relpages < otta THEN 0 "
                "ELSE bs*(sml.relpages-otta)::bigint END AS wastedbytes, "
                "CASE WHEN relpages < otta THEN '0 bytes'::text "
                "ELSE (bs*(relpages-otta))::bigint || ' bytes' END AS wastedsize, "
                "iname, ituples::bigint AS itups, ipages::bigint AS ipages, iotta, "
                "ROUND(CASE WHEN ipages=0 OR ipages<=iotta THEN 0.0 ELSE "
                "(ipages-iotta::numeric)/ipages END,3) AS ibloat, "
                "CASE WHEN ipages < iotta THEN 0 ELSE ipages::bigint - iotta END "
                "AS wastedipages, CASE WHEN ipages < iotta THEN 0 "
                "ELSE bs*(ipages-iotta) END AS wastedibytes, "
                "CASE WHEN ipages < iotta THEN '0 bytes' ELSE "
                "(bs*(ipages-iotta))::bigint || ' bytes' END AS wastedisize, CASE "
                "WHEN relpages < otta THEN CASE WHEN ipages < iotta THEN 0 "
                "ELSE bs*(ipages-iotta::bigint) END ELSE CASE WHEN ipages < iotta "
                "THEN bs*(relpages-otta::bigint) "
                "ELSE bs*(relpages-otta::bigint + ipages-iotta::bigint) END "
                "END AS totalwastedbytes FROM (SELECT nn.nspname AS schemaname, "
                "cc.relname AS tablename, COALESCE(cc.reltuples,0) AS reltuples, "
                "COALESCE(cc.relpages,0) AS relpages, COALESCE(bs,0) AS bs, "
                "COALESCE(CEIL((cc.reltuples*((datahdr+ma-(CASE WHEN datahdr%ma=0 "
                "THEN ma ELSE datahdr%ma END))+nullhdr2+4))/(bs-20::float)),0) AS otta, "
                "COALESCE(c2.relname,'?') AS iname, COALESCE(c2.reltuples,0) AS ituples, "
                "COALESCE(c2.relpages,0) AS ipages, "
                "COALESCE(CEIL((c2.reltuples*(datahdr-12))/(bs-20::float)),0) AS iotta "
                "FROM pg_class cc JOIN pg_namespace nn ON cc.relnamespace = nn.oid "
                "AND nn.nspname <> 'information_schema' LEFT "
                "JOIN(SELECT ma,bs,foo.nspname,foo.relname, "
                "(datawidth+(hdr+ma-(case when hdr%ma=0 THEN ma "
                "ELSE hdr%ma END)))::numeric AS datahdr, "
                "(maxfracsum*(nullhdr+ma-(case when nullhdr%ma=0 THEN ma "
                "ELSE nullhdr%ma END))) AS nullhdr2 "
                "FROM (SELECT ns.nspname, tbl.relname, hdr, ma, bs, "
                "SUM((1-coalesce(null_frac,0))*coalesce(avg_width, 2048)) "
                "AS datawidth, MAX(coalesce(null_frac,0)) AS maxfracsum, hdr+("
                "SELECT 1+count(*)/8 FROM pg_stats s2 WHERE null_frac<>0 "
                "AND s2.schemaname = ns.nspname AND s2.tablename = tbl.relname) "
                "AS nullhdr FROM pg_attribute att JOIN pg_class tbl "
                "ON att.attrelid = tbl.oid JOIN pg_namespace ns ON "
                "ns.oid = tbl.relnamespace LEFT JOIN pg_stats s "
                "ON s.schemaname=ns.nspname AND s.tablename = tbl.relname "
                "AND s.attname=att.attname, (SELECT ("
                "SELECT current_setting('block_size')::numeric) AS bs, CASE WHEN "
                "SUBSTRING(SPLIT_PART(v, ' ', 2) FROM '#\"[0-9]+.[0-9]+#\"%' for '#') "
                "IN ('8.0','8.1','8.2') THEN 27 ELSE 23 END AS hdr, CASE "
                "WHEN v ~ 'mingw32' OR v ~ '64-bit' THEN 8 ELSE 4 END AS ma "
                "FROM (SELECT version() AS v) AS foo) AS constants WHERE att.attnum > 0 "
                "AND tbl.relkind='r' GROUP BY 1,2,3,4,5) AS foo) AS rs ON "
                "cc.relname = rs.relname AND nn.nspname = rs.nspname LEFT JOIN pg_index i "
                "ON indrelid = cc.oid LEFT JOIN pg_class c2 ON c2.oid = i.indexrelid) "
                "AS sml WHERE sml.relpages - otta > 0 OR ipages - iotta > 10 ORDER "
                "BY totalwastedbytes DESC LIMIT 10;")

        query = "\\pset footer off"

        cur_rows_only = False
        for idx, database in enumerate(databases):

            query = "%s\n\\c %s\n%s" % (query, database, bloat_query)
            if idx == 0:
                query = "%s\n\\pset tuples_only on" % query

        return self.run_sql_as_db_user(query, mixed_cmd=True, rows_only=cur_rows_only)


def postgres_factory(db_user, pg_instance):
    # type: (str, Dict[str, str]) -> PostgresBase
    if IS_LINUX:
        return PostgresLinux(db_user, pg_instance)
    if IS_WINDOWS:
        return PostgresWin(db_user, pg_instance)
    raise NotImplementedError("The OS type(%s) is not yet implemented." % platform.system())


def open_env_file(file_to_open):
    """Wrapper around built-in open to be able to monkeypatch through all python versions"""
    return open(file_to_open).readlines()


def parse_env_file(env_file):
    pg_port = None  # mandatory in env_file
    pg_database = "postgres"  # default value
    for line in open_env_file(env_file):
        line = line.strip()
        if 'PGDATABASE=' in line:
            pg_database = re.sub(re.compile("#.*"), "", line.split("=")[-1]).strip()
        if 'PGPORT=' in line:
            pg_port = re.sub(re.compile("#.*"), "", line.split("=")[-1]).strip()
    if pg_port is None:
        raise ValueError("PGPORT is not specified in %s" % env_file)
    return pg_database, pg_port


def parse_postgres_cfg(postgres_cfg):
    """
    Parser for Postgres config. x-Plattform compatible.

    Example for .cfg file:
    DBUSER=postgres
    INSTANCE=/home/postgres/db1.env:USER_NAME:/PATH/TO/.pgpass
    INSTANCE=/home/postgres/db2.env:USER_NAME:/PATH/TO/.pgpass
    """
    if IS_LINUX:
        conf_sep = ":"
    elif IS_WINDOWS:
        conf_sep = "|"
    else:
        raise NotImplementedError("The OS type(%s) is not yet implemented." % platform.system())
    dbuser = None
    instances = []
    for line in postgres_cfg:
        if line.startswith("#") or "=" not in line:
            continue
        line = line.strip()
        key, value = line.split("=")
        if key == "DBUSER":
            dbuser = value.rstrip()
        if key == "INSTANCE":
            env_file, pg_user, pg_passfile = value.split(conf_sep)
            env_file = env_file.strip()
            pg_database, pg_port = parse_env_file(env_file)
            instances.append({
                "name": env_file.split(os.sep)[-1].split(".")[0],
                "pg_user": pg_user.strip(),
                "pg_passfile": pg_passfile.strip(),
                "pg_database": pg_database,
                "pg_port": pg_port,
            })
    if dbuser is None:
        raise ValueError("DBUSER must be specified in postgres.cfg")
    return dbuser, instances


def parse_arguments(argv):
    parser = optparse.OptionParser()
    parser.add_option('-v', '--verbose', action="count", default=0)
    parser.add_option("-t",
                      "--test-connection",
                      default=False,
                      action="store_true",
                      help="Test if postgres is ready")
    options, _ = parser.parse_args(argv)
    return options


def get_postgres_user_linux():
    for user_id in ("pgsql", "postgres"):
        try:
            proc = subprocess.Popen(["id", user_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            proc.communicate()
            if proc.returncode == 0:
                return user_id.rstrip()
        except subprocess.CalledProcessError:
            pass
    raise ValueError("Could not determine postgres user!")


def main(argv=None):
    # type: (Optional[List]) -> int

    if argv is None:
        argv = sys.argv[1:]

    opt = parse_arguments(argv)

    logging.basicConfig(
        format="%(levelname)s %(asctime)s %(name)s: %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        level={
            0: logging.WARN,
            1: logging.INFO,
            2: logging.DEBUG
        }.get(opt.verbose, logging.DEBUG),
    )

    if IS_LINUX:
        default_path = "/etc/check_mk"
        fallback_dbuser = get_postgres_user_linux()
    elif IS_WINDOWS:
        default_path = "c:\\ProgramData\\checkmk\\agent\\config"
        fallback_dbuser = "postgres"
    else:
        raise NotImplementedError("The OS type(%s) is not yet implemented." % platform.system())

    dbuser = fallback_dbuser
    instances = []
    try:
        postgres_cfg_path = os.path.join(os.getenv("MK_CONFDIR", default_path), "postgres.cfg")
        postgres_cfg = open(postgres_cfg_path).readlines()
        dbuser, instances = parse_postgres_cfg(postgres_cfg)
    except Exception:
        _, e = sys.exc_info()[:2]  # python2 and python3 compatible exception logging
        LOGGER.debug("try_parse_config: exception: %s", str(e))
        LOGGER.debug("Using \"%s\" as default postgres user.", dbuser)

    if not instances:
        default_postgres_installation_parameters = {
            # default database name of postgres installation
            "name": "main" if IS_LINUX else "data",
            "pg_user": "postgres",
            "pg_database": "postgres",
            "pg_port": "5432",
            # Assumption: if no pg_passfile is specified no password will be required.
            # If a password is required but no pg_passfile is specified the process will
            # interactivly prompt for a password.
            "pg_passfile": "",
        }
        instances.append(default_postgres_installation_parameters)

    for instance in instances:
        postgres = postgres_factory(dbuser, instance)
        if opt.test_connection:
            postgres.is_pg_ready()
            sys.exit(0)
        postgres.execute_all_queries()
    return 0


if __name__ == "__main__":
    main()
