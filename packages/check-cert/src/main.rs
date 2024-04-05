// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Result;
use check_cert::check::{self, Levels, LevelsChecker, LevelsStrategy};
use check_cert::checker::certificate::{self, Config as CertChecks};
use check_cert::checker::fetcher::{self as fetcher_check, Config as FetcherChecks};
use check_cert::checker::verification::{self, Config as VerifChecks};
use check_cert::fetcher::{self, Config as FetcherConfig};
use check_cert::truststore;
use clap::{Parser, ValueEnum};
use std::time::Duration as StdDuration;
use time::{Duration, Instant};

#[allow(non_camel_case_types)]
#[allow(clippy::upper_case_acronyms)]
#[derive(Debug, Clone, ValueEnum)]
enum SignatureAlgorithm {
    RSA,
    RSASSA_PSS,
    RSAAES_OAEP,
    DSA,
    ECDSA,
    ED25519,
}

impl SignatureAlgorithm {
    fn as_str(&self) -> &'static str {
        match self {
            Self::RSA => "RSA",
            Self::RSASSA_PSS => "RSASSA_PSS",
            Self::RSAAES_OAEP => "RSAAES_OAEP",
            Self::DSA => "DSA",
            Self::ECDSA => "ECDSA",
            Self::ED25519 => "ED25519",
        }
    }
}

#[allow(non_camel_case_types)]
#[allow(clippy::upper_case_acronyms)]
#[derive(Debug, Clone, ValueEnum)]
enum PubKeyAlgorithm {
    RSA,
    EC,
    DSA,
    Gost_R3410,
    Gost_R3410_2012,
    Unknown,
}

impl PubKeyAlgorithm {
    fn as_str(&self) -> &'static str {
        match self {
            Self::RSA => "RSA",
            Self::EC => "EC",
            Self::DSA => "DSA",
            Self::Gost_R3410 => "GostR3410",
            Self::Gost_R3410_2012 => "GostR3410_2012",
            Self::Unknown => "Unknown",
        }
    }
}

fn parse_levels<F, T1, T2, U>(strat: LevelsStrategy, lvl: Vec<T1>, mut conv: F) -> LevelsChecker<U>
where
    T1: std::fmt::Debug,
    T2: std::fmt::Debug + std::convert::From<T1>,
    U: Clone + std::default::Default + std::cmp::PartialOrd,
    F: FnMut(T2) -> U,
{
    let lvl: [_; 2] = lvl.try_into().expect("invalid arg count");
    let Ok(lvl_chk) = LevelsChecker::try_new(strat, Levels::from(&mut lvl.map(|x| conv(x.into()))))
    else {
        check::bail_out("invalid args")
    };
    lvl_chk
}

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
    serial: Option<String>,

    /// Expected subject common name (CN)
    #[arg(long)]
    subject_cn: Option<String>,

    /// Expected subject alternative name (DNS names only)
    #[arg(long, num_args = 0..)]
    subject_alt_names: Option<Vec<String>>,

    /// Expected subject organization (O)
    #[arg(long)]
    subject_o: Option<String>,

    /// Expected subject organizational unit (OU)
    #[arg(long)]
    subject_ou: Option<String>,

    /// Expected issuer common name (CN)
    #[arg(long)]
    issuer_cn: Option<String>,

    /// Expected issuer organization (O)
    #[arg(long)]
    issuer_o: Option<String>,

    /// Expected issuer organizational unit (OU)
    #[arg(long)]
    issuer_ou: Option<String>,

    /// Expected issuer state or province (ST)
    #[arg(long)]
    issuer_st: Option<String>,

    /// Expected issuer country (C)
    #[arg(long)]
    issuer_c: Option<String>,

    /// Expected signature algorithm
    #[arg(long)]
    signature_algorithm: Option<SignatureAlgorithm>,

    /// Expected public key algorithm
    #[arg(long)]
    pubkey_algorithm: Option<PubKeyAlgorithm>,

    /// Expected public key size
    #[arg(long)]
    pubkey_size: Option<usize>,

    /// Certificate expiration levels in days [WARN:CRIT]
    #[arg(long, num_args = 2, value_delimiter = ':', default_value = "30:0")]
    not_after: Vec<u32>,

    /// Max allowed validity (difference between not_before and not_after, in days)
    #[arg(long)]
    max_validity: Option<u32>,

    /// Response time levels in milliseconds [WARN:CRIT]
    #[arg(
        long,
        num_args = 2,
        value_delimiter = ':',
        default_value = "60000:90000"
    )]
    response_time: Vec<u32>,

    /// Load CA store at this location in place of the default one
    #[arg(long)]
    ca_store: Option<std::path::PathBuf>,

    /// Allow self-signed certificates
    #[arg(long, default_value_t = false, action = clap::ArgAction::SetTrue)]
    allow_self_signed: bool,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // We ran into https://github.com/sfackler/rust-openssl/issues/575
    // without openssl_probe.
    openssl_probe::init_ssl_cert_env_vars();

    let args = Args::parse();

    let not_after = parse_levels(LevelsStrategy::Lower, args.not_after, Duration::days);
    let response_time = parse_levels(
        LevelsStrategy::Upper,
        args.response_time,
        Duration::milliseconds,
    );

    let Ok(trust_store) = (match args.ca_store {
        Some(ca_store) => truststore::load_store(&ca_store),
        None => truststore::system(),
    }) else {
        check::abort("Failed to load trust store")
    };

    let start = Instant::now();
    let chain = match fetcher::fetch_server_cert(
        &args.url,
        args.port,
        FetcherConfig::builder()
            .timeout((args.timeout != 0).then_some(StdDuration::new(args.timeout, 0)))
            .build(),
    ) {
        Ok(chain) => chain,
        Err(err) => check::abort(format!("{:?}", err)),
    };
    let elapsed = start.elapsed();

    if chain.is_empty() {
        check::abort("Empty or invalid certificate chain on host")
    }

    let mut collection = fetcher_check::check(
        elapsed,
        FetcherChecks::builder()
            .response_time(Some(response_time))
            .build(),
    );
    collection.join(&mut verification::check(
        &chain,
        VerifChecks::builder()
            .trust_store(&trust_store)
            .allow_self_signed(args.allow_self_signed)
            .build(),
    ));
    collection.join(&mut certificate::check(
        &chain[0],
        CertChecks::builder()
            .serial(args.serial)
            .subject_cn(args.subject_cn)
            .subject_alt_names(args.subject_alt_names)
            .subject_o(args.subject_o)
            .subject_ou(args.subject_ou)
            .issuer_cn(args.issuer_cn)
            .issuer_o(args.issuer_o)
            .issuer_ou(args.issuer_ou)
            .issuer_st(args.issuer_st)
            .issuer_c(args.issuer_c)
            .signature_algorithm(
                args.signature_algorithm
                    .map(|sig| String::from(sig.as_str())),
            )
            .pubkey_algorithm(args.pubkey_algorithm.map(|sig| String::from(sig.as_str())))
            .pubkey_size(args.pubkey_size)
            .not_after(Some(not_after))
            .max_validity(args.max_validity.map(|x| Duration::days(x.into())))
            .build(),
    ));

    println!("{}", collection);
    std::process::exit(check::exit_code(&collection))
}
