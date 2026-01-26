// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Result as AnyhowResult;
use check_http::checking_types::State;
use check_http::checks::{CheckParameters, RequestInformation};
use check_http::http::{ClientConfig, OnRedirect, RequestConfig};
use check_http::output::Output;
use check_http::runner::collect_checks;
use reqwest::{Method, Url};

use std::io::{Read, Write};
use std::net::TcpListener;
use std::sync::atomic;
use std::time::Duration;

const START_PORT: u16 = 8888;
const MAX_PORTS: u16 = 100;
const LOCALHOST_DNS: &str = "localhost";

static PORT_INDEX: atomic::AtomicU16 = atomic::AtomicU16::new(0);

#[tokio::test(flavor = "multi_thread")]
async fn test_basic_get() -> AnyhowResult<()> {
    check_http_output(
        "HTTP/1.1 200 OK\nConnection: close\n\n",
        "GET / HTTP/1.1",
        State::Ok,
        "Version: HTTP/1.1, Status: 200 OK",
    )
    .await
}

#[tokio::test(flavor = "multi_thread")]
async fn test_status_4xx() -> AnyhowResult<()> {
    check_http_output(
        "HTTP/1.1 401 nope\nConnection: close\n\n",
        "GET / HTTP/1.1",
        State::Warn,
        "Version: HTTP/1.1, Status: 401 Unauthorized",
    )
    .await
}

async fn check_http_output(
    http_response: &str,
    expected_http_payload_start: &str,
    expected_state: State,
    expected_summary_start: &str,
) -> AnyhowResult<()> {
    let (port, listener) = tcp_listener("0.0.0.0");
    let url = Url::parse(&format!("http://{}:{}", LOCALHOST_DNS, port)).unwrap();
    let (client_cfg, request_cfg, request_information, check_params) =
        make_standard_configs(url.clone());

    let check_http_thread = tokio::spawn(collect_checks(
        client_cfg,
        request_cfg,
        request_information,
        check_params,
    ));

    let check_http_payload = process_http(listener, http_response)?;

    let output = Output::from_check_results(check_http_thread.await?);

    assert!(check_http_payload.starts_with(expected_http_payload_start));
    assert!(output.worst_state == expected_state);
    assert!(output
        .to_string()
        .starts_with(&format!("{}, {}", url, expected_summary_start)));

    Ok(())
}

fn make_standard_configs(
    url: Url,
) -> (
    ClientConfig,
    RequestConfig,
    RequestInformation,
    CheckParameters,
) {
    (
        ClientConfig {
            version: None,
            user_agent: "test_http".to_string(),
            timeout: Duration::from_secs(1),
            onredirect: OnRedirect::Follow,
            max_redirs: 10,
            force_ip: None,
            min_tls_version: None,
            max_tls_version: None,
            tls_compatibility_mode: false,
            collect_tls_info: false,
            ignore_proxy_env: false,
            proxy_url: None,
            proxy_auth: None,
            disable_certificate_verification: false,
            url: url.clone(),
            server: None,
        },
        RequestConfig {
            url: url.clone(),
            method: Method::GET,
            version: None,
            headers: vec![],
            body: None,
            content_type: None,
            auth_user: None,
            auth_pw: None,
            without_body: false,
            token_auth: None,
        },
        RequestInformation {
            request_url: url,
            method: Method::GET,
            user_agent: "test_http".to_string(),
            onredirect: OnRedirect::Follow,
            timeout: Duration::from_secs(1),
            server: None,
        },
        CheckParameters {
            status_code: vec![],
            page_size: None,
            response_time_levels: None,
            document_age_levels: None,
            body_matchers: vec![],
            header_matchers: vec![],
            certificate_levels: None,
            disable_certificate_verification: false,
            content_search_fail_state: State::Crit,
        },
    )
}

fn process_http(listener: TcpListener, send_response: &str) -> AnyhowResult<String> {
    let (mut stream, _addr) = listener.accept()?;
    let mut buffer: [u8; 1024] = [0; 1024];
    let len = stream.read(&mut buffer)?;
    stream.write_all(send_response.as_bytes())?;
    stream.shutdown(std::net::Shutdown::Both)?;

    Ok(String::from_utf8(buffer[..len].into())?)
}

fn next_port_index() -> u16 {
    let next_port = PORT_INDEX.fetch_add(1, atomic::Ordering::Relaxed);
    if next_port > MAX_PORTS {
        panic!("No free port after {} tries", MAX_PORTS);
    };
    next_port
}

fn tcp_listener(addr: &str) -> (u16, TcpListener) {
    loop {
        let port = START_PORT + next_port_index();
        if let Ok(listener) = TcpListener::bind(format!("{}:{}", addr, port)) {
            return (port, listener);
        };
    }
}
