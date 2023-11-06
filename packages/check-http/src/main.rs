// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use check_http::cli::Cli;
use check_http::output::Output;
use check_http::runner::collect_checks;
use clap::Parser;

#[tokio::main]
async fn main() {
    let args = Cli::parse();
    let output = Output::from_check_results(collect_checks(args).await);
    println!("{}", output);
    std::process::exit(output.worst_state.into());
}
