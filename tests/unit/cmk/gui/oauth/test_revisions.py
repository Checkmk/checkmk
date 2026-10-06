#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from sqlite3 import Connection
from typing import override

from cmk.schema_manager import ManagedDatabase
from cmk.schema_manager.backend.sqlite import Sqlite
from cmk.schema_migrations.oauth import schema_manager_oauth
from cmk.testlib.schema_manager import RevisionTestSuite


class TestOauthRevisions(RevisionTestSuite[Connection]):
    @property
    @override
    def managed_database(self) -> ManagedDatabase[Connection, Sqlite]:
        return schema_manager_oauth
