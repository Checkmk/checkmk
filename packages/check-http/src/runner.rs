// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::cli;
use std::time::Instant;

use crate::checking;
use crate::checking::{Bounds, CheckResult, Limits, State};
use crate::http;
use crate::redirect;
use std::time::Duration;

pub async fn collect_checks(args: cli::Cli) -> Vec<CheckResult> {
    let Ok(request) = http::prepare_request(
        args.url,
        args.method,
        args.user_agent,
        args.headers,
        args.timeout,
        args.auth_user,
        args.auth_pw.auth_pw_plain.or(args.auth_pw.auth_pwstore),
        match args.onredirect {
            cli::OnRedirect::Ok => redirect::OnRedirect::Ok,
            cli::OnRedirect::Warning => redirect::OnRedirect::Warning,
            cli::OnRedirect::Critical => redirect::OnRedirect::Critical,
            cli::OnRedirect::Follow => redirect::OnRedirect::Follow,
            cli::OnRedirect::Sticky => redirect::OnRedirect::Sticky,
            cli::OnRedirect::Stickyport => redirect::OnRedirect::Stickyport,
        },
        args.max_redirs,
        match args.force_ip_version {
            None => None,
            Some(cli::ForceIP::Ipv4) => Some(redirect::ForceIP::Ipv4),
            Some(cli::ForceIP::Ipv6) => Some(redirect::ForceIP::Ipv6),
        },
    ) else {
        return vec![CheckResult {
            state: State::Unknown,
            summary: "Error building the request".to_string(),
        }];
    };

    let now = Instant::now();
    let response = match http::perform_request(request, args.without_body).await {
        Ok(resp) => resp,
        Err(err) => {
            if err.is_timeout() {
                return vec![CheckResult {
                    state: State::Crit,
                    summary: "timeout".to_string(),
                }];
            } else if err.is_connect() {
                return vec![CheckResult {
                    state: State::Crit,
                    summary: "Failed to connect".to_string(),
                }];
            } else if err.is_redirect() {
                return vec![CheckResult {
                    state: State::Crit,
                    summary: err.to_string(),
                }];
            // Hit one of max_redirs, sticky, stickyport
            } else {
                return vec![CheckResult {
                    state: State::Unknown,
                    summary: "Error while sending request".to_string(),
                }];
            }
        }
    };
    let elapsed = now.elapsed();

    vec![
        checking::check_status(
            response.status,
            response.version,
            match args.onredirect {
                cli::OnRedirect::Ok => redirect::OnRedirect::Ok,
                cli::OnRedirect::Warning => redirect::OnRedirect::Warning,
                cli::OnRedirect::Critical => redirect::OnRedirect::Critical,
                cli::OnRedirect::Follow => redirect::OnRedirect::Follow,
                cli::OnRedirect::Sticky => redirect::OnRedirect::Sticky,
                cli::OnRedirect::Stickyport => redirect::OnRedirect::Stickyport,
            },
        ),
        checking::check_body(
            response.body,
            match args.page_size {
                None => Bounds::None,
                Some((x, None)) => Bounds::Lower(x),
                Some((x, Some(y))) => Bounds::LowerUpper(x, y),
            },
        ),
        checking::check_response_time(
            elapsed,
            match args.response_time_levels {
                None => Limits::None,
                Some((x, None)) => Limits::Warn(Duration::from_secs_f64(x)),
                Some((x, Some(y))) => {
                    Limits::WarnCrit(Duration::from_secs_f64(x), Duration::from_secs_f64(y))
                }
            },
        ),
        checking::check_document_age(&response.headers, args.document_age_levels),
    ]
    .into_iter()
    .flatten()
    .collect()
}
