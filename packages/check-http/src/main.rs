// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use check_http::checking_types::{Bounds, LowerLevels, UpperLevels};
use check_http::checks::{CheckParameters, TextMatcher};
use check_http::http::{self, ClientConfig, RequestConfig};
use check_http::output::Output;
use check_http::runner::collect_checks;
use clap::Parser;
use cli::Cli;
use reqwest::{tls::Version as TlsVersion, Method, Version};

mod cli;
mod pwstore;

const DEFAULT_USER_AGENT: &str = "Checkmk/check_http";

#[tokio::main]
async fn main() {
    let args = Cli::parse();
    let (client_cfg, request_cfg, check_params) = make_configs(args);
    let output =
        Output::from_check_results(collect_checks(client_cfg, request_cfg, check_params).await);
    println!("{}", output);
    std::process::exit(output.worst_state.into());
}

fn make_configs(args: Cli) -> (ClientConfig, RequestConfig, CheckParameters) {
    (
        ClientConfig {
            version: args.http_version.clone().map(|ver| match ver {
                cli::HttpVersion::Http11 => Version::HTTP_11,
                cli::HttpVersion::Http2 => Version::HTTP_2,
            }),
            user_agent: args.user_agent.unwrap_or(DEFAULT_USER_AGENT.to_string()),
            timeout: args.timeout,
            onredirect: match args.onredirect {
                cli::OnRedirect::Ok => http::OnRedirect::Ok,
                cli::OnRedirect::Warning => http::OnRedirect::Warning,
                cli::OnRedirect::Critical => http::OnRedirect::Critical,
                cli::OnRedirect::Follow => http::OnRedirect::Follow,
                cli::OnRedirect::Sticky => http::OnRedirect::Sticky,
                cli::OnRedirect::Stickyport => http::OnRedirect::Stickyport,
            },
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
            collect_tls_info: args.certificate_levels.is_some(),
        },
        RequestConfig {
            url: args.url,
            headers: args.headers,
            method: args.method.unwrap_or_else(|| {
                if args.body.is_some() {
                    Method::POST
                } else {
                    Method::GET
                }
            }),
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
        CheckParameters {
            onredirect: match args.onredirect {
                cli::OnRedirect::Ok => http::OnRedirect::Ok,
                cli::OnRedirect::Warning => http::OnRedirect::Warning,
                cli::OnRedirect::Critical => http::OnRedirect::Critical,
                cli::OnRedirect::Follow => http::OnRedirect::Follow,
                cli::OnRedirect::Sticky => http::OnRedirect::Sticky,
                cli::OnRedirect::Stickyport => http::OnRedirect::Stickyport,
            },
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
            timeout: args.timeout,
            body_matchers: args
                .body_string
                .into_iter()
                .map(Into::into)
                .chain(
                    args.body_regex
                        .into_iter()
                        .map(|pattern| TextMatcher::from_regex(pattern, !args.body_regex_invert)),
                )
                .collect(),
            header_matchers: args
                .header_strings
                .into_iter()
                .map(|(name, value)| (name.into(), value.into()))
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
