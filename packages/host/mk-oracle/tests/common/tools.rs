// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.
pub const SQL_DB_ENDPOINT: &str = "CI_TEST_ORA_SQL_DB_ENDPOINT";

#[allow(dead_code)]
pub struct SqlDbEndpoint {
    pub host: String,
    pub user: String,
    pub pwd: String,
}
