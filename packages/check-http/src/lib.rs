// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Result as AnyhowResult;
use bytes::Bytes;
use cli::{Cli, DocumentAgeLevels, ForceIP, PageSizeLimits, ResponseTimeLevels};
use http::{HeaderMap, HeaderName, HeaderValue};
use httpdate::parse_http_date;
use reqwest::{
    header::USER_AGENT,
    redirect::{Action, Attempt, Policy},
    Error as ReqwestError, Method, RequestBuilder, Result as ReqwestResult, StatusCode, Version,
};
use std::{
    net::{IpAddr, Ipv4Addr, Ipv6Addr, SocketAddr},
    time::{Duration, Instant, SystemTime},
};

use crate::checking::{CheckResult, State};
use crate::cli::OnRedirect;

pub mod checking;
pub mod cli;
mod pwstore;

struct ProcessedResponse {
    pub version: Version,
    pub status: StatusCode,
    pub headers: HeaderMap, // TODO(au): use
    pub body: Option<ReqwestResult<Bytes>>,
    pub elapsed: Duration,
}

pub async fn check_http(args: Cli) -> CheckResult {
    let Ok(request) = prepare_request(
        args.url,
        args.method,
        args.user_agent,
        args.headers,
        args.timeout,
        args.auth_user,
        args.auth_pw.auth_pw_plain.or(args.auth_pw.auth_pwstore),
        args.onredirect.clone(),
        args.max_redirs,
        args.force_ip_version,
    ) else {
        return CheckResult::from_summary(State::Unknown, "Error building the request");
    };

    let response = match perform_request(request, args.without_body).await {
        Ok(resp) => resp,
        Err(err) => {
            if err.is_timeout() {
                return CheckResult::from_summary(State::Crit, "timeout");
            } else if err.is_connect() {
                return CheckResult::from_summary(State::Crit, "Failed to connect");
            } else if err.is_redirect() {
                return CheckResult::from_summary(State::Crit, &err.to_string());
            // Hit one of max_redirs, sticky, stickyport
            } else {
                return CheckResult::from_summary(State::Unknown, "Error while sending request");
            }
        }
    };

    merge_check_results(
        &collect_response_checks(
            response,
            args.onredirect,
            args.page_size,
            args.response_time_levels,
            args.document_age_levels,
        )
        .await,
    )
}

#[allow(clippy::too_many_arguments)] //TODO(au): Fix - Introduce separate configs/options for each function
fn prepare_request(
    url: String,
    method: Method,
    user_agent: Option<HeaderValue>,
    headers: Option<Vec<(HeaderName, HeaderValue)>>,
    timeout: Duration,
    auth_user: Option<String>,
    auth_pw: Option<String>,
    onredirect: OnRedirect,
    max_redirs: usize,
    force_ip: Option<ForceIP>,
) -> AnyhowResult<RequestBuilder> {
    let mut cli_headers = HeaderMap::new();
    if let Some(ua) = user_agent {
        cli_headers.insert(USER_AGENT, ua);
    }
    if let Some(hds) = headers {
        cli_headers.extend(hds);
    }

    let redirect_policy = get_redirect_policy(onredirect, force_ip.clone(), max_redirs);
    let client = reqwest::Client::builder();

    let client = match force_ip {
        None => client,
        Some(ipv) => match ipv {
            ForceIP::Ipv4 => client.local_address(IpAddr::V4(Ipv4Addr::UNSPECIFIED)),
            ForceIP::Ipv6 => client.local_address(IpAddr::V6(Ipv6Addr::UNSPECIFIED)),
        },
    };

    let client = client
        .redirect(redirect_policy)
        .timeout(timeout)
        .default_headers(cli_headers)
        .build()?;

    let req = client.request(method, url);
    if let Some(user) = auth_user {
        Ok(req.basic_auth(user, auth_pw))
    } else {
        Ok(req)
    }
}

fn get_redirect_policy(
    onredirect: OnRedirect,
    force_ip: Option<ForceIP>,
    max_redirs: usize,
) -> Policy {
    match onredirect {
        OnRedirect::Ok | OnRedirect::Warning | OnRedirect::Critical => Policy::none(),
        OnRedirect::Follow => Policy::limited(max_redirs),
        OnRedirect::Sticky => {
            Policy::custom(move |att| policy_sticky(att, force_ip.clone(), max_redirs, false))
        }
        OnRedirect::Stickyport => {
            Policy::custom(move |att| policy_sticky(att, force_ip.clone(), max_redirs, true))
        }
    }
}

fn policy_sticky(
    attempt: Attempt,
    force_ip: Option<ForceIP>,
    max_redirs: usize,
    sticky_port: bool,
) -> Action {
    if attempt.previous().len() > max_redirs {
        return attempt.error("too many redirects");
    }

    let previous_socket_addrs = attempt
        .previous()
        .last()
        .unwrap()
        .socket_addrs(|| None)
        .unwrap();
    let socket_addrs = attempt.url().socket_addrs(|| None).unwrap();

    let previous_socket_addr = filter_socket_addrs(previous_socket_addrs, force_ip.clone());
    let socket_addr = filter_socket_addrs(socket_addrs, force_ip);

    match sticky_port {
        false => {
            if contains_unchanged_ip(&previous_socket_addr, &socket_addr) {
                attempt.follow()
            } else {
                attempt.error("Detected changed IP")
            }
        }
        true => {
            if contains_unchanged_addr(&previous_socket_addr, &socket_addr) {
                attempt.follow()
            } else {
                attempt.error("Detected changed IP/port")
            }
        }
    }
}

