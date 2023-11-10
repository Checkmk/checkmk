// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::cli;
use std::time::Instant;

use crate::checking::{self, Bounds, CheckParameters, CheckResult, State, UpperLevels};
use crate::connection::{self, ConnectionConfig};
use crate::http::{self, RequestConfig};
use std::time::Duration;

pub async fn collect_checks(args: cli::Cli) -> Vec<CheckResult> {
    let Ok(request) = http::prepare_request(
        RequestConfig {
            url: args.url,
            method: args.method,
            user_agent: args.user_agent,
            headers: args.headers,
            timeout: args.timeout,
            auth_user: args.auth_user,
            auth_pw: args.auth_pw.auth_pw_plain.or(args.auth_pw.auth_pwstore),
        },
        ConnectionConfig {
            onredirect: match args.onredirect {
                cli::OnRedirect::Ok => connection::OnRedirect::Ok,
                cli::OnRedirect::Warning => connection::OnRedirect::Warning,
                cli::OnRedirect::Critical => connection::OnRedirect::Critical,
                cli::OnRedirect::Follow => connection::OnRedirect::Follow,
                cli::OnRedirect::Sticky => connection::OnRedirect::Sticky,
                cli::OnRedirect::Stickyport => connection::OnRedirect::Stickyport,
            },
            max_redirs: args.max_redirs,
            force_ip: match args.force_ip_version {
                None => None,
                Some(cli::ForceIP::Ipv4) => Some(connection::ForceIP::Ipv4),
                Some(cli::ForceIP::Ipv6) => Some(connection::ForceIP::Ipv6),
            },
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

    checking::collect_response_checks(
        response,
        elapsed,
        CheckParameters {
            onredirect: match args.onredirect {
                cli::OnRedirect::Ok => connection::OnRedirect::Ok,
                cli::OnRedirect::Warning => connection::OnRedirect::Warning,
                cli::OnRedirect::Critical => connection::OnRedirect::Critical,
                cli::OnRedirect::Follow => connection::OnRedirect::Follow,
                cli::OnRedirect::Sticky => connection::OnRedirect::Sticky,
                cli::OnRedirect::Stickyport => connection::OnRedirect::Stickyport,
            },
            page_size: args.page_size.map(|val| match val {
                (x, None) => Bounds::lower(x),
                (x, Some(y)) => Bounds::lower_upper(x, y),
            }),
            response_time_levels: args.response_time_levels.map(|val| match val {
                (x, None) => UpperLevels::warn(Duration::from_secs_f64(x)),
                (x, Some(y)) => {
                    UpperLevels::warn_crit(Duration::from_secs_f64(x), Duration::from_secs_f64(y))
                }
            }),
            document_age_levels: args
                .document_age_levels
                .map(|val| UpperLevels::warn(Duration::from_secs(val))),
        },
    )
}
