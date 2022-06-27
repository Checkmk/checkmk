// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use core::future::Future;
use std::collections::HashMap;
use std::error::Error;
use std::sync::Arc;

use crate::{config, misc::anyhow_error_to_human_redable, monitoring_data, tls_server, types};
use anyhow::{anyhow, bail, Context, Error as AnyhowError, Result as AnyhowResult};
use async_trait::async_trait;
use log::{debug, info, warn};
use socket2::{Domain, SockAddr, Socket, Type};
use std::net::{IpAddr, Ipv4Addr, Ipv6Addr, SocketAddr, TcpListener as TcpListenerStd};
use tokio::io::AsyncWriteExt;
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::Semaphore;
use tokio::time::{timeout, Duration};
use tokio_rustls::TlsAcceptor;

const TLS_ID: &[u8] = b"16";
const HEADER_VERSION: &[u8] = b"\x00\x00";
const ONE_MINUTE: u64 = 60;
const FIVE_MINUTES: u64 = 300;

struct ListeningConfig {
    pub addr_v4: Ipv4Addr,
    pub addr_v6: Ipv6Addr,
    pub port: u16,
}

trait PullState {
    fn refresh(&mut self) -> AnyhowResult<()>;
    fn tls_acceptor(&self) -> TlsAcceptor;
    fn allow_legacy_pull(&self) -> bool;
    fn is_active(&self) -> bool;
    fn ip_allowlist(&self) -> &[String];
    fn listening_config(&self) -> ListeningConfig;
    fn connection_timeout(&self) -> u64;
}
struct PullStateImpl {
    allow_legacy_pull: bool,
    tls_acceptor: TlsAcceptor,
    config: config::PullConfig,
}

impl std::convert::TryFrom<config::PullConfig> for PullStateImpl {
    type Error = AnyhowError;

    fn try_from(config: config::PullConfig) -> AnyhowResult<Self> {
        Ok(Self {
            allow_legacy_pull: config.allow_legacy_pull(),
            tls_acceptor: tls_server::tls_acceptor(config.connections())
                .context("Could not initialize TLS.")?,
            config,
        })
    }
}

impl PullState for PullStateImpl {
    fn refresh(&mut self) -> AnyhowResult<()> {
        if self.config.refresh()? {
            self.tls_acceptor = tls_server::tls_acceptor(self.config.connections())
                .context("Could not initialize TLS.")?;
        };
        self.allow_legacy_pull = self.config.allow_legacy_pull();
        Ok(())
    }

    fn tls_acceptor(&self) -> TlsAcceptor {
        self.tls_acceptor.clone()
    }

    fn allow_legacy_pull(&self) -> bool {
        self.allow_legacy_pull
    }

    fn is_active(&self) -> bool {
        self.allow_legacy_pull || self.config.has_connections()
    }

    fn ip_allowlist(&self) -> &[String] {
        &self.config.allowed_ip
    }

    fn listening_config(&self) -> ListeningConfig {
        ListeningConfig {
            addr_v4: Ipv4Addr::UNSPECIFIED,
            addr_v6: Ipv6Addr::UNSPECIFIED,
            port: self.config.port,
        }
    }

    fn connection_timeout(&self) -> u64 {
        self.config.connection_timeout
    }
}

#[async_trait]
trait AgentOutputCollector: std::clone::Clone + Sync + Send + 'static {
    async fn plain_output(&self, remote_ip: std::net::IpAddr) -> AnyhowResult<Vec<u8>>;
    async fn encoded_output(&self, remote_ip: std::net::IpAddr) -> AnyhowResult<Vec<u8>>;
}

#[derive(Clone)]
struct AgentOutputCollectorImpl {
    agent_channel: types::AgentChannel,
}

impl AgentOutputCollectorImpl {
    fn encode(&self, raw_agent_output: &[u8]) -> AnyhowResult<Vec<u8>> {
        let mut encoded_data = HEADER_VERSION.to_vec();
        encoded_data.append(&mut monitoring_data::compression_header_info().pull);
        encoded_data.append(
            &mut monitoring_data::compress(raw_agent_output)
                .context("Error compressing monitoring data")?,
        );
        Ok(encoded_data)
    }
}

