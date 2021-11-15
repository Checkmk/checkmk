#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#
#       U  ___ u  __  __   ____
#        \/"_ \/U|' \/ '|u|  _"\
#        | | | |\| |\/| |/| | | |
#    .-,_| |_| | | |  | |U| |_| |\
#     \_)-\___/  |_|  |_| |____/ u
#          \\   <<,-,,-.   |||_
#         (__)   (./  \.) (__)_)
#
# This file is part of OMD - The Open Monitoring Distribution.
# The official homepage is at <http://omdistro.org>.
#
# OMD  is  free software;  you  can  redistribute it  and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the  Free Software  Foundation  in  version 2.  OMD  is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import contextlib
import os
import shutil
import sys
from typing import Iterator

import cmk.utils.tty as tty


def is_dockerized() -> bool:
    return os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv")


@contextlib.contextmanager
def chdir(path: str) -> Iterator[None]:
    """Change working directory and return on exit"""
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def ok() -> None:
    sys.stdout.write(tty.ok + "\n")


def delete_user_file(user_path: str) -> None:
    if not os.path.islink(user_path) and os.path.isdir(user_path):
        shutil.rmtree(user_path)
    else:
        os.remove(user_path)


def delete_directory_contents(d: str) -> None:
    for f in os.listdir(d):
        delete_user_file(d + "/" + f)


def omd_base_path() -> str:
    return "/"