fn filter_socket_addrs(addrs: Vec<SocketAddr>, force_ip: Option<ForceIP>) -> Vec<SocketAddr> {
    match force_ip {
        None => addrs,
        Some(ipv) => match ipv {
            ForceIP::Ipv4 => addrs.into_iter().filter(|addr| addr.is_ipv4()).collect(),
            ForceIP::Ipv6 => addrs.into_iter().filter(|addr| addr.is_ipv6()).collect(),
        },
    }
}

fn contains_unchanged_ip(old: &[SocketAddr], new: &[SocketAddr]) -> bool {
    old.iter()
        .any(|addr| new.iter().any(|prev_addr| prev_addr.ip() == addr.ip()))
}

fn contains_unchanged_addr(old: &[SocketAddr], new: &[SocketAddr]) -> bool {
    old.iter()
        .any(|addr| new.iter().any(|prev_addr| prev_addr == addr))
}

async fn perform_request(
    request: RequestBuilder,
    without_body: bool,
) -> Result<ProcessedResponse, ReqwestError> {
    let now = Instant::now();
    let response = request.send().await?;

    let headers = response.headers().to_owned();
    let version = response.version();
    let status = response.status();
    let body = match without_body {
        false => Some(response.bytes().await),
        true => None,
    };
    let elapsed = now.elapsed();

    Ok(ProcessedResponse {
        version,
        status,
        headers,
        body,
        elapsed,
    })
}

async fn collect_response_checks(
    response: ProcessedResponse,
    onredirect: OnRedirect,
    page_size_limits: Option<PageSizeLimits>,
    response_time_levels: Option<ResponseTimeLevels>,
    document_age_levels: Option<DocumentAgeLevels>,
) -> Vec<CheckResult> {
    vec![
        check_status(response.status, response.version, onredirect),
        check_body(response.body, page_size_limits),
        check_response_time(response.elapsed, response_time_levels),
        check_document_age(&response.headers, document_age_levels),
    ]
}

fn check_status(status: StatusCode, version: Version, onredirect: OnRedirect) -> CheckResult {
    let response_state = if status.is_client_error() {
        State::Warn
    } else if status.is_server_error() {
        State::Crit
    } else if status.is_redirection() {
        match onredirect {
            OnRedirect::Warning => State::Warn,
            OnRedirect::Critical => State::Crit,
            _ => State::Ok, // If we reach this point, the redirect is ok
        }
    } else {
        State::Ok
    };

    CheckResult::from_summary(response_state, &format!("{:?} {}", version, status))
}

fn check_body(
    body: Option<Result<Bytes, ReqwestError>>,
    page_size_limits: Option<PageSizeLimits>,
) -> CheckResult {
    let Some(body) = body else {
        return CheckResult::from_state(State::Ok);
    };

    match body {
        Ok(bd) => check_page_size(bd.len(), page_size_limits),
        Err(_) => CheckResult::from_summary(State::Crit, "Error fetching the reponse body"),
    }
}

fn check_page_size(page_size: usize, page_size_limits: Option<PageSizeLimits>) -> CheckResult {
    let state = match page_size_limits {
        Some((lower, _)) if page_size < lower => State::Warn,
        Some((_, Some(upper))) if page_size > upper => State::Warn,
        _ => State::Ok,
    };

    CheckResult::from_summary(state, &format!("Page size: {} bytes", page_size))
}

fn check_response_time(
    response_time: Duration,
    response_time_levels: Option<ResponseTimeLevels>,
) -> CheckResult {
    let state = match response_time_levels {
        Some((_, Some(crit))) if response_time.as_secs_f64() >= crit => State::Crit,
        Some((warn, _)) if response_time.as_secs_f64() >= warn => State::Warn,
        _ => State::Ok,
    };

    CheckResult::from_summary(
        state,
        &format!(
            "Response time: {}.{}s",
            response_time.as_secs(),
            response_time.subsec_millis()
        ),
    )
}

fn check_document_age(
    headers: &HeaderMap,
    document_age_levels: Option<DocumentAgeLevels>,
) -> CheckResult {
    if document_age_levels.is_none() {
        return CheckResult::from_state(State::Ok);
    };

    let now = SystemTime::now();

    let age_header = headers.get("last-modified").or(headers.get("date"));
    let Some(document_age) = age_header else {
        return CheckResult::from_summary(State::Crit, "Can't determine document age");
    };
    let Ok(Ok(age)) = document_age.to_str().map(parse_http_date) else {
        return CheckResult::from_summary(State::Crit, "Can't decode document age");
    };

    //TODO(au): Specify "too old" in Output
    match document_age_levels {
        Some((_, Some(crit))) if now - Duration::from_secs(crit) > age => {
            CheckResult::from_summary(State::Crit, "Document age too old")
        }
        Some((warn, _)) if now - Duration::from_secs(warn) > age => {
            CheckResult::from_summary(State::Warn, "Document age too old")
        }
        _ => CheckResult::from_state(State::Ok),
    }
}

