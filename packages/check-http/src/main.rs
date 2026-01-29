// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use check_http::checking_types::{Bounds, CheckResult, LowerLevels, State, UpperLevels};
use check_http::checks::{CheckParameters, RequestInformation, TextMatcher};
use check_http::http::{self, ClientConfig, RequestConfig};
use check_http::output::Output;
use check_http::runner::collect_checks;
use clap::Parser;
use cli::Cli;
use reqwest::{tls::Version as TlsVersion, Method, Version};
use std::net::SocketAddr;
use tracing_subscriber::{
    self,
    filter::{EnvFilter, FilterFn, LevelFilter},
    fmt,
    prelude::*,
};
mod cli;
mod pwstore;
mod version;

const DEFAULT_USER_AGENT: &str = "checkmk-active-httpv2/2.6.0";

#[tokio::main]
async fn main() {
    let args = Cli::parse();

    init_tracing(args.logging_level(), args.debug_headers, args.debug_content);

    if let Err(e) = args.validate() {
        eprintln!("Error: {}", e);
        std::process::exit(3);
    }

    let (client_cfg, request_cfg, request_information, check_params) = make_configs(args);
    let output = Output::from_check_results(
        collect_checks(client_cfg, request_cfg, request_information, check_params).await,
    );
    println!("{}", output);
    std::process::exit(output.worst_state.into());
}

fn init_tracing(logging_level: LevelFilter, debug_headers: bool, debug_content: bool) {
    // General tracing/logging.
    // The directives from env and the logging_level are additive, so the RUST_LOG env var
    // and the verbosity flag can be used together.
    let env_filter = EnvFilter::builder()
        .with_default_directive(LevelFilter::OFF.into())
        .from_env_lossy()
        .add_directive(logging_level.into());

    // We want to completely filter out the headers and content debug events here...
    let exclude_headers_and_content =
        FilterFn::new(|metadata| !matches!(metadata.target(), "debug_headers" | "debug_content"));

    // ...and handle them in a separate layer with different formatting
    let headers_or_content_layer = if !debug_headers && !debug_content {
        None
    } else {
        let include_headers_or_content = FilterFn::new(move |metadata| {
            (debug_headers && metadata.target() == "debug_headers")
                || (debug_content && metadata.target() == "debug_content")
        });
        Some(
            fmt::layer()
                .with_writer(std::io::stderr)
                .with_level(false)
                .with_target(false)
                .without_time()
                .with_filter(include_headers_or_content),
        )
    };

    tracing_subscriber::registry()
        .with(
            fmt::layer()
                .with_writer(std::io::stderr)
                .with_filter(env_filter)
                .with_filter(exclude_headers_and_content),
        )
        .with(headers_or_content_layer)
        .init();
}

