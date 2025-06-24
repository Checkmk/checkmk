#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# DB2 support requires installation of the IBM Data Server Client:
#  http://www-01.ibm.com/support/docview.wss?uid=swg27016878
# as well as the ibm_db2 Python DBI driver for DB2:
#  https://pypi.org/pypi/ibm_db

# SQLAnywhere support requires installation of the SAP SQL Anywhere binaries, the `sqlanydb` python
# package, and certain environment variables set in the site's runtime environment. See the checkman
# documentation for more information.
"""Checkmk SQL Database Request Check"""

import argparse
import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn

from cmk.utils import password_store

LOG = logging.getLogger(__name__)

DEFAULT_PORTS = {
    "postgres": 5432,
    "mysql": 3306,
    "mssql": 1433,
    "oracle": 1521,
    "db2": 50000,
    "sqlanywhere": 2638,
}

MP_INF: tuple[float, float] = (float("-inf"), float("+inf"))

#   . parse commandline argumens


def levels(values: str) -> tuple[float, float]:
    lower, upper = values.split(":")
    _lower = float(lower) if lower else MP_INF[0]
    _upper = float(upper) if upper else MP_INF[1]
    return (_lower, _upper)


def sql_cmd_piece(values: str) -> str:
    """Parse every piece of the SQL command (replace \\n and \\;)"""
    return values.replace(r"\n", "\n").replace(r"\;", ";")


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse commandline arguments (incl password store and logging set up)"""
    help_fmt = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=help_fmt)
    # flags
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="""Verbose mode: print SQL statement and levels
                             (for even more output use -vv""",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="""Debug mode: let Python exceptions come through""",
    )
    parser.add_argument(
        "-m",
        "--metrics",
        nargs="?",
        metavar="METRIC_NAME",
        const="performance_data",
        help="""Add performance data to the output. Store data with metric_name in RRD.""",
    )
    parser.add_argument(
        "-o",
        "--procedure",
        action="store_true",
        help="""Treat the main argument as a procedure instead
                              of an SQL-Statement""",
    )
    parser.add_argument(
        "-i",
        "--input",
        metavar="CSV",
        default=[],
        type=lambda s: s.split(","),
        help="""Comma separated list of values of input variables
                             if required by the procedure""",
    )
    # optional arguments
    parser.add_argument(
        "-d",
        "--dbms",
        default="postgres",
        choices=["postgres", "mysql", "mssql", "oracle", "db2", "sqlanywhere"],
        help='''Name of the database management system.
                             Default is "postgres"''',
    )
    parser.add_argument(
        "-H",
        "--hostname",
        metavar="HOST",
        default="127.0.0.1",
        help='''Hostname or IP-Address where the database lives.
                             Default is "127.0.0.1"''',
    )
    parser.add_argument(
        "-P",
        "--port",
        default=None,
        type=int,
        help="""Port used to connect to the database.
                             Default depends on DBMS""",
    )
    parser.add_argument(
        "-w",
        "--warning",
        metavar="RANGE",
        default=MP_INF,
        type=levels,
        help="""Lower and upper level for the warning state,
                             separated by a colon""",
    )
    parser.add_argument(
        "-c",
        "--critical",
        metavar="RANGE",
        default=MP_INF,
        type=levels,
        help="""Lower and upper level for the critical state,
                             separated by a colon""",
    )
    parser.add_argument(
        "-t",
        "--text",
        default="",
        help="""Additional text prefixed to the output""",
    )

    # required arguments
    parser.add_argument(
        "-n",
        "--name",
        required=True,
        help="""Name of the database on the DBMS""",
    )
    parser.add_argument(
        "-u",
        "--user",
        required=True,
        help="""Username for database access""",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--password-reference",
        help="Password store reference of the password for the database access.",
    )
    group.add_argument(
        "-p",
        "--password",
        help="""Password for database access""",
    )
    parser.add_argument(
        "cmd",
        metavar="SQL-Statement|Procedure",
        type=sql_cmd_piece,
        nargs="+",
        help="""Valid SQL-Statement for the selected database.
                             The statement must return at least a number and a
                             string, plus optional performance data.

                             Alternatively: If the the "-o" option is given,
                             treat the argument as a procedure name.

                             The procedure must return one output variable,
                             which content is evaluated the same way as the
                             output of the SQL-Statement""",
    )
    args = parser.parse_args(argv[1:])
    args.cmd = " ".join(args.cmd)

    # LOGGING
    fmt = "%(message)s"
    if args.verbose > 1:
        fmt = "%(levelname)s: %(lineno)s: " + fmt
        if args.dbms == "mssql":
            os.environ["TDSDUMP"] = "stdout"
    logging.basicConfig(level=max(30 - 10 * args.verbose, 0), format=fmt)

    # V-VERBOSE INFO
    for key, val in args.__dict__.items():
        if key in ("user", "password"):
            val = "****"
        LOG.debug("argparse: %s = %r", key, val)
    return args


# .


def bail_out(exit_code: int, output: str) -> NoReturn:
    sys.stdout.write("%s\n" % output)
    sys.exit(exit_code)


#   . DBMS specific code here!
#
# For every DBMS specify a connect and execute function.
# Add them in the dict in the 'main' connect and execute functions
#
def _default_execute(
    cursor: Any, cmd: str, inpt: Sequence[str], procedure: str
) -> list[tuple[Any, ...]]:
    if procedure:
        LOG.info("SQL Procedure Name: %s", cmd)
        LOG.info("Input Values: %s", inpt)
        cursor.callproc(cmd, inpt)
        LOG.debug("inpt after 'callproc' = %r", inpt)
    else:
        LOG.info("SQL Statement: %s", cmd)
        cursor.execute(cmd)

    return cursor.fetchall()


def postgres_connect(host: str, port: int, db_name: str, user: str, pwd: str) -> Any:
    import psycopg2

    return psycopg2.connect(host=host, port=port, database=db_name, user=user, password=pwd)


def postgres_execute(
    cursor: Any, cmd: str, inpt: Sequence[str], procedure: str
) -> list[tuple[Any, ...]]:
    return _default_execute(cursor, cmd, inpt, procedure)


def mysql_connect(host: str, port: int, db_name: str, user: str, pwd: str) -> Any:
    import pymysql

    return pymysql.connect(host=host, port=port, db=db_name, user=user, passwd=pwd)


def mysql_execute(
    cursor: Any, cmd: str, inpt: Sequence[str], procedure: str
) -> list[tuple[Any, ...]]:
    return _default_execute(cursor, cmd, inpt, procedure)


def mssql_connect(host: str, port: int, db_name: str, user: str, pwd: str) -> Any:
    import pymssql  # type: ignore[import-not-found]

    return pymssql.connect(host=host, port=str(port), database=db_name, user=user, password=pwd)


def mssql_execute(
    cursor: Any, cmd: str, _inpt: Sequence[str], procedure: bool
) -> list[tuple[Any, ...]]:
    if procedure:
        LOG.info("SQL Procedure Name: %s", cmd)
        cmd = "EXEC " + cmd
    else:
        LOG.info("SQL Statement: %s", cmd)

    cursor.execute(cmd)

    return cursor.fetchall()


def oracle_connect(host: str, port: int, db_name: str, user: str, pwd: str) -> Any:
    sys.path.append(
        f"/usr/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
    )
    import oracledb  # type: ignore[import-not-found]

    try:
        oracledb.init_oracle_client()
    except oracledb.DatabaseError as dbe:
        # this seems to be the official way to differentiate between exceptions:
        # https://python-oracledb.readthedocs.io/en/latest/user_guide/exception_handling.html#exception
        if dbe.args[0].full_code == "DPI-1047":
            LOG.info(
                "Could not activate thick mode, will continue and use thin mode instead. "
                "https://python-oracledb.readthedocs.io/en/latest/user_guide/initialization.html#initializing-python-oracledb"
            )
        else:
            raise

    cstring = f"{user}/{pwd}@{host}:{port}/{db_name}"
    return oracledb.connect(cstring)


def oracle_execute(
    cursor: Any, cmd: str, inpt: Sequence[str], procedure: bool
) -> list[tuple[Any, ...]]:
    import oracledb

    if procedure:
        LOG.info("SQL Procedure Name: %s", cmd)
        LOG.info("Input Values: %s", inpt)

        # In an earlier version, this code-branch
        # had been executed regardles of the dbms.
        # clearly this is oracle specific.
        outvar = cursor.var(oracledb.STRING)
        # However, I have not been able to test it.
        parameters = [*inpt, outvar]
        cursor.callproc(cmd, parameters)

        LOG.debug("parameters after 'callproc' = %r", parameters)
        LOG.debug("outvar = %r", outvar)

        # for empty input this is just
        #  _res = outvar.getvalue()
        _res = ",".join(i.getvalue() for i in parameters)

        LOG.debug("outvar.getvalue() = %r", _res)
        params_result = _res.split(",")
        LOG.debug("params_result = %r", params_result)

    else:
        LOG.info("SQL Statement: %s", cmd)
        cursor.execute(cmd)

    return cursor.fetchall()


def db2_connect(host: str, port: int, db_name: str, user: str, pwd: str) -> Any:
    # IBM data server driver
    try:
        import ibm_db  # type: ignore[import-untyped]
        import ibm_db_dbi  # type: ignore[import-not-found]
    except ImportError as exc:
        bail_out(3, "%s. Please install it via pip." % exc)

    cstring = (
        "DRIVER={IBM DB2 ODBC DRIVER};DATABASE=%s;"
        "HOSTNAME=%s;PORT=%s;PROTOCOL=TCPIP;UID=%s;PWD=%s;" % (db_name, host, port, user, pwd)
    )
    ibm_db_conn = ibm_db.connect(cstring, "", "")
    return ibm_db_dbi.Connection(ibm_db_conn)


def db2_execute(
    cursor: Any, cmd: str, inpt: Sequence[str], procedure: str
) -> list[tuple[Any, ...]]:
    return _default_execute(cursor, cmd, inpt, procedure)


def sqlanywhere_connect(host: str, port: int, db_name: str, user: str, pwd: str) -> Any:
    site = os.getenv("OMD_SITE")

    if not any("sqlanywhere" in path for path in sys.path):
        message = (
            "ERROR: SQL Anywhere binaries weren't found on your $PATH\nMake sure that they are "
            f"installed under /omd/sites/{site}/local/lib with the correct file permissions:\n\n"
            f"$ chown -R {site}:{site} /omd/sites/{site}/local/lib/sqlanywhere*\n\n"
            f"Now, source the environment variables inside: /omd/sites/{site}/.bashrc\n\n"
            "Here is how it'd look if SQL Anywhere 17 on a 64 bit machine is installed:\n\n"
            "source ./local/lib/sqlanywhere17/bin64/sa_config.sh\n\n"
            "Finally, run 'omd restart' so that the site loads the necessary environment "
            "variables."
        )
        bail_out(3, message)

    try:
        import sqlanydb  # type: ignore[import-not-found]
    except ImportError as exc:
        bail_out(3, f"{exc}. Please install via `omd[{site}]$ pip3 install sqlanydb`.")

    return sqlanydb.connect(uid=user, pwd=pwd, dbn=db_name, host=f"{host}:{port}")


def sqlanywhere_execute(
    cursor: Any, cmd: str, inpt: Sequence[str], procedure: str
) -> list[tuple[Any, ...]]:
    return _default_execute(cursor, cmd, inpt, procedure)


# .


def connect(dbms: str, host: str, port: int | None, db_name: str, user: str, pwd: str) -> Any:
    """Connect to the correct database

    A python library is imported depending on the value of dbms.
    Return the created connection object.
    """
    if port is None:
        port = DEFAULT_PORTS[dbms]

    return {
        "postgres": postgres_connect,
        "mysql": mysql_connect,
        "mssql": mssql_connect,
        "oracle": oracle_connect,
        "db2": db2_connect,
        "sqlanywhere": sqlanywhere_connect,
    }[dbms](host, port, db_name, user, pwd)


def execute(
    dbms: str, connection: Any, cmd: str, inpt: Sequence[str], procedure: bool = False
) -> list[tuple[Any, ...]]:
    """Execute the sql statement, or call the procedure.

    Some corrections are made for libraries that do not adhere to the
    python SQL API: https://www.python.org/dev/peps/pep-0249/
    """
    cursor = connection.cursor()

    try:
        result = {
            "postgres": postgres_execute,
            "mysql": mysql_execute,
            "mssql": mssql_execute,
            "oracle": oracle_execute,
            "db2": db2_execute,
            "sqlanywhere": sqlanywhere_execute,
        }[dbms](cursor, cmd, inpt, procedure)  # type: ignore[operator]
    finally:
        cursor.close()
        connection.close()

    LOG.info("SQL Result:\n%r", result)
    return result


def process_result(
    result: list[tuple[Any, ...]],
    warn: tuple[float, float],
    crit: tuple[float, float],
    metrics: str | None,
    debug: bool,
) -> tuple[int, str]:
    """Process the first row (!) of the result of the SQL command.

    Only the first row of the result (result[0]) is considered.
    It is assumed to be an sequence of length 3, consisting of of
    [numerical_value, text, performance_data].
    The full result is returned as muliline output.
    """
    if not result:
        bail_out(3, "SQL statement/procedure returned no data")
    row0 = result[0]

    number = float(row0[0])

    # handle case where sql query only results in one column
    if len(row0) == 1:
        text = "%s" % row0[0]
    else:
        text = "%s" % row0[1]

    perf = ""
    if metrics:
        try:
            perf = f" | {metrics}={str(row0[2])}"
        except IndexError:
            if debug:
                raise

    state = 0
    if warn != MP_INF or crit != MP_INF:
        if not warn[0] <= number < warn[1]:
            state = 1
        if not crit[0] <= number < crit[1]:
            state = 2
        text += ": %s" % number
    elif number in (0, 1, 2, 3):  # no levels were given
        state = int(number)
    else:
        bail_out(3, "<%d> is not a state, and no levels given" % number)

    return state, text + perf


def _make_secret(args: argparse.Namespace) -> str:
    if (ref := args.password_reference) is None:
        return args.password

    pw_id, pw_file = ref.split(":", 1)
    return password_store.lookup(Path(pw_file), pw_id)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv or sys.argv)

    msg = "connecting to database"
    try:
        conn = connect(
            args.dbms, args.hostname, args.port, args.name, args.user, _make_secret(args)
        )

        msg = "executing SQL command"
        result = execute(args.dbms, conn, args.cmd, args.input, procedure=args.procedure)

        msg = "processing result of SQL statement/procedure"
        state, text = process_result(
            result,
            args.warning,
            args.critical,
            metrics=args.metrics,
            debug=args.debug,
        )
    except Exception as exc:
        if args.debug:
            raise
        errmsg = str(exc).strip("()").replace(r"\n", " ")
        bail_out(3, f"Error while {msg}: {errmsg}")

    bail_out(state, args.text + text)


if __name__ == "__main__":
    main()
