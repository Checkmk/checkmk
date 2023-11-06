// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Result as AnyhowResult;
use bytes::Bytes;
use http::{HeaderMap, HeaderName, HeaderValue};
use reqwest::{
    header::USER_AGENT,
    redirect::{Action, Attempt, Policy},
    Error as ReqwestError, Method, RequestBuilder, Result as ReqwestResult, StatusCode, Version,
};
use std::{
    net::{IpAddr, Ipv4Addr, Ipv6Addr, SocketAddr},
    time::{Duration, Instant},
};

use crate::cli::{ForceIP, OnRedirect};

pub struct ProcessedResponse {
    pub version: Version,
    pub status: StatusCode,
    pub headers: HeaderMap, // TODO(au): use
    pub body: Option<ReqwestResult<Bytes>>,
    pub elapsed: Duration,
}

#[allow(clippy::too_many_arguments)] //TODO(au): Fix - Introduce separate configs/options for each function
pub fn prepare_request(
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

pub async fn perform_request(
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

#[cfg(test)]
mod tests {
    use std::net::SocketAddr;

    use crate::http::{
        contains_unchanged_addr, contains_unchanged_ip, filter_socket_addrs, ForceIP,
    };

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