fn make_configs(
    args: Cli,
) -> (
    ClientConfig,
    RequestConfig,
    RequestInformation,
    CheckParameters,
) {
    let user_agent = args.user_agent.unwrap_or(DEFAULT_USER_AGENT.to_string());
    let method = args.method.unwrap_or_else(|| {
        if args.body.is_some() {
            Method::POST
        } else {
            Method::GET
        }
    });
    let onredirect = match args.onredirect {
        cli::OnRedirect::Ok => http::OnRedirect::Ok,
        cli::OnRedirect::Warning => http::OnRedirect::Warning,
        cli::OnRedirect::Critical => http::OnRedirect::Critical,
        cli::OnRedirect::Follow => http::OnRedirect::Follow,
        cli::OnRedirect::Sticky => http::OnRedirect::Sticky,
        cli::OnRedirect::Stickyport => http::OnRedirect::Stickyport,
    };

    let server: Option<SocketAddr> = match args.server.as_ref() {
        Some(server) => {
            let url = args.url.clone();
            let port = url.port().unwrap_or_else(|| match url.scheme() {
                "http" => 80,
                "https" => 443,
                scheme => {
                    let output = Output::from_check_results(vec![
                        CheckResult::summary(State::Crit, "Unsupported URL scheme").unwrap(),
                        CheckResult::details(State::Crit, scheme).unwrap(),
                    ]);
                    println!("{}", output);
                    std::process::exit(output.worst_state.into());
                }
            });

            match server.to_socket_addr(port) {
                Ok(addrs) => Some(addrs),
                Err(e) => {
                    let output = Output::from_check_results(vec![
                        CheckResult::summary(State::Crit, "Error resolving server address")
                            .unwrap(),
                        CheckResult::details(State::Crit, e.to_string().as_str()).unwrap(),
                    ]);
                    println!("{}", output);
                    std::process::exit(output.worst_state.into());
                }
            }
        }
        None => None,
    };

    (
        ClientConfig {
            version: args.http_version.clone().map(|ver| match ver {
                cli::HttpVersion::Http11 => Version::HTTP_11,
                cli::HttpVersion::Http2 => Version::HTTP_2,
            }),
            user_agent: user_agent.clone(),
            timeout: args.timeout,
            onredirect: onredirect.clone(),
            max_redirs: args.max_redirs,
            force_ip: match args.force_ip_version {
                None => None,
                Some(cli::ForceIP::Ipv4) => Some(http::ForceIP::Ipv4),
                Some(cli::ForceIP::Ipv6) => Some(http::ForceIP::Ipv6),
            },
            min_tls_version: args
                .min_tls_version
                .as_ref()
                .map(map_tls_version)
                .or(args.tls_version.as_ref().map(map_tls_version)),
            max_tls_version: args.tls_version.as_ref().map(map_tls_version),
            tls_compatibility_mode: args.tls_compatibility_mode,
            collect_tls_info: args.certificate_levels.is_some(),
            ignore_proxy_env: args.ignore_proxy_env,
            proxy_url: args.proxy_url,
            proxy_auth: if let (Some(proxy_user), Some(proxy_pw)) = (
                args.proxy_user,
                args.proxy_pw
                    .proxy_pw_plain
                    .or(args.proxy_pw.proxy_pw_pwstore),
            ) {
                Some((proxy_user, proxy_pw))
            } else {
                None
            },
            disable_certificate_verification: args.disable_certificate_verification,
            url: args.url.clone(),
            server,
        },
        RequestConfig {
            url: args.url.clone(),
            headers: args.headers,
            method: method.clone(),
            version: args.http_version.map(|ver| match ver {
                cli::HttpVersion::Http11 => Version::HTTP_11,
                cli::HttpVersion::Http2 => Version::HTTP_2,
            }),
            body: args.body,
            auth_user: args.auth_user,
            auth_pw: args.auth_pw.auth_pw_plain.or(args.auth_pw.auth_pw_pwstore),
            token_auth: if let (Some(token_header), Some(token_key)) = (
                args.token_header,
                args.token_key
                    .token_key_plain
                    .or(args.token_key.token_key_pwstore),
            ) {
                Some((token_header, token_key))
            } else {
                None
            },
            content_type: args.content_type,
            without_body: args.without_body,
        },
        RequestInformation {
            request_url: args.url,
            method,
            user_agent,
            onredirect,
            timeout: args.timeout,
            server: args.server.map(|server| server.to_string()),
        },
        CheckParameters {
            status_code: args.status_code,
            page_size: args.page_size.map(|val| match val {
                (x, None) => Bounds::lower(x),
                (x, Some(y)) => Bounds::lower_upper(x, y),
            }),
            response_time_levels: args.response_time_levels.map(|val| match val {
                (x, None) => UpperLevels::warn(x),
                (x, Some(y)) => UpperLevels::warn_crit(x, y),
            }),
            document_age_levels: args.document_age_levels.map(UpperLevels::warn),
            body_matchers: args
                .body_string
                .into_iter()
                .map(TextMatcher::Contains)
                .chain(
                    args.body_regex
                        .into_iter()
                        .map(|pattern| TextMatcher::from_regex(pattern, !args.body_regex_invert)),
                )
                .collect(),
            header_matchers: args
                .header_strings
                .into_iter()
                .map(|(name, value)| (TextMatcher::Exact(name), TextMatcher::Exact(value)))
                .chain(
                    args.header_regexes
                        .into_iter()
                        .map(|(name_pattern, value_pattern)| {
                            (
                                TextMatcher::from_regex(name_pattern, !args.header_regexes_invert),
                                TextMatcher::from_regex(value_pattern, !args.header_regexes_invert),
                            )
                        }),
                )
                .collect(),
            certificate_levels: args.certificate_levels.map(|val| match val {
                (x, None) => LowerLevels::warn(x),
                (x, Some(y)) => LowerLevels::warn_crit(x, y),
            }),
            disable_certificate_verification: args.disable_certificate_verification,
            content_search_fail_state: args
                .content_search_fail_state
                .as_ref()
                .map(map_content_search_fail_state)
                .unwrap_or(State::Crit),
        },
    )
}

