// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::pwstore;
use anyhow::{anyhow, Result as AnyhowResult};
use clap::{Args, Parser, ValueEnum};
use http::{HeaderName, HeaderValue, Method};
use std::{str::FromStr, time::Duration};

#[derive(Parser, Debug)]
#[command(about = "check_http")]
pub struct Cli {
    /// Username for HTTP Basic Auth
    #[arg(long, group = "authuser")]
    pub auth_user: Option<String>,

    #[command(flatten)]
    pub auth_pw: AuthPw,

    /// Additional header in the form NAME:VALUE. Use multiple times for additional headers.
    #[arg(short = 'k', long="header", value_parser=split_header)]
    pub headers: Option<Vec<(HeaderName, HeaderValue)>>,

    /// URL to check
    #[arg(short, long)]
    pub url: String,

    /// Set timeout in seconds
    #[arg(short, long, default_value = "10", value_parser=parse_seconds)]
    pub timeout: Duration,

    /// Wait for document body
    #[arg(long, default_value_t = false)]
    pub without_body: bool,

    /// Set user-agent
    #[arg(long)]
    pub user_agent: Option<HeaderValue>,

    /// Set HTTP method. Default: GET
    #[arg(short='j', long, default_value_t=Method::GET)]
    pub method: Method,

    /// How to handle redirected pages. sticky is like follow but stick to the
    /// specified IP address. stickyport also ensures port stays the same.
    #[arg(short = 'f', long, default_value = "follow")]
    pub onredirect: OnRedirect,

    /// Maximal number of redirects
    #[arg(long, default_value_t = 15)]
    pub max_redirs: usize,

    /// Force IP version for connection
    #[arg(long)]
    pub force_ip_version: Option<ForceIP>,

    /// Minimum/Maximum expected page size in bytes (Format: MIN[,MAX])
    #[arg(long, value_parser = parse_optional_pair::<usize>)]
    pub page_size: Option<PageSizeLimits>,

    /// WARN/CRIT levels for response time (Format: WARN>[,CRIT])
    #[arg(long, value_parser = parse_optional_pair::<f64>)]
    pub response_time_levels: Option<ResponseTimeLevels>,

    /// WARN/CRIT levels for document age (Format: WARN>[,CRIT])
    /// If document age is not set, setting this option will also lead to state CRIT
    #[arg(long, value_parser = parse_optional_pair::<u64>)]
    pub document_age_levels: Option<DocumentAgeLevels>,
}

pub type PageSizeLimits = (usize, Option<usize>);
pub type ResponseTimeLevels = (f64, Option<f64>);
pub type DocumentAgeLevels = (u64, Option<u64>);

#[derive(Clone, Debug, ValueEnum)]
pub enum OnRedirect {
    Ok,
    Warning,
    Critical,
    Follow,
    Sticky,
    Stickyport,
}

#[derive(Clone, Debug, ValueEnum)]
pub enum ForceIP {
    Ipv4,
    Ipv6,
}

#[derive(Args, Debug)]
#[group(multiple = false)]
pub struct AuthPw {
    /// Plain password for HTTP Basic Auth
    #[arg(long, requires = "authuser")]
    pub auth_pw_plain: Option<String>,

    /// Password for HTTP Basic Auth, provided as ID for password store lookup
    #[arg(long, requires = "authuser", value_parser=pwstore::password_from_store)]
    pub auth_pwstore: Option<String>,
}

fn split_header(header: &str) -> AnyhowResult<(HeaderName, HeaderValue)> {
    let Some((name, value)) = header.split_once(':') else {
        return Err(anyhow!("Invalid HTTP header: {} (missing ':')", header));
    };
    Ok((name.trim().parse()?, value.trim().parse()?))
}

fn parse_seconds(secs: &str) -> AnyhowResult<Duration> {
    Ok(Duration::from_secs(secs.parse()?))
}

fn parse_optional_pair<T>(input: &str) -> AnyhowResult<(T, Option<T>)>
where
    T: FromStr,
    T::Err: 'static + std::error::Error + std::marker::Send + std::marker::Sync,
{
    match input.split_once(',') {
        Some((a, b)) => Ok((a.parse()?, Some(b.parse()?))),
        None => Ok((input.parse()?, None)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use clap::CommandFactory;
    use http::{HeaderName, HeaderValue};
    use std::str::FromStr;

    #[test]
    fn verify_cli() {
        Cli::command().debug_assert()
    }

    #[test]
    fn test_split_header() {
        assert!(split_header(":value").is_err());
        assert!(split_header("name value").is_err());
        assert!(split_header("name:some\r\nvalue").is_err());
        assert_eq!(
            split_header("name:value").unwrap(),
            (
                HeaderName::from_str("name").unwrap(),
                HeaderValue::from_str("value").unwrap()
            )
        );
        assert_eq!(
            split_header("name:").unwrap(),
            (
                HeaderName::from_str("name").unwrap(),
                HeaderValue::from_str("").unwrap()
            )
        );
        assert_eq!(
            split_header("name  :  value  ").unwrap(),
            (
                HeaderName::from_str("name").unwrap(),
                HeaderValue::from_str("value").unwrap()
            )
        );
    }
}
