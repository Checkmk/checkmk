// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use check_http::checking_types::{Bounds, UpperLevels};
use check_http::checks::{CheckParameters, TextMatcher};
use check_http::http::{self, ClientConfig, RequestConfig};
use check_http::output::Output;
use check_http::runner::collect_checks;
use clap::Parser;
use cli::Cli;
use regex::{Regex, RegexBuilder};
use reqwest::Method;

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
            body: args.body,
            auth_user: args.auth_user,
            auth_pw: args.auth_pw.auth_pw_plain.or(args.auth_pw.auth_pwstore),
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
            body_matcher: args
                .body_string
                .map(Into::into)
                .or(args.body_regex.map(|pattern| {
                    TextMatcher::from_regex(
                        regex_from_args(
                            &pattern,
                            args.body_regex_case_insensitive,
                            args.body_regex_linespan,
                        ),
                        !args.body_regex_invert,
                    )
                })),
            header_strings: args.header_strings,
        },
    )
}

fn regex_from_args(pattern: &str, case_insensitive: bool, linespan: bool) -> Regex {
    RegexBuilder::new(pattern)
        .crlf(true)
        .case_insensitive(case_insensitive)
        .multi_line(!linespan)
        .dot_matches_new_line(linespan)
        .build()
        .unwrap() //TODO(au): This would panic. Better handle this with an UNKNOWN state.
}

#[cfg(test)]
mod test_regex_from_args {
    use crate::regex_from_args;

    #[test]
    fn test_simple() {
        assert!(regex_from_args("f.*r", false, false).is_match("foobar"))
    }

    #[test]
    fn test_case_insensitive_false() {
        assert!(!regex_from_args("f.*r", false, false).is_match("foobaR"))
    }

    #[test]
    fn test_case_insensitive_true() {
        assert!(regex_from_args("f.*r", true, false).is_match("foobaR"))
    }

    #[test]
    fn test_no_linespan_true() {
        assert!(regex_from_args("^f.*r$", true, false).is_match("baz\nfoobar\nmooh"))
    }

    #[test]
    fn test_no_linespan_false() {
        assert!(!regex_from_args("f.*h", true, false).is_match("baz\nfoobar\nmooh"))
    }

    #[test]
    fn test_linespan_false() {
        assert!(!regex_from_args("^f.*r$", true, true).is_match("baz\nfoobar\nmooh"))
    }

    #[test]
    fn test_linespan_anchors_true() {
        assert!(regex_from_args("^b.*h$", true, true).is_match("baz\nfoobar\nmooh"))
    }

    #[test]
    fn test_linespan_no_anchors_true() {
        assert!(regex_from_args("f.*h", true, true).is_match("baz\nfoobar\nmooh"))
    }

    #[test]
    fn test_no_linespan_crlf() {
        assert!(regex_from_args("^f.*r$", true, false).is_match("baz\r\nfoobar\r\nmooh"))
    }

    #[test]
    fn test_no_linespan_cr() {
        assert!(regex_from_args("^f.*r$", true, false).is_match("baz\rfoobar\rmooh"))
    }

    #[test]
    fn test_unicode_no_match() {
        assert!(!regex_from_args("^foobar..baz$", true, false).is_match("foobar💩baz"))
    }

    #[test]
    fn test_unicode_match() {
        assert!(regex_from_args("^foobar.baz$", true, false).is_match("foobar🦀baz"))
    }
}
