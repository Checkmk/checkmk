// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// Test files are compiled to seperate crates, so there
// may be some unused functions in the common module
#![allow(dead_code)]
mod common;
use self::certs::X509Certs;
use anyhow::{Context, Result as AnyhowResult};
use cmk_agent_ctl::{certs as lib_certs, configuration::config, site_spec};
use common::certs;
use std::io::{Read, Result as IoResult, Write};
use std::net::{IpAddr, Ipv4Addr, Ipv6Addr, SocketAddr};
use std::path::{Path, PathBuf};
use std::str::FromStr;
use tokio::process::{Child, Command};

fn registry(
    path: &Path,
    certs: &certs::X509Certs,
    controller_uuid: uuid::Uuid,
) -> config::Registry {
    let mut registry = config::Registry::from_file(path).unwrap();
    registry.register_connection(
        &config::ConnectionType::Pull,
        &site_spec::SiteID::from_str("some_server/some_site").unwrap(),
        config::TrustedConnectionWithRemote {
            trust: config::TrustedConnection {
                uuid: controller_uuid,
                private_key: String::from_utf8(certs.controller_private_key.clone()).unwrap(),
                certificate: String::from_utf8(certs.controller_cert.clone()).unwrap(),
                root_cert: String::from_utf8(certs.ca_cert.clone()).unwrap(),
            },
            receiver_port: 1234,
        },
    );
    registry
}

#[test]
fn test_pull_inconsistent_cert() -> AnyhowResult<()> {
    #[cfg(windows)]
    if !is_elevated::is_elevated() {
        println!("Test is skipped, must be in elevated mode");
        return Ok(());
    }

    let test_dir = common::setup_test_dir("cmk_agent_ctl_test_pull_inconsistent_cert");
    let test_path = test_dir.path();

    let controller_uuid = uuid::Uuid::new_v4();
    let x509_certs =
        common::certs::X509Certs::new("Test CA", "Test receiver", "some certainly wrong uuid");
    let registry = registry(
        &test_path.join("registered_connections.json"),
        &x509_certs,
        controller_uuid,
    );
    registry.save()?;

    let output_err = common::controller_command()
        .env("DEBUG_HOME_DIR", test_path)
        .arg("pull")
        .timeout(std::time::Duration::from_secs(5))
        .unwrap_err();
    let stderr = std::str::from_utf8(&output_err.as_output().unwrap().stderr)?;
    assert!(stderr.contains("Could not initialize TLS"));
    assert!(stderr.contains("The server certificate is not valid for the given name"));

    test_dir
        .close()
        .context("Failed to remove temporary test directory")
}

fn tls_client_connection(certs: X509Certs, address: &str) -> rustls::ClientConnection {
    let root_cert =
        lib_certs::rustls_certificate(&String::from_utf8(certs.ca_cert).unwrap()).unwrap();
    let client_cert =
        lib_certs::rustls_certificate(&String::from_utf8(certs.receiver_cert).unwrap()).unwrap();
    let private_key =
        lib_certs::rustls_private_key(&String::from_utf8(certs.receiver_private_key).unwrap())
            .unwrap();

    let mut root_cert_store = rustls::RootCertStore::empty();
    root_cert_store.add(&root_cert).unwrap();

    let client_chain = vec![client_cert, root_cert];

    let client_config = std::sync::Arc::new(
        rustls::ClientConfig::builder()
            .with_safe_defaults()
            .with_root_certificates(root_cert_store)
            .with_single_cert(client_chain, private_key)
            .unwrap(),
    );
    let server_name = rustls::client::ServerName::try_from(address).unwrap();

    rustls::ClientConnection::new(client_config, server_name).unwrap()
}

struct PullFixture {
    test_agent_output: String,
    uuid: String,
    certs: common::certs::X509Certs,
    agent_stream_thread: tokio::task::JoinHandle<std::result::Result<(), anyhow::Error>>,
    pull_child_proc: Child,
    test_dir: tempfile::TempDir,
}

impl PullFixture {
    fn setup(prefix: &str, port: &u16) -> AnyhowResult<Self> {
        // Uncomment for debugging
        // common::init_logging(&test_path.join("log"))?;
        let test_dir = common::setup_test_dir(prefix);
        let test_path = test_dir.path();
        let test_agent_output = "some test agent output";
        #[cfg(unix)]
        let agent_socket_address = common::setup_agent_socket_path(test_path);
        #[cfg(windows)]
        let agent_socket_address = "localhost:7999".to_string();
        let (uuid, certs) = Self::setup_registry(test_path)?;
        let agent_stream_thread = tokio::spawn(common::agent::agent_response_loop(
            agent_socket_address,
            test_agent_output.to_string(),
        ));

        Ok(Self {
            test_agent_output: test_agent_output.to_string(),
            uuid,
            certs,
            agent_stream_thread,
            pull_child_proc: Self::start_pull_process(test_path, port)?,
            test_dir,
        })
    }

    fn setup_registry(path: &Path) -> AnyhowResult<(String, certs::X509Certs)> {
        let controller_uuid = uuid::Uuid::new_v4();
        let x509_certs =
            certs::X509Certs::new("Test CA", "Test receiver", &controller_uuid.to_string());
        registry(
            &path.join("registered_connections.json"),
            &x509_certs,
            controller_uuid,
        )
        .save()?;

        Ok((controller_uuid.to_string(), x509_certs))
    }

