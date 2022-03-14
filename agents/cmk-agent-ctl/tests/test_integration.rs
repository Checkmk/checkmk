// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// Test files are compiled to seperate crates, so there
// may be some unused functions in the common module
#![allow(dead_code)]
mod common;

use anyhow::Result as AnyhowResult;
#[cfg(unix)]
use std::io::{Read, Write};

#[test]
fn test_pull_inconsistent_cert() -> AnyhowResult<()> {
    let test_dir = tempfile::Builder::new()
        .prefix("cmk_agent_ctl_test_pull")
        .tempdir()
        .unwrap();
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
        "1234",
        "dummy".into(),
        registry,
    ))
    .unwrap_err();

    assert!(error.to_string().contains("Could not initialize TLS"));

    Ok(())
}

#[cfg(unix)]
#[tokio::test(flavor = "multi_thread")]
async fn test_pull_tls() -> AnyhowResult<()> {
    // Setup test data
    let test_dir = tempfile::Builder::new()
        .prefix("cmk_agent_ctl_test_pull_tls")
        .tempdir()
        .unwrap();
    let test_path = test_dir.path();
    std::env::set_var("DEBUG_HOME_DIR", test_path.to_str().unwrap());
    std::fs::create_dir(test_path.join("run"))?;
    let test_port = "9999";
    let test_agent_output = "some test agent output";
    let mut compressed_agent_output = b"\x00\x00\x01".to_vec();
    let mut zlib_enc = flate2::write::ZlibEncoder::new(Vec::new(), flate2::Compression::default());
    zlib_enc.write_all(test_agent_output.as_bytes())?;
    compressed_agent_output.append(&mut zlib_enc.finish()?);
    let (uuid, pull_config, certs) = common::testing_pull_setup(
        test_path,
        test_port,
        test_path.join("run/check-mk-agent.socket").into(),
    );

    // Uncomment for debugging
    // common::init_logging(&test_path.join("log"))?;

    // Provide agent stream for the pull thread
    let agent_socket_path = test_path.join("run/check-mk-agent.socket");
    let unix_socket = tokio::net::UnixListener::bind(agent_socket_path).unwrap();
    let agent_stream_thread =
        tokio::spawn(common::unix::agent_loop(unix_socket, test_agent_output));

    // Setup the pull thread that we intend to test
    let pull_thread = tokio::task::spawn(cmk_agent_ctl::modes::pull::async_pull(pull_config));
    // Give it some time to provide the TCP socket
    tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

    let mut id_buf: [u8; 2] = [0; 2];

    // Talk to the pull thread successfully
    let mut message_buf: Vec<u8> = vec![];
    let mut client_connection = common::testing_tls_client_connection(certs.clone(), &uuid);
    let mut tcp_stream = std::net::TcpStream::connect(format!("127.0.0.1:{}", test_port))?;
    tcp_stream.read_exact(&mut id_buf)?;
    assert_eq!(&id_buf, b"16");
    let mut tls_stream = rustls::Stream::new(&mut client_connection, &mut tcp_stream);
    tls_stream.read_to_end(&mut message_buf)?;
    assert_eq!(message_buf, compressed_agent_output);

    tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;
    tokio::task::yield_now().await;

    // Talk to the pull thread using an unknown uuid
    let mut client_connection =
        common::testing_tls_client_connection(certs, "certainly_wrong_uuid");
    let mut tcp_stream = std::net::TcpStream::connect(format!("127.0.0.1:{}", test_port))?;
    tcp_stream.read_exact(&mut id_buf)?;
    assert_eq!(&id_buf, b"16");
    let mut tls_stream = rustls::Stream::new(&mut client_connection, &mut tcp_stream);
    assert!(tls_stream.read_to_end(&mut message_buf).is_err());

    tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;
    tokio::task::yield_now().await;

    // Talk too much
    let mut tcp_stream_1 = std::net::TcpStream::connect(format!("127.0.0.1:{}", test_port))?;
    let mut tcp_stream_2 = std::net::TcpStream::connect(format!("127.0.0.1:{}", test_port))?;
    let mut tcp_stream_3 = std::net::TcpStream::connect(format!("127.0.0.1:{}", test_port))?;
    let mut tcp_stream_4 = std::net::TcpStream::connect(format!("127.0.0.1:{}", test_port))?;
    assert!(tcp_stream_1.read_exact(&mut id_buf).is_ok());
    assert!(tcp_stream_2.read_exact(&mut id_buf).is_ok());
    assert!(tcp_stream_3.read_exact(&mut id_buf).is_ok());
    assert!(tcp_stream_4.read_exact(&mut id_buf).is_err());

    // Kill threads
    agent_stream_thread.abort();
    assert!(agent_stream_thread.await.unwrap_err().is_cancelled());
    pull_thread.abort();
    assert!(pull_thread.await.unwrap_err().is_cancelled());

    Ok(())
}
