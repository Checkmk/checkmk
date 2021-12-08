// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

mod agent_receiver_api;
mod certs;
mod cli;
mod config;
mod monitoring_data;
mod tls_server;
use anyhow::{anyhow, Context, Result as AnyhowResult};
use config::JSONLoader;
use nix::unistd;
use std::fs;
use std::io::Result as IoResult;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use structopt::StructOpt;
use uuid::Uuid;

use log::{info, LevelFilter};
use log4rs::append::file::FileAppender;
use log4rs::config::{Appender, Config, Root};
use log4rs::encode::pattern::PatternEncoder;

const CMK_AGENT_USER: &str = "cmk-agent";
const HOME_DIR: &str = "/var/lib/cmk-agent";
// Normally, the config would be expected at /etc/check_mk/, but we
// need to read it as cmk-agent user, so we use its home directory.
const CONFIG_FILE: &str = "cmk-agent-ctl-config.json";

const CONN_FILE: &str = "registered_connections.json";
const LOG_FILE: &str = "cmk-agent-ctl.log";
const LEGACY_PULL_FILE: &str = "allow-legacy-pull";
const TLS_ID: &[u8] = b"16";

fn register(
    config: config::RegistrationConfig,
    mut reg_conns: config::RegisteredConnections,
    path_state_out: &Path,
) -> AnyhowResult<()> {
    // TODO: what if registration_state.contains_key(agent_receiver_address) (already registered)?
    let uuid = Uuid::new_v4().to_string();
    let server_cert = match &config.root_certificate {
        Some(cert) => Some(cert.clone()),
        None => {
            let fetched_server_cert = certs::fetch_server_cert(&config.agent_receiver_address)
                .context("Error establishing trust with agent_receiver.")?;
            println!("Trusting \n\n{}\nfor pairing", &fetched_server_cert);
            None
        }
    };

    let (csr, private_key) = certs::make_csr(&uuid).context("Error creating CSR.")?;
    let pairing_response = agent_receiver_api::pairing(
        &config.agent_receiver_address,
        server_cert,
        csr,
        &config.credentials,
    )
    .context(format!(
        "Error pairing with {}",
        &config.agent_receiver_address
    ))?;

    match config.host_reg_data {
        config::HostRegistrationData::Name(hn) => {
            agent_receiver_api::register_with_hostname(
                &config.agent_receiver_address,
                &pairing_response.root_cert,
                &config.credentials,
                &uuid,
                &hn,
            )
            .context(format!(
                "Error registering with hostname at {}",
                &config.agent_receiver_address
            ))?;
        }
        config::HostRegistrationData::Labels(al) => {
            agent_receiver_api::register_with_agent_labels(
                &config.agent_receiver_address,
                &pairing_response.root_cert,
                &config.credentials,
                &uuid,
                &al,
            )
            .context(format!(
                "Error registering with agent labels at {}",
                &config.agent_receiver_address
            ))?;
        }
    }

    // TODO: obtain actual connection mode from status endpoint
    let connection_type = "pull";

    (match connection_type {
        "push" => &mut reg_conns.push,
        _ => &mut reg_conns.pull,
    })
    .insert(
        config.agent_receiver_address,
        config::RegisteredConnection {
            uuid,
            private_key,
            certificate: pairing_response.client_cert,
            root_cert: pairing_response.root_cert,
        },
    );

    reg_conns.to_file(path_state_out)?;

    disallow_legacy_pull()
        .context("Registration successful, but could not delete marker for legacy pull mode")?;
    Ok(())
}

fn push(reg_conns: config::RegisteredConnections) -> AnyhowResult<()> {
    let mon_data = monitoring_data::collect().context("Error collecting monitoring data")?;

    for (agent_receiver_address, server_spec) in reg_conns.push.iter() {
        agent_receiver_api::agent_data(
            agent_receiver_address,
            &server_spec.root_cert,
            &server_spec.uuid,
            &server_spec.certificate,
            &mon_data,
        )
        .context(format!(
            "Error pushing monitoring data to {}.",
            agent_receiver_address
        ))?
    }

    Ok(())
}

fn dump() -> AnyhowResult<()> {
    let mon_data = monitoring_data::collect().context("Error collecting monitoring data.")?;
    io::stdout()
        .write_all(&mon_data)
        .context("Error writing monitoring data to stdout.")?;

    Ok(())
}

fn status(_reg_conns: config::RegisteredConnections) -> AnyhowResult<()> {
    Err(anyhow!("Status mode not yet implemented"))
}

