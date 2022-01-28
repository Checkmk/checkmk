// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use structopt::StructOpt;

#[derive(StructOpt)]
pub struct RegistrationArgs {
    #[structopt(long, short = "s", parse(from_str))]
    pub server: Option<String>,

    #[structopt(long, short = "u", requires = "password", parse(from_str))]
    pub user: Option<String>,

    #[structopt(long, short = "p", requires = "user", parse(from_str))]
    pub password: Option<String>,

    #[structopt(long, short = "H", parse(from_str))]
    pub host_name: Option<String>,

    /// Blindly trust the server certificate used by the Checkmk instance contacted for registration
    #[structopt(long)]
    pub trust_server_cert: bool,
}

#[derive(StructOpt)]
pub struct StatusArgs {
    #[structopt(long)]
    pub json: bool,
}

#[derive(StructOpt)]
pub struct DeleteArgs {
    /// Connection name or UUID of the connection to be deleted. Connection name can be either
    /// 'servername:port' or 'imported-...', see the output of the 'status' command.
    #[structopt(name = "CONNECTION")]
    pub connection: String,
}

#[derive(StructOpt)]
pub struct ImportArgs {
    /// Path to a file containing the JSON-encoded connection to be imported (output of the
    /// 'register-surrogate-pull' command). If not provided, the JSON data is expected via stdin.
    #[structopt(name = "CONNECTION_FILE")]
    pub conn_file: Option<std::path::PathBuf>,

    /// Enable verbose output
    #[structopt(long, short = "v")]
    pub verbose: bool,
}

#[derive(StructOpt)]
#[structopt(name = "cmk-agent-ctl", about = "Checkmk agent controller.")]
pub enum Args {
    #[structopt(about = "Register with a Checkmk instance for monitoring")]
    Register(RegistrationArgs),

    #[structopt(about = "Surrogate registration for hosts which cannot register themselves")]
    RegisterSurrogatePull(RegistrationArgs),

    #[structopt(
        about = "Push monitoring data to all Checkmk instances where this host is registered"
    )]
    Push {},

    #[structopt(
        about = "Handle an incoming connection from a Checkmk instance for collecting monitoring data"
    )]
    Pull {},

    #[structopt(about = "Collects monitoring data and prints it to stdout")]
    Dump {},

    #[structopt(about = "Query the registration status of this host")]
    Status(StatusArgs),

    #[structopt(about = "Delete a connection to a Checkmk instance")]
    Delete(DeleteArgs),

    #[structopt(about = "Delete all connections to Checkmk instances")]
    DeleteAll {},

    #[structopt(about = "Import a pull connection, provided either via stdin or from a file")]
    Import(ImportArgs),
}
