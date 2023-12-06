// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::pwstore;
use anyhow::{bail, Result as AnyhowResult};
use clap::{Args, Parser, ValueEnum};
use regex::{Regex, RegexBuilder};
use reqwest::{
    header::{HeaderName, HeaderValue},
    Method, StatusCode,
};
use std::{str::FromStr, time::Duration};

#[derive(Parser, Debug)]
#[command(about = "check_http")]
pub struct Cli {
    /// Username for HTTP Basic Auth
    #[arg(long)]
    pub auth_user: Option<String>,

    #[command(flatten)]
    pub auth_pw: AuthPw,

    /// Additional header in the form NAME:VALUE. Use multiple times for additional headers.
    #[arg(short = 'k', long="header", value_parser=split_header::<HeaderName, HeaderValue>)]
    pub headers: Option<Vec<(HeaderName, HeaderValue)>>,

    /// URL to check
    #[arg(short, long)]
    pub url: String,

    /// URL version to use for the request.
    /// If not set, start with HTTP/1.1 and upgrade to HTTP/2 if supported by the server.
    /// If set to "http11", send the request with HTTP/1.1 without HTTP/2 upgrade.
    /// If set to "http2", send the request with HTTP/2.
    /// Note: While HTTP/2 without TLS (h2c) is theoretically available, it's de facto
    /// unsupported by common server software, so sending a HTTP/2 request
    /// without TLS will most likely fail.
    #[arg(long)]
    pub http_version: Option<HttpVersion>,

    /// Set timeout in seconds
    #[arg(short, long, default_value = "10", value_parser=parse_seconds)]
    pub timeout: Duration,

    /// Wait for document body
    #[arg(long, default_value_t = false)]
    pub without_body: bool,

    /// Set user-agent
    #[arg(long)]
    pub user_agent: Option<String>,

    /// Set HTTP method. If no body text is specified with --body, this defaults to GET,
    /// otherwise to POST.
    #[arg(short = 'j', long)]
    pub method: Option<Method>,

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
    #[arg(long, conflicts_with = "without_body", value_parser = parse_optional_pair::<usize>)]
    pub page_size: Option<PageSizeLimits>,

    /// WARN/CRIT levels for response time (Format: WARN>[,CRIT])
    #[arg(long, value_parser = parse_optional_pair::<f64>)]
    pub response_time_levels: Option<ResponseTimeLevels>,

    /// WARN level for document age
    /// If document age is not set, setting this option will also lead to state CRIT
    #[arg(long)]
    pub document_age_levels: Option<u64>,

    /// Text to send in HTTP body. This will set the HTTP method to POST if unset,
    /// but will not overwrite the method specified with --method.
    /// Also, no encoding (like url-encoding) will be applied.
    #[arg(long)]
    pub body: Option<String>,

    /// Specify Content-Type header when sending HTTP body.
    /// This does not encode the specified body text automatically.
    #[arg(short = 'T', long, requires = "body")]
    pub content_type: Option<HeaderValue>,

    /// String(s) to expect in the response body.
    /// Specify multiple times for additional search strings.
    #[arg(short = 's', long, conflicts_with = "without_body")]
    pub body_string: Vec<String>,

    /// Regular expression(s) to expect in the response body.
    /// Specify multiple times for regexes.
    /// Inline flags with "(?...)" are supported.
    /// E.g., "(?im)^myregexpattern" will match case-insensitively,
    /// and the caret will match on every beginning line.
    /// Regexes with more than O(len(pattnern)*len(text)) complexity,
    /// like backreferences and lookaround, are unsupported.
    #[arg(
        short = 'r',
        long,
        conflicts_with = "body_string",
        conflicts_with = "without_body",
        value_parser = parse_regex_pattern,
    )]
    pub body_regex: Vec<Regex>,

    /// Expect the specified regex to *not* match on the body.
    #[arg(long, requires = "body_regex", default_value_t = false)]
    pub body_regex_invert: bool,

    /// Strings to expect in the headers. Format: [KEY]:[VALUE]
    /// Specify multiple times for additional headers.
    /// It's possible to only specify key or value, but a (first) separating colon is
    /// mandatory to identify them.
    /// Keys are matched case-insensitive and may only contain ASCII characters.
    /// Values are matched case-sensitive. If they contain non-ASCII characters,
    /// they are expected to be latin-1
    #[arg(short = 'd', long, value_parser=parse_string_header_pair)]
    pub header_strings: Vec<(String, String)>,

    /// Regular expressions to expect in the HTTP headers. Format: [KEY]:[VALUE]
    /// Again, the first colon will be recognized as the KEY-VALUE separator, so
    /// a colon is not allowed in the KEY part of the regex specification.
    /// The same rules as for the body regex apply, while key and value are taken as two separate
    /// regex patterns.
    /// Also note that case-insensitive matching is enabled for the the header name part by default,
    /// and flags affecting newlines would have no effect, since newlines are not allowed within headers
    #[arg(long, conflicts_with = "header_strings", value_parser = parse_regex_pattern_header_pair)]
    pub header_regexes: Vec<(Regex, Regex)>,

    /// Expect the specified regexes to *not* match on the headers.
    #[arg(long, requires = "header_regexes", default_value_t = false)]
    pub header_regexes_invert: bool,

    /// Expected HTTP status code.
    /// Note: Avoid setting this to a 3xx code while setting "--onredirect=warning/critical"
    #[arg(short = 'e', long)]
    pub status_code: Option<StatusCode>,

    /// Use TLS version for HTTPS requests.
    /// Not relevant for HTTP connections without TLS.
    #[arg(short = 'S', long)]
    pub tls_version: Option<TlsVersion>,

    /// Set minimum accepted TLS version for HTTPS requests.
    /// Not relevant for HTTP connections without TLS.
    #[arg(long, conflicts_with = "tls_version")]
    pub min_tls_version: Option<TlsVersion>,
}

