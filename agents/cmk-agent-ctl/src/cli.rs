// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::site_spec;
#[cfg(windows)]
use super::types;
use structopt::StructOpt;

#[derive(StructOpt)]
pub struct LoggingOpts {
    // TODO (jh): make this field private again once the Windows agent reads its pull configuration
    // from a file instead of from the command line. Currently, we need this to be public for
    // testing.
    /// Enable verbose output. Use once (-v) for logging level INFO and twice (-vv) for logging
    /// level DEBUG.
    #[structopt(short, long, parse(from_occurrences))]
    pub verbose: u8,
}

impl LoggingOpts {
    fn logging_level(&self) -> String {
        match self.verbose {
            2.. => String::from("debug"),
            1 => String::from("info"),
            _ => String::from("warn"),
        }
    }
}

#[derive(StructOpt)]
pub struct ClientOpts {
    /// Detect and use proxy settings configured on this system for outgoing HTTPS connections.
    /// The default is to ignore configured proxies and to connect directly.
    #[structopt(long, short = "d")]
    pub detect_proxy: bool,
}

#[derive(StructOpt)]
pub struct RegistrationArgs {
    /// Address of the Checkmk site in the format "<server>" or "<server>:<port>"
    #[structopt(long, short = "s", requires = "site", parse(try_from_str))]
    pub server: Option<site_spec::ServerSpec>,

    /// Name of the Checkmk site
    #[structopt(long, short = "i", requires = "server", parse(from_str))]
    pub site: Option<String>,

    /// API user to use for registration
    #[structopt(long, short = "U", parse(from_str))]
    pub user: Option<String>,

    /// Password for API user. Can also be entered interactively.
    #[structopt(long, short = "P", requires = "user", parse(from_str))]
    pub password: Option<String>,

    /// Name of this host in the monitoring site
    // We are consistent with agent updater, which uses "hostname", not "host-name".
    #[structopt(long, short = "H", long = "hostname", parse(from_str))]
    pub host_name: Option<String>,

    /// Blindly trust the server certificate of the Checkmk site
    // We are consistent with agent updater, which uses "trust-cert"
    #[structopt(long = "trust-cert")]
    pub trust_server_cert: bool,

    #[structopt(flatten)]
    pub client_opts: ClientOpts,

    #[structopt(flatten)]
    pub logging_opts: LoggingOpts,
}

#[derive(StructOpt)]
pub struct StatusArgs {
    /// Write output in JSON format
    #[structopt(long)]
    pub json: bool,

    /// Do not query the remote about our status
    #[structopt(long)]
    pub no_query_remote: bool,

    #[structopt(flatten)]
    pub client_opts: ClientOpts,

    #[structopt(flatten)]
    pub logging_opts: LoggingOpts,
}

#[derive(StructOpt)]
pub struct DeleteArgs {
    /// The connection to delete
    #[structopt(name = "CONNECTION")]
    pub connection: String,

    #[structopt(flatten)]
    pub logging_opts: LoggingOpts,
}

#[derive(StructOpt)]
pub struct PushArgs {
    #[structopt(flatten)]
    pub client_opts: ClientOpts,

    #[structopt(flatten)]
    pub logging_opts: LoggingOpts,
}

#[derive(StructOpt)]
pub struct DeleteAllArgs {
    /// Enable insecure connections (no TLS, agent output will be accessible via TCP agent port without encryption)
    #[structopt(long)]
    pub enable_insecure_connections: bool,

    #[structopt(flatten)]
    pub logging_opts: LoggingOpts,
}

// TODO (sk): Remove port and allowed_ip and instead read from a toml file, as is done under unix
#[cfg(windows)]
#[derive(StructOpt)]
pub struct PullOpts {
    /// TCP port to listen on for incoming pull connections
    #[structopt(long, short = "P", parse(try_from_str = site_spec::parse_port))]
    pub port: Option<u16>,

    /// List of IP addresses & templates separated with ' '
    #[structopt(long, short = "A", parse(from_str))]
    pub allowed_ip: Option<Vec<String>>,

    /// TCP connection "ip:port"
    /// None means default behavior
    #[structopt(long, parse(from_str))]
    pub agent_channel: Option<types::AgentChannel>,
}

#[cfg(unix)]
#[derive(StructOpt)]
pub struct PullOpts {
    /// TCP port to listen on for incoming pull connections
    #[structopt(long, short = "P", parse(try_from_str = site_spec::parse_port))]
    pub port: Option<u16>,

