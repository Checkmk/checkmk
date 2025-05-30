// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#[cfg(not(feature = "build_system_bazel"))]
mod common;

#[cfg(feature = "build_system_bazel")]
extern crate common;

use common::tools::SQL_DB_ENDPOINT;

#[allow(clippy::const_is_empty)]
#[tokio::test(flavor = "multi_thread")]
async fn test_local_connection() {
    assert!(!SQL_DB_ENDPOINT.is_empty());
}
