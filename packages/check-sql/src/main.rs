// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.
use anyhow::Result;
use check_sql::ms_sql::api;
use check_sql::setup;
use log::info;

#[tokio::main]
async fn main() -> Result<()> {
    info!("Starting");
    let _config = setup::init(std::env::args_os())?;
    let _local_client = api::create_client_for_logged_user("localhost", 1433).await?;
    println!("Integrated Success");
    let _remote_client = api::create_client(
        "agentbuild3.lan.tribe29.com",
        1433,
        api::Credentials::SqlServer {
            user: "u",
            password: "u",
        },
    )
    .await?;
    println!("Remote Success");

    Ok(())
}
