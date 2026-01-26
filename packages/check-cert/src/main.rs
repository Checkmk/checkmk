// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Result;
use check_cert::check::{self, Levels, LevelsStrategy};
use check_cert::checker::certificate::{self, Config as CertChecks};
use check_cert::checker::fetcher::{self as fetcher_check, Config as FetcherChecks};
use check_cert::checker::info::{self, Config as InfoConfig};
use check_cert::checker::verification::{self, Config as VerifChecks};
use check_cert::fetcher::{self, Config as FetcherConfig, ProxyAuth, ProxyConfig};
use check_cert::pwstore::password_from_store;
use check_cert::truststore;
use clap::{Parser, ValueEnum};
use log::{debug, info};
use std::io::{self, Write};
use std::mem;
use std::time::Duration as StdDuration;
use std::time::Instant;
use time::Duration;

mod version;

#[allow(non_camel_case_types)]
#[allow(clippy::upper_case_acronyms)]
#[derive(Debug, Clone, ValueEnum)]
enum ClapPubKeyAlgorithm {
    RSA,
    EC,
    DSA,
    Gost_R3410,
    Gost_R3410_2012,
    Unknown,
}

impl ClapPubKeyAlgorithm {
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

fn parse_levels<F, T1, T2, U>(strat: LevelsStrategy, lvl: Vec<T1>, mut conv: F) -> Levels<U>
where
    T1: std::fmt::Debug + Clone,
    T2: std::fmt::Debug + std::convert::From<T1>,
    U: Clone + std::default::Default + std::cmp::PartialOrd + std::fmt::Debug,
    F: FnMut(T2) -> U,
{
    let lvl: [_; 2] = lvl.try_into().expect("invalid arg count");
    let lvl_orig = lvl.clone();
    let mut lvl = lvl.map(|x| conv(x.into()));
    let Ok(lvl) = Levels::try_new(
        strat.clone(),
        mem::take(&mut lvl[0]),
        mem::take(&mut lvl[1]),
    ) else {
        check::bail_out(match strat {
            LevelsStrategy::Upper => format!(
                "invalid args: WARN must be smaller than or equal to CRIT but got {:?} {:?}",
                lvl_orig[0], lvl_orig[1]
            ),
            LevelsStrategy::Lower => format!(
                "invalid args: WARN must be larger than or equal to CRIT but got {:?} {:?}",
                lvl_orig[0], lvl_orig[1]
            ),
        })
    };
    lvl
}

#[derive(Parser, Debug)]
pub struct ProxyPassword {
    /// Plain password for proxy server Basic Auth
    #[arg(long, requires = "proxy_user")]
    pub proxy_pw_plain: Option<String>,

    /// Password for proxy server Basic Auth, provided as ID for password store lookup
    #[arg(long, requires = "proxy_user", value_parser=password_from_store)]
    pub proxy_pw_pwstore: Option<String>,
}

#[derive(Parser, Debug)]
#[command(about = "check_cert", version = version::VERSION)]
struct Args {
    /// DNS resolvable hostname or IP address to be checked
    #[arg(short = 'H', long)]
    hostname: String,

    /// Port
    #[arg(short, long, default_value_t = 443)]
    port: u16,

    /// Connection type: tls, proxy_tls, smtp_starttls, postgres_starttls
    #[arg(long, default_value = "tls")]
    connection_type: fetcher::ConnectionType,

    /// Verbose output
    #[arg(short, long, action = clap::ArgAction::Count)]
    verbose: u8,

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

    /// Expected signature algorithm (OID)
    #[arg(long)]
    signature_algorithm: Option<String>,

    /// Expected public key algorithm
    #[arg(long)]
    pubkey_algorithm: Option<ClapPubKeyAlgorithm>,

    /// Expected public key size
    #[arg(long)]
    pubkey_size: Option<usize>,

    /// Certificate expiration levels in seconds [WARN CRIT]
    #[arg(long, num_args = 2)]
    not_after: Option<Vec<u32>>,

    /// Max allowed validity (difference between not_before and not_after, in days)
    #[arg(long)]
    max_validity: Option<u32>,

    /// Overall response time levels in seconds [WARN CRIT]
    #[arg(long, num_args = 2)]
    response_time: Option<Vec<f64>>,

    /// Load CA store at this location in place of the default one
    #[arg(long)]
    ca_store: Option<std::path::PathBuf>,

    /// Allow self-signed certificates
    #[arg(long, default_value_t = false, action = clap::ArgAction::SetTrue)]
    allow_self_signed: bool,

    /// Proxy server URL.
    #[arg(long, requires_if("proxy_tls", "connection_type"))]
    pub proxy_url: Option<String>,

    /// Proxy server port.
    #[arg(long, requires_if("proxy_tls", "connection_type"))]
    pub proxy_port: Option<u16>,

    /// Username for proxy server basic auth.
    #[arg(long, requires = "ProxyPassword")]
    pub proxy_user: Option<String>,