fn merge_check_results(outputs: &[CheckResult]) -> CheckResult {
    let summary = outputs
        .iter()
        .filter_map(|output| output.summary.clone())
        .collect::<Vec<String>>()
        .join(", ");
    let summary = if summary.is_empty() {
        None
    } else {
        Some(summary)
    };
    let details = outputs
        .iter()
        .filter_map(|output| output.details.clone())
        .collect::<Vec<String>>()
        .join("\n");
    let details = if details.is_empty() {
        None
    } else {
        Some(details)
    };

    let state = outputs
        .iter()
        .map(|output| output.state.clone())
        .max()
        .unwrap();

    CheckResult {
        state,
        summary,
        details,
    }
}

#[cfg(test)]
mod tests {
    use std::net::SocketAddr;

    use crate::{contains_unchanged_addr, contains_unchanged_ip, filter_socket_addrs, ForceIP};

    #[test]
    fn test_contains_unchanged_ip() {
        let old_addrs: Vec<SocketAddr> = vec![
            "1.2.3.4:80".parse().unwrap(),
            "[1234:abcd::]:80".parse().unwrap(),
        ];
        let new_addrs = old_addrs.clone();
        assert!(contains_unchanged_ip(&old_addrs, &new_addrs));

        let new_addrs: Vec<SocketAddr> = vec![
            "1.2.3.4:443".parse().unwrap(),
            "[2345:abcd::]:80".parse().unwrap(),
        ];
        assert!(contains_unchanged_ip(&old_addrs, &new_addrs));

        let new_addrs: Vec<SocketAddr> = vec![
            "2.3.4.5:80".parse().unwrap(),
            "[2345:abcd::]:80".parse().unwrap(),
        ];
        assert!(!contains_unchanged_ip(&old_addrs, &new_addrs));
    }

    #[test]
    fn test_contains_unchanged_addr() {
        let old_addrs: Vec<SocketAddr> = vec![
            "1.2.3.4:80".parse().unwrap(),
            "[1234:abcd::]:80".parse().unwrap(),
        ];
        let new_addrs = old_addrs.clone();
        assert!(contains_unchanged_addr(&old_addrs, &new_addrs));

        let new_addrs: Vec<SocketAddr> = vec![
            "1.2.3.4:443".parse().unwrap(),
            "[2345:abcd::]:80".parse().unwrap(),
        ];
        assert!(!contains_unchanged_addr(&old_addrs, &new_addrs));
    }

    #[test]
    fn test_filter_socket_addrs() {
        let addrs: Vec<SocketAddr> = vec![
            "1.2.3.4:443".parse().unwrap(),
            "2.3.4.5:1234".parse().unwrap(),
            "[2345:abcd::]:80".parse().unwrap(),
            "[1234:abcd::]:8888".parse().unwrap(),
        ];
        let ipv4_addrs: Vec<SocketAddr> = vec![
            "1.2.3.4:443".parse().unwrap(),
            "2.3.4.5:1234".parse().unwrap(),
        ];
        let ipv6_addrs: Vec<SocketAddr> = vec![
            "[2345:abcd::]:80".parse().unwrap(),
            "[1234:abcd::]:8888".parse().unwrap(),
        ];
        assert_eq!(addrs, filter_socket_addrs(addrs.clone(), None));
        assert_eq!(
            ipv4_addrs,
            filter_socket_addrs(addrs.clone(), Some(ForceIP::Ipv4))
        );
        assert_eq!(ipv6_addrs, filter_socket_addrs(addrs, Some(ForceIP::Ipv6)));
    }
}

#[cfg(test)]
mod test_check_functions {
    use crate::check_page_size;
    use crate::checking::State;

    #[test]
    fn test_check_page_size_without_limits() {
        assert_eq!(check_page_size(42, None).state, State::Ok);
    }

    #[test]
    fn test_check_page_size_with_lower_within_bounds() {
        assert_eq!(check_page_size(42, Some((12, None))).state, State::Ok);
    }

    #[test]
    fn test_check_page_size_with_lower_out_of_bounds() {
        assert_eq!(check_page_size(42, Some((56, None))).state, State::Warn);
    }

    #[test]
    fn test_check_page_size_with_lower_and_higher_within_bounds() {
        assert_eq!(check_page_size(56, Some((42, Some(100)))).state, State::Ok);
    }

    #[test]
    fn test_check_page_size_with_lower_and_higher_too_low() {
        assert_eq!(
            check_page_size(42, Some((56, Some(100)))).state,
            State::Warn
        );
    }

    #[test]
    fn test_check_page_size_with_lower_and_higher_too_high() {
        assert_eq!(
            check_page_size(142, Some((56, Some(100)))).state,
            State::Warn
        );
    }
}
