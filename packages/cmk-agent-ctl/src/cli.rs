// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#[cfg(windows)]
use super::types;
use super::{site_spec, version};
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(about = "Checkmk agent controller.", version = version::VERSION)]
pub struct Cli {
    /// Enable verbose output. Use once (-v) for logging level INFO and twice (-vv) for logging
    /// level DEBUG.
    #[arg(short, long, action = clap::ArgAction::Count)]
    verbose: u8,

    #[command(subcommand)]
    pub mode: Mode,
}

#[derive(Subcommand)]
pub enum Mode {
    /// Register with a Checkmk site
    ///
    /// Register with a Checkmk instance for monitoring. The required information
    /// can be read from a config file or must be passed via command line.
    Register(RegisterOpts),

    /// Register with a Checkmk site, automatically creating a new host.
    ///
    /// Register with a Checkmk instance for monitoring. A new host will be created
    /// in the target Checkmk instance. This mode is only available if the target
    /// is a Cloud edition.
    RegisterNew(RegisterNewOpts),

    /// Register with a Checkmk site on behalf of another host
    ///
    /// This allows a registration by proxy for hosts which cannot register themselves.
    /// The gathered connection information is written to standard output.
    ProxyRegister(RegisterOpts),

    /// Push monitoring data to all Checkmk sites configured for 'push'
    ///
    /// This command will collect monitoring data, send them to all
    /// Checkmk site configured for 'push' and exit.
    Push(ClientOpts),

    /// Handle incoming connections from Checkmk sites collecting monitoring data
    ///
    /// This command will listen for incoming connections
    Pull(PullOpts),

    /// Run as daemon and handle all pull and push connections
    ///
    /// Listen for incoming connections (as the 'pull' command does),
    /// and send data to all Checkmk sites configured for 'push'
    /// (as the 'push' command does) once a minute.
    Daemon(DaemonOpts),

    /// Collect monitoring data and write it to standard output
    Dump,

    /// Query the registration status of this host
    Status(StatusOpts),

    /// Delete a connection to a Checkmk instance
    Delete(ConnectionOpts),

    /// Delete all connections to Checkmk sites
    DeleteAll(DeleteAllOpts),

    /// Import a pull connection from file or standard input
    ///
    /// A connection is imported from the JSON-encoded connection information.
    /// A compatible dataset can be created using the 'proxy-register' command.
    Import(ImportOpts),

    /// Renew the certificate for a connection to a Checkmk instance.
    ///
    /// Only possible for non-imported connections. To renew imported connections,
    /// please proxy-register and import again.
    RenewCertificate(RenewCertificateOpts),
}

#[derive(Parser)]
// #[command(author, version, about, long_about = None)]
pub struct RegisterOpts {
    #[clap(flatten)]
    pub connection_opts: RegistrationConnectionOpts,

    /// Name of this host in the monitoring site
    // We are consistent with agent updater, which uses "hostname", not "host-name".
    #[arg(long, short = 'H', long, value_parser = clap::value_parser!(String))]
    pub hostname: String,
}

#[derive(Parser)]
pub struct RegistrationConnectionOpts {
    /// Address of the Checkmk site in the format "<server>" or "<server>:<port>"
    ///
    /// "<server>" can be an IPv4/6 address or a hostname. IPv6 addresses must be enclosed in square brackets.
    /// Examples: checkmk.server.com, checkmk.server.com:8000, 127.0.0.1, 127.0.0.1:8000, [3a02:87b0:504::2], [3a02:87b0:504::2]:8000.
    #[arg(long = "server", short = 's', value_parser = clap::value_parser!(site_spec::ServerSpec), verbatim_doc_comment)]
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

    #[clap(flatten)]
    pub reg_client_opts: RegistrationClientOpts,
}

#[derive(Parser)]
pub struct ClientOpts {
    /// Detect and use proxy settings configured on this system for outgoing HTTPS connections.
    /// The default is to ignore configured proxies and to connect directly.
    #[arg(short = 'd', long)]
    pub detect_proxy: bool,
}

#[derive(Parser)]
pub struct RegistrationClientOpts {
    /// Enable TLS certificate validation for querying the agent receiver port from the Checkmk
    /// REST API. By default, certificate validation is disabled because it is not security-relevant
    /// at this stage, see werk #14715.
    #[arg(long)]
    pub validate_api_cert: bool,
}

