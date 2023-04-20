// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// Test files are compiled to seperate crates, so there
// may be some unused functions in the common module
#![allow(dead_code)]
mod common;
use self::certs::X509Certs;
use anyhow::{bail, Context, Result as AnyhowResult};
use cmk_agent_ctl::{certs as lib_certs, configuration::config, site_spec};
use common::certs;
use std::io::{Read, Result as IoResult, Write};
use std::net::{IpAddr, Ipv4Addr, Ipv6Addr, SocketAddr};
use std::path::Path;
use std::str::FromStr;
use tokio::process::{Child, Command};

fn registry(
    path: &Path,
    certs: &certs::X509Certs,
    controller_uuid: uuid::Uuid,
) -> config::Registry {
    let mut registry = config::Registry::from_file(path).unwrap();
    registry.register_connection(
        &config::ConnectionMode::Pull,
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

struct PullProcessFixture {
    process: Child,
}

impl PullProcessFixture {
    fn setup(test_path: &Path, port: &u16) -> IoResult<Self> {
        Command::new(assert_cmd::cargo::cargo_bin("cmk-agent-ctl"))
            .env("DEBUG_HOME_DIR", test_path)
            .env("DEBUG_CONNECTION_TIMEOUT", "1")
            .args(["pull", "--port", &port.to_string()])
            .spawn()
            .map(|process| Self { process })
    }

    async fn teardown(mut self) -> IoResult<()> {
        self.process.kill().await
    }
}

struct AgentStreamFixture {
    thread: tokio::task::JoinHandle<std::result::Result<(), anyhow::Error>>,
}

impl AgentStreamFixture {
    #[cfg(unix)]
    fn setup(test_path: &Path) -> Self {
        Self {
            thread: tokio::spawn(common::agent::agent_response_loop(
                common::setup_agent_socket_path(test_path),
                Self::test_agent_output(),
            )),
        }
    }

    #[cfg(windows)]
    fn setup(_test_path: &Path) -> Self {
        panic!("AgentStreamFixture::setup currently not implemented under Windows")
    }

    fn compressed_agent_output(&self) -> AnyhowResult<Vec<u8>> {
        let mut compressed_agent_output = b"\x00\x00\x01".to_vec();
        let mut zlib_enc =
            flate2::write::ZlibEncoder::new(Vec::new(), flate2::Compression::default());
        zlib_enc.write_all(Self::test_agent_output().as_bytes())?;
        compressed_agent_output.append(&mut zlib_enc.finish()?);
        Ok(compressed_agent_output)
    }

    fn teardown(self) {
        self.thread.abort()
    }

    fn test_agent_output() -> String {
        String::from("some test agent output")
    }
}

struct TrustFixture {
    uuid: String,
    certs: common::certs::X509Certs,
}

impl TrustFixture {
    fn setup(test_path: &Path) -> IoResult<Self> {
        let controller_uuid = uuid::Uuid::new_v4();
        let certs = certs::X509Certs::new("Test CA", "Test receiver", &controller_uuid.to_string());
        registry(
            &test_path.join("registered_connections.json"),
            &certs,
            controller_uuid,
        )
        .save()?;

        Ok(Self {
            uuid: controller_uuid.to_string(),
            certs,
        })
    }
}

async fn delete_all_connections(test_path: &Path, enable_legacy_mode: bool) -> AnyhowResult<()> {
    let mut cmd = Command::new(assert_cmd::cargo::cargo_bin("cmk-agent-ctl"));
    cmd.env("DEBUG_HOME_DIR", test_path).args(["delete-all"]);
    if enable_legacy_mode {
        cmd.arg("--enable-insecure-connections");
    }
    if cmd.spawn()?.wait().await?.success() {
        return Ok(());
    }
    bail!("Failed to delete all connections")
}

async fn teardown(
    test_dir: tempfile::TempDir,
    pull_procress_fixture: PullProcessFixture,
    agent_stream_fixture: Option<AgentStreamFixture>,
) -> IoResult<()> {
    pull_procress_fixture.teardown().await?;
    if let Some(agent_stream_fixture) = agent_stream_fixture {
        agent_stream_fixture.teardown()
    }
    test_dir.close()
}

async fn _test_pull_tls_main(prefix: &str, socket_addr: SocketAddr) -> AnyhowResult<()> {
    #[cfg(windows)]
    if !is_elevated::is_elevated() {
        println!("Test is skipped, must be in elevated mode");
        return Ok(());
    }

    let test_dir = common::setup_test_dir(prefix);
    let agent_stream_fixture = AgentStreamFixture::setup(test_dir.path());
    let trust_fixture = TrustFixture::setup(test_dir.path())?;
    let pull_proc_fixture = PullProcessFixture::setup(test_dir.path(), &socket_addr.port())?;

    // Give it some time to provide the TCP socket
    tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;

    let mut id_buf: [u8; 2] = [0; 2];

    // Talk to the pull thread successfully
    let mut message_buf: Vec<u8> = vec![];
    let mut client_connection =
        tls_client_connection(trust_fixture.certs.clone(), &trust_fixture.uuid);
    let mut tcp_stream = std::net::TcpStream::connect(socket_addr)?;
    tcp_stream.read_exact(&mut id_buf)?;
    assert_eq!(&id_buf, b"16");
    let mut tls_stream = rustls::Stream::new(&mut client_connection, &mut tcp_stream);
    tls_stream.read_to_end(&mut message_buf)?;
    assert_eq!(message_buf, agent_stream_fixture.compressed_agent_output()?);

    // Talk to the pull thread using an unknown uuid
    let mut client_connection =
        tls_client_connection(trust_fixture.certs.clone(), "certainly_wrong_uuid");
    let mut tcp_stream = std::net::TcpStream::connect(socket_addr)?;
    tcp_stream.read_exact(&mut id_buf)?;
    assert_eq!(&id_buf, b"16");
    let mut tls_stream = rustls::Stream::new(&mut client_connection, &mut tcp_stream);
    assert!(tls_stream.read_to_end(&mut message_buf).is_err());

    teardown(test_dir, pull_proc_fixture, Some(agent_stream_fixture))
        .await
        .context("Teardown failed")
}

// TODO(sk): reenable test according to https://jira.lan.tribe29.com/browse/CMK-11921
#[tokio::test(flavor = "multi_thread")]
#[cfg_attr(target_os = "windows", ignore)]
async fn test_pull_tls_main_ipv4() -> AnyhowResult<()> {
    _test_pull_tls_main(
        "test_pull_tls_main_ipv4",
        SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), 9970),
    )
    .await
}