    /// List of IP addresses & templates separated with ' '
    #[structopt(long, short = "A", parse(from_str))]
    pub allowed_ip: Option<Vec<String>>,
}

#[derive(StructOpt)]
pub struct PullArgs {
    #[structopt(flatten)]
    pub pull_opts: PullOpts,

    #[structopt(flatten)]
    pub logging_opts: LoggingOpts,
}

#[derive(StructOpt)]
pub struct DaemonArgs {
    #[structopt(flatten)]
    pub pull_opts: PullOpts,

    #[structopt(flatten)]
    pub client_opts: ClientOpts,

    #[structopt(flatten)]
    pub logging_opts: LoggingOpts,
}

#[derive(StructOpt)]
pub struct ImportArgs {
    /// The file to import. If not provided, data is read from standard input.
    #[structopt(name = "CONNECTION_FILE")]
    pub conn_file: Option<std::path::PathBuf>,

    #[structopt(flatten)]
    pub logging_opts: LoggingOpts,
}

#[derive(StructOpt)]
pub struct SharedArgsOnly {
    #[structopt(flatten)]
    pub logging_opts: LoggingOpts,
}

#[derive(StructOpt)]
#[structopt(name = "cmk-agent-ctl", about = "Checkmk agent controller.")]
pub enum Args {
    /// Register with a Checkmk site
    ///
    /// Register with a Checkmk instance for monitoring. The required information
    /// can be read from a config file or must be passed via command line.
    #[structopt()]
    Register(RegistrationArgs),

    /// Register with a Checkmk site on behalf of another host
    ///
    /// This allows a registration by proxy for hosts which cannot register themselves.
    /// The gathered connection information is written to standard output.
    #[structopt()]
    ProxyRegister(RegistrationArgs),

    /// Push monitoring data to all Checkmk sites configured for 'push'
    ///
    /// This command will collect monitoring data, send them to all
    /// Checkmk site configured for 'push' and exit.
    #[structopt()]
    Push(PushArgs),

    /// Handle incoming connections from Checkmk sites collecting monitoring data
    ///
    /// This command will listen for incoming connections
    #[structopt()]
    Pull(PullArgs),

    /// Run as daemon and handle all pull and push connections
    ///
    /// Listen for incoming connections (as the 'pull' command does),
    /// and send data to all Checkmk sites configured for 'push'
    /// (as the 'push' command does) once a minute.
    #[structopt()]
    Daemon(DaemonArgs),

    /// Collect monitoring data and write it to standard output
    #[structopt()]
    Dump(SharedArgsOnly),

    /// Query the registration status of this host
    #[structopt()]
    Status(StatusArgs),

    /// Delete a connection to a Checkmk instance
    ///
    /// Connections can be specified either by their site address or their UUID.
    /// The site address is '<servername>:<port>/<site>', see the output of the
    /// status command.
    #[structopt()]
    Delete(DeleteArgs),

    /// Delete all connections to Checkmk sites
    #[structopt()]
    DeleteAll(DeleteAllArgs),

    /// Import a pull connection from file or standard input
    ///
    /// A connection is imported from the JSON-encoded connection information.
    /// A compatible dataset can be created using the 'proxy-register' command.
    #[structopt()]
    Import(ImportArgs),
}

impl Args {
    pub fn logging_level(&self) -> String {
        match self {
            Args::Register(args) => args.logging_opts.logging_level(),
            Args::ProxyRegister(args) => args.logging_opts.logging_level(),
            Args::Push(args) => args.logging_opts.logging_level(),
            Args::Pull(args) => args.logging_opts.logging_level(),
            Args::Daemon(args) => args.logging_opts.logging_level(),
            Args::Dump(args) => args.logging_opts.logging_level(),
            Args::Status(args) => args.logging_opts.logging_level(),
            Args::Delete(args) => args.logging_opts.logging_level(),
            Args::DeleteAll(args) => args.logging_opts.logging_level(),
            Args::Import(args) => args.logging_opts.logging_level(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_logging_level() {
        assert_eq!((LoggingOpts { verbose: 0 }).logging_level(), "warn");
        assert_eq!((LoggingOpts { verbose: 1 }).logging_level(), "info");
        assert_eq!((LoggingOpts { verbose: 2 }).logging_level(), "debug");
    }
}
