#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
r"""Check_MK Agent Plugin: mk_postgres

This is a Check_MK Agent plugin. If configured, it will be called by the
agent without any arguments.
"""

__version__ = "2.0.0b6"

import subprocess
import re
import os
import abc
import platform
import sys
import logging
import argparse
from collections import namedtuple
try:
    from typing import Dict, List, Optional, Tuple
except ImportError:
    # We need typing only for testing
    pass

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


# Borrowed from six
def ensure_str(s):
    if sys.version_info[0] >= 3:
        if isinstance(s, bytes):
            return s.decode("utf-8")
    else:
        if isinstance(s, unicode):  # pylint: disable=undefined-variable
            return s.encode("utf-8")
    return s


#   .--Postgres Base-------------------------------------------------------.
#   |    ____           _                        ____                      |
#   |   |  _ \ ___  ___| |_ __ _ _ __ ___  ___  | __ )  __ _ ___  ___      |
#   |   | |_) / _ \/ __| __/ _` | '__/ _ \/ __| |  _ \ / _` / __|/ _ \     |
#   |   |  __/ (_) \__ \ || (_| | | |  __/\__ \ | |_) | (_| \__ \  __/     |
#   |   |_|   \___/|___/\__\__, |_|  \___||___/ |____/ \__,_|___/\___|     |
#   |                      |___/                                           |
#   +----------------------------------------------------------------------+


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
    _agent_prefix = "postgres"

    def __init__(self, db_user, instance=None):
        # type: (str, Optional[Dict]) -> None
        self.db_user = db_user

        if instance:
            self.instance = instance
        else:
            self.instance = {}
        self.my_env = os.environ.copy()
        self.my_env["PGPASSFILE"] = self.instance.get("pg_passfile", "")
        self.get_pg_env()
        self.sep = os.sep
        self.psql, self.bin_path = self.get_psql_and_bin_path()
        self.databases = self.get_databases()
        self.numeric_version = self.get_server_version()
        self.row, self.idle = self.get_condition_vars()
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
    def get_pg_env(self):
        """This method tries to get env variables from a .env file"""

    @abc.abstractmethod
    def get_instances(self):
        """Gets all instances"""

    @abc.abstractmethod
    def get_stats(self):
        """Get the stats"""

    @abc.abstractmethod
    def get_version_and_connection_time(self):
        """Get the pg version and the time for the query connection"""

    @abc.abstractmethod
    def get_bloat(self):
        """Get the db bloats"""

    def get_databases(self):
        """Gets all non template databases"""
        sql_cmd = "SELECT datname FROM pg_database WHERE datistemplate = false;"
        out = self.run_sql_as_db_user(sql_cmd)
        return out.replace("\r", "").split("\n")

    def get_server_version(self):
        """Gets the server version"""
        out = self.run_sql_as_db_user('SHOW server_version;')
        version_as_string = out.split()[0]
        # Use Major and Minor version for float casting: "12.6.4" -> 12.6
        return float(".".join(version_as_string.split(".")[0:2]))

    def get_condition_vars(self):
        """Gets condition variables for other queries"""
        if self.numeric_version > 9.2:
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

    def get_sessions(self):
        """Gets idle and open sessions"""
        condition = "%s = %s" % (self.row, self.idle)

        sql_cmd = ("SELECT %s, count(*) FROM pg_stat_activity "
                   "WHERE %s IS NOT NULL GROUP BY (%s);") % (condition, self.row, condition)

        out = self.run_sql_as_db_user(sql_cmd,
                                      quiet=False,
                                      extra_args="--variable ON_ERROR_STOP=1",
                                      field_sep=" ")

        # line with number of idle sessions is sometimes missing on Postgres 8.x. This can lead
        # to an altogether empty section and thus the check disappearing.
        if not out.startswith("t"):
            out += "\nt 0"
        return out

    def get_query_duration(self):
        """Gets the query duration"""
        # Previously part of simple_queries

        if self.numeric_version > 9.2:
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

        out = subprocess.check_output([
            "%s%spg_isready" % (self.bin_path, self.sep), "-p",
            self.instance.get("pg_port", "5432")
        ],)

        sys.stdout.write("%s\n" % ensure_str(out))

    def execute_all_queries(self):
        """Executes all queries and writes the output formatted to stdout"""

        query_template = namedtuple("query", ["method", "section", "has_db_text"])
        queries = [
            query_template(self.get_instances, "instances", False),
            query_template(self.get_sessions, "sessions", False),
            query_template(self.get_stat_database, "stat_database:sep(59)", False),
            query_template(self.get_locks, "locks:sep(59)", True),
            query_template(self.get_query_duration, "query_duration:sep(59)", True),
            query_template(self.get_connections, "connections:sep(59)", True),
            query_template(self.get_stats, "stats:sep(59)", True),
            query_template(self.get_version, "version:sep(1)", False),
            query_template(self.get_connection_time, "conn_time", False),
            query_template(self.get_bloat, "bloat:sep(59)", True)
        ]

        database_text = "\n[databases_start]\n%s\n[databases_end]" % "\n".join(self.databases)

        if self.instance.get("name"):
            instance = "\n[[[%s]]]" % self.instance["name"]
        else:
            instance = ""

        for query in queries:
            out = "<<<%s_%s>>>" % (self._agent_prefix, query.section)
            out += instance
            if query.has_db_text:
                out += database_text
            out += "\n%s" % query.method()
            sys.stdout.write("%s\n" % out)


