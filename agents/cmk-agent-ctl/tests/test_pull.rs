// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// Test files are compiled to seperate crates, so there
// may be some unused functions in the common module
#![allow(dead_code)]
mod common;
use anyhow::Result as AnyhowResult;
use std::io::{Read, Write};
use std::net::{IpAddr, Ipv4Addr, Ipv6Addr, SocketAddr};

#[test]
fn test_pull_inconsistent_cert() -> AnyhowResult<()> {
    let test_dir = common::setup_test_dir("cmk_agent_ctl_test_pull");
    let test_path = test_dir.path();

    let controller_uuid = uuid::Uuid::new_v4();
    let x509_certs =
        common::certs::X509Certs::new("Test CA", "Test receiver", "some certainly wrong uuid");
    let registry = common::testing_registry(
        &test_path.join("registered_connections.json"),
        &x509_certs,
        controller_uuid,
    );

    let error = cmk_agent_ctl::modes::pull::pull(common::testing_pull_config(
        test_path,
        1234,
        "dummy".into(),
        registry,
    ))
    .unwrap_err();

    assert!(error.to_string().contains("Could not initialize TLS"));

    Ok(())
}

struct PullFixture {
    test_port: u16,
    test_agent_output: String,
    uuid: String,
    certs: common::certs::X509Certs,
    agent_stream_thread: tokio::task::JoinHandle<std::result::Result<(), anyhow::Error>>,
    pull_thread: tokio::task::JoinHandle<std::result::Result<(), anyhow::Error>>,
    test_dir: tempfile::TempDir,
}

impl PullFixture {
    fn setup(port: u16, prefix: &str, save_legacy: bool) -> AnyhowResult<PullFixture> {
        // Uncomment for debugging
        // common::init_logging(&test_path.join("log"))?;
        let test_dir = common::setup_test_dir(prefix);
        let test_path = test_dir.path();
        std::env::set_var("DEBUG_HOME_DIR", test_path.to_str().unwrap());
        let test_port = port;
        let test_agent_output = "some test agent output";
        #[cfg(unix)]
        let agent_socket_address = common::setup_agent_socket_path(test_path);
        #[cfg(windows)]
        let agent_socket_address = "localhost:7999".to_string();
        let (uuid, pull_config, certs) =
            common::testing_pull_setup(test_path, test_port, agent_socket_address.as_str().into());
        if save_legacy {
            pull_config.registry.save()?;
        }
        let agent_stream_thread = tokio::spawn(common::agent::agent_response_loop(
            agent_socket_address,
            test_agent_output.to_string(),
        ));
        // Setup the pull thread that we intend to test
        let pull_thread = tokio::task::spawn(cmk_agent_ctl::modes::pull::async_pull(pull_config));

        Ok(PullFixture {
            test_port: port,
            test_agent_output: test_agent_output.to_string(),
            uuid,
            certs,
            agent_stream_thread,
            pull_thread,
            test_dir,
        })
    }

    fn compressed_agent_output(&self) -> AnyhowResult<Vec<u8>> {
        let mut compressed_agent_output = b"\x00\x00\x01".to_vec();
        let mut zlib_enc =
            flate2::write::ZlibEncoder::new(Vec::new(), flate2::Compression::default());
        zlib_enc.write_all(self.test_agent_output.as_bytes())?;
        compressed_agent_output.append(&mut zlib_enc.finish()?);
        Ok(compressed_agent_output)
    }

    fn teardown(self) {
        self.agent_stream_thread.abort();
        self.pull_thread.abort();
        self.test_dir.close().unwrap();
    }

    fn enable_legacy_pull(&self) {
        common::legacy_pull_marker(self.test_dir.path())
            .create()
            .unwrap();
    }

    fn disable_legacy_pull(&self) {
        common::legacy_pull_marker(self.test_dir.path())
            .remove()
            .unwrap();
    }
}

async fn _test_pull_tls_main(socket_addr: SocketAddr) -> AnyhowResult<()> {
    let fixture: PullFixture = PullFixture::setup(socket_addr.port(), "test_pull_tls_main", false)?;
    // Give it some time to provide the TCP socket
    tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;

    let mut id_buf: [u8; 2] = [0; 2];

    // Talk to the pull thread successfully
    let mut message_buf: Vec<u8> = vec![];
    let mut client_connection =
        common::testing_tls_client_connection(fixture.certs.clone(), &fixture.uuid);
    let mut tcp_stream = std::net::TcpStream::connect(socket_addr)?;
    tcp_stream.read_exact(&mut id_buf)?;
    assert_eq!(&id_buf, b"16");
    let mut tls_stream = rustls::Stream::new(&mut client_connection, &mut tcp_stream);
    tls_stream.read_to_end(&mut message_buf)?;
    assert_eq!(message_buf, fixture.compressed_agent_output()?);

    // Talk to the pull thread using an unknown uuid
    let mut client_connection =
        common::testing_tls_client_connection(fixture.certs.clone(), "certainly_wrong_uuid");
    let mut tcp_stream = std::net::TcpStream::connect(socket_addr)?;
    tcp_stream.read_exact(&mut id_buf)?;
    assert_eq!(&id_buf, b"16");
    let mut tls_stream = rustls::Stream::new(&mut client_connection, &mut tcp_stream);
    assert!(tls_stream.read_to_end(&mut message_buf).is_err());

    fixture.teardown();

    Ok(())
}

