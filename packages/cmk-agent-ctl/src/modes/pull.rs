// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use core::future::Future;
use std::collections::HashMap;
use std::error::Error;
use std::sync::Arc;

use crate::{config, misc::anyhow_error_to_human_readable, monitoring_data, tls_server, types};
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
const PULL_ACTIVITY_TIMEOUT: u64 = 330; // Avoid exactly 5 minutes, as this is a common check interval

struct ListeningConfig {
    pub addr_v4: Ipv4Addr,
    pub addr_v6: Ipv6Addr,
    pub port: u16,
}

#[derive(Clone)]
enum ConnectionMode {
    Active(CryptoMode),
    Inactive,
}

#[derive(Clone)]
enum CryptoMode {
    Tls(TlsAcceptor),
    Plain,
}

impl std::convert::TryFrom<&config::PullConfig> for ConnectionMode {
    type Error = AnyhowError;

    fn try_from(config: &config::PullConfig) -> AnyhowResult<Self> {
        if config.allow_legacy_pull() {
            return Ok(Self::Active(CryptoMode::Plain));
        }
        if config.has_connections() {
            Ok(Self::Active(CryptoMode::Tls(
                tls_server::tls_acceptor(
                    // this would fail if we passed in an empty iterator
                    config.get_pull_connections(),
                )
                .context("Could not initialize TLS.")?,
            )))
        } else {
            Ok(Self::Inactive)
        }
    }
}

struct PullState {
    connection_mode: ConnectionMode,
    config: config::PullConfig,
}

impl std::convert::TryFrom<config::PullConfig> for PullState {
    type Error = AnyhowError;

    fn try_from(config: config::PullConfig) -> AnyhowResult<Self> {
        Ok(Self {
            connection_mode: ConnectionMode::try_from(&config)?,
            config,
        })
    }
}

impl PullState {
    fn refresh(&mut self) -> AnyhowResult<()> {
        if self.config.refresh()? {
            self.connection_mode = ConnectionMode::try_from(&self.config)?;
        };
        Ok(())
    }

    fn listening_config(&self) -> ListeningConfig {
        ListeningConfig {
            addr_v4: Ipv4Addr::UNSPECIFIED,
            addr_v6: Ipv6Addr::UNSPECIFIED,
            port: self.config.port,
        }
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

    pub fn obtain_connection_semaphore(&mut self, ip_addr: IpAddr) -> Arc<Semaphore> {
        Arc::clone(
            self.active_connections
                .entry(ip_addr)
                .or_insert_with(|| Arc::new(Semaphore::new(self.max_connections))),
        )
    }
}

pub fn fn_thread(pull_config: config::PullConfig) -> AnyhowResult<()> {
    pull_runtime_wrapper(pull_config)
}

#[tokio::main(flavor = "current_thread")]
async fn pull_runtime_wrapper(pull_config: config::PullConfig) -> AnyhowResult<()> {
    let agent_output_collector = AgentOutputCollectorImpl::from(&pull_config.agent_channel);
    let pull_state = PullState::try_from(pull_config)?;
    _pull(pull_state, agent_output_collector).await
}

async fn _pull(
    mut pull_state: PullState,
    agent_output_collector: impl AgentOutputCollector,
) -> AnyhowResult<()> {
    loop {
        if matches!(pull_state.connection_mode, ConnectionMode::Inactive) {
            tokio::time::sleep(Duration::from_secs(ONE_MINUTE)).await;
            // Allow a crash due to a failing registry reload. It's not likely to recover
            // here without action taken, and it's vital for all connections.
            pull_state.refresh()?;
            continue;
        }
        info!("Start listening for incoming pull requests");
        _pull_loop(&mut pull_state, agent_output_collector.clone()).await?;
    }
}

#[cfg(windows)]
/// In windows REUSE is forbidden due to security reasons
fn set_socket_for_exclusive_use(socket: &Socket, on: bool) -> std::io::Result<()> {
    use std::os::windows::prelude::AsRawSocket;
    use winapi::{ctypes, um::winsock2};
    let on = u32::from(on);
    let ret = unsafe {
        let sock = socket.as_raw_socket() as winsock2::SOCKET;
        let ptr = &on as *const ctypes::c_ulong as *const ctypes::c_void as *const ctypes::c_char;
        winsock2::setsockopt(
            sock,
            winsock2::SOL_SOCKET,
            winsock2::SO_EXCLUSIVEADDRUSE,
            ptr,
            4,
        )
    };
    match ret {
        0 => Ok(()),
        code => Err(std::io::Error::from_raw_os_error(code)),
    }
}

pub enum SocketMode {
    Reuse,
    Exclusive,
}

fn configure_socket(socket: Socket, mode: SocketMode) -> AnyhowResult<Socket> {
    socket.set_nonblocking(true)?;
    // https://stackoverflow.com/questions/3229860/what-is-the-meaning-of-so-reuseaddr-setsockopt-option-linux
    // Allow re-using the address, even if there are still connections. After sending the agent
    // data, we end up with a waiting connection which will be dropped at some point, but not
    // immediately (this is OK, standard TCP protocol). However, this will block the re-creation
    // of the socket if the agent controller is restarted (agent update or manual restart).
    match mode {
        #[cfg(windows)]
        SocketMode::Exclusive => set_socket_for_exclusive_use(&socket, true)?,
        #[cfg(unix)]
        SocketMode::Exclusive => panic!("Not supported in Linux"),
        SocketMode::Reuse => socket.set_reuse_address(true)?,
    }

    Ok(socket)
}

#[cfg(windows)]
const DEFAULT_SOCKET_MODE: SocketMode = SocketMode::Exclusive;
#[cfg(unix)]
const DEFAULT_SOCKET_MODE: SocketMode = SocketMode::Reuse;

fn tcp_listener_v4(address: Ipv4Addr, port: u16) -> AnyhowResult<TcpListenerStd> {
    let socket = configure_socket(
        Socket::new(Domain::IPV4, Type::STREAM, None)?,
        DEFAULT_SOCKET_MODE,
    )?;
    socket.bind(&SockAddr::from(SocketAddr::new(IpAddr::V4(address), port)))?;
    socket.listen(4096)?;
    Ok(socket.into())
}

fn tcp_listener_v6(address: Ipv6Addr, port: u16) -> AnyhowResult<TcpListenerStd> {
    let socket = configure_socket(
        Socket::new(Domain::IPV6, Type::STREAM, None)?,
        DEFAULT_SOCKET_MODE,
    )?;
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
        anyhow_error_to_human_readable(&err_v6),
        anyhow_error_to_human_readable(&err_v4),
    );
}

