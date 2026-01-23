// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// Test files are compiled to separate crates, so there
// may be some unused functions in the common module
#![allow(dead_code)]

#[cfg(not(feature = "build_system_bazel"))]
mod common;

#[cfg(feature = "build_system_bazel")]
extern crate common;

use anyhow::{bail, Context, Result as AnyhowResult};
use cmk_agent_ctl::{certs as lib_certs, configuration::config, site_spec};
use common::agent;
use common::certs::{self, X509Certs};
use rustls::crypto::ring::default_provider;
use std::io::{Read, Result as IoResult, Write};
use std::net::{IpAddr, Ipv4Addr, Ipv6Addr, SocketAddr};
use std::path::Path;
use std::str::FromStr;
use std::sync::atomic;
use std::sync::Arc;
use tokio::process::{Child, Command};

const PULL_BASE_PORT: u16 = 9970;
const PULL_TLS_CHECK_PORT: u16 = 9980;
const PULL_LEGACY_PORT: u16 = 9990;
const PULL_NO_CONNECTION_PORT: u16 = 10000;
const PULL_RELOAD_PORT: u16 = 10010;

const FREE_RANGE_PORT_START: u16 = 12400;
const FREE_RANGE_PORT_END: u16 = FREE_RANGE_PORT_START + 4096;

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
    if agent::is_elevation_required() {
        println!("Test is skipped, must be in elevated mode");
        return Ok(());
    }

    let test_dir = common::setup_test_dir("cmk_agent_ctl_test_pull_inconsistent_cert");
    let test_path = test_dir.path();

    let controller_uuid = uuid::Uuid::new_v4();
    let x509_certs = X509Certs::new("Test CA", "Test receiver", "some certainly wrong uuid");
    let registry = registry(
        &test_path.join("registered_connections.json"),
        &x509_certs,
        controller_uuid,
    );
    registry.save()?;

    let output_err = assert_cmd::Command::new(common::controller_command_path())
        .env("DEBUG_HOME_DIR", test_path)
        .arg("pull")
        .timeout(std::time::Duration::from_secs(5))
        .unwrap_err();
    let stderr = std::str::from_utf8(&output_err.as_output().unwrap().stderr)?;
    assert!(stderr.contains("Could not initialize TLS"));
    assert!(stderr.contains("not valid for name"));

    test_dir
        .close()
        .context("Failed to remove temporary test directory")
}

fn tls_client_connection(
    config_builder: rustls::ConfigBuilder<rustls::ClientConfig, rustls::WantsVerifier>,
    certs: X509Certs,
    address: String,
) -> rustls::ClientConnection {
    let root_cert =
        lib_certs::rustls_certificate(&String::from_utf8(certs.ca_cert).unwrap()).unwrap();
    let client_cert =
        lib_certs::rustls_certificate(&String::from_utf8(certs.receiver_cert).unwrap()).unwrap();
    let private_key =
        lib_certs::rustls_private_key(&String::from_utf8(certs.receiver_private_key).unwrap())
            .unwrap();

    let mut root_cert_store = rustls::RootCertStore::empty();
    root_cert_store.add(root_cert.clone()).unwrap();

    let client_chain = vec![client_cert, root_cert];

    let client_config = std::sync::Arc::new(
        config_builder
            .with_root_certificates(root_cert_store)
            .with_client_auth_cert(client_chain, private_key)
            .unwrap(),
    );
    let server_name = rustls::pki_types::ServerName::try_from(address).unwrap();

    rustls::ClientConnection::new(client_config, server_name).unwrap()
}

struct PullProcessFixture {
    process: Child,
}

impl PullProcessFixture {
    fn setup(test_path: &Path, port: &u16, agent_channel: Option<&str>) -> IoResult<Self> {
        let port_string = port.to_string();
        let mut commands = vec!["pull", "--port", &port_string];
        if let Some(value) = agent_channel {
            commands.extend_from_slice(&["--agent-channel", value]);
            #[cfg(unix)]
            panic!(
                "agent channel is not supported for Linux, path {:?}",
                test_path
            );
        }
        Command::new(common::controller_command_path())
            .env("DEBUG_HOME_DIR", test_path)
            .env("DEBUG_CONNECTION_TIMEOUT", "1")
            .args(commands)
            .spawn()
            .map(|process| Self { process })
    }