#   .--Postgres Win--------------------------------------------------------.
#   |     ____           _                       __        ___             |
#   |    |  _ \ ___  ___| |_ __ _ _ __ ___  ___  \ \      / (_)_ __        |
#   |    | |_) / _ \/ __| __/ _` | '__/ _ \/ __|  \ \ /\ / /| | '_ \       |
#   |    |  __/ (_) \__ \ || (_| | | |  __/\__ \   \ V  V / | | | | |      |
#   |    |_|   \___/|___/\__\__, |_|  \___||___/    \_/\_/  |_|_| |_|      |
#   |                       |___/                                          |
#   +----------------------------------------------------------------------+


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
        if self.instance.get("pg_user"):
            extra_args += " -U %s" % self.instance.get("pg_user")

        if self.instance.get("pg_database"):
            extra_args += " -d %s" % self.instance.get("pg_database")

        if self.instance.get("pg_port"):
            extra_args += " -p %s" % self.instance.get("pg_port")

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

    def get_pg_env(self):
        # type: () -> None

        try:
            env_file = open_wrapper(self.instance.get("env_file", ""))
            for line in env_file:
                for key, match_string in (
                    ("pg_database", '@SET PGDATABASE='),
                    ("pg_port", '@SET PGPORT='),
                ):
                    if match_string in line:
                        line = line.split("=")[-1]
                        self.instance[key] = line.strip().rstrip()

        except IOError:
            LOGGER.debug("No postgres .env file, using fallback values.")
            self.instance["pg_database"] = "postgres"
            self.instance["pg_port"] = "5432"

    def get_instances(self):
        # type: () -> str
        """Gets all instances"""

        procs_to_match = [
            re.compile(pattern) for pattern in
            [r"(.*)bin\\postgres(.*)", r"(.*)bin\\postmaster(.*)", r"(.*)bin\\edb-postgres(.*)"]
        ]

        taskslist = ensure_str(
            subprocess.check_output(
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
                out += "%s %s\n" % (PID, cmd_line)

        return out.rstrip()

    def get_stats(self):
        # type: () -> str
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
        for cnt, database in enumerate(self.databases):

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

    def get_bloat(self):
        # type: () -> str
        """Get the db bloats"""
        # Bloat index and tables
        # Supports versions <9.0, >=9.0
        # This huge query has been gratefully taken from Greg Sabino Mullane's check_postgres.pl
        if self.numeric_version > 9.0:
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
        for idx, database in enumerate(self.databases):

            query = "%s \\c %s \\\\ %s" % (query, database, bloat_query)
            if idx == 0:
                query = "%s \\pset tuples_only on" % query

        return self.run_sql_as_db_user(query, mixed_cmd=True, rows_only=cur_rows_only)


#   .--Postgres Linux------------------------------------------------------.
#   |  ____           _                        _     _                     |
#   | |  _ \ ___  ___| |_ __ _ _ __ ___  ___  | |   (_)_ __  _   ___  __   |
#   | | |_) / _ \/ __| __/ _` | '__/ _ \/ __| | |   | | '_ \| | | \ \/ /   |
#   | |  __/ (_) \__ \ || (_| | | |  __/\__ \ | |___| | | | | |_| |>  <    |
#   | |_|   \___/|___/\__\__, |_|  \___||___/ |_____|_|_| |_|\__,_/_/\_\   |
#   |                    |___/                                             |
#   +----------------------------------------------------------------------+


class PostgresLinux(PostgresBase):
    def __init__(self, db_user, pg_instance=None):
        super(PostgresLinux, self).__init__(db_user, pg_instance)

    def run_sql_as_db_user(self,
                           sql_cmd,
                           extra_args="",
                           field_sep=";",
                           quiet=True,
                           rows_only=True,
                           mixed_cmd=False):
        # type: (str, str, str, bool, bool, bool) -> str
        base_cmd_list = ["su", "-", self.db_user, "-c", r"""%s -X %s -A -F'%s'%s"""]

        if self.instance.get("pg_user"):
            extra_args += " -U %s" % self.instance.get("pg_user")

        if self.instance.get("pg_database"):
            extra_args += " -d %s" % self.instance.get("pg_database")

        if self.instance.get("pg_port"):
            extra_args += " -p %s" % self.instance.get("pg_port")

        if quiet:
            extra_args += " -q"
        if rows_only:
            extra_args += " -t"

        # In case we want to use postgres meta commands AND SQL queries in one call, we need to pipe
        # the full cmd string into psql executable
        # see https://www.postgresql.org/docs/9.2/app-psql.html
        if mixed_cmd:
            cmd_to_pipe = subprocess.Popen(["echo", sql_cmd], stdout=subprocess.PIPE)
            base_cmd_list[-1] = base_cmd_list[-1] % (self.psql, extra_args, field_sep, "")
            receiving_pipe = subprocess.Popen(base_cmd_list,
                                              stdin=cmd_to_pipe.stdout,
                                              stdout=subprocess.PIPE,
                                              env=self.my_env)
            out = ensure_str(receiving_pipe.communicate()[0])

        else:
            base_cmd_list[-1] = base_cmd_list[-1] % (self.psql, extra_args, field_sep,
                                                     " -c \"%s\" " % sql_cmd)
            proc = subprocess.Popen(base_cmd_list, env=self.my_env, stdout=subprocess.PIPE)
            out = ensure_str(proc.communicate()[0])

        return out.rstrip()

    def get_pg_env(self):

        try:
            env_file = open_wrapper(self.instance.get("env_file", ""))
            for line in env_file:

                for key, match_string in (("pg_database", 'export PGDATABASE='),
                                          ("pg_port", 'export PGPORT=')):

                    if match_string in line:
                        line = line.split("=")[-1]
                        self.instance[key] = re.sub(re.compile("#.*"), "", line).strip().rstrip()

        except IOError:
            LOGGER.debug("No postgres .env file, using fallback values.")
            self.instance["pg_database"] = "postgres"
            self.instance["pg_port"] = "5432"

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

        procs_list = ensure_str(subprocess.check_output(["ps", "h", "-eo",
                                                         "pid:1,command:1"])).split("\n")
        out = ""
        for proc in procs_list:
            proc_list = proc.split(" ")
            if len(proc_list) != 2:
                continue
            PID = proc_list[0]
            joined_cmd_line = " ".join(proc_list[1])
            if any(pat.search(joined_cmd_line) for pat in procs_to_match):
                out += "%s %s\n" % (PID, joined_cmd_line)
        return out.rstrip()

    def get_query_duration(self):
        # type: () -> str
        # Previously part of simple_queries

        if self.numeric_version > 9.2:
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

    def get_stats(self):
        # type: () -> str
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
        for cnt, database in enumerate(self.databases):

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

    def get_bloat(self):
        # type: () -> str
        # Bloat index and tables
        # Supports versions <9.0, >=9.0
        # This huge query has been gratefully taken from Greg Sabino Mullane's check_postgres.pl
        if self.numeric_version > 9.0:
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
        for idx, database in enumerate(self.databases):

            query = "%s\n\\c %s\n%s" % (query, database, bloat_query)
            if idx == 0:
                query = "%s\n\\pset tuples_only on" % query

        return self.run_sql_as_db_user(query, mixed_cmd=True, rows_only=cur_rows_only)


#   .--factory-------------------------------------------------------------.
#   |                  __            _                                     |
#   |                 / _| __ _  ___| |_ ___  _ __ _   _                   |
#   |                | |_ / _` |/ __| __/ _ \| '__| | | |                  |
#   |                |  _| (_| | (__| || (_) | |  | |_| |                  |
#   |                |_|  \__,_|\___|\__\___/|_|   \__, |                  |
#   |                                              |___/                   |
#   +----------------------------------------------------------------------+


def postgres_factory(db_user, pg_instance=None):
    # type: (str, Optional[Dict[str, str]]) -> PostgresBase
    if IS_LINUX:
        return PostgresLinux(db_user, pg_instance)
    if IS_WINDOWS:
        return PostgresWin(db_user, pg_instance)
    raise NotImplementedError("The OS type(%s) is not yet implemented." % platform.system())


#   .--PostgresConfig------------------------------------------------------.
#   | ____           _                       ____             __ _         |
#   ||  _ \ ___  ___| |_ __ _ _ __ ___  ___ / ___|___  _ __  / _(_) __ _   |
#   || |_) / _ \/ __| __/ _` | '__/ _ \/ __| |   / _ \| '_ \| |_| |/ _` |  |
#   ||  __/ (_) \__ \ || (_| | | |  __/\__ \ |__| (_) | | | |  _| | (_| |  |
#   ||_|   \___/|___/\__\__, |_|  \___||___/\____\___/|_| |_|_| |_|\__, |  |
#   |                   |___/                                      |___/   |
#   +----------------------------------------------------------------------+


class PostgresConfig:
    """
    Parser for Postgres config. x-Plattform compatible.

    Example for .cfg file:
    DBUSER=postgres
    INSTANCE=/home/postgres/db1.env:USER_NAME:/PATH/TO/.pgpass
    INSTANCE=/home/postgres/db2.env:USER_NAME:/PATH/TO/.pgpass
    """

    _cfg_name = "postgres.cfg"
    _default_win = "c:\\ProgramData\\checkmk\\agent\\config"
    _default_linux = "/etc/check_mk"

    def __init__(self):

        # Handle OS differences
        if IS_LINUX:
            default_path = self._default_linux
            conf_sep = ":"
        if IS_WINDOWS:
            default_path = self._default_win
            conf_sep = "|"

        self.path_to_config = os.path.join(os.getenv("MK_CONFDIR", default_path), self._cfg_name)
        self.conf_sep = conf_sep

        self.instances = []  # type: List[Dict[str, str]]
        self.dbuser = ""
        self.try_parse_config()

    def try_parse_config(self):
        try:
            config = open_wrapper(self.path_to_config)
            for line in config:
                if line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=")

                if key == "DBUSER":
                    self.dbuser = value.rstrip()
                if key == "INSTANCE":

                    env_file, pg_user, pg_passfile = value.split(self.conf_sep)
                    self.instances.append({
                        "env_file": env_file,
                        "name": env_file.split(os.sep)[-1].split(".")[0],
                        "pg_user": pg_user,
                        "pg_passfile": pg_passfile.rstrip()
                    })

        except (IOError, TypeError):
            LOGGER.debug("Config file \"%s\" not found. Continuing with fall back.",
                         self.path_to_config)
            self.get_fall_back()

    def get_fall_back(self):

        if IS_WINDOWS:
            raise NotImplementedError(
                "Fallback in case of missing cfg file on windows not implemented yet.\n"
                "Please create a postgres.cfg under %s." % self.path_to_config)
        if IS_LINUX:
            for user_id in ("pgsql", "postgres"):
                try:
                    proc = subprocess.Popen(["id", user_id],
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
                    proc.communicate()
                    if proc.returncode == 0:
                        self.dbuser = user_id.rstrip()
                        return
                except subprocess.CalledProcessError:
                    pass
            raise ValueError("Could not determine postgres user!")


#   .--parse---------------------------------------------------------------.
#   |                                                                      |
#   |                      _ __   __ _ _ __ ___  ___                       |
#   |                     | '_ \ / _` | '__/ __|/ _ \                      |
#   |                     | |_) | (_| | |  \__ \  __/                      |
#   |                     | .__/ \__,_|_|  |___/\___|                      |
#   |                     |_|                                              |
#   +----------------------------------------------------------------------+


def parse_arguments(argv):
    # type: (List[str]) -> argparse.Namespace

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verbose', '-v', action="count", default=0)
    parser.add_argument("-t",
                        "--test-connection",
                        default=False,
                        action="store_true",
                        help="Test if postgres is ready")

    return parser.parse_args(argv)


def open_wrapper(file_to_open):
    """Wrapper around built-in open to be able to monkeypatch through all python versions"""
    return open(file_to_open).readlines()


#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+


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

    config = PostgresConfig()

    if not config.instances:
        my_collector = postgres_factory(config.dbuser)
        if opt.test_connection:
            my_collector.is_pg_ready()
            sys.exit(0)
        my_collector.execute_all_queries()

    for instance in config.instances:
        my_collector = postgres_factory(config.dbuser, instance)
        if opt.test_connection:
            my_collector.is_pg_ready()
            sys.exit(0)
        my_collector.execute_all_queries()

    return 0


if __name__ == "__main__":
    main()
