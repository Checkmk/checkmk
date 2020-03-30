#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
import argparse
import os
from subprocess import Popen, PIPE, DEVNULL

from typing import List, Iterable, Dict, Optional

LISTER = "db2ilist.exe"


def make_env(instance):
    # type: (Optional[str]) -> Dict[str, str]
    env = os.environ.copy()
    env["DB2CLP"] = "DB20FADE"
    if instance is not None:
        env["DB2INSTANCE"] = instance

    return env


class Config():
    def __init__(self):
        self.args = self._parse_arguments()

    def _parse_arguments(self):
        # type: () -> argparse.Namespace
        parser = argparse.ArgumentParser(description='DB2 information')
        parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
        return parser.parse_args()

    def is_verbose(self):
        return self.args.verbose


def print_header():
    print(r"<<<db2_version:sep(1)>>>")


def print_database_info(database):
    # type: (str) -> None
    print(database)


def list_instances(config):
    # type: (Config) -> List[str]
    try:
        process = Popen(args=LISTER,
                        shell=False,
                        stdout=PIPE,
                        stdin=DEVNULL,
                        stderr=DEVNULL,
                        close_fds=True,
                        encoding="utf-8")
        stdout = process.communicate()[0]
        return stdout.split("\n")
    except (OSError, ValueError) as e:
        if config.is_verbose():
            print(" database list error with Exception {}".format(e,))
        return []


def check_database(config, name):
    # type: (Config, str) -> Iterable[str]
    try:
        process = Popen(args=["db2.exe", "connect", "to", name],
                        shell=False,
                        stdout=PIPE,
                        stdin=DEVNULL,
                        stderr=DEVNULL,
                        close_fds=True,
                        encoding="utf-8",
                        env=make_env(instance=None))
        stdout = process.communicate()[0]
        return filter(len, [_line.replace("\r", "") for _line in stdout.split("\n")])
    except (OSError, ValueError) as e:
        if config.is_verbose():
            print(" database list error with Exception {}".format(e,))
        return []


def list_databases(config, instance):
    # type: (Config, str) -> Iterable[str]
    try:
        process = Popen(args=["db2.exe", "list", "db", "directory"],
                        shell=False,
                        stdout=PIPE,
                        stdin=DEVNULL,
                        stderr=DEVNULL,
                        close_fds=True,
                        encoding="utf-8",
                        env=make_env(instance=instance))
        stdout = process.communicate()[0]
        return filter(len, [_line.replace("\r", "") for _line in stdout.split("\n")])
    except (OSError, ValueError) as e:
        if config.is_verbose():
            print(" database list error with Exception {}".format(e,))
        return []


# MAIN:
if __name__ == '__main__':
    c = Config()
    instances = list_instances(config=c)
    if len(instances) == 0:
        sys.exit(0)

    print_header()
    for i in instances:
        db = list_databases(config=c, instance=i)
        for d in db:
            print(d)

    sys.exit(0)