// TODO(sk): reenable test according to https://jira.lan.tribe29.com/browse/CMK-11921
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
    #[cfg(windows)]
    if !is_elevated::is_elevated() {
        println!("Test is skipped, must be in elevated mode");
        return Ok(());
    }

    let test_dir = common::setup_test_dir(prefix);
    TrustFixture::setup(test_dir.path())?;
    let pull_proc_fixture = PullProcessFixture::setup(test_dir.path(), &socket_addr.port())?;

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

    teardown(test_dir, pull_proc_fixture, None)
        .await
        .context("Teardown failed")
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

async fn _test_pull_legacy(prefix: &str, socket_addr: SocketAddr) -> AnyhowResult<()> {
    #[cfg(windows)]
    if !is_elevated::is_elevated() {
        println!("Test is skipped, must be in elevated mode");
        return Ok(());
    }

    let test_dir = common::setup_test_dir(prefix);
    TrustFixture::setup(test_dir.path())?;
    // Manually create legacy pull file to test scenario where we have connections AND the legacy
    // marker; this shouldn't happen in reality, but who knows ...
    std::fs::write(test_dir.path().join("allow-legacy-pull"), "")?;
    let agent_stream_fixture = AgentStreamFixture::setup(test_dir.path());
    let pull_proc_fixture = PullProcessFixture::setup(test_dir.path(), &socket_addr.port())?;

    // Give it some time to provide the TCP socket.
    tokio::time::sleep(tokio::time::Duration::from_millis(1500)).await;

    // Make sure the legacy mode is currently *not* active
    let mut message_buf: Vec<u8> = vec![];
    let mut tcp_stream = std::net::TcpStream::connect(socket_addr)?;
    tcp_stream.read_to_end(&mut message_buf)?;
    assert_eq!(message_buf, b"16");

    // Properly enable legacy mode
    delete_all_connections(test_dir.path(), true).await?;

    // Access agent output without TLS
    message_buf.clear();
    let mut tcp_stream = std::net::TcpStream::connect(socket_addr)?;
    tcp_stream.read_to_end(&mut message_buf)?;
    assert_eq!(
        message_buf,
        AgentStreamFixture::test_agent_output().as_bytes()
    );

    teardown(test_dir, pull_proc_fixture, Some(agent_stream_fixture))
        .await
        .context("Teardown failed")
}