    #[command(flatten)]
    pub proxy_pw: ProxyPassword,
}

struct SimpleLogger {
    level: log::LevelFilter,
}

impl log::Log for SimpleLogger {
    fn enabled(&self, metadata: &log::Metadata) -> bool {
        metadata.level() <= self.level
    }

    fn log(&self, record: &log::Record) {
        if self.enabled(record.metadata()) {
            eprintln!("{}: {}", record.level(), record.args());
        }
    }

    fn flush(&self) {
        let _ = io::stderr().flush();
    }
}

fn init_logging(verbosity: u8) {
    let level = match verbosity {
        2.. => log::LevelFilter::Debug,
        1 => log::LevelFilter::Info,
        _ => log::LevelFilter::Warn,
    };
    log::set_boxed_logger(Box::new(SimpleLogger { level }))
        .map(|()| log::set_max_level(level))
        .unwrap_or_else(|_| eprintln!("Failed to initialize logging"));
}

fn to_pem(der: &[u8]) -> Vec<u8> {
    openssl::x509::X509::from_der(der)
        .unwrap()
        .to_pem()
        .unwrap()
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // We ran into https://github.com/sfackler/rust-openssl/issues/575
    // without openssl_probe.
    #[allow(deprecated)]
    openssl_probe::init_ssl_cert_env_vars();

    let args = Args::parse();

    init_logging(args.verbose);

    info!("start check-cert");

    let response_time = args
        .response_time
        .map(|rt| parse_levels(LevelsStrategy::Upper, rt, StdDuration::from_secs_f64));
    let not_after: Option<Levels<Duration>> = args
        .not_after
        .map(|na| parse_levels(LevelsStrategy::Lower, na, Duration::seconds));

    info!("load trust store...");
    let Ok(trust_store) = (match args.ca_store {
        Some(ca_store) => truststore::load_store(&ca_store),
        None => truststore::system(),
    }) else {
        check::abort("Failed to load trust store")
    };
    info!("loaded {} certificates", trust_store.len());

    info!("contact host...");
    let start = Instant::now();
    let connection_type = args.connection_type;

    let chain = match fetcher::fetch_server_cert(
        &args.hostname,
        args.port,
        FetcherConfig::builder()
            .timeout((args.timeout != 0).then_some(StdDuration::new(args.timeout, 0)))
            .connection_type(connection_type)
            .proxy(match (args.proxy_url, args.proxy_port) {
                (Some(proxy_url), Some(proxy_port)) => Some(
                    ProxyConfig::builder()
                        .url(proxy_url)
                        .port(proxy_port)
                        .auth(
                            match (
                                args.proxy_user,
                                args.proxy_pw.proxy_pw_plain,
                                args.proxy_pw.proxy_pw_pwstore,
                            ) {
                                (Some(proxy_user), Some(proxy_pw_plain), None) => Some(
                                    ProxyAuth::builder()
                                        .username(proxy_user)
                                        .password(proxy_pw_plain)
                                        .build(),
                                ),
                                (Some(proxy_user), None, Some(proxy_pw_pwstore)) => Some(
                                    ProxyAuth::builder()
                                        .username(proxy_user)
                                        .password(proxy_pw_pwstore)
                                        .build(),
                                ),
                                (_, _, _) => None,
                            },
                        )
                        .build(),
                ),
                (_, _) => None,
            })
            .build(),
    ) {
        Ok(chain) => chain,
        Err(err) => check::abort(format!("{:?}", err)),
    };
    let elapsed = start.elapsed();
    info!("received chain of {} certificates from host", chain.len());

    if chain.is_empty() {
        check::abort("Empty or invalid certificate chain on host")
    }

    info!("check certificate...");
    debug!(
        "\n{}",
        std::str::from_utf8(&to_pem(&chain[0])).expect("valid utf8")
    );
    info!(" 1/3 - check fetching process");
    let mut check = info::collect(
        InfoConfig::builder()
            .server(&args.hostname)
            .port(args.port)
            .build(),
    );
    check.join(&mut fetcher_check::check(
        elapsed,
        FetcherChecks::builder()
            .response_time(response_time)
            .build(),
    ));
    info!(" 2/3 - verify certificate with trust store");
    check.join(&mut verification::check(
        &chain,
        VerifChecks::builder()
            .trust_store(&trust_store)
            .allow_self_signed(args.allow_self_signed)
            .build(),
    ));
    info!(" 3/3 - check certificate");
    check.join(&mut certificate::check(
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
            .signature_algorithm(args.signature_algorithm)
            .pubkey_algorithm(args.pubkey_algorithm.map(|sig| String::from(sig.as_str())))
            .pubkey_size(args.pubkey_size)
            .not_after(not_after)
            .max_validity(args.max_validity.map(|x| Duration::days(x.into())))
            .build(),
    ));
    info!("check certificate... done");

    println!("{}", check);
    std::process::exit(check::exit_code(&check))
}
