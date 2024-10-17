# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.config import builtin_role_ids
from cmk.gui.userdb._roles import BuiltInUserRoleValues


def test_buildin_role_ids_var_is_complete() -> None:
    ids = [m.value for m in BuiltInUserRoleValues]
    assert set(ids) == set(builtin_role_ids)
