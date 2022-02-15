// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use core::future::Future;
use std::collections::HashMap;
use std::error::Error;
use std::io::Result as IoResult;
use std::sync::Arc;

use super::{config, constants, monitoring_data, tls_server};
use anyhow::{anyhow, Context, Result as AnyhowResult};
use log::{info, warn};
use std::net::{IpAddr, SocketAddr};
use tokio::io::AsyncWriteExt;
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::Semaphore;
use tokio::time::{timeout, Duration};
use tokio_rustls::TlsAcceptor;

const TLS_ID: &[u8] = b"16";
const HEADER_VERSION: &[u8] = b"\x00\x00";

pub struct MaxConnectionsGuard {
    max_connections: usize,
    active_connections: HashMap<IpAddr, Arc<Semaphore>>,
}

impl MaxConnectionsGuard {
    pub fn new(max_connections: usize) -> Self {
        MaxConnectionsGuard {
            max_connections,
            active_connections: HashMap::new(),
        }
    }

    pub fn try_make_task_for_addr(
        &mut self,
        addr: SocketAddr,
        fut: impl Future<Output = AnyhowResult<()>>,
    ) -> AnyhowResult<impl Future<Output = AnyhowResult<()>>> {
        let ip_addr = addr.ip();
        let sem = self
            .active_connections
            .entry(ip_addr)
            .or_insert_with(|| Arc::new(Semaphore::new(self.max_connections)));
        if let Ok(permit) = sem.clone().try_acquire_owned() {
            Ok(async move {
                let res = fut.await;
                drop(permit);
                res
            })
        } else {
            Err(anyhow!("Too many active connections"))
        }
    }
}

pub fn pull(
    registry: config::Registry,
    legacy_pull_marker: std::path::PathBuf,
    port: String,
    max_connections: usize,
    _allowed_ip: Vec<String>, // TODO: use this value!
) -> AnyhowResult<()> {
    let pull_config = PullConfigurationImpl::new(registry, legacy_pull_marker)?;
    let guard = MaxConnectionsGuard::new(max_connections);
    // Plain agent output for legacy handling only
    let collect_plain_mondata = monitoring_data::async_collect;
    // Compressed monitoring data with internal protocol handler
    let collect_encoded_mondata = collect_and_encode_mondata;
    _pull(
        pull_config,
        guard,
        collect_plain_mondata,
        collect_encoded_mondata,
        "0.0.0.0",
        &port,
        constants::CONNECTION_TIMEOUT,
    )
}

#[tokio::main(flavor = "current_thread")]
pub async fn _pull<Fut1, Fut2>(
    mut pull_config: impl PullConfiguration,
    mut guard: MaxConnectionsGuard,
    collect_plain_mondata: impl Fn() -> Fut1,
    collect_encoded_mondata: impl Fn() -> Fut2,
    ipmask: &str,
    port: &str,
    timeout: u64,
) -> AnyhowResult<()>
where
    // TODO: Unify these two types. However, they must still be
    // specified seperately as they are two seperate opaque types for the Rust compiler.
    Fut1: Future<Output = IoResult<Vec<u8>>> + Send + 'static,
    Fut2: Future<Output = AnyhowResult<Vec<u8>>> + Send + 'static,
{
    let listener = TcpListener::bind(format!("{}:{}", ipmask, port)).await?;

    loop {
        let (stream, addr) = listener
            .accept()
            .await
            .context("Failed accepting pull connection")?;
        info!("{}: Handling pull request", addr);

        pull_config.refresh()?;

        let plain_mondata = collect_plain_mondata();
        let encoded_mondata = collect_encoded_mondata();

        let request_handler_fut = handle_request(
            stream,
            plain_mondata,
            encoded_mondata,
            pull_config.is_legacy_pull(),
            pull_config.tls_acceptor(),
            timeout,
        );

        match guard.try_make_task_for_addr(addr, request_handler_fut) {
            Ok(connection_fut) => {
                tokio::spawn(async move {
                    if let Err(err) = connection_fut.await {
                        warn!("PULL: Request from {} failed: {}", addr, err)
                    };
                });
            }
            Err(error) => {
                warn!("PULL: Request from {} failed: {}", addr, error);
            }
        }
    }
}

pub trait PullConfiguration {
    fn refresh(&mut self) -> AnyhowResult<()>;
    fn tls_acceptor(&self) -> TlsAcceptor;
    fn is_legacy_pull(&self) -> bool;
}
struct PullConfigurationImpl {
    legacy_pull: bool,
    tls_acceptor: TlsAcceptor,
    registry: config::Registry,
    legacy_pull_marker: std::path::PathBuf,
}

