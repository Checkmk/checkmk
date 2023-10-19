use anyhow::Result as AnyhowResult;
use check_http::{check_http, cli::Cli};
use clap::Parser;

use std::io::{Read, Write};
use std::net::TcpListener;

const TEST_PORT: u16 = 8888;
const LOCALHOST_DNS: &str = "localhost";

const BASIC_HTTP_RESPONSE: &str = "HTTP/1.1 200 OK\nConnection: close\n\n";

#[tokio::test(flavor = "multi_thread")]
async fn test_basic_get() -> AnyhowResult<()> {
    let listener = TcpListener::bind("0.0.0.0:8888")?;

    let args = Cli::parse_from(vec![
        "check_http",
        "-u",
        &format!("http://{}:{}", LOCALHOST_DNS, TEST_PORT),
        "-t",
        "1",
    ]);
    let check_http_thread = tokio::spawn(check_http(args));

    let check_http_payload = process_http(listener, BASIC_HTTP_RESPONSE)?;

    check_http_thread.await??;

    assert!(check_http_payload.starts_with("GET / HTTP/1.1"));

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
