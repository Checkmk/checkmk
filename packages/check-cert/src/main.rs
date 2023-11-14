// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::{Context, Result};
use check_cert::{checker, fetcher};
use clap::Parser;
use openssl::asn1::{Asn1Time, Asn1TimeRef};
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

fn diff_to_now(x: &Asn1TimeRef) -> i32 {
    let exp = Asn1Time::days_from_now(0).unwrap().diff(x).unwrap();
    exp.days
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();

    let warn_time = Asn1Time::days_from_now(args.warn).context("Invalid warn value")?;
    let crit_time = Asn1Time::days_from_now(args.crit).context("Invalid crit value")?;
    if warn_time < crit_time {
        eprintln!("crit limit larger than warn limit");
        std::process::exit(1);
    }

    let cert = fetcher::fetch_server_cert(
        &args.url,
        &args.port,
        if args.timeout == 0 {
            None
        } else {
            Some(Duration::new(args.timeout, 0))
        },
        !args.disable_sni,
    )?;

    match checker::check_validity(cert.not_after(), &warn_time, &crit_time) {
        checker::Validity::OK => {
            println!(
                "OK - Certificate '{}' will expire on {}",
                args.url,
                cert.not_after()
            );
            std::process::exit(0)
        }
        checker::Validity::Warn => {
            println!(
                "WARNING - Certificate '{}' expires in {} day(s) ({})",
                args.url,
                diff_to_now(cert.not_after()),
                cert.not_after()
            );
            std::process::exit(1)
        }
        checker::Validity::Crit => {
            println!(
                "CRITICAL - Certificate '{}' expires in {} day(s) ({})",
                args.url,
                diff_to_now(cert.not_after()),
                cert.not_after()
            );
            std::process::exit(2)
        }
    }
}

#[cfg(test)]
mod test_diff_to_now {
    use crate::diff_to_now;
    use openssl::asn1::Asn1Time;

    fn days_from_now(days: u32) -> Asn1Time {
        Asn1Time::days_from_now(days).unwrap()
    }

    #[test]
    fn test_diff_to_today() {
        assert!(diff_to_now(days_from_now(0).as_ref()) == 0);
    }

    #[test]
    fn test_diff_to_tomorrow() {
        assert!(diff_to_now(days_from_now(1).as_ref()) == 1);
    }
}