impl PullConfigurationImpl {
    pub fn new(
        registry: config::Registry,
        legacy_pull_marker: std::path::PathBuf,
    ) -> AnyhowResult<Self> {
        Ok(PullConfigurationImpl {
            legacy_pull: is_legacy_pull(&registry, &legacy_pull_marker),
            tls_acceptor: tls_server::tls_acceptor(registry.pull_connections())
                .context("Could not initialize TLS.")?,
            registry,
            legacy_pull_marker,
        })
    }
}

impl PullConfiguration for PullConfigurationImpl {
    fn refresh(&mut self) -> AnyhowResult<()> {
        if self.registry.refresh()? {
            self.tls_acceptor = tls_server::tls_acceptor(self.registry.pull_connections())
                .context("Could not initialize TLS.")?;
            self.legacy_pull = is_legacy_pull(&self.registry, &self.legacy_pull_marker);
        };
        Ok(())
    }

    fn tls_acceptor(&self) -> TlsAcceptor {
        self.tls_acceptor.clone()
    }

    fn is_legacy_pull(&self) -> bool {
        self.legacy_pull
    }
}

fn is_legacy_pull(registry: &config::Registry, legacy_pull_marker: &std::path::Path) -> bool {
    if legacy_pull_marker.exists() {
        return false;
    }
    if !registry.is_empty() {
        return false;
    }
    true
}

async fn handle_request(
    mut stream: TcpStream,
    plain_mondata: impl Future<Output = IoResult<Vec<u8>>>,
    encoded_modata: impl Future<Output = AnyhowResult<Vec<u8>>>,
    is_legacy_pull: bool,
    tls_acceptor: TlsAcceptor,
    timeout: u64,
) -> AnyhowResult<()> {
    if is_legacy_pull {
        return handle_legacy_pull_request(stream, plain_mondata, timeout).await;
    }

    let handshake = with_timeout(
        async move {
            stream.write_all(TLS_ID).await?;
            stream.flush().await?;
            tls_acceptor.accept(stream).await
        },
        timeout,
    );

    let (mon_data, tls_stream) = tokio::join!(encoded_modata, handshake);
    let mon_data = mon_data?;
    let mut tls_stream = tls_stream?;

    with_timeout(
        async move {
            tls_stream.write_all(&mon_data).await?;
            tls_stream.flush().await
        },
        timeout,
    )
    .await
}

async fn handle_legacy_pull_request(
    mut stream: TcpStream,
    plain_mondata: impl Future<Output = IoResult<Vec<u8>>>,
    timeout: u64,
) -> AnyhowResult<()> {
    let mon_data = plain_mondata
        .await
        .context("Error collecting monitoring data.")?;

    with_timeout(
        async move {
            stream.write_all(&mon_data).await?;
            stream.flush().await
        },
        timeout,
    )
    .await
}

pub fn disallow_legacy_pull(legacy_pull_marker: &std::path::Path) -> std::io::Result<()> {
    if !legacy_pull_marker.exists() {
        return Ok(());
    }

    std::fs::remove_file(legacy_pull_marker)
}

//TODO: Move this to monitoring_data.rs
pub async fn collect_and_encode_mondata() -> AnyhowResult<Vec<u8>> {
    let mon_data = monitoring_data::async_collect()
        .await
        .context("Error collecting monitoring data.")?;
    encode_data_for_transport(&mon_data)
}

fn encode_data_for_transport(raw_agent_output: &[u8]) -> AnyhowResult<Vec<u8>> {
    let mut encoded_data = HEADER_VERSION.to_vec();
    encoded_data.append(&mut monitoring_data::compression_header_info().pull);
    encoded_data.append(
        &mut monitoring_data::compress(raw_agent_output)
            .context("Error compressing monitoring data")?,
    );
    Ok(encoded_data)
}

async fn with_timeout<T, E: 'static + Error + Send + Sync>(
    fut: impl Future<Output = Result<T, E>>,
    seconds: u64,
) -> AnyhowResult<T> {
    match timeout(Duration::from_secs(seconds), fut).await {
        Ok(inner) => Ok(inner?),
        Err(err) => Err(anyhow!(err)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encode_data_for_transport() {
        let mut expected_result = b"\x00\x00\x01".to_vec();
        expected_result.append(&mut monitoring_data::compress(b"abc").unwrap());
        assert_eq!(encode_data_for_transport(b"abc").unwrap(), expected_result);
    }
}
