// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use reqwest::{
    redirect::{Action, Attempt, Policy},
    tls::Version as TlsVersion,
    Client, Proxy, Result as ReqwestResult, Url, Version,
};
use std::time::Duration;
use std::{
    net::{IpAddr, Ipv4Addr, Ipv6Addr, SocketAddr},
    sync::{Arc, Mutex},
};

#[derive(Clone)]
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
    pub min_tls_version: Option<TlsVersion>,
    pub max_tls_version: Option<TlsVersion>,
    pub collect_tls_info: bool,
    pub ignore_proxy_env: bool,
    pub proxy_url: Option<String>,
    pub proxy_auth: Option<(String, String)>,
    pub disable_certificate_verification: bool,
    pub url: Url,
    pub server: Option<SocketAddr>,
}

pub struct ClientAdapter {
    pub client: Client,
    pub redirect_recorder: Arc<Mutex<Option<Url>>>,
}

impl ClientAdapter {
    pub fn new(cfg: ClientConfig) -> ReqwestResult<Self> {
        let redirect_recorder = Arc::new(Mutex::<Option<Url>>::new(None));
        Ok(Self {
            client: build(cfg, redirect_recorder.clone())?,
            redirect_recorder,
        })
    }
}

fn build(cfg: ClientConfig, record_redirect: Arc<Mutex<Option<Url>>>) -> ReqwestResult<Client> {
    let client = reqwest::Client::builder()
        .danger_accept_invalid_certs(cfg.disable_certificate_verification);

    let client = if let Some(server_socket_addr) = cfg.server {
        let domain = cfg.url.domain().unwrap_or_default();
        client.resolve(domain, server_socket_addr)
    } else {
        client
    };

    let client = if cfg.ignore_proxy_env {
        client.no_proxy()
    } else {
        client
    };

    let client = if let Some(proxy) = get_proxy(cfg.proxy_url, cfg.proxy_auth) {
        client.proxy(proxy?)
    } else {
        client
    };

    let client = if let Some(version) = cfg.min_tls_version {
        match version {
            TlsVersion::TLS_1_0 | TlsVersion::TLS_1_1 => {
                // Caveat: Enforcing TLS 1.0 or 1.1 may still fail, even with native_tls!
                // The availability of TLS versions + required cipher suites relies on the
                // system's OpenSSL version and config.
                client.use_native_tls().min_tls_version(version)
            }
            _ => client.use_rustls_tls().min_tls_version(version),
        }
    } else {
        client.use_rustls_tls()
    };

    let client = if let Some(version) = cfg.max_tls_version {
        client.max_tls_version(version)
    } else {
        client
    };

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
        .redirect(get_policy(
            cfg.onredirect,
            cfg.max_redirs,
            cfg.force_ip,
            record_redirect,
        ))
        .tls_info(cfg.collect_tls_info)
        .build()
}

fn get_proxy(
    proxy_url: Option<String>,
    proxy_auth: Option<(String, String)>,
) -> Option<ReqwestResult<Proxy>> {
    let proxy_url = proxy_url?;

    let proxy = Proxy::all(proxy_url);

    if let Some((proxy_user, proxy_pw)) = proxy_auth {
        Some(proxy.map(|p| p.basic_auth(&proxy_user, &proxy_pw)))
    } else {
        Some(proxy)
    }
}

fn get_policy(
    onredirect: OnRedirect,
    max_redirs: usize,
    force_ip: Option<ForceIP>,
    record_redirect: Arc<Mutex<Option<Url>>>,
) -> Policy {
    match onredirect {
        OnRedirect::Ok | OnRedirect::Warning | OnRedirect::Critical => Policy::custom(move |att| {
            *record_redirect.lock().unwrap() = Some(att.url().to_owned());
            att.stop()
        }),
        OnRedirect::Follow => Policy::limited(max_redirs),
        OnRedirect::Sticky => Policy::custom(move |att| {
            policy_sticky(
                att,
                force_ip.clone(),
                max_redirs,
                false,
                record_redirect.clone(),
            )
        }),
        OnRedirect::Stickyport => Policy::custom(move |att| {
            policy_sticky(
                att,
                force_ip.clone(),
                max_redirs,
                true,
                record_redirect.clone(),
            )
        }),
    }
}

fn policy_sticky(
    attempt: Attempt,
    force_ip: Option<ForceIP>,
    max_redirs: usize,
    sticky_port: bool,
    record_redirect: Arc<Mutex<Option<Url>>>,
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

    let contains = if sticky_port {
        contains_unchanged_addr
    } else {
        contains_unchanged_ip
    };

    if contains(&previous_socket_addr, &socket_addr) {
        attempt.follow()
    } else {
        *record_redirect.lock().unwrap() = Some(attempt.url().to_owned());
        attempt.stop()
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
