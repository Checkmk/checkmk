// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.
use anyhow::Result;
use check_sql::setup;

#[tokio::main]
async fn main() -> Result<()> {
    let (config, environment) = setup::init(std::env::args_os())?;
    match config.exec(&environment).await {
        Ok(output) => {
            print!("{output}");
            log::info!("Success");
            Ok(())
        }
        Err(e) => {
            log::error!("{e}");
            Err(anyhow::anyhow!("{e}"))
        }
    }
}
