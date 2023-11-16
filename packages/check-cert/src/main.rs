// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::{Context, Result};
use check_cert::{checker, fetcher, output};
use clap::Parser;
use openssl::asn1::Asn1Time;
use openssl::x509::X509;
use std::time::Duration;

#[derive(Parser, Debug)]
#[command(about = "check_cert")]
struct Args {
    /// URL to check
    #[arg(short, long)]
    url: String,

    /// Port
    #[arg(short, long, default_value_t = 443)]
    port: u16,

    /// Set timeout in seconds
    #[arg(long, default_value_t = 10)]
    timeout: u64,

    /// Warn if certificate expires in n days
    #[arg(long, default_value_t = 30)]
    warn: u32,

    /// Crit if certificate expires in n days
    #[arg(long, default_value_t = 0)]
    crit: u32,

    /// Disable SNI extension
    #[arg(long, action = clap::ArgAction::SetTrue)]
    disable_sni: bool,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();

    let warn_time = Asn1Time::days_from_now(args.warn).context("Invalid warn value")?;
    let crit_time = Asn1Time::days_from_now(args.crit).context("Invalid crit value")?;
    if warn_time < crit_time {
        eprintln!("crit limit larger than warn limit");
        std::process::exit(1);
    }

    let der = fetcher::fetch_server_cert(
        &args.url,
        &args.port,
        if args.timeout == 0 {
            None
        } else {
            Some(Duration::new(args.timeout, 0))
        },
        !args.disable_sni,
    )?;

    let cert = X509::from_der(&der)?;
    let out = output::Output::from(vec![checker::check_validity(
        &args.url,
        cert.not_after(),
        &warn_time,
        &crit_time,
    )]);
    println!("HTTP {}", out);
    std::process::exit(match out.state {
        checker::State::Ok => 0,
        checker::State::Warn => 1,
        checker::State::Crit => 2,
        checker::State::Unknown => 3,
    })
}
