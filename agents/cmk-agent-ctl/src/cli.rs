// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use structopt::StructOpt;

#[derive(StructOpt)]
pub struct RegistrationArgs {
    /// Checkmk site to register with
    #[structopt(long, short = "s", parse(from_str))]
    pub server: Option<String>,

    /// API user to use for registration
    #[structopt(long, short = "u", requires = "password", parse(from_str))]
    pub user: Option<String>,

    /// Password for API user
    #[structopt(long, short = "p", requires = "user", parse(from_str))]
    pub password: Option<String>,

    /// Name of this host in the monitoring site
    #[structopt(long, short = "H", parse(from_str))]
    pub host_name: Option<String>,

    /// Blindly trust the server certificate of the Checkmk site
    #[structopt(long)]
    pub trust_server_cert: bool,
}

#[derive(StructOpt)]
pub struct StatusArgs {
    /// Write output in JSON format
    #[structopt(long)]
    pub json: bool,
}

#[derive(StructOpt)]
pub struct DeleteArgs {
    /// The connection to delete
    #[structopt(name = "CONNECTION")]
    pub connection: String,
}

#[derive(StructOpt)]
pub struct ImportArgs {
    /// The file to import. If not provided, data is read from standard input.
    #[structopt(name = "CONNECTION_FILE")]
    pub conn_file: Option<std::path::PathBuf>,

    /// Enable verbose output
    #[structopt(long, short = "v")]
    pub verbose: bool,
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
    /// This allows a surrogate registration for hosts which cannot register themselves.
    /// The gathered connection information is written to standard output.
    #[structopt()]
    RegisterSurrogatePull(RegistrationArgs),

    /// Push monitoring data to all Checkmk sites configured for 'push'
    ///
    /// This command will collect monitoring data, send them to all
    /// Checkmk site configured for 'push' and exit.
    #[structopt()]
    Push {},

    /// Handle incoming connections from Checkmk sites collecting monitoring data
    ///
    /// This command will listen for incoming connections
    #[structopt()]
    Pull {},

    /// Run as daemon and handle all pull and push connections
    ///
    /// Listen for incoming connections (as the 'pull' command does),
    /// and send data to all Checkmk sites configured for 'push'
    /// (as the 'push' command does) once a minute.
    #[structopt()]
    Daemon {},

    /// Collect monitoring data and write it to standard output
    #[structopt()]
    Dump {},

    /// Query the registration status of this host
    #[structopt()]
    Status(StatusArgs),

    /// Delete a connection to a Checkmk instance
    ///
    /// Connections can be specified either by their name or their UUID.
    /// The connections name is '<servername>:<port>' or 'imported-<number>',
    /// see the output of the 'status' command.
    #[structopt()]
    Delete(DeleteArgs),

    /// Delete all connections to Checkmk sites
    #[structopt()]
    DeleteAll {},

    /// Import a pull connection from file or standard input
    ///
    /// A connection is imported from the JSON-encoded connection information.
    /// A compatible dataset can be created using the 'register-surrogate-pull' command.
    #[structopt()]
    Import(ImportArgs),
}
