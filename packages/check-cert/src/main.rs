// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::{Context, Result};
use clap::Parser;
use openssl::asn1::{Asn1Time, Asn1TimeRef};
use openssl::ssl::{SslConnector, SslMethod, SslVerifyMode};
use openssl::x509::X509;
use std::net::TcpStream;

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

fn fetch_server_cert(server: &str, port: &u16) -> Result<X509> {
    let stream = TcpStream::connect(format!("{server}:{port}"))?;
    let mut connector_builder = SslConnector::builder(SslMethod::tls())?;
    connector_builder.set_verify(SslVerifyMode::NONE);
    let mut stream = connector_builder.build().connect(server, stream)?;

    let cert = stream
        .ssl()
        .peer_cert_chain()
        .context("Failed fetching peer cert chain")?
        .iter()
        .next()
        .context("Failed unpacking peer cert chain")?
        .to_owned();
    stream.shutdown()?;
    Ok(cert)
}

#[derive(PartialEq, Eq)]
enum Validity {
    OK,
    Warn,
    Crit,
}

fn check_validity(x: &Asn1TimeRef, warn: &Asn1Time, crit: &Asn1Time) -> Validity {
    std::assert!(warn >= crit);

    if crit >= x {
        Validity::Crit
    } else if warn >= x {
        Validity::Warn
    } else {
        Validity::OK
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();

    let warn_time = Asn1Time::days_from_now(args.warn).context("Invalid warn value")?;
    let crit_time = Asn1Time::days_from_now(args.crit).context("Invalid crit value")?;
    if warn_time < crit_time {
        eprintln!("crit limit larger than warn limit");
        std::process::exit(1);
    }

    let cert = fetch_server_cert(&args.url, &args.port)?;
    match check_validity(cert.not_after(), &warn_time, &crit_time) {
        Validity::OK => println!("OK!"),
        Validity::Warn => println!("WARN!"),
        Validity::Crit => println!("CRIT!"),
    }
    Ok(())
}

#[cfg(test)]
mod test_check_validity {
    use crate::{check_validity, Validity};
    use openssl::asn1::Asn1Time;

    fn days_from_now(days: u32) -> Asn1Time {
        Asn1Time::days_from_now(days).unwrap()
    }

    #[test]
    fn test_check_validity_ok() {
        assert!(
            check_validity(
                days_from_now(30).as_ref(),
                &days_from_now(0),
                &days_from_now(0),
            ) == Validity::OK
        );
        assert!(
            check_validity(
                days_from_now(30).as_ref(),
                &days_from_now(15),
                &days_from_now(7),
            ) == Validity::OK
        );
    }

    #[test]
    fn test_check_validity_warn() {
        assert!(
            check_validity(
                days_from_now(10).as_ref(),
                &days_from_now(15),
                &days_from_now(7),
            ) == Validity::Warn
        );
    }

    #[test]
    fn test_check_validity_crit() {
        assert!(
            check_validity(
                days_from_now(3).as_ref(),
                &days_from_now(15),
                &days_from_now(7),
            ) == Validity::Crit
        );
        assert!(
            check_validity(
                days_from_now(3).as_ref(),
                &days_from_now(15),
                &days_from_now(15),
            ) == Validity::Crit
        );
    }
}