impl std::convert::From<types::AgentChannel> for AgentOutputCollectorImpl {
    fn from(agent_channel: types::AgentChannel) -> Self {
        AgentOutputCollectorImpl { agent_channel }
    }
}

impl std::convert::From<&types::AgentChannel> for AgentOutputCollectorImpl {
    fn from(agent_channel: &types::AgentChannel) -> Self {
        AgentOutputCollectorImpl {
            agent_channel: agent_channel.clone(),
        }
    }
}

#[async_trait]
impl AgentOutputCollector for AgentOutputCollectorImpl {
    async fn plain_output(&self, remote_ip: std::net::IpAddr) -> AnyhowResult<Vec<u8>> {
        Ok(monitoring_data::async_collect(&self.agent_channel, remote_ip).await?)
    }

    async fn encoded_output(&self, remote_ip: std::net::IpAddr) -> AnyhowResult<Vec<u8>> {
        let mon_data = monitoring_data::async_collect(&self.agent_channel, remote_ip)
            .await
            .context("Error collecting monitoring data.")?;
        self.encode(&mon_data)
    }
}
struct MaxConnectionsGuard {
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
                debug!("processed task!");
                res
            })
        } else {
            debug!("Too many active connections");
            Err(anyhow!("Too many active connections"))
        }
    }
}

pub fn pull(pull_config: config::PullConfig) -> AnyhowResult<()> {
    pull_runtime_wrapper(pull_config)
}

pub async fn async_pull(pull_config: config::PullConfig) -> AnyhowResult<()> {
    let guard = MaxConnectionsGuard::new(pull_config.max_connections);
    let agent_output_collector = AgentOutputCollectorImpl::from(&pull_config.agent_channel);
    let pull_state = PullStateImpl::try_from(pull_config)?;
    _pull(pull_state, guard, agent_output_collector).await
}

#[tokio::main(flavor = "current_thread")]
async fn pull_runtime_wrapper(pull_config: config::PullConfig) -> AnyhowResult<()> {
    async_pull(pull_config).await
}

async fn _pull(
    mut pull_state: impl PullState,
    mut guard: MaxConnectionsGuard,
    agent_output_collector: impl AgentOutputCollector,
) -> AnyhowResult<()> {
    loop {
        if !pull_state.is_active() {
            tokio::time::sleep(Duration::from_secs(ONE_MINUTE)).await;
            // Allow a crash due to a failing registry reload. It's not likely to recover
            // here without action taken, and it's vital for all connections.
            pull_state.refresh()?;
            continue;
        }
        info!("Start listening for incoming pull requests");
        _pull_cycle(&mut pull_state, &mut guard, agent_output_collector.clone()).await?;
    }
}

fn configure_socket(socket: Socket) -> AnyhowResult<Socket> {
    socket.set_nonblocking(true)?;
    // https://stackoverflow.com/questions/3229860/what-is-the-meaning-of-so-reuseaddr-setsockopt-option-linux
    // Allow re-using the address, even if there are still connections. After sending the agent
    // data, we end up with a waiting connection which will be dropped at some point, but not
    // immediately (this is OK, standard TCP protocol). However, this will block the re-creation
    // of the socket if the agent controller is restarted (agent update or manual restart).
    socket.set_reuse_address(true)?;
    Ok(socket)
}

fn tcp_listener_v4(address: Ipv4Addr, port: u16) -> AnyhowResult<TcpListenerStd> {
    let socket = configure_socket(Socket::new(Domain::IPV4, Type::STREAM, None)?)?;
    socket.bind(&SockAddr::from(SocketAddr::new(IpAddr::V4(address), port)))?;
    socket.listen(4096)?;
    Ok(socket.into())
}