    async fn teardown(mut self) -> IoResult<()> {
        self.process.kill().await
    }
}

struct AgentStreamFixture {
    thread: tokio::task::JoinHandle<std::result::Result<(), anyhow::Error>>,
    agent_channel: Option<String>,
}

impl AgentStreamFixture {
    #[cfg(unix)]
    fn setup(test_path: &Path) -> Self {
        Self {
            thread: tokio::spawn(agent::linux::agent_response_loop(
                agent::linux::setup_agent_socket_path(test_path),
                Self::test_agent_output(),
            )),
            agent_channel: None,
        }
    }

    #[cfg(windows)]
    fn setup(_test_path: &Path) -> Self {
        let backend = agent::win::make_agent_response_peer().unwrap();
        let agent_channel = Some("ms/".to_string() + backend.used_name());
        Self {
            thread: tokio::spawn(agent::win::run_agent_response_loop(
                backend,
                Self::test_agent_output(),
            )),
            agent_channel,
        }
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

    fn get_agent_channel(&self) -> Option<&str> {
        self.agent_channel.as_deref()
    }
}

struct TrustFixture {
    uuid: String,
    certs: X509Certs,
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
    let mut cmd = Command::new(common::controller_command_path());
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
    pull_process_fixture: PullProcessFixture,
    agent_stream_fixture: Option<AgentStreamFixture>,
) -> IoResult<()> {
    pull_process_fixture.teardown().await?;
    if let Some(agent_stream_fixture) = agent_stream_fixture {
        agent_stream_fixture.teardown()
    }
    test_dir.close()
}

#[tokio::test(flavor = "multi_thread")]
async fn test_pull_tls_main_ipv4() -> AnyhowResult<()> {
    _test_pull_tls_main(
        "test_pull_tls_main_ipv4",
        IpAddr::V4(Ipv4Addr::LOCALHOST),
        PULL_BASE_PORT,
        rustls::ClientConfig::builder_with_provider(Arc::new(default_provider()))
            .with_safe_default_protocol_versions()?,
    )
    .await
}

#[tokio::test(flavor = "multi_thread")]
async fn test_pull_tls_main_ipv6() -> AnyhowResult<()> {
    _test_pull_tls_main(
        "test_pull_tls_main_ipv6",
        IpAddr::V6(Ipv6Addr::LOCALHOST),
        PULL_BASE_PORT + 1,
        rustls::ClientConfig::builder_with_provider(Arc::new(default_provider()))
            .with_safe_default_protocol_versions()?,
    )
    .await
}

async fn _test_pull_tls_main(
    prefix: &str,
    ip_addr: IpAddr,
    port: u16,
    client_config_builder: rustls::ConfigBuilder<rustls::ClientConfig, rustls::WantsVerifier>,
) -> AnyhowResult<()> {
    if agent::is_elevation_required() {
        println!("Test is skipped, must be in elevated mode");
        return Ok(());
    }

    let test_dir = common::setup_test_dir(prefix);
    let agent_stream_fixture = AgentStreamFixture::setup(test_dir.path());
    let trust_fixture = TrustFixture::setup(test_dir.path())?;
    let p = find_available_port_if_busy(port);
    let pull_proc_fixture = PullProcessFixture::setup(
        test_dir.path(),
        &p,
        agent_stream_fixture.get_agent_channel(),
    )?;

    // Give it some time to provide the TCP socket
    tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;

    let mut id_buf: [u8; 2] = [0; 2];

    // Talk to the pull thread successfully
    let mut message_buf: Vec<u8> = vec![];
    let mut client_connection = tls_client_connection(
        client_config_builder.clone(),
        trust_fixture.certs.clone(),
        trust_fixture.uuid,
    );

    let socket_addr = SocketAddr::new(ip_addr, p);
    let mut tcp_stream = std::net::TcpStream::connect(socket_addr)?;
    tcp_stream.read_exact(&mut id_buf)?;
    assert_eq!(&id_buf, b"16");
    let mut tls_stream = rustls::Stream::new(&mut client_connection, &mut tcp_stream);
    tls_stream.read_to_end(&mut message_buf)?;
    assert_eq!(message_buf, agent_stream_fixture.compressed_agent_output()?);

    // Talk to the pull thread using an unknown uuid
    let mut client_connection = tls_client_connection(
        client_config_builder.clone(),
        trust_fixture.certs.clone(),
        "certainly_wrong_uuid".into(),
    );
    let mut tcp_stream = std::net::TcpStream::connect(socket_addr)?;
    tcp_stream.read_exact(&mut id_buf)?;
    assert_eq!(&id_buf, b"16");
    let mut tls_stream = rustls::Stream::new(&mut client_connection, &mut tcp_stream);
    assert!(tls_stream.read_to_end(&mut message_buf).is_err());

    teardown(test_dir, pull_proc_fixture, Some(agent_stream_fixture))
        .await
        .context("Teardown failed")
}

fn find_available_port_if_busy(proposed_port: u16) -> u16 {
    let mut port = proposed_port;
    while !agent::is_port_available(port) {
        port = FREE_RANGE_PORT_START + make_port_personal();
        if port >= FREE_RANGE_PORT_END {
            panic!("Can't find free port")
        }
    }
    port
}

fn make_port_personal() -> u16 {
    static UNIQUE_PORT_INDEX: atomic::AtomicU16 = atomic::AtomicU16::new(0);
    UNIQUE_PORT_INDEX.fetch_add(1, atomic::Ordering::Relaxed)
}

#[tokio::test(flavor = "multi_thread")]
async fn test_pull_tls_check_guards_ipv4() -> AnyhowResult<()> {
    _test_pull_tls_check_guards(
        "test_pull_tls_check_guards_ipv4",
        IpAddr::V4(Ipv4Addr::LOCALHOST),
        PULL_TLS_CHECK_PORT,
    )
    .await
}

#[tokio::test(flavor = "multi_thread")]
async fn test_pull_tls_check_guards_ipv6() -> AnyhowResult<()> {
    _test_pull_tls_check_guards(
        "test_pull_tls_check_guards_ipv6",
        IpAddr::V6(Ipv6Addr::LOCALHOST),
        PULL_TLS_CHECK_PORT + 1,
    )
    .await
}

async fn _test_pull_tls_check_guards(prefix: &str, ip_addr: IpAddr, port: u16) -> AnyhowResult<()> {
    if agent::is_elevation_required() {
        println!("Test is skipped, must be in elevated mode");
        return Ok(());
    }

    let test_dir = common::setup_test_dir(prefix);
    TrustFixture::setup(test_dir.path())?;
    let pull_proc_fixture = PullProcessFixture::setup(test_dir.path(), &port, None)?;

    // Give it some time to provide the TCP socket
    tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;

    let mut id_buf: [u8; 2] = [0; 2];

    let socket_addr = SocketAddr::new(ip_addr, port);
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
async fn test_pull_legacy_ipv4() -> AnyhowResult<()> {
    _test_pull_legacy(
        "test_pull_legacy_ipv4",
        IpAddr::V4(Ipv4Addr::LOCALHOST),
        PULL_LEGACY_PORT,
    )
    .await
}

#[tokio::test(flavor = "multi_thread")]
async fn test_pull_legacy_ipv6() -> AnyhowResult<()> {
    _test_pull_legacy(
        "test_pull_legacy_ipv6",
        IpAddr::V6(Ipv6Addr::LOCALHOST),
        PULL_LEGACY_PORT + 1,
    )
    .await
}

async fn _test_pull_legacy(prefix: &str, ip_addr: IpAddr, port: u16) -> AnyhowResult<()> {
    if agent::is_elevation_required() {
        println!("Test is skipped, must be in elevated mode");
        return Ok(());
    }

    let test_dir = common::setup_test_dir(prefix);
    TrustFixture::setup(test_dir.path())?;
    // Manually create legacy pull file to test scenario where we have connections AND the legacy
    // marker; this shouldn't happen in reality, but who knows ...
    std::fs::write(test_dir.path().join("allow-legacy-pull"), "")?;
    let agent_stream_fixture = AgentStreamFixture::setup(test_dir.path());
    let p = find_available_port_if_busy(port);
    let pull_proc_fixture = PullProcessFixture::setup(
        test_dir.path(),
        &p,
        agent_stream_fixture.get_agent_channel(),
    )?;

    // Give it some time to provide the TCP socket.
    tokio::time::sleep(tokio::time::Duration::from_millis(1500)).await;

    let socket_addr = SocketAddr::new(ip_addr, p);
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
async fn test_pull_no_connections_ipv4() -> AnyhowResult<()> {
    _test_pull_no_connections(
        "test_pull_no_connections_ipv4",
        IpAddr::V4(Ipv4Addr::LOCALHOST),
        PULL_NO_CONNECTION_PORT,
    )
    .await
}

#[tokio::test(flavor = "multi_thread")]
async fn test_pull_no_connections_ipv6() -> AnyhowResult<()> {
    _test_pull_no_connections(
        "test_pull_no_connections_ipv6",
        IpAddr::V6(Ipv6Addr::LOCALHOST),
        PULL_NO_CONNECTION_PORT + 1,
    )
    .await
}

async fn _test_pull_no_connections(prefix: &str, ip_addr: IpAddr, port: u16) -> AnyhowResult<()> {
    if agent::is_elevation_required() {
        println!("Test is skipped, must be in elevated mode");
        return Ok(());
    }

    let test_dir = common::setup_test_dir(prefix);
    let pull_proc_fixture = PullProcessFixture::setup(test_dir.path(), &port, None)?;

    // Give it some time to provide the TCP socket (it shouldn't)
    tokio::time::sleep(tokio::time::Duration::from_millis(1500)).await;

    let socket_addr = SocketAddr::new(ip_addr, port);
    assert!(std::net::TcpStream::connect(socket_addr).is_err());

    teardown(test_dir, pull_proc_fixture, None)
        .await
        .context("Teardown failed")
}

#[tokio::test(flavor = "multi_thread")]
async fn test_pull_reload_ipv4() -> AnyhowResult<()> {
    _test_pull_reload(
        "test_pull_reload_ipv4",
        IpAddr::V4(Ipv4Addr::LOCALHOST),
        PULL_RELOAD_PORT,
    )
    .await
}

#[tokio::test(flavor = "multi_thread")]
async fn test_pull_reload_ipv6() -> AnyhowResult<()> {
    _test_pull_reload(
        "test_pull_reload_ipv6",
        IpAddr::V6(Ipv6Addr::LOCALHOST),
        PULL_RELOAD_PORT + 1,
    )
    .await
}
async fn _test_pull_reload(prefix: &str, ip_addr: IpAddr, port: u16) -> AnyhowResult<()> {
    if agent::is_elevation_required() {
        println!("Test is skipped, must be in elevated mode");
        return Ok(());
    }
    let test_dir = common::setup_test_dir(prefix);
    TrustFixture::setup(test_dir.path())?;
    let p = find_available_port_if_busy(port);
    let pull_proc_fixture = PullProcessFixture::setup(test_dir.path(), &p, None)?;

    // Give it some time to provide the TCP socket
    tokio::time::sleep(tokio::time::Duration::from_millis(1500)).await;

    let socket_addr = SocketAddr::new(ip_addr, p);
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
    assert!(
        message_buf.is_empty(),
        "port is {} message is {:#?}",
        p,
        message_buf
    );
    // give windows some time to close socket
    #[cfg(windows)]
    tokio::time::sleep(tokio::time::Duration::from_millis(1500)).await;

    // Time needed to close socket is highly variable.
    let mut socket_closed = std::net::TcpStream::connect(socket_addr).is_err();
    // So retry rather than cause test to fail.
    for delay in 1..10 {
        if socket_closed {
            break;
        }
        // Delay before retry on socket
        tokio::time::sleep(tokio::time::Duration::from_millis(delay * delay * 100)).await;
        socket_closed = std::net::TcpStream::connect(socket_addr).is_err();
    }
    // If socket is still not closed we will fail.
    assert!(socket_closed, "port is {} ", p,);

    teardown(test_dir, pull_proc_fixture, None)
        .await
        .context("Teardown failed")
}