    fn start_pull_process(path_home_dir: &Path, port: &u16) -> IoResult<Child> {
        Command::new(assert_cmd::cargo::cargo_bin("cmk-agent-ctl"))
            .env("DEBUG_HOME_DIR", path_home_dir)
            .env("DEBUG_CONNECTION_TIMEOUT", "1")
            .args(["pull", "--port", &port.to_string()])
            .spawn()
    }

    fn compressed_agent_output(&self) -> AnyhowResult<Vec<u8>> {
        let mut compressed_agent_output = b"\x00\x00\x01".to_vec();
        let mut zlib_enc =
            flate2::write::ZlibEncoder::new(Vec::new(), flate2::Compression::default());
        zlib_enc.write_all(self.test_agent_output.as_bytes())?;
        compressed_agent_output.append(&mut zlib_enc.finish()?);
        Ok(compressed_agent_output)
    }

    async fn teardown(mut self) {
        self.agent_stream_thread.abort();
        self.pull_child_proc.kill().await.unwrap();
        self.test_dir.close().unwrap();
    }

    fn enable_legacy_pull(&self) {
        std::fs::write(
            self.path_legacy_pull_marker(),
            "file content does not matter",
        )
        .unwrap();
    }

    fn disable_legacy_pull(&self) {
        std::fs::remove_file(self.path_legacy_pull_marker()).unwrap()
    }

    fn path_legacy_pull_marker(&self) -> PathBuf {
        self.test_dir.path().join("allow-legacy-pull")
    }
}

async fn _test_pull_tls_main(prefix: &str, socket_addr: SocketAddr) -> AnyhowResult<()> {
    let fixture: PullFixture = PullFixture::setup(prefix, &socket_addr.port())?;
    // Give it some time to provide the TCP socket
    tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;

    let mut id_buf: [u8; 2] = [0; 2];

    // Talk to the pull thread successfully
    let mut message_buf: Vec<u8> = vec![];
    let mut client_connection = tls_client_connection(fixture.certs.clone(), &fixture.uuid);
    let mut tcp_stream = std::net::TcpStream::connect(socket_addr)?;
    tcp_stream.read_exact(&mut id_buf)?;
    assert_eq!(&id_buf, b"16");
    let mut tls_stream = rustls::Stream::new(&mut client_connection, &mut tcp_stream);
    tls_stream.read_to_end(&mut message_buf)?;
    assert_eq!(message_buf, fixture.compressed_agent_output()?);

    // Talk to the pull thread using an unknown uuid
    let mut client_connection =
        tls_client_connection(fixture.certs.clone(), "certainly_wrong_uuid");
    let mut tcp_stream = std::net::TcpStream::connect(socket_addr)?;
    tcp_stream.read_exact(&mut id_buf)?;
    assert_eq!(&id_buf, b"16");
    let mut tls_stream = rustls::Stream::new(&mut client_connection, &mut tcp_stream);
    assert!(tls_stream.read_to_end(&mut message_buf).is_err());

    fixture.teardown().await;

    Ok(())
}

// TODO(sk): Fix this test
#[tokio::test(flavor = "multi_thread")]
#[cfg_attr(target_os = "windows", ignore)]
async fn test_pull_tls_main_ipv4() -> AnyhowResult<()> {
    _test_pull_tls_main(
        "test_pull_tls_main_ipv4",
        SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), 9970),
    )
    .await
}

// TODO(sk): Fix this test
#[tokio::test(flavor = "multi_thread")]
#[cfg_attr(target_os = "windows", ignore)]
async fn test_pull_tls_main_ipv6() -> AnyhowResult<()> {
    _test_pull_tls_main(
        "test_pull_tls_main_ipv6",
        SocketAddr::new(IpAddr::V6(Ipv6Addr::LOCALHOST), 9971),
    )
    .await
}

async fn _test_pull_tls_check_guards(prefix: &str, socket_addr: SocketAddr) -> AnyhowResult<()> {
    let fixture: PullFixture = PullFixture::setup(prefix, &socket_addr.port())?;

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

    fixture.teardown().await;
    Ok(())
}

#[tokio::test(flavor = "multi_thread")]
async fn test_pull_tls_check_guards_ipv4() -> AnyhowResult<()> {
    _test_pull_tls_check_guards(
        "test_pull_tls_check_guards_ipv4",
        SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), 9980),
    )
    .await
}

#[tokio::test(flavor = "multi_thread")]
async fn test_pull_tls_check_guards_ipv6() -> AnyhowResult<()> {
    _test_pull_tls_check_guards(
        "test_pull_tls_check_guards_ipv6",
        SocketAddr::new(IpAddr::V6(Ipv6Addr::LOCALHOST), 9981),
    )
    .await
}

#[cfg(unix)]
async fn _test_pull_legacy(prefix: &str, socket_addr: SocketAddr) -> AnyhowResult<()> {
    let fixture: PullFixture = PullFixture::setup(prefix, &socket_addr.port())?;
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

    fixture.teardown().await;
    Ok(())
}

#[cfg(unix)]
#[tokio::test(flavor = "multi_thread")]
async fn test_pull_legacy_ipv4() -> AnyhowResult<()> {
    _test_pull_legacy(
        "test_pull_legacy_ipv4",
        SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), 9990),
    )
    .await
}

#[cfg(unix)]
#[tokio::test(flavor = "multi_thread")]
async fn test_pull_legacy_ipv6() -> AnyhowResult<()> {
    _test_pull_legacy(
        "test_pull_legacy_ipv6",
        SocketAddr::new(IpAddr::V6(Ipv6Addr::LOCALHOST), 9991),
    )
    .await
}