fn tcp_listener_v6(address: Ipv6Addr, port: u16) -> AnyhowResult<TcpListenerStd> {
    let socket = configure_socket(Socket::new(Domain::IPV6, Type::STREAM, None)?)?;
    socket.set_only_v6(false)?;
    socket.bind(&SockAddr::from(SocketAddr::new(IpAddr::V6(address), port)))?;
    socket.listen(4096)?;
    Ok(socket.into())
}

fn tcp_listener(listening_config: ListeningConfig) -> AnyhowResult<TcpListenerStd> {
    let err_v6 = match tcp_listener_v6(listening_config.addr_v6, listening_config.port) {
        Ok(listener) => {
            info!(
                "Listening on {} for incoming pull connections (IPv6 & IPv4 if activated)",
                listener.local_addr()?
            );
            return Ok(listener);
        }
        Err(err_v6) => err_v6,
    };
    info!("Failed to open IPv6 socket for pull connections, attempting with IPv4");
    let err_v4 = match tcp_listener_v4(listening_config.addr_v4, listening_config.port) {
        Ok(listener) => {
            info!(
                "Listening on {} for incoming pull connections (IPv4)",
                listener.local_addr()?
            );
            return Ok(listener);
        }
        Err(err_v4) => err_v4,
    };
    bail!(
        "Failed to listen on TCP socket for incoming pull connections.\n\nError with IPV6:\n{}\n\nError with IPV4:\n{}",
        anyhow_error_to_human_redable(&err_v6),
        anyhow_error_to_human_redable(&err_v4),
    );
}

async fn _pull_cycle(
    pull_state: &mut impl PullState,
    guard: &mut MaxConnectionsGuard,
    agent_output_collector: impl AgentOutputCollector,
) -> AnyhowResult<()> {
    let listener = TcpListener::from_std(tcp_listener(pull_state.listening_config())?)?;

    loop {
        let (stream, remote) = match match timeout(
            Duration::from_secs(FIVE_MINUTES),
            listener.accept(),
        )
        .await
        {
            Ok(accepted_result) => accepted_result,
            Err(_) => {
                debug!(
                        "Got no pull request within five minutes. Registration may have changed, thus restarting pull handling."
                    );
                return Ok(());
            }
        } {
            Ok(accepted) => accepted,
            Err(error) => {
                warn!("Failed accepting pull connection. ({})", error);
                continue;
            }
        };

        if !is_addr_allowed(&remote, pull_state.ip_allowlist()) {
            warn!(
                "{}: Rejecting pull request - connection from IP is not allowed.",
                remote
            );
            continue;
        }

        // Act on most recent registration data
        pull_state.refresh()?;

        // Check if pull was deactivated meanwhile before actually handling the request.
        if !pull_state.is_active() {
            info!("Detected empty registry, closing current connection and stop listening.");
            return Ok(());
        }

        info!("{}: Handling pull request.", remote);

        let request_handler_fut = handle_request(
            stream,
            agent_output_collector.clone(),
            remote.ip(),
            pull_state.allow_legacy_pull(),
            pull_state.tls_acceptor(),
            pull_state.connection_timeout(),
        );

        match guard.try_make_task_for_addr(remote, request_handler_fut) {
            Ok(connection_fut) => {
                tokio::spawn(async move {
                    if let Err(err) = connection_fut.await {
                        warn!("{}: Request failed. ({})", remote, err)
                    };
                });
            }
            Err(error) => {
                warn!("{}: Request failed. ({})", remote, error);
            }
        }
        debug!("{}: Handling pull request DONE (Task detached).", remote);
    }
}

fn is_addr_allowed(addr: &SocketAddr, allowed_ip: &[String]) -> bool {
    if allowed_ip.is_empty() {
        return true;
    }
    let can_addr = to_canonical(addr.ip());
    for ip in allowed_ip {
        // Our list may contain both network, ip addresses and bad data(!)
        // Examples: network - 192.168.1.14/24, address - 127.0.0.1
        if let Ok(allowed_net) = ip.parse::<ipnet::IpNet>() {
            if allowed_net.contains(&can_addr) {
                return true;
            }
        }
        if let Ok(allowed_addr) = ip.parse::<IpAddr>() {
            if allowed_addr == can_addr {
                return true;
            }
        }
        // NOTE: no reporting about bad data here.
        // We prefer to ignore error here: despite the possibility
        // to have invalid settings we should check and report this once
    }
    false
}

