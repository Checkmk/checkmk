// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use check_http::{check_http, cli::Cli};
use clap::Parser;

#[tokio::main]
async fn main() {
    let args = Cli::parse();
    let output = check_http(args).await;
    println!("{}", output);
    std::process::exit(output.state.into());
}
