// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::check::{Check, SimpleCheckResult};
use typed_builder::TypedBuilder;

#[derive(Debug, TypedBuilder)]
pub struct Config<'a> {
    server: &'a str,
    port: u16,
}

pub fn collect(config: Config) -> Check {
    Check::from(&mut vec![
        SimpleCheckResult::notice(format!("Host to test: {}", config.server)).into(),
        SimpleCheckResult::notice(format!("Host port: {}", config.port)).into(),
    ])
}
