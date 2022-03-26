// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// Test files are compiled to seperate crates, so there
// may be some unused functions in the common module
#![allow(dead_code)]
mod common;

use anyhow::Result as AnyhowResult;
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
    #[cfg(unix)]
    let agent_socket_address = test_path
        .join("run/check-mk-agent.socket")
        .into_os_string()
        .into_string()
        .unwrap();
    #[cfg(windows)]
    let agent_socket_address = "localhost:1999".to_string();
    let (uuid, pull_config, certs) =
        common::testing_pull_setup(test_path, test_port, agent_socket_address.as_str().into());

    // Uncomment for debugging
    // common::init_logging(&test_path.join("log"))?;

    // Provide agent stream for the pull thread
    let agent_stream_thread = tokio::spawn(common::agent::agent_response_loop(
        agent_socket_address,
        test_agent_output,
    ));

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

    // Talk to the pull thread using an unknown uuid
    let mut client_connection =
        common::testing_tls_client_connection(certs, "certainly_wrong_uuid");
    let mut tcp_stream = std::net::TcpStream::connect(format!("127.0.0.1:{}", test_port))?;
    tcp_stream.read_exact(&mut id_buf)?;
    assert_eq!(&id_buf, b"16");
    let mut tls_stream = rustls::Stream::new(&mut client_connection, &mut tcp_stream);
    assert!(tls_stream.read_to_end(&mut message_buf).is_err());

    //TODO(au): Investigate why it takes so long to release the MaxConnections semaphore, because ...
    tokio::time::sleep(tokio::time::Duration::from_millis(200)).await;

    // Talk too much
    let mut tcp_stream_1 = std::net::TcpStream::connect(format!("127.0.0.1:{}", test_port))?;
    let mut tcp_stream_2 = std::net::TcpStream::connect(format!("127.0.0.1:{}", test_port))?;
    let mut tcp_stream_3 = std::net::TcpStream::connect(format!("127.0.0.1:{}", test_port))?;
    let mut tcp_stream_4 = std::net::TcpStream::connect(format!("127.0.0.1:{}", test_port))?;
    // NOTE(sk): Give peers some time to perform their operations.
    tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
    assert!(tcp_stream_1.read_exact(&mut id_buf).is_ok());
    assert!(tcp_stream_2.read_exact(&mut id_buf).is_ok());
    //TODO(au): ... on my Windows VM, this check frequently fails on the third connection without the sleep(200)
    assert!(tcp_stream_3.read_exact(&mut id_buf).is_ok());
    assert!(tcp_stream_4.read_exact(&mut id_buf).is_err());

    // Done, kill threads
    agent_stream_thread.abort();
    assert!(agent_stream_thread.await.unwrap_err().is_cancelled());
    pull_thread.abort();
    assert!(pull_thread.await.unwrap_err().is_cancelled());

    Ok(())
}

#[tokio::test(flavor = "multi_thread")]
async fn test_pull_legacy() -> AnyhowResult<()> {
    // Setup test data
    let test_dir = tempfile::Builder::new()
        .prefix("cmk_agent_ctl_test_pull_legacy")
        .tempdir()
        .unwrap();
    let test_path = test_dir.path();
    std::env::set_var("DEBUG_HOME_DIR", test_path.to_str().unwrap());
    std::fs::create_dir(test_path.join("run"))?;
    let test_port = "9998";
    let test_agent_output = "some test agent output";
    #[cfg(unix)]
    let agent_socket_address = test_path
        .join("run/check-mk-agent.socket")
        .into_os_string()
        .into_string()
        .unwrap();
    #[cfg(windows)]
    let agent_socket_address = "localhost:1998".to_string();
    let (_uuid, pull_config, _certs) =
        common::testing_pull_setup(test_path, test_port, agent_socket_address.as_str().into());
    pull_config.registry.save()?;

    // Uncomment for debugging.
    // common::init_logging(&test_path.join("log"))?;

    // Provide agent stream for the pull thread.
    let agent_stream_thread = tokio::spawn(common::agent::agent_response_loop(
        agent_socket_address,
        test_agent_output,
    ));

    // Setup the pull thread that we intend to test.
    let pull_thread = tokio::task::spawn(cmk_agent_ctl::modes::pull::async_pull(pull_config));
    // Give it some time to provide the TCP socket.
    tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

    // Try to read plain data from TLS controller.
    // Connection will timeout after 1 sec, only sending the 16.
    let mut message_buf: Vec<u8> = vec![];
    let mut tcp_stream = std::net::TcpStream::connect(format!("127.0.0.1:{}", test_port))?;
    tcp_stream.read_to_end(&mut message_buf)?;
    assert_eq!(message_buf, b"16");

    // Create allow_legacy_pull file, but still be registered.
    // Connection will timeout after 1 sec, only sending the 16.
    let mut message_buf: Vec<u8> = vec![];
    std::fs::File::create(test_path.join("allow_legacy_pull"))?;
    let mut tcp_stream = std::net::TcpStream::connect(format!("127.0.0.1:{}", test_port))?;
    tcp_stream.read_to_end(&mut message_buf)?;
    assert_eq!(message_buf, b"16");

    // Delete registry. Now we can finally receive our output in plain text.
    let mut message_buf: Vec<u8> = vec![];
    std::fs::remove_file(test_path.join("registered_connections.json"))?;
    let mut tcp_stream = std::net::TcpStream::connect(format!("127.0.0.1:{}", test_port))?;
    tcp_stream.read_to_end(&mut message_buf)?;
    assert_eq!(message_buf, test_agent_output.as_bytes());

    // Disallow legacy pull. First successing connection will be dropped, thus the response being empty.
    // The TCP socket will close afterwards, leading to a refused connection on connect().
    let mut message_buf: Vec<u8> = vec![];
    std::fs::remove_file(test_path.join("allow_legacy_pull"))?;
    let mut tcp_stream = std::net::TcpStream::connect(format!("127.0.0.1:{}", test_port))?;
    tcp_stream.read_to_end(&mut message_buf)?;
    assert_eq!(message_buf, b"");
    assert!(std::net::TcpStream::connect(format!("127.0.0.1:{}", test_port)).is_err());

    // Done, kill threads
    agent_stream_thread.abort();
    assert!(agent_stream_thread.await.unwrap_err().is_cancelled());
    pull_thread.abort();
    assert!(pull_thread.await.unwrap_err().is_cancelled());

    Ok(())
}