#[derive(Parser)]
pub struct RegisterNewOpts {
    #[clap(flatten)]
    pub connection_opts: RegistrationConnectionOpts,

    /// User-defined agent labels in the form KEY:VALUE. These labels supersede the automatic labels.
    #[arg(long = "agent-labels", name = "KEY:VALUE",  value_parser = parse_agent_labels, )]
    pub agent_labels_raw: Vec<(String, String)>,
}

//https://github.com/clap-rs/clap/blob/master/examples/tutorial_derive/04_02_validate.rs
fn parse_agent_labels(s: &str) -> Result<(String, String), String> {
    // TODO(sk): better to use something more rust, splitn: split_once and collect_tuple
    match s.splitn(2, ':').collect::<Vec<&str>>()[..] {
        [a, b] => Ok((a.to_owned(), b.to_owned())),
        _ => Err(format!("invalid <KEY:VALUE>: no `:` found in `{s}`")),
    }
}

#[cfg(unix)]
#[derive(Parser)]
pub struct PullOpts {
    /// TCP port to listen on for incoming pull connections
    #[arg(long, short = 'P', value_parser = site_spec::parse_port)]
    pub port: Option<u16>,
}

#[cfg(windows)]
#[derive(Parser)]
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

#[derive(Parser)]
pub struct DaemonOpts {
    #[clap(flatten)]
    pub pull_opts: PullOpts,

    #[clap(flatten)]
    pub client_opts: ClientOpts,

    #[clap(flatten)]
    pub reg_client_opts: RegistrationClientOpts,
}

#[derive(Parser)]
pub struct StatusOpts {
    /// Write output in JSON format
    #[arg(long)]
    pub json: bool,

    /// Do not query the remote about our status
    #[arg(long)]
    pub no_query_remote: bool,

    #[clap(flatten)]
    pub client_opts: ClientOpts,
}

#[derive(Parser)]
pub struct ConnectionOpts {
    /// Target connection,
    /// specified either by its site address or its UUID.
    /// The site address is '<servername>/<site>', see the output of the
    /// status command.
    #[arg(name = "CONNECTION")]
    pub connection: String,
}

#[derive(Parser)]
pub struct DeleteAllOpts {
    /// Enable insecure connections (no TLS, agent output will be accessible via TCP agent port without encryption)
    #[arg(long)]
    pub enable_insecure_connections: bool,
}

#[derive(Parser)]
pub struct ImportOpts {
    /// The file to import. If not provided, data is read from standard input.
    #[arg(name = "CONNECTION_FILE")]
    pub conn_file: Option<std::path::PathBuf>,
}

#[derive(Parser)]
pub struct RenewCertificateOpts {
    #[clap(flatten)]
    pub connection_opts: ConnectionOpts,

    #[clap(flatten)]
    pub client_opts: ClientOpts,
}

impl Cli {
    pub fn logging_level(&self) -> String {
        String::from(match self.verbose {
            2.. => "debug",
            1 => "info",
            _ => "warn",
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_logging_level() {
        assert_eq!(
            (Cli {
                verbose: 0,
                mode: Mode::Dump
            })
            .logging_level(),
            "warn"
        );
        assert_eq!(
            (Cli {
                verbose: 1,
                mode: Mode::Dump
            })
            .logging_level(),
            "info"
        );
        assert_eq!(
            (Cli {
                verbose: 2,
                mode: Mode::Dump
            })
            .logging_level(),
            "debug"
        );
    }

    #[test]
    fn test_parse_agent_labels_ok() {
        assert_eq!(
            parse_agent_labels("a:b").unwrap(),
            (String::from("a"), String::from("b"))
        );
        assert_eq!(
            parse_agent_labels("abc-123:456:def").unwrap(),
            (String::from("abc-123"), String::from("456:def"))
        );
        assert_eq!(
            parse_agent_labels("abc-123456-def").unwrap_err(),
            "invalid <KEY:VALUE>: no `:` found in `abc-123456-def`"
        );
    }

    #[test]
    fn test_parse_agent_labels_error() {
        assert!(parse_agent_labels("missing-colon").is_err(),);
    }
}