type PageSizeLimits = (usize, Option<usize>);
type ResponseTimeLevels = (f64, Option<f64>);

// Only support HTTP/1.1 and HTTP/2 for now.
// HTTP/0.9 is deprecated for over two decades, and while it's settable,
// reqwest technically doesn't support it and refuses to execute the
// request.
// Same goes for HTTP/1.0. While the request doesn't fail, it's still sent
// with virtual host header, so it's technically a HTTP/1.1 request.
// Supporting these would require changing the HTTP backend.
#[derive(Clone, Debug, ValueEnum)]
pub enum HttpVersion {
    Http11,
    Http2,
}

#[derive(Clone, Debug, ValueEnum)]
pub enum TlsVersion {
    Tls10,
    Tls11,
    Tls12,
    Tls13,
}

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
    #[arg(long, requires = "auth_user")]
    pub auth_pw_plain: Option<String>,

    /// Password for HTTP Basic Auth, provided as ID for password store lookup
    #[arg(long, requires = "auth_user", value_parser=pwstore::password_from_store)]
    pub auth_pwstore: Option<String>,
}

fn split_header<T, U>(header: &str) -> AnyhowResult<(T, U)>
where
    T: FromStr,
    T::Err: 'static + std::error::Error + std::marker::Send + std::marker::Sync,
    U: FromStr,
    U::Err: 'static + std::error::Error + std::marker::Send + std::marker::Sync,
{
    let Some((name, value)) = header.split_once(':') else {
        bail!("Invalid HTTP header: {} (missing ':')", header);
    };
    Ok((name.trim().parse()?, value.trim().parse()?))
}

fn parse_string_header_pair(header_pair: &str) -> AnyhowResult<(String, String)> {
    let (name, value): (String, String) = split_header(header_pair)?;

    Ok((
        // HeaderNames have some properties and requirements (case insensitive, only ASCII).
        // Instead of checking and formatting manually, we convert to HeaderName and back.
        // But we want to allow an empty name.
        if name.is_empty() {
            name
        } else {
            HeaderName::from_str(&name)?.to_string()
        },
        // We leave the value string unchecked:
        // HeaderValues, while they *should* only contain ASCII chars, are allowed to be
        // ISO-8859-1 ("latin-1") encoded, and are even ophaque bytes in general.
        // By that, it makes sense to search for arbitrary text in the latin-1-decoded
        // HeaderValue text, as this also includes ASCII. Characters that can't be encoded in
        // latin-1 can't be found in a latin-1 HeaderValue, but thats rather a problem of the
        // caller than invalid input.
        value,
    ))
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

fn parse_regex_pattern_header_pair(pattern_pair: &str) -> AnyhowResult<(String, String)> {
    let (name, value): (String, String) = split_header(pattern_pair)?;
    RegexBuilder::new(&name).case_insensitive(true).build()?;
    Regex::new(&value)?;
    Ok((name, value))
}

fn parse_regex_pattern(pattern: &str) -> Result<String, regex::Error> {
    RegexBuilder::new(pattern).crlf(true).build()?;
    Ok(pattern.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use clap::CommandFactory;
    use http::{HeaderName, HeaderValue};
    use std::str::FromStr;

    fn split_header(header: &str) -> AnyhowResult<(HeaderName, HeaderValue)> {
        super::split_header(header)
    }

    #[test]
    fn verify_cli() {
        Cli::command().debug_assert()
    }

    #[test]
    fn test_split_header() {
        assert!(split_header(":value").is_err());
        assert!(split_header("name value").is_err());
        assert!(split_header("name:some\r\nvalue").is_err());
        assert!(split_header("näme:some\r\nvalue").is_err());
        assert_eq!(
            split_header("name:value").unwrap(),
            (
                HeaderName::from_str("name").unwrap(),
                HeaderValue::from_str("value").unwrap()
            )
        );
        assert_eq!(
            split_header("name:valüe").unwrap(),
            (
                HeaderName::from_str("name").unwrap(),
                HeaderValue::from_str("valüe").unwrap()
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

    #[test]
    fn test_parse_header_pair() {
        assert!(split_header("name value").is_err());
        assert!(split_header("name:some\r\nvalue").is_err());
        assert!(split_header("näme:value").is_err());
        assert_eq!(
            parse_string_header_pair(":value").unwrap(),
            ("".to_string(), "value".to_string())
        );
        assert_eq!(
            parse_string_header_pair("name:").unwrap(),
            ("name".to_string(), "".to_string())
        );
        assert_eq!(
            parse_string_header_pair("NaMe:VaLüE").unwrap(),
            ("name".to_string(), "VaLüE".to_string())
        );
    }
}
