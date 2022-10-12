// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#[cfg(windows)]
use super::types;
use super::{constants, site_spec};
use clap::Parser;

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
pub struct LoggingOpts {
    // TODO (jh): make this field private again once the Windows agent reads its pull configuration
    // from a file instead of from the command line. Currently, we need this to be public for
    // testing.
    /// Enable verbose output. Use once (-v) for logging level INFO and twice (-vv) for logging
    /// level DEBUG.
    #[arg(short, long, action = clap::ArgAction::Count)]
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

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
pub struct ClientOpts {
    /// Detect and use proxy settings configured on this system for outgoing HTTPS connections.
    /// The default is to ignore configured proxies and to connect directly.
    #[arg(short = 'd', long)]
    pub detect_proxy: bool,

    /// Enable TLS certificate validation for querying the agent receiver port from the Checkmk
    /// REST API. By default, certificate validation is disabled because it is not security-relevant
    /// at this stage, see werk #14715.
    #[arg(long)]
    pub validate_api_cert: bool,
}

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
pub struct RegistrationArgsConnection {
    /// Address of the Checkmk site in the format "<server>" or "<server>:<port>"
    #[arg(long = "server", short = 's', value_parser = clap::value_parser!(site_spec::ServerSpec))]
    pub server_spec: site_spec::ServerSpec,

    /// Name of the Checkmk site
    #[arg(long, short = 'i')]
    pub site: String,

    /// API user to use for registration
    #[arg(long, short = 'U')]
    pub user: String,

    /// Password for API user. Can also be entered interactively.
    #[arg(long, short = 'P')]
    pub password: Option<String>,

    /// Blindly trust the server certificate of the Checkmk site
    // We are consistent with agent updater, which uses "trust-cert"
    #[arg(long = "trust-cert")]
    pub trust_server_cert: bool,

    #[clap(flatten)]
    pub client_opts: ClientOpts,
}

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
pub struct RegistrationArgsHostName {
    #[clap(flatten)]
    pub connection_args: RegistrationArgsConnection,

    #[clap(flatten)]
    pub logging_opts: LoggingOpts,

    /// Name of this host in the monitoring site
    // We are consistent with agent updater, which uses "hostname", not "host-name".
    #[arg(long, short = 'H', long = "hostname", value_parser = clap::value_parser!(String))]
    pub host_name: String,
}

#[derive(Parser)]
pub struct RegistrationArgsAgentLabels {
    #[clap(flatten)]
    pub connection_args: RegistrationArgsConnection,

    #[clap(flatten)]
    pub logging_opts: LoggingOpts,

    /// User-defined agent labels in the form KEY=VALUE. These labels supersede the automatic labels.
    #[arg(long = "agent-labels", name = "KEY=VALUE",  value_parser = parse_agent_labels, )]
    pub agent_labels_raw: Vec<(String, String)>,
}

//https://github.com/clap-rs/clap/blob/master/examples/tutorial_derive/04_02_validate.rs
fn parse_agent_labels(s: &str) -> Result<(String, String), String> {
    // TODO(sk): better to use something more rust, splitn: split_once and collect_tuple
    match s.splitn(2, '=').collect::<Vec<&str>>()[..] {
        [a, b] => Ok((a.to_owned(), b.to_owned())),
        _ => Err(format!("invalid KEY=VALUE: no `=` found in `{}`", s)),
    }
}

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
pub struct StatusArgs {
    /// Write output in JSON format
    #[arg(long)]
    pub json: bool,

    /// Do not query the remote about our status
    #[arg(long)]
    pub no_query_remote: bool,

    #[clap(flatten)]
    pub client_opts: ClientOpts,

    #[clap(flatten)]
    pub logging_opts: LoggingOpts,
}

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
pub struct DeleteArgs {
    /// The connection to delete
    #[arg(name = "CONNECTION")]
    pub connection: String,

    #[clap(flatten)]
    pub logging_opts: LoggingOpts,
}

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
pub struct PushArgs {
    #[clap(flatten)]
    pub client_opts: ClientOpts,

    #[clap(flatten)]
    pub logging_opts: LoggingOpts,
}

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
pub struct DeleteAllArgs {
    /// Enable insecure connections (no TLS, agent output will be accessible via TCP agent port without encryption)
    #[arg(long)]
    pub enable_insecure_connections: bool,

    #[clap(flatten)]
    pub logging_opts: LoggingOpts,
}

#[cfg(windows)]
#[derive(Parser)]
#[command(author, version, about, long_about = None)]
pub struct PullOpts {
    /// TCP port to listen on for incoming pull connections
    #[arg(long, short = 'P', value_parser = site_spec::parse_port)]
    pub port: Option<u16>,

