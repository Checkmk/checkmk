// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

mod agent_receiver_api;
mod certs;
mod cli;
mod config;
mod monitoring_data;
mod registration;
mod status;
mod tls_server;
use anyhow::{Context, Result as AnyhowResult};
use config::JSONLoader;
use nix::unistd;
use std::fs;
use std::io::Result as IoResult;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use structopt::StructOpt;

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

fn push(registry: config::Registry) -> AnyhowResult<()> {
    let compressed_mon_data = monitoring_data::compress(
        &monitoring_data::collect().context("Error collecting monitoring data")?,
    )
    .context("Error compressing monitoring data")?;

    for (agent_receiver_address, server_spec) in registry.push_connections() {
        agent_receiver_api::agent_data(
            agent_receiver_address,
            &server_spec.root_cert,
            &server_spec.uuid,
            &server_spec.certificate,
            &compressed_mon_data,
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

fn pull(registry: config::Registry) -> AnyhowResult<()> {
    if is_legacy_pull(&registry) {
        return dump();
    }

    let mut stream = tls_server::IoStream::new();

    stream.write_all(TLS_ID)?;
    stream.flush()?;

    let mut tls_connection = tls_server::tls_connection(registry.pull_connections())
        .context("Could not initialize TLS.")?;
    let mut tls_stream = tls_server::tls_stream(&mut tls_connection, &mut stream);

    let mon_data = monitoring_data::collect().context("Error collecting monitoring data.")?;
    tls_stream.write_all(&mon_data)?;
    tls_stream.flush()?;

    disallow_legacy_pull().context("Just provided agent data via TLS, but legacy pull mode is still allowed, and could not delete marker")?;
    Ok(())
}

fn is_legacy_pull(registry: &config::Registry) -> bool {
    if !Path::new(HOME_DIR).join(LEGACY_PULL_FILE).exists() {
        return false;
    }
    if !registry.is_empty() {
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

fn try_sanitize_home_dir_ownership(home_dir: &Path, user: &str) {
    if let Err(error) = sanitize_home_dir_ownership(home_dir, user).context(format!(
        "Failed to recursively set ownership of {} to {}",
        home_dir.display(),
        user
    )) {
        io::stderr()
            .write_all(format!("{:?}", error).as_bytes())
            .unwrap_or(());
        info!("{:?}", error)
    };
}
fn sanitize_home_dir_ownership(home_dir: &Path, user: &str) -> AnyhowResult<()> {
    if !unistd::Uid::current().is_root() {
        return Ok(());
    }
    let cmk_agent_user =
        unistd::User::from_name(user)?.context(format!("Could not find user {}", user))?;
    let cmk_agent_group =
        unistd::Group::from_name(user)?.context(format!("Could not find group {}", user))?;
    Ok(recursive_chown(
        home_dir,
        Some(cmk_agent_user.uid),
        Some(cmk_agent_group.gid),
    )?)
}

fn recursive_chown(
    dir: &Path,
    uid: Option<unistd::Uid>,
    gid: Option<unistd::Gid>,
) -> io::Result<()> {
    unistd::chown(dir, uid, gid)?;
    for entry in fs::read_dir(dir)? {
        let path = entry?.path();
        if path.is_dir() {
            recursive_chown(&path, uid, gid)?;
        } else {
            unistd::chown(&path, uid, gid)?;
        }
    }
    Ok(())
}

fn init() -> (cli::Args, PathBuf, PathBuf) {
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

    (args, config_path, conn_path)
}

fn run_requested_mode(args: cli::Args, config_path: &Path, conn_path: &Path) -> AnyhowResult<()> {
    let stored_config = config::ConfigFromDisk::load(config_path)?;
    let registry = config::Registry::from_file(conn_path)
        .context("Error while loading registered connections.")?;
    match args {
        cli::Args::Register(reg_args) => {
            registration::register(
                config::RegistrationConfig::new(stored_config, reg_args)?,
                registry,
            )?;
            disallow_legacy_pull().context(
                "Registration successful, but could not delete marker for legacy pull mode",
            )
        }
        cli::Args::Push { .. } => push(registry),
        cli::Args::Pull { .. } => pull(registry),
        cli::Args::Dump { .. } => dump(),
        cli::Args::Status(status_args) => status::status(registry, status_args.json),
    }
}

fn main() -> AnyhowResult<()> {
    let (args, config_path, conn_path) = init();

    let result = run_requested_mode(args, &config_path, &conn_path);

    if let Err(error) = &result {
        info!("{:?}", error)
    }

    try_sanitize_home_dir_ownership(Path::new(HOME_DIR), CMK_AGENT_USER);

    result
}
