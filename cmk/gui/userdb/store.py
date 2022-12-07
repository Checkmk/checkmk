#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path
from typing import Any, Callable, TypeVar

from cmk.utils.paths import var_dir
from cmk.utils.store import load_text_from_file, mkdir, save_text_to_file
from cmk.utils.type_defs import UserId

T = TypeVar("T")


def load_custom_attr(
    *,
    user_id: UserId,
    key: str,
    parser: Callable[[str], T],
    lock: bool = False,
) -> T | None:
    result = load_text_from_file(Path(custom_attr_path(user_id, key)), lock=lock)
    return None if result == "" else parser(result.strip())


def custom_attr_path(userid: UserId, key: str) -> str:
    return var_dir + "/web/" + userid + "/" + key + ".mk"


def save_custom_attr(userid: UserId, key: str, val: Any) -> None:
    path = custom_attr_path(userid, key)
    mkdir(os.path.dirname(path))
    save_text_to_file(path, "%s\n" % val)
