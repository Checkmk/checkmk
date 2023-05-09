// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::monitoring_data;
use anyhow::{Context, Result as AnyhowResult};
use std::io::Write;

pub fn dump() -> AnyhowResult<()> {
    let mon_data = monitoring_data::collect().context("Error collecting monitoring data.")?;
    std::io::stdout()
        .write_all(&mon_data)
        .context("Error writing monitoring data to stdout.")?;
    Ok(())
}
