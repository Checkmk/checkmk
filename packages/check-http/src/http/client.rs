// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use reqwest::{
    redirect::{Action, Attempt, Policy},
    Client, Result as ReqwestResult, Version,
};
use std::net::{IpAddr, Ipv4Addr, Ipv6Addr, SocketAddr};
use std::time::Duration;

pub enum OnRedirect {
    Ok,
    Warning,
    Critical,
    Follow,
    Sticky,
    Stickyport,
}

#[derive(Clone)]
pub enum ForceIP {
    Ipv4,
    Ipv6,
}

pub struct ClientConfig {
    pub version: Option<Version>,
    pub user_agent: String,
    pub timeout: Duration,
    pub onredirect: OnRedirect,
    pub max_redirs: usize,
    pub force_ip: Option<ForceIP>,
}

pub fn build(cfg: ClientConfig) -> ReqwestResult<Client> {
    let client = reqwest::Client::builder()
        // rustls (or native-tls with native-tls-alpn feature) backend is needed to establish
        // a HTTP/2 connection via TLS.
        .use_rustls_tls();

    let client = match cfg.version {
        // See IETF RFC 9113, Section 3:
        // HTTP/2 without TLS can only be established with "prior knowledge".
        // HTTP/2 without TLS always uses ALPN and is not affected by this setting, so we can
        // safely enable it.
        // That said, HTTP/2 over TLS is de facto unsupported by common server software,
        // so this will probably fail anyways.
        Some(Version::HTTP_2) => client.http2_prior_knowledge(),
        Some(Version::HTTP_11) => client.http1_only(),
        _ => client,
    };

    let client = match &cfg.force_ip {
        None => client,
        Some(ipv) => match ipv {
            ForceIP::Ipv4 => client.local_address(IpAddr::V4(Ipv4Addr::UNSPECIFIED)),
            ForceIP::Ipv6 => client.local_address(IpAddr::V6(Ipv6Addr::UNSPECIFIED)),
        },
    };

    client
        .timeout(cfg.timeout)
        .user_agent(cfg.user_agent)
        .redirect(get_policy(cfg.onredirect, cfg.max_redirs, cfg.force_ip))
        .build()
}

fn get_policy(onredirect: OnRedirect, max_redirs: usize, force_ip: Option<ForceIP>) -> Policy {
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

#[cfg(test)]
mod tests {
    use std::net::SocketAddr;

    use super::*;

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
