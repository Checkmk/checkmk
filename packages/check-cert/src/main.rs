// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Result;
use check_cert::check::{Levels, LevelsChecker, LevelsStrategy, SimpleCheckResult, Writer};
use check_cert::{checker, fetcher};
use clap::Parser;
use std::time::Duration as StdDuration;
use time::{Duration, Instant};
use x509_parser::certificate::X509Certificate;
use x509_parser::prelude::FromDer;

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

    /// Expected serial
    #[arg(long)]
    pub serial: Option<String>,

    /// Expected subject
    #[arg(long)]
    pub subject: Option<String>,

    /// Expected issuer
    #[arg(long)]
    pub issuer: Option<String>,

    /// Certificate expiration levels in days [WARN:CRIT]
    #[arg(long, num_args = 2, value_delimiter = ':', default_value = "30:0")]
    not_after: Vec<u32>,

    /// Response time levels in milliseconds [WARN:CRIT]
    #[arg(
        long,
        num_args = 2,
        value_delimiter = ':',
        default_value = "60000:90000"
    )]
    response_time: Vec<u32>,

    /// Disable SNI extension
    #[arg(long, action = clap::ArgAction::SetTrue)]
    disable_sni: bool,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();

    let Ok(not_after_levels) = LevelsChecker::try_new(
        LevelsStrategy::Lower,
        Levels::from(
            &mut args
                .not_after
                .try_into()
                .expect("invalid arg count for not_after"),
        )
        .map(&|v| v * Duration::DAY),
    ) else {
        Writer::bail_out("invalid args: not after crit level larger than warn");
    };

    let Ok(response_time_levels) = LevelsChecker::try_new(
        LevelsStrategy::Upper,
        Levels::from(
            &mut args
                .response_time
                .try_into()
                .expect("invalid arg count for response_time"),
        )
        .map(&|v| v * Duration::MILLISECOND),
    ) else {
        Writer::bail_out("invalid args: response time crit higher than warn");
    };

    let start = Instant::now();
    let der = fetcher::fetch_server_cert(
        &args.url,
        &args.port,
        if args.timeout == 0 {
            None
        } else {
            Some(StdDuration::new(args.timeout, 0))
        },
        !args.disable_sni,
    )?;
    let response_time = start.elapsed();

    let (_rem, cert) = X509Certificate::from_der(&der)?;
    let out = Writer::from(&vec![
        SimpleCheckResult::from_levels(
            &response_time_levels,
            &response_time,
            format!(
                "Certificate obtained in {} ms",
                response_time.whole_milliseconds()
            ),
        )
        .into(),
        checker::check_details_serial(cert.tbs_certificate.raw_serial_as_string(), args.serial)
            .unwrap_or_default()
            .into(),
        checker::check_details_subject(cert.tbs_certificate.subject(), args.subject)
            .unwrap_or_default()
            .into(),
        checker::check_details_issuer(cert.tbs_certificate.issuer(), args.issuer)
            .unwrap_or_default()
            .into(),
        checker::check_validity_not_after(
            cert.tbs_certificate.validity().time_to_expiration(),
            not_after_levels,
            cert.tbs_certificate.validity().not_after,
        )
        .into(),
    ]);
    println!("HTTP {}", out);
    out.bye()
}
