// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.
use log::info;
use sql_check::setup;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    setup::init(std::env::args_os())?;
    info!("Starting");
    sql_check::ms_sql::api::check_connect("agentbuild3.lan.tribe29.com", 1433, "u", "u").await?;
    println!("Success");

    Ok(())
}