#[tokio::test(flavor = "multi_thread")]
#[cfg_attr(target_os = "windows", ignore)]
async fn test_pull_legacy_ipv4() -> AnyhowResult<()> {
    _test_pull_legacy(
        "test_pull_legacy_ipv4",
        SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), 9990),
    )
    .await
}

#[tokio::test(flavor = "multi_thread")]
#[cfg_attr(target_os = "windows", ignore)]
async fn test_pull_legacy_ipv6() -> AnyhowResult<()> {
    _test_pull_legacy(
        "test_pull_legacy_ipv6",
        SocketAddr::new(IpAddr::V6(Ipv6Addr::LOCALHOST), 9991),
    )
    .await
}

async fn _test_pull_no_connections(prefix: &str, socket_addr: SocketAddr) -> AnyhowResult<()> {
    #[cfg(windows)]
    if !is_elevated::is_elevated() {
        println!("Test is skipped, must be in elevated mode");
        return Ok(());
    }

    let test_dir = common::setup_test_dir(prefix);
    let pull_proc_fixture = PullProcessFixture::setup(test_dir.path(), &socket_addr.port())?;

    // Give it some time to provide the TCP socket (it shouldn't)
    tokio::time::sleep(tokio::time::Duration::from_millis(1500)).await;

    assert!(std::net::TcpStream::connect(socket_addr).is_err());

    teardown(test_dir, pull_proc_fixture, None)
        .await
        .context("Teardown failed")
}

#[tokio::test(flavor = "multi_thread")]
async fn test_pull_no_connections_ipv4() -> AnyhowResult<()> {
    _test_pull_no_connections(
        "test_pull_no_connections_ipv4",
        SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), 10000),
    )
    .await
}

#[tokio::test(flavor = "multi_thread")]
async fn test_pull_no_connections_ipv6() -> AnyhowResult<()> {
    _test_pull_no_connections(
        "test_pull_no_connections_ipv6",
        SocketAddr::new(IpAddr::V6(Ipv6Addr::LOCALHOST), 10001),
    )
    .await
}

async fn _test_pull_reload(prefix: &str, socket_addr: SocketAddr) -> AnyhowResult<()> {
    #[cfg(windows)]
    if !is_elevated::is_elevated() {
        println!("Test is skipped, must be in elevated mode");
        return Ok(());
    }

    let test_dir = common::setup_test_dir(prefix);
    TrustFixture::setup(test_dir.path())?;
    let pull_proc_fixture = PullProcessFixture::setup(test_dir.path(), &socket_addr.port())?;

    // Give it some time to provide the TCP socket
    tokio::time::sleep(tokio::time::Duration::from_millis(1500)).await;

    // Make sure we currently can connect
    let mut message_buf: Vec<u8> = vec![];
    let mut tcp_stream = std::net::TcpStream::connect(socket_addr)?;
    tcp_stream.read_to_end(&mut message_buf)?;
    assert_eq!(message_buf, b"16");

    // Clear all connections. On the next connection attempt, we will receive empty output and then,
    // the socket will close.
    delete_all_connections(test_dir.path(), false).await?;
    message_buf.clear();
    let mut tcp_stream = std::net::TcpStream::connect(socket_addr)?;
    tcp_stream.read_to_end(&mut message_buf)?;
    assert!(message_buf.is_empty());
    assert!(std::net::TcpStream::connect(socket_addr).is_err());

    teardown(test_dir, pull_proc_fixture, None)
        .await
        .context("Teardown failed")
}

// TODO(sk): reenable test according to https://jira.lan.tribe29.com/browse/CMK-11921
#[tokio::test(flavor = "multi_thread")]
#[cfg_attr(target_os = "windows", ignore)]
async fn test_pull_reload_ipv4() -> AnyhowResult<()> {
    _test_pull_reload(
        "test_pull_reload_ipv4",
        SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), 10010),
    )
    .await
}

// TODO(sk): reenable test according to https://jira.lan.tribe29.com/browse/CMK-11921
#[tokio::test(flavor = "multi_thread")]
#[cfg_attr(target_os = "windows", ignore)]
async fn test_pull_reload_ipv6() -> AnyhowResult<()> {
    _test_pull_reload(
        "test_pull_reload_ipv6",
        SocketAddr::new(IpAddr::V6(Ipv6Addr::LOCALHOST), 10011),
    )
    .await
}