fn to_canonical(ip_addr: IpAddr) -> IpAddr {
    //IpAddr::to_canonical is unstable API :-(
    match ip_addr {
        IpAddr::V4(_v4) => ip_addr,
        IpAddr::V6(v6) => {
            let v4_map_subnet =
                ipnet::Ipv6Net::new(Ipv6Addr::new(0, 0, 0, 0, 0, 0xffff, 0, 0), 96).unwrap();
            if v4_map_subnet.contains(&v6) {
                IpAddr::V4(v6.to_ipv4().unwrap())
            } else {
                ip_addr
            }
        }
    }
}

async fn handle_request(
    mut stream: TcpStream,
    agent_output_collector: impl AgentOutputCollector,
    remote_ip: IpAddr,
    is_legacy_pull: bool,
    tls_acceptor: TlsAcceptor,
    connection_timeout: u64,
) -> AnyhowResult<()> {
    if is_legacy_pull {
        return handle_legacy_pull_request(
            stream,
            agent_output_collector.plain_output(remote_ip),
            connection_timeout,
        )
        .await;
    }
    debug!("handle_request starts");

    let handshake = with_timeout(
        async move {
            stream.write_all(TLS_ID).await?;
            stream.flush().await?;
            tls_acceptor.accept(stream).await
        },
        connection_timeout,
    );

    let encoded_mondata = agent_output_collector.encoded_output(remote_ip);

    let (mon_data, tls_stream) = tokio::join!(encoded_mondata, handshake);
    let mon_data = mon_data?;
    let mut tls_stream = tls_stream?;
    with_timeout(
        async move {
            tls_stream.write_all(&mon_data).await?;
            tls_stream.flush().await
        },
        connection_timeout,
    )
    .await
}