async fn _pull_loop(
    pull_state: &mut PullState,
    agent_output_collector: impl AgentOutputCollector,
) -> AnyhowResult<()> {
    let listener = TcpListener::from_std(tcp_listener(pull_state.listening_config())?)?;
    let mut guard = MaxConnectionsGuard::new(pull_state.config.max_connections);
    let max_connections = guard.max_connections;

    loop {
        let Ok(connection_attempt) = timeout(
            Duration::from_secs(PULL_ACTIVITY_TIMEOUT),
            listener.accept(),
        )
        .await
        else {
            // No connection within timeout. Refresh config and check if we're still active.
            pull_state.refresh()?;
            if matches!(pull_state.connection_mode, ConnectionMode::Inactive) {
                info!(
                    "No pull connection registered, stop listening on {}.",
                    listener.local_addr()?
                );
                return Ok(());
            }
            // If still active, don't return as this would close the socket - Just continue listening.
            continue;
        };

        let (stream, remote) = match connection_attempt {
            Ok(accepted) => accepted,
            Err(error) => {
                warn!("Failed accepting pull connection. ({})", error);
                continue;
            }
        };

        if !is_addr_allowed(&remote, &pull_state.config.allowed_ip) {
            warn!("{remote}: Rejecting pull connection - IP is not allowed.");
            continue;
        }

        // Act on most recent registration data
        pull_state.refresh()?;

        // Check if pull was deactivated meanwhile before actually handling the request.
        match pull_state.connection_mode.clone() {
            ConnectionMode::Inactive => {
                info!(
                    "No pull connection registered, closing current connection and stop listening."
                );
                return Ok(());
            }

            ConnectionMode::Active(crypto_mode) => {
                info!("{remote} (pull): Handling connection.");
                debug!("{remote} (pull): Acquiring connection slot.");
                let ip_addr = remote.ip();
                let sem = guard.obtain_connection_semaphore(ip_addr);

                // NOTE(sk). Below this point we should NOT use shared mutable `guard` - may "leak"
                if let Ok(permit) = sem.try_acquire_owned() {
                    let task_num = max_connections - permit.semaphore().available_permits();
                    let io_future = make_handle_request_future(
                        stream,
                        agent_output_collector.clone(),
                        remote.ip(),
                        crypto_mode,
                        pull_state.config.connection_timeout,
                    );
                    tokio::spawn(async move {
                        if let Err(err) = io_future.await {
                            warn!("{remote} (pull): Failed processing task #{task_num} ({err})");
                        } else {
                            debug!("{remote} (pull): Successfully processed task #{task_num}");
                        };
                        drop(permit);
                    });
                    debug!("{remote} (pull): Task #{task_num} started.");
                } else {
                    warn!("{remote} (pull): Too many active connections. Rejecting.");
                    continue;
                }
            }
        }
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

async fn make_handle_request_future(
    mut stream: TcpStream,
    agent_output_collector: impl AgentOutputCollector,
    remote_ip: IpAddr,
    crypto_mode: CryptoMode,
    connection_timeout: u64,
) -> AnyhowResult<()> {
    match crypto_mode {
        CryptoMode::Tls(tls_acceptor) => {
            handle_request_with_tls(
                &mut stream,
                agent_output_collector,
                remote_ip,
                &tls_acceptor,
                connection_timeout,
            )
            .await
        }
        CryptoMode::Plain => {
            debug!("handle_request: starts in legacy mode from {:?}", remote_ip);
            handle_legacy_pull_request(
                &mut stream,
                agent_output_collector.plain_output(remote_ip),
                connection_timeout,
            )
            .await
        }
    }
}

async fn handle_request_with_tls(
    stream: &mut TcpStream,
    agent_output_collector: impl AgentOutputCollector,
    remote_ip: IpAddr,
    tls_acceptor: &TlsAcceptor,
    connection_timeout: u64,
) -> AnyhowResult<()> {
    debug!("handle_request: starts from {:?}", remote_ip);

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
    debug!("handle_request: ready to be send {:?}", remote_ip);
    with_timeout(
        async move {
            tls_stream.write_all(&mon_data).await?;
            debug!("handle_request: had been send {:?}", remote_ip);
            tls_stream.flush().await?;
            tls_stream.shutdown().await
        },
        connection_timeout,
    )
    .await
}

async fn handle_legacy_pull_request(
    stream: &mut TcpStream,
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
    Ok(timeout(Duration::from_secs(seconds), fut)
        .await
        .map_err(|e| anyhow!(e))??)
}

#[cfg(test)]
mod tests {
    use std::str::FromStr;

    use super::*;
    use crate::types::AgentChannel;

    #[cfg(windows)]
    mod win {
        use socket2::{Domain, SockAddr, Socket, Type};
        use std::net::{IpAddr, Ipv4Addr, SocketAddr};

        use crate::modes::pull::{configure_socket, SocketMode};

        fn make_socket_std() -> Socket {
            let socket_a = Socket::new(Domain::IPV4, Type::STREAM, None).unwrap();
            configure_socket(socket_a, SocketMode::Reuse).unwrap()
        }

        fn make_socket_exclusive() -> Socket {
            let socket_exclusive = Socket::new(Domain::IPV4, Type::STREAM, None).unwrap();
            configure_socket(socket_exclusive, SocketMode::Exclusive).unwrap()
        }

        #[test]
        fn test_socket_reuse_exclusive() {
            let socket_a = make_socket_std();
            let socket_b = make_socket_std();
            let socket_exclusive = make_socket_exclusive();
            let addr = SockAddr::from(SocketAddr::new(IpAddr::V4(Ipv4Addr::UNSPECIFIED), 19900));
            let a = socket_a.bind(&addr);
            let b = socket_b.bind(&addr);
            let exclusive = socket_exclusive.bind(&addr);

            assert!(a.is_ok());
            assert!(b.is_ok());
            assert!(exclusive.is_err());
        }
        #[test]
        fn test_socket_exclusive_reuse() {
            let socket_std = make_socket_std();
            let socket_exclusive = make_socket_exclusive();
            let addr = SockAddr::from(SocketAddr::new(IpAddr::V4(Ipv4Addr::UNSPECIFIED), 19901));

            let exclusive = socket_exclusive.bind(&addr);
            let a = socket_std.bind(&addr);

            assert!(a.is_err());
            assert!(exclusive.is_ok());
        }
        #[test]
        fn test_socket_exclusive_exclusive() {
            {
                let socket_exclusive = make_socket_exclusive();
                let addr =
                    SockAddr::from(SocketAddr::new(IpAddr::V4(Ipv4Addr::UNSPECIFIED), 19902));
                let exclusive = socket_exclusive.bind(&addr);
                assert!(exclusive.is_ok());
            }
            let socket_exclusive = make_socket_exclusive();
            let addr = SockAddr::from(SocketAddr::new(IpAddr::V4(Ipv4Addr::UNSPECIFIED), 19902));
            let exclusive = socket_exclusive.bind(&addr);
            assert!(exclusive.is_ok());
        }
    }

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
            format!("[::]:{port}")
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
            format!("{addr}:80").parse::<SocketAddr>().unwrap()
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
            let args = &[];
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