// TODO(sk): Fix this test
#[tokio::test(flavor = "multi_thread")]
#[cfg_attr(target_os = "windows", ignore)]
async fn test_pull_tls_main_ipv4() -> AnyhowResult<()> {
    _test_pull_tls_main(SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), 9970)).await
}

// TODO(sk): Fix this test
#[tokio::test(flavor = "multi_thread")]
#[cfg_attr(target_os = "windows", ignore)]
async fn test_pull_tls_main_ipv6() -> AnyhowResult<()> {
    _test_pull_tls_main(SocketAddr::new(IpAddr::V6(Ipv6Addr::LOCALHOST), 9971)).await
}

async fn _test_pull_tls_check_guards(socket_addr: SocketAddr) -> AnyhowResult<()> {
    let fixture: PullFixture =
        PullFixture::setup(socket_addr.port(), "test_pull_tls_check_guards", false)?;

    // Give it some time to provide the TCP socket
    tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;

    let mut id_buf: [u8; 2] = [0; 2];

    // Talk too much
    let mut tcp_stream_1 = std::net::TcpStream::connect(socket_addr)?;
    let mut tcp_stream_2 = std::net::TcpStream::connect(socket_addr)?;
    let mut tcp_stream_3 = std::net::TcpStream::connect(socket_addr)?;
    let mut tcp_stream_4 = std::net::TcpStream::connect(socket_addr)?;
    // NOTE(sk): Give peers some time to perform their operations.
    tokio::time::sleep(tokio::time::Duration::from_millis(200)).await;
    assert!(tcp_stream_1.read_exact(&mut id_buf).is_ok());
    assert!(tcp_stream_2.read_exact(&mut id_buf).is_ok());
    assert!(tcp_stream_3.read_exact(&mut id_buf).is_ok());
    assert!(tcp_stream_4.read_exact(&mut id_buf).is_err());

    fixture.teardown();
    Ok(())
}

#[tokio::test(flavor = "multi_thread")]
async fn test_pull_tls_check_guards_ipv4() -> AnyhowResult<()> {
    _test_pull_tls_check_guards(SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), 9980)).await
}

#[tokio::test(flavor = "multi_thread")]
async fn test_pull_tls_check_guards_ipv6() -> AnyhowResult<()> {
    _test_pull_tls_check_guards(SocketAddr::new(IpAddr::V6(Ipv6Addr::LOCALHOST), 9981)).await
}

#[cfg(unix)]
async fn _test_pull_legacy(socket_addr: SocketAddr) -> AnyhowResult<()> {
    let fixture: PullFixture = PullFixture::setup(socket_addr.port(), "test_pull_legacy", true)?;
    // Give it some time to provide the TCP socket.
    tokio::time::sleep(tokio::time::Duration::from_millis(1500)).await;

    // Try to read plain data from TLS controller.
    // Connection will timeout after 1 sec, only sending the 16.
    let mut message_buf: Vec<u8> = vec![];
    let mut tcp_stream = std::net::TcpStream::connect(socket_addr)?;
    tcp_stream.read_to_end(&mut message_buf)?;
    assert_eq!(message_buf, b"16");

    // Create allow_legacy_pull file, but still be registered.
    // Connection will timeout after 1 sec, only sending the 16.
    let mut message_buf: Vec<u8> = vec![];
    fixture.enable_legacy_pull();
    let mut tcp_stream = std::net::TcpStream::connect(socket_addr)?;
    tcp_stream.read_to_end(&mut message_buf)?;
    assert_eq!(message_buf, b"16");

    // Delete registry. Now we can finally receive our output in plain text.
    let mut message_buf: Vec<u8> = vec![];
    std::fs::remove_file(fixture.test_dir.path().join("registered_connections.json"))?;
    let mut tcp_stream = std::net::TcpStream::connect(socket_addr)?;
    tcp_stream.read_to_end(&mut message_buf)?;
    assert_eq!(message_buf, fixture.test_agent_output.as_bytes());

    // Disallow legacy pull. First successing connection will be dropped, thus the response being empty.
    // The TCP socket will close afterwards, leading to a refused connection on connect().
    let mut message_buf: Vec<u8> = vec![];
    fixture.disable_legacy_pull();
    let mut tcp_stream = std::net::TcpStream::connect(socket_addr)?;
    tcp_stream.read_to_end(&mut message_buf)?;
    assert_eq!(message_buf, b"");
    assert!(std::net::TcpStream::connect(socket_addr).is_err());

    fixture.teardown();
    Ok(())
}

#[cfg(unix)]
#[tokio::test(flavor = "multi_thread")]
async fn test_pull_legacy_ipv4() -> AnyhowResult<()> {
    _test_pull_legacy(SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), 9990)).await
}

#[cfg(unix)]
#[tokio::test(flavor = "multi_thread")]
async fn test_pull_legacy_ipv6() -> AnyhowResult<()> {
    _test_pull_legacy(SocketAddr::new(IpAddr::V6(Ipv6Addr::LOCALHOST), 9991)).await
}
