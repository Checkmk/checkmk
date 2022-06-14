#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import os
import platform
import sys
import time
from subprocess import DEVNULL, PIPE, Popen, run
from typing import Dict, Iterable, List, Optional

LISTER = "db2ilist.exe"


def make_env(instance: Optional[str]) -> Dict[str, str]:
    env = os.environ.copy()
    env["DB2CLP"] = "DB20FADE"
    if instance is not None:
        env["DB2INSTANCE"] = instance

    return env


class Database:
    def __init__(self):
        self.args = self._parse_arguments()

    def _parse_arguments(self) -> argparse.Namespace:
        parser = argparse.ArgumentParser(description="DB2 information")
        parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
        return parser.parse_args()

    def is_verbose(self) -> bool:
        return self.args.verbose

    def write_log(self, message: str) -> None:
        if self.is_verbose():
            print(message)

    def print_db2_version_header(self):
        print(r"<<<db2_version:sep(1)>>>")

    def print_database_info(self, database: str) -> None:
        print(database)

    @staticmethod
    def cleanup_input(data: str) -> List[str]:
        return [_line.replace("\r", "") for _line in data.split(sep="\n") if len(_line)]  #

    @staticmethod
    def run_db2(args: List[str], instance: str) -> Popen:
        return Popen(
            args=["db2.exe"] + args,
            shell=False,
            stdout=PIPE,
            stdin=DEVNULL,
            stderr=DEVNULL,
            close_fds=True,
            encoding="utf-8",
            env=make_env(instance=instance),
        )

    def list_instances(self) -> List[str]:
        try:
            completed_process = run(
                args=LISTER,
                shell=False,
                stdout=PIPE,
                stdin=DEVNULL,
                stderr=DEVNULL,
                close_fds=True,
                encoding="utf-8",
                check=False,
            )
            return completed_process.stdout.strip().split(sep="\n")
        except (OSError, ValueError) as e:
            if self.is_verbose():
                print(
                    " database list error with Exception {}".format(
                        e,
                    )
                )
            return []

    def check_database(self, instance: str, name: str) -> List[str]:
        try:
            process = Database.run_db2(args=["connect", "to", name], instance=instance)
            stdout = process.communicate()[0]
            return Database.cleanup_input(stdout)
        except (OSError, ValueError) as e:
            self.write_log(
                " database list error with Exception {}".format(
                    e,
                )
            )
            return []

    def get_list_databases(self, instance: str) -> List[str]:
        try:
            process = Database.run_db2(args=["list", "db", "directory"], instance=instance)
            stdout = process.communicate()[0]
            return Database.cleanup_input(stdout)
        except (OSError, ValueError) as e:
            self.write_log(
                " database list error with Exception {}".format(
                    e,
                )
            )
            return []

    def snapshot_databases(self, instance: str) -> List[str]:
        try:
            process = Database.run_db2(args=["get", "snapshot", "for", "dbm"], instance=instance)
            stdout = process.communicate()[0]
            return Database.cleanup_input(stdout)
        except (OSError, ValueError) as e:
            self.write_log(
                " database list error with Exception {}".format(
                    e,
                )
            )
            return []

    @staticmethod
    def find_value(key: str, data: Iterable[str]) -> str:
        for d in data:
            if d.find(key) != -1:
                value = d.split("=")[1]
                return value.strip()

        return ""

    @staticmethod
    def is_database_presented(db_list: List[str]) -> bool:
        return len(db_list) > 3

    def process_databases(self, database: str, port: int, now: int, instance: str) -> None:
        # before = time.time()
        # process = Database.run_db2(args=["connect", "to", database], instance=instance )
        # stdout = process.communicate()[0]
        # output = Database.cleanup_input(stdout)

        print("<<<db2_connections>>>")
        print("[[[{}:{}]]]".format(instance, database))
        print("{}".format(port))
        print("connections ")  # | tr -d '\n'
        # db2 -x "SELECT count(*)-1 FROM TABLE(mon_get_connection(CAST(NULL AS BIGINT), -2)) AS t"
        # after = time.time()
        # diff = round((after - before), ndigits=3)*1000

        print("latency {}".format(123435))

        print("<<<db2_tablespaces>>>")
        print("[[[{}:{}]]]".format(instance, database))
        _ = "SELECT tbsp_name, tbsp_type, tbsp_state, tbsp_usable_size_kb, tbsp_total_size_kb, tbsp_used_size_kb, tbsp_free_size_kb FROM sysibmadm.tbsp_utilization WHERE tbsp_type = 'DMS' UNION ALL SELECT tu.tbsp_name, tu.tbsp_type, tu.tbsp_state, tu.tbsp_usable_size_kb, tu.tbsp_total_size_kb, tu.tbsp_used_size_kb, (cu.fs_total_size_kb - cu.fs_used_size_kb) AS tbsp_free_size_kb FROM sysibmadm.tbsp_utilization tu INNER JOIN ( SELECT tbsp_id, 1 AS fs_total_size_kb, 0 AS fs_used_size_kb FROM sysibmadm.container_utilization WHERE (fs_total_size_kb IS NULL OR fs_used_size_kb IS NULL) GROUP BY tbsp_id) cu ON (tu.tbsp_type = 'SMS' AND tu.tbsp_id = cu.tbsp_id) UNION ALL SELECT tu.tbsp_name, tu.tbsp_type, tu.tbsp_state, tu.tbsp_usable_size_kb, tu.tbsp_total_size_kb, tu.tbsp_used_size_kb, (cu.fs_total_size_kb - cu.fs_used_size_kb) AS tbsp_free_size_kb FROM sysibmadm.tbsp_utilization tu INNER JOIN ( SELECT tbsp_id, SUM(fs_total_size_kb) AS fs_total_size_kb, SUM(fs_used_size_kb) AS fs_used_size_kb FROM sysibmadm.container_utilization WHERE (fs_total_size_kb IS NOT NULL AND fs_used_size_kb IS NOT NULL) GROUP BY tbsp_id) cu ON (tu.tbsp_type = 'SMS' AND tu.tbsp_id = cu.tbsp_id)"  # noqa: E501
        # db2 "${SQL}" | awk '{print $1" "$2" "$3" "$4" "$5" "$6" "$7}' | sed -e '/^[ ]*$/d' -e '/^-/d' -e '/selected/d'

        print("<<<db2_counters>>>")
        print("TIMESTAMP {}".format(now))
        # echo "$INSTANCE:$DB deadlocks " | tr -d '\n'
        # db2 -x "SELECT deadlocks from sysibmadm.snapdb" | tr -d ' '
        # echo "$INSTANCE:$DB lockwaits " | tr -d '\n'
        # db2 -x "SELECT lock_waits from sysibmadm.snapdb" | tr -d ' '
        # echo "$INSTANCE:$DB sortoverflows " | tr -d '\n'
        # db2 -x "SELECT sort_overflows from sysibmadm.snapdb" | tr -d ' '
        print("<<<db2_logsizes>>>")
        print("TIMESTAMP {}".format(now))
        print("[[[{}:{}]]]".format(instance, database))
        # echo "usedspace " | tr -d '\n'
        # db2 -x "SELECT total_log_used from sysibmadm.snapdb" | tr -d ' '
        # db2 -x "SELECT NAME, VALUE FROM SYSIBMADM.DBCFG WHERE NAME IN ('logfilsiz','logprimary','logsecond')"| awk '{print $1" "$2}'

        print("<<<db2_bp_hitratios>>>")
        print("[[[{}:{}]]]".format(instance, database))
        # db2 "SELECT SUBSTR(BP_NAME,1,14) AS BP_NAME, TOTAL_HIT_RATIO_PERCENT, DATA_HIT_RATIO_PERCENT, INDEX_HIT_RATIO_PERCENT, XDA_HIT_RATIO_PERCENT FROM SYSIBMADM.BP_HITRATIO" | grep -v "selected." | sed -e '/^$/d' -e '/^-/d'

        print("<<<db2_sort_overflow>>>")
        print("[[[{}:{}]]]".format(instance, database))
        # db2 -x "get snapshot for database on $DB" | grep -e "^Total sorts" -e "^Sort overflows" | tr -d '='

        print("<<<db2_backup>>>")
        print("[[[{}:{}]]]".format(instance, database))
        # if compare_version_greater_equal "$VERSION_NUMBER" 10.5; then
        #  # MON_GET_DATBASE(-2) gets information of all active members
        #  db2 -x "select LAST_BACKUP from TABLE (MON_GET_DATABASE(-2))" | grep -v "selected." | tail -n 1
        # else
        #  db2 -x "select SQLM_ELM_LAST_BACKUP from table(SNAPSHOT_DATABASE( cast( null as VARCHAR(255)), cast(null as int))) as ref" | grep -v "selected." | tail -n 1
        # fi

        # disconnect from database
        # db2 connect reset > /dev/null
        # process = Database.run_db2(args=["connect", "reset"], instance=instance )
        # stdout = process.communicate()[0]
        # pass

    @staticmethod
    def find_port(instance: str, database: str) -> str:
        return "Port 0"  # default value

    @staticmethod
    def find_database_names(db_list, allowed_entry_types):
        # type (List[str], List[str]) -> List[str]

        # builds list of $1 if $2 in allowed_entry_types
        # .......
        # Database name        = $1
        # .......
        # Directory entry type = $2
        # .......
        db_name = ""
        db_names: List[str] = []
        for entry in db_list:
            line = entry.split("=")
            if len(line) != 2:
                continue

            if line[0].strip().lower() == "database name":
                db_name = line[1].strip()
                continue

            if (
                line[0].strip().lower() == "directory entry type"
                and line[1].strip().lower() in allowed_entry_types
            ):
                if len(db_name) > 0:
                    db_names.append(db_name)

        return db_names

    def process_instance(self, instance, db_list, cur_time):
        # type (str, List[str]) -> None

        snapshot = db.snapshot_databases(instance=instance)
        db.print_db2_version_header()
        product_name = Database.find_value(key="Product name", data=snapshot)
        service_level = Database.find_value(key="Service level", data=snapshot)
        # Replicates output  of the bash script mk_db2.linux

        # The check 'db2_version' expects the line not to be split by Checkmk base.
        # For this reason we set a column separator, '\1', that does not apply to the output.
        # This situation may be changed in the future
        # Spaces are removed because the check 'db2_version' expects precisely two tokens
        # splitted by ' '.
        print(
            "{} {},{}".format(
                instance, product_name.replace(" ", ""), service_level.replace(" ", "")
            )
        )

        db_names = Database.find_database_names(db_list, ["home", "indirect"])

        for db_name in db_names:
            db.process_databases(
                database=db_name,
                port=int(Database.find_port(instance=instance, database=db_name)),
                now=cur_time,
                instance=instance,
            )

            # we need to do so
            # grep -e 'Product name' -e 'Service level' | awk -v FS='=' '{print $2}' | sed 'N;s/\n/,/g' | sed 's/ //g'
            # to get so
            # expected DB2v11.5.0.1077,s1906101300(DYN1906101300WIN64)

    # TODO: use platform independent approach:
    #
    # class ABCConnector:
    #     @abc.abstractmethod
    #     def run_db2(self, cmd):
    #         raise NotImplementedError()
    #
    # class WindowsConnector(ABCConnector):
    #     def run_db2(self, cmd):
    #         return ...
    #
    # def connector_registry():
    #     if platform.system() == "Windows":
    #         return WindowsConnector()
    #     raise SystemExit("Unsupported Platform")

    #
    # prototype just to check that db2 works as intended in a windows shell
    #
    @staticmethod
    def shell_runner():
        if platform.system() == "Windows":
            with Popen(
                ["cmd.exe"],
                shell=False,
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
                universal_newlines=True,
                close_fds=True,
                bufsize=0,
            ) as shell:
                if shell.stdin is None or shell.stdout is None:
                    raise Exception("Huh? stdin or stdout vanished...")
                shell.stdin.write("@set DB2CLP=DB20FADE\n")
                shell.stdin.write("@db2 connect to SAMPLE\n")
                shell.stdin.write('@db2 -x "SELECT deadlocks from sysibmadm.snapdb"\n')
                shell.stdin.write("@db2 connect reset\n")
                shell.stdin.write("@exit\n")
                for line in shell.stdout:
                    print(line.strip())
        else:
            raise SystemExit("Unsupported Platform")


# MAIN:
if __name__ == "__main__":
    db = Database()
    current_time = int(time.time())
    for i in db.list_instances():
        databases = db.get_list_databases(instance=i)
        if Database.is_database_presented(db_list=databases):
            db.process_instance(instance=i, db_list=databases, cur_time=current_time)
            # database reader:
            # Database.shell_runner()
    sys.exit(0)
