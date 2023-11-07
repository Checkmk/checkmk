// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Result as AnyhowResult;
use check_http::{checking::State, cli::Cli, output::Output, runner::collect_checks};
use clap::Parser;

use std::io::{Read, Write};
use std::net::TcpListener;
use std::sync::atomic;

const START_PORT: u16 = 8888;
const MAX_PORTS: u16 = 100;
const LOCALHOST_DNS: &str = "localhost";

static PORT_INDEX: atomic::AtomicU16 = atomic::AtomicU16::new(0);

#[tokio::test(flavor = "multi_thread")]
async fn test_basic_get() -> AnyhowResult<()> {
    check_http_output(
        vec!["check_http", "-t", "1"],
        "HTTP/1.1 200 OK\nConnection: close\n\n",
        "GET / HTTP/1.1",
        State::Ok,
        "HTTP OK - HTTP/1.1 200 OK",
    )
    .await
}

#[tokio::test(flavor = "multi_thread")]
async fn test_status_4xx() -> AnyhowResult<()> {
    check_http_output(
        vec!["check_http", "-t", "1"],
        "HTTP/1.1 401 nope\nConnection: close\n\n",
        "GET / HTTP/1.1",
        State::Warn,
        "HTTP WARNING - HTTP/1.1 401 Unauthorized",
    )
    .await
}

async fn check_http_output(
    mut raw_args: Vec<&str>,
    http_response: &str,
    expected_http_payload_start: &str,
    expected_state: State,
    expected_summary_start: &str,
) -> AnyhowResult<()> {
    let (port, listener) = tcp_listener("0.0.0.0");
    let url = format!("http://{}:{}", LOCALHOST_DNS, port);

    raw_args.extend(["-u", &url].iter());
    let args = Cli::parse_from(raw_args);

    let check_http_thread = tokio::spawn(collect_checks(args));

    let check_http_payload = process_http(listener, http_response)?;

    let output = Output::from_check_results(check_http_thread.await?);

    assert!(check_http_payload.starts_with(expected_http_payload_start));
    assert!(output.worst_state == expected_state);
    assert!(output.to_string().starts_with(expected_summary_start));

    Ok(())
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
