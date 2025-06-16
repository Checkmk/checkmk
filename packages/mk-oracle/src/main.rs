// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.
use mk_oracle::setup;

#[tokio::main]
async fn main() {
    let result = setup::init(std::env::args_os());
    if let Ok((config, environment)) = result {
        match config.exec(&environment).await {
            Ok(output) => {
                print!("{output}");
                log::info!("Success");
                std::process::exit(0);
            }
            Err(e) => {
                display_and_log(e);
                std::process::exit(1);
            }
        }
    } else {
        display_and_log(result.err().unwrap());
        std::process::exit(1);
    }
}

fn display_and_log(e: impl std::fmt::Display) {
    log::error!("{e}",);
    eprintln!("Stop on error: `{e}`",);
}