fn map_tls_version(tls_version: &cli::TlsVersion) -> TlsVersion {
    match *tls_version {
        cli::TlsVersion::Tls10 => TlsVersion::TLS_1_0,
        cli::TlsVersion::Tls11 => TlsVersion::TLS_1_1,
        cli::TlsVersion::Tls12 => TlsVersion::TLS_1_2,
        cli::TlsVersion::Tls13 => TlsVersion::TLS_1_3,
    }
}

fn map_content_search_fail_state(fail_state: &cli::ContentSearchFailState) -> State {
    match *fail_state {
        cli::ContentSearchFailState::Ok => State::Ok,
        cli::ContentSearchFailState::Warning => State::Warn,
        cli::ContentSearchFailState::Critical => State::Crit,
        cli::ContentSearchFailState::Unknown => State::Unknown,
    }
}

#[cfg(test)]
mod test_regex_from_args {
    use regex::{Regex, RegexBuilder};

    // While this test module doesn't test *our* code, it tests/documents the regex
    // flags and options that we support in Checkmk Setup.
    // - "case-insensitive" maps to: (?i)
    // - "linespan" maps to the absense of the C-Style REG_NEWLINE flag, and by that to: (?s),
    //   while "!linespan" maps to: (?m)
    // - "crlf" mode is enabled by default, since we can't know which newline-character we will encounter,
    //   while /r/n is common.
    // - unicode matching is on by default, since both the pattern and the matched-on text are decoded to text/unicode internally.

    fn regex(pattern: &str) -> Regex {
        RegexBuilder::new(pattern).crlf(true).build().unwrap()
    }

    #[test]
    fn test_simple() {
        assert!(regex("(?m)f.*r").is_match("foobar"))
    }

    #[test]
    fn test_case_insensitive_false() {
        assert!(!regex("(?m)f.*r").is_match("foobaR"))
    }

    #[test]
    fn test_case_insensitive_true() {
        assert!(regex("(?mi)f.*r").is_match("foobaR"))
    }

    #[test]
    fn test_no_linespan_true() {
        assert!(regex("(?m)^f.*r$").is_match("baz\nfoobar\nmooh"))
    }

    #[test]
    fn test_no_linespan_false() {
        assert!(!regex("(?m)f.*h").is_match("baz\nfoobar\nmooh"))
    }

    #[test]
    fn test_linespan_false() {
        assert!(!regex("(?s)^f.*r$").is_match("baz\nfoobar\nmooh"))
    }

    #[test]
    fn test_linespan_anchors_true() {
        assert!(regex("(?s)^b.*h$").is_match("baz\nfoobar\nmooh"))
    }

    #[test]
    fn test_linespan_no_anchors_true() {
        assert!(regex("(?s)f.*h").is_match("baz\nfoobar\nmooh"))
    }

    #[test]
    fn test_no_linespan_crlf() {
        assert!(regex("(?m)^f.*r$").is_match("baz\r\nfoobar\r\nmooh"))
    }

    #[test]
    fn test_no_linespan_cr() {
        assert!(regex("(?m)^f.*r$").is_match("baz\rfoobar\rmooh"))
    }

    #[test]
    fn test_unicode_no_match() {
        assert!(!regex("(?m)^foobar..baz$").is_match("foobar💩baz"))
    }

    #[test]
    fn test_unicode_match() {
        assert!(regex("(?m)^foobar.baz$").is_match("foobar🦀baz"))
    }
}