fn pull(mut reg_conns: config::RegisteredConnections) -> AnyhowResult<()> {
    if is_legacy_pull(&reg_conns) {
        return dump();
    }

    let mut stream = tls_server::IoStream::new();

    stream.write_all(TLS_ID)?;
    stream.flush()?;

    let mut pull_conns: Vec<config::RegisteredConnection> = reg_conns.pull.into_values().collect();
    pull_conns.append(&mut reg_conns.pull_imported);
    let mut tls_connection =
        tls_server::tls_connection(pull_conns).context("Could not initialize TLS.")?;
    let mut tls_stream = tls_server::tls_stream(&mut tls_connection, &mut stream);

    let mon_data = monitoring_data::collect().context("Error collecting monitoring data.")?;
    tls_stream.write_all(&mon_data)?;
    tls_stream.flush()?;

    disallow_legacy_pull().context("Just provided agent data via TLS, but legacy pull mode is still allowed, and could not delete marker")?;
    Ok(())
}

fn is_legacy_pull(reg_conns: &config::RegisteredConnections) -> bool {
    if !Path::new(HOME_DIR).join(LEGACY_PULL_FILE).exists() {
        return false;
    }
    if !reg_conns.is_empty() {
        return false;
    }
    true
}

fn disallow_legacy_pull() -> IoResult<()> {
    let legacy_pull_marker = Path::new(HOME_DIR).join(LEGACY_PULL_FILE);
    if !legacy_pull_marker.exists() {
        return Ok(());
    }

    fs::remove_file(legacy_pull_marker)
}

fn init_logging(path: &Path) -> AnyhowResult<()> {
    let logfile = FileAppender::builder()
        .encoder(Box::new(PatternEncoder::new("{l} - {m}\n")))
        .build(path)?;

    let config = Config::builder()
        .appender(Appender::builder().build("logfile", Box::new(logfile)))
        .build(Root::builder().appender("logfile").build(LevelFilter::Info))?;

    log4rs::init_config(config)?;

    Ok(())
}

fn ensure_home_directory(path: &Path) -> io::Result<()> {
    if !path.exists() {
        fs::create_dir_all(path)?;
    }
    Ok(())
}

fn try_sanitize_home_dir_ownership(home_dir: &Path, paths: [&Path; 3], user: &str) {
    if let Err(error) = sanitize_home_dir_ownership([home_dir, paths[0], paths[1], paths[2]], user)
        .context(format!(
            "Failed to set ownership of {} to {}",
            home_dir.display(),
            user
        ))
    {
        io::stderr()
            .write_all(format!("{:?}", error).as_bytes())
            .unwrap_or(());
        info!("{:?}", error)
    };
}

fn sanitize_home_dir_ownership(paths: [&Path; 4], user: &str) -> AnyhowResult<()> {
    if !unistd::Uid::current().is_root() {
        return Ok(());
    }

    let cmk_agent_user =
        unistd::User::from_name(user)?.context(format!("Could not find user {}", user))?;
    let cmk_agent_group =
        unistd::Group::from_name(user)?.context(format!("Could not find group {}", user))?;

    for path in paths {
        if path.exists() {
            unistd::chown(path, Some(cmk_agent_user.uid), Some(cmk_agent_group.gid))?;
        }
    }

    Ok(())
}

fn init() -> (cli::Args, PathBuf, PathBuf, PathBuf) {
    let conn_path = Path::new(HOME_DIR).join(CONN_FILE);
    let config_path = Path::new(HOME_DIR).join(CONFIG_FILE);
    let log_path = Path::new(HOME_DIR).join(LOG_FILE);

    // Parse args as first action to directly exit from --help or malformatted arguments
    let args = cli::Args::from_args();

    // TODO: Decide: Check if running as cmk-agent or root, and abort otherwise?
    if let Err(error) = ensure_home_directory(Path::new(HOME_DIR)) {
        panic!(
            "Cannot go on: Missing cmk-agent home directory and failed to create it: {}",
            error
        );
    }

    if let Err(error) = init_logging(&log_path) {
        io::stderr()
            .write_all(format!("Failed to initialize logging: {:?}", error).as_bytes())
            .unwrap_or(());
    }

    (args, config_path, conn_path, log_path)
}

fn run_requested_mode(args: cli::Args, config_path: &Path, conn_path: &Path) -> AnyhowResult<()> {
    let stored_config = config::ConfigFromDisk::load(config_path)?;
    let reg_conns = config::RegisteredConnections::load(conn_path)
        .context("Error while loading registered connections.")?;
    match args {
        cli::Args::Register(reg_args) => register(
            config::RegistrationConfig::new(stored_config, reg_args)?,
            reg_conns,
            conn_path,
        ),
        cli::Args::Push { .. } => push(reg_conns),
        cli::Args::Pull { .. } => pull(reg_conns),
        cli::Args::Dump { .. } => dump(),
        cli::Args::Status { .. } => status(reg_conns),
    }
}

fn main() -> AnyhowResult<()> {
    let (args, config_path, conn_path, log_path) = init();

    let result = run_requested_mode(args, &config_path, &conn_path);

    if let Err(error) = &result {
        info!("{:?}", error)
    }

    try_sanitize_home_dir_ownership(
        Path::new(HOME_DIR),
        [&conn_path, &config_path, &log_path],
        CMK_AGENT_USER,
    );

    result
}