    /// Connection in format "type/peer"
    /// where
    ///     type is either "ms" or "ip"
    ///     peer is correct mailslot address or ip address
    /// examples
    ///     "ms/Global\\WinAgent_13"
    ///     "ip/localhost:28250"
    /// None means default behavior
    #[arg(long, value_parser = clap::value_parser!(types::AgentChannel))]
    pub agent_channel: Option<types::AgentChannel>,
}

#[cfg(unix)]
#[derive(Parser)]
#[command(author, version, about, long_about = None)]
pub struct PullOpts {
    /// TCP port to listen on for incoming pull connections
    #[arg(long, short = 'P', value_parser = site_spec::parse_port)]
    pub port: Option<u16>,
}

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
pub struct PullArgs {
    #[clap(flatten)]
    pub pull_opts: PullOpts,

    #[clap(flatten)]
    pub logging_opts: LoggingOpts,
}

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
pub struct DaemonArgs {
    #[clap(flatten)]
    pub pull_opts: PullOpts,

    #[clap(flatten)]
    pub client_opts: ClientOpts,

    #[clap(flatten)]
    pub logging_opts: LoggingOpts,
}

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
pub struct ImportArgs {
    /// The file to import. If not provided, data is read from standard input.
    #[arg(name = "CONNECTION_FILE")]
    pub conn_file: Option<std::path::PathBuf>,

    #[clap(flatten)]
    pub logging_opts: LoggingOpts,
}

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
pub struct SharedArgsOnly {
    #[clap(flatten)]
    pub logging_opts: LoggingOpts,
}

#[derive(Parser)]
#[command(about = "Checkmk agent controller.", version = constants::VERSION)]
pub enum Args {
    /// Register with a Checkmk site
    ///
    /// Register with a Checkmk instance for monitoring. The required information
    /// can be read from a config file or must be passed via command line.
    #[command(name = "register")]
    RegisterHostName(RegistrationArgsHostName),

    /// Register with a Checkmk site, automatically creating a new host.
    ///
    /// Register with a Checkmk instance for monitoring. A new host will be created
    /// in the target Checkmk instance. This mode is only available if the target
    /// is an Enterprise Plus edition.
    #[command(name = "register-new")]
    RegisterAgentLabels(RegistrationArgsAgentLabels),

    /// Register with a Checkmk site on behalf of another host
    ///
    /// This allows a registration by proxy for hosts which cannot register themselves.
    /// The gathered connection information is written to standard output.
    #[command()]
    ProxyRegister(RegistrationArgsHostName),

    /// Push monitoring data to all Checkmk sites configured for 'push'
    ///
    /// This command will collect monitoring data, send them to all
    /// Checkmk site configured for 'push' and exit.
    #[command()]
    Push(PushArgs),

    /// Handle incoming connections from Checkmk sites collecting monitoring data
    ///
    /// This command will listen for incoming connections
    #[command()]
    Pull(PullArgs),

    /// Run as daemon and handle all pull and push connections
    ///
    /// Listen for incoming connections (as the 'pull' command does),
    /// and send data to all Checkmk sites configured for 'push'
    /// (as the 'push' command does) once a minute.
    #[command()]
    Daemon(DaemonArgs),

    /// Collect monitoring data and write it to standard output
    #[command()]
    Dump(SharedArgsOnly),

    /// Query the registration status of this host
    #[command()]
    Status(StatusArgs),

    /// Delete a connection to a Checkmk instance
    ///
    /// Connections can be specified either by their site address or their UUID.
    /// The site address is '<servername>:<port>/<site>', see the output of the
    /// status command.
    #[command()]
    Delete(DeleteArgs),

    /// Delete all connections to Checkmk sites
    #[command()]
    DeleteAll(DeleteAllArgs),

    /// Import a pull connection from file or standard input
    ///
    /// A connection is imported from the JSON-encoded connection information.
    /// A compatible dataset can be created using the 'proxy-register' command.
    #[command()]
    Import(ImportArgs),
}

impl Args {
    pub fn logging_level(&self) -> String {
        match self {
            Args::RegisterHostName(args) => args.logging_opts.logging_level(),
            Args::RegisterAgentLabels(args) => args.logging_opts.logging_level(),
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

    #[test]
    fn test_parse_agent_labels_ok() {
        assert_eq!(
            parse_agent_labels("a=b").unwrap(),
            (String::from("a"), String::from("b"))
        );
        assert_eq!(
            parse_agent_labels("abc-123=456=def").unwrap(),
            (String::from("abc-123"), String::from("456=def"))
        );
        assert_eq!(
            parse_agent_labels("abc-123456-def").unwrap_err(),
            "invalid KEY=VALUE: no `=` found in `abc-123456-def`"
        );
    }

    #[test]
    fn test_parse_agent_labels_error() {
        assert!(parse_agent_labels("missing-equal-sign").is_err(),);
    }
}
