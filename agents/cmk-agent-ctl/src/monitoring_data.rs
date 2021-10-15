// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::io::{Read, Result};
use std::os::unix::net::UnixStream;

pub fn collect(package_name: &Option<String>) -> Result<Vec<u8>> {
    let mut mondata: Vec<u8> = vec![];
    let package_name = match package_name {
        Some(pkg) => &pkg,
        None => "check-mk-agent",
    };
    UnixStream::connect(format!("/run/{}.socket", package_name))?.read_to_end(&mut mondata)?;
    return Ok(mondata);
}