async fn handle_legacy_pull_request(
    mut stream: TcpStream,
    plain_mondata: impl Future<Output = AnyhowResult<Vec<u8>>>,
    connection_timeout: u64,
) -> AnyhowResult<()> {
    let mon_data = plain_mondata
        .await
        .context("Error collecting monitoring data.")?;

    with_timeout(
        async move {
            stream.write_all(&mon_data).await?;
            stream.flush().await
        },
        connection_timeout,
    )
    .await
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
    use std::str::FromStr;

    use super::*;
    use crate::types::AgentChannel;

    #[test]
    fn test_encode_data_for_transport() {
        let mut expected_result = b"\x00\x00\x01".to_vec();
        expected_result.append(&mut monitoring_data::compress(b"abc").unwrap());
        let agout = AgentOutputCollectorImpl::from(AgentChannel::from("dummy"));
        assert_eq!(agout.encode(b"abc").unwrap(), expected_result);
    }

    fn listening_config(port: u16) -> ListeningConfig {
        ListeningConfig {
            addr_v4: Ipv4Addr::UNSPECIFIED,
            addr_v6: Ipv6Addr::UNSPECIFIED,
            port,
        }
    }

    // we rely on our CI system using IPv6
    #[test]
    fn test_tcp_listener() {
        let port = 45147;
        assert_eq!(
            tcp_listener(listening_config(port))
                .unwrap()
                .local_addr()
                .unwrap()
                .to_string(),
            format!("[::]:{}", port)
        );
    }

    // we rely on our CI system using IPv6
    #[test]
    fn test_tcp_listener_v6() {
        let lc = listening_config(45148);
        assert_eq!(
            tcp_listener_v6(lc.addr_v6, lc.port)
                .unwrap()
                .local_addr()
                .unwrap()
                .to_string(),
            format!("[::]:{}", lc.port)
        );
    }

    #[test]
    fn test_tcp_listener_ipv4() {
        let lc = listening_config(45149);
        assert_eq!(
            tcp_listener_v4(lc.addr_v4, lc.port)
                .unwrap()
                .local_addr()
                .unwrap()
                .to_string(),
            format!("0.0.0.0:{}", lc.port)
        );
    }

    mod allowed_ip {
        use super::*;
        fn args_good() -> Vec<String> {
            vec![
                "192.168.1.14/24".to_string(), // net
                "::1".to_string(),
                "127.0.0.1".to_string(),
                "fd00::/17".to_string(), // net
                "fd05::3".to_string(),
            ]
        }

        fn args_bad() -> Vec<String> {
            vec![
                "192168114/24".to_string(), // invalid
                "::1".to_string(),
                "127.0.0.1".to_string(),
                "fd00::/17".to_string(),
            ]
        }

        fn to_sock_addr(addr: &str) -> SocketAddr {
            format!("{}:80", addr).parse::<SocketAddr>().unwrap()
        }

        fn to_ip_addr(addr: &str) -> IpAddr {
            IpAddr::from_str(addr).unwrap()
        }

        #[test]
        fn test_to_canonical() {
            assert_eq!(
                to_canonical(to_ip_addr("::ffff:1.2.3.4")),
                to_ip_addr("1.2.3.4")
            );
            assert_eq!(
                to_canonical(to_ip_addr("::fffe:1.2.3.4")),
                to_ip_addr("::fffe:1.2.3.4")
            );
            assert_eq!(to_canonical(to_ip_addr("::1")), to_ip_addr("::1"));
            assert_eq!(to_canonical(to_ip_addr("fd05::3")), to_ip_addr("fd05::3"));
            assert_eq!(to_canonical(to_ip_addr("1.2.3.4")), to_ip_addr("1.2.3.4"));
        }
        #[test]
        fn test_empty_list() {
            let args = &vec![];
            assert!(is_addr_allowed(&to_sock_addr("127.0.0.2"), args));
            assert!(is_addr_allowed(&to_sock_addr("127.0.0.1"), args));
        }
        #[test]
        fn test_good_list_ipaddr() {
            let args = &args_good();
            assert!(is_addr_allowed(&to_sock_addr("127.0.0.1"), args));
            assert!(!is_addr_allowed(&to_sock_addr("127.0.0.2"), args));
            assert!(is_addr_allowed(&to_sock_addr("[::ffff:127.0.0.1]"), args));
            assert!(!is_addr_allowed(&to_sock_addr("[::ffff:127.0.0.2]"), args));
            assert!(is_addr_allowed(&to_sock_addr("[::1]"), args));
            assert!(!is_addr_allowed(&to_sock_addr("[::2]"), args));
            assert!(is_addr_allowed(&to_sock_addr("[fd05::3]"), args));
            assert!(!is_addr_allowed(&to_sock_addr("[fd05::9]"), args));
        }
        #[test]
        fn test_bad_list_ipaddr() {
            let args = &args_bad();
            assert!(is_addr_allowed(&to_sock_addr("127.0.0.1"), args));
            assert!(!is_addr_allowed(&to_sock_addr("127.0.0.2"), args));
            assert!(is_addr_allowed(&to_sock_addr("[::ffff:127.0.0.1]"), args));
            assert!(!is_addr_allowed(&to_sock_addr("[::ffff:127.0.0.2]"), args));
        }
        #[test]
        fn test_valid_list_net() {
            let args = &args_good();
            assert!(is_addr_allowed(&to_sock_addr("192.168.1.13"), args));
            assert!(!is_addr_allowed(&to_sock_addr("172.168.1.13"), args));
            assert!(is_addr_allowed(
                &to_sock_addr("[::ffff:192.168.1.13]"),
                args
            ));
            assert!(!is_addr_allowed(
                &to_sock_addr("[::ffff:172.168.1.13]"),
                args
            ));
            assert!(is_addr_allowed(&to_sock_addr("[fd00::1]"), args));
            assert!(!is_addr_allowed(&to_sock_addr("[fd01::1]"), args));
        }
    }
}
