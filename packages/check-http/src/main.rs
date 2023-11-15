// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use check_http::checking::{Bounds, CheckParameters, UpperLevels, U64};
use check_http::connection::{self, ConnectionConfig};
use check_http::http::{ClientConfig, RequestConfig};
use check_http::output::Output;
use check_http::runner::collect_checks;
use clap::Parser;
use cli::Cli;

mod cli;
mod pwstore;

#[tokio::main]
async fn main() {
    let args = Cli::parse();
    let (client_cfg, connection_cfg, request_cfg, check_params) = make_configs(args);
    let output = Output::from_check_results(
        collect_checks(client_cfg, connection_cfg, request_cfg, check_params).await,
    );
    println!("{}", output);
    std::process::exit(output.worst_state.into());
}

fn make_configs(
    args: Cli,
) -> (
    ClientConfig,
    ConnectionConfig,
    RequestConfig,
    CheckParameters,
) {
    (
        ClientConfig {
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
        RequestConfig {
            without_body: args.without_body,
        },
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
                (x, None) => UpperLevels::warn(x),
                (x, Some(y)) => UpperLevels::warn_crit(x, y),
            }),
            document_age_levels: args.document_age_levels.map(|w| UpperLevels::warn(U64(w))),
        },
    )
}
