// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

mod agent_receiver_api;
pub mod certs;
mod cli;
pub mod configuration;
mod constants;
mod environment;
#[cfg(windows)]
mod log_ext;
#[cfg(windows)]
pub mod mailslot_transport;
mod misc;
pub mod modes;
mod monitoring_data;
mod setup;
pub mod site_spec;
mod tls_server;
pub mod types;
pub mod updater;
mod version;
use anyhow::{bail, Context, Result as AnyhowResult};
use configuration::config;
use configuration::config::TOMLLoaderMissingSafe;
use modes::daemon::daemon;
use modes::delete_connection::{delete, delete_all};
use modes::dump::dump;
use modes::import_connection::import;
#[cfg(unix)]
use modes::install_agent::install_agent;
use modes::pull::fn_thread;
use modes::push::handle_push_cycle as push;
use modes::registration;
use modes::renew_certificate::renew_certificate;
use modes::status::status;
use modes::update::{check, update};
pub use setup::init;

use crate::updater::Updater;
#[cfg(windows)]
pub use misc::validate_elevation;

pub fn run_requested_mode(cli: cli::Cli, paths: environment::PathResolver) -> AnyhowResult<()> {
    // Dispatched before anything is loaded, because this mode runs as root and
    // works on the agent package alone.
    #[cfg(unix)]
    if let cli::Mode::InstallAgent = cli.mode {
        return install_agent(&paths.updater_package_dir, &paths.install_result_path);
    }

    configuration::migrate::migrate_registered_connections(&paths.registry_path)?;
    agent_socket_operational(&cli.mode)?;

    let runtime_config = config::RuntimeConfig::load_missing_safe(&paths.config_path)?;
    let mut registry = config::Registry::from_file(&paths.registry_path).with_context(|| {
        format!(
            "Error while loading registered connections from {:?}.",
            &paths.registry_path
        )
    })?;
    log::info!(
        "Loaded config from '{:?}', connection registry from '{:?}'",
        &paths.config_path,
        &paths.registry_path
    );
    // Loaded for every mode: the updater is an integral part of the controller,
    // not a subsystem the individual modes opt into. It may be adjusted later, but
    // the updater is _always_ present and its state is _always_ relevant.
    let updater = updater::Updater::new(&paths);
    // Kept at info although the default level is still warn: the default is to be
    // raised, and the summary is then wanted on every run.
    log::info!("Updater {}", updater.summary());
    match cli.mode {
        cli::Mode::Register(reg_opts) => {
            let updater_registration =
                runtime_config.updater_registration(reg_opts.automatic_updates);
            let config = config::RegisterExistingConfig::new(runtime_config, reg_opts)?;
            let connection = registration::register_existing(&config, &mut registry)?;
            updater::after_connection_changes(
                &[connection],
                &updater_registration,
                detect_agent_updater(),
                &config.connection_config.client_config,
                &registry,
            )?;
            register_update_source(
                &mut Updater::writable(&paths)?,
                &mut registry,
                &config.connection_config.site_id,
                &updater_registration,
            )
        }
        cli::Mode::RegisterNew(reg_new_opts) => {
            let updater_registration = runtime_config.configured_updater_registration();
            let config = config::RegisterNewConfig::new(
                config::RegistrationConnectionConfig::from_register_new_opts(
                    runtime_config,
                    reg_new_opts.connection_opts,
                )?,
                reg_new_opts.agent_labels_raw.into_iter().collect(),
            )?;
            let connection = registration::register_new(&config, &mut registry)?;
            updater::after_connection_changes(
                &[connection],
                &updater_registration,
                detect_agent_updater(),
                &config.connection_config.client_config,
                &registry,
            )?;
            register_update_source(
                &mut Updater::writable(&paths)?,
                &mut registry,
                &config.connection_config.site_id,
                &updater_registration,
            )
        }
        cli::Mode::ProxyRegister(reg_opts) => registration::proxy_register(
            &config::RegisterExistingConfig::new(runtime_config, reg_opts)?,
        ),
        cli::Mode::Import(import_opts) => import(&mut registry, &import_opts),
        cli::Mode::Push(client_opts) => push(
            &registry,
            &config::ClientConfig::new(runtime_config, client_opts, None),
            &setup::agent_channel(),
        ),
        cli::Mode::Pull(pull_opts) => fn_thread(config::PullConfig::new(
            runtime_config,
            pull_opts,
            registry,
        )?),
        cli::Mode::Daemon(daemon_opts) => {
            let updater_registration = runtime_config.configured_updater_registration();
            daemon(
                paths,
                registry.clone(),
                config::PullConfig::new(runtime_config.clone(), daemon_opts.pull_opts, registry)?,
                config::ClientConfig::new(
                    runtime_config,
                    daemon_opts.client_opts,
                    Some(daemon_opts.reg_client_opts),
                ),
                updater_registration,
                detect_agent_updater(),
            )
        }
        cli::Mode::Dump => dump(),
        cli::Mode::Status(status_opts) => status(
            &registry,
            &config::PullConfig::new(
                runtime_config.clone(),
                // this will vanish once the Windows agent also uses the toml config
                cli::PullOpts {
                    port: None,
                    #[cfg(windows)]
                    agent_channel: None,
                },
                registry.clone(),
            )?,
            config::ClientConfig::new(runtime_config, status_opts.client_opts, None),
            status_opts.json,
            !status_opts.no_query_remote,
        ),
        cli::Mode::Delete(delete_opts) => {
            delete(&mut registry, &delete_opts.connection)?;
            Updater::writable(&paths)?.forget_vanished_update_source(&registry)
        }
        cli::Mode::DeleteAll(delete_all_opts) => {
            delete_all(&mut registry, delete_all_opts.enable_insecure_connections)?;
            Updater::writable(&paths)?.forget_vanished_update_source(&registry)
        }
        cli::Mode::Update(update_opts) => {
            let client_config =
                config::ClientConfig::new(runtime_config, update_opts.client_opts, None);
            if update_opts.check_only {
                check(&updater, &registry, &client_config)
            } else {
                update(
                    &mut Updater::writable(&paths)?,
                    &registry,
                    &client_config,
                    if update_opts.skip_signatures {
                        updater::SignatureCheck::Skip
                    } else {
                        updater::SignatureCheck::Required
                    },
                )
            }
        }
        #[cfg(unix)]
        cli::Mode::InstallAgent => {
            unreachable!("install-agent returns before the controller's files are loaded")
        }
        cli::Mode::RenewCertificate(renew_certificate_opts) => renew_certificate(
            registry,
            &renew_certificate_opts.connection_opts.connection,
            config::ClientConfig::new(runtime_config, renew_certificate_opts.client_opts, None),
        ),
    }
}

/// Hand the connection a registration just created to the updater.
///
/// The source is the connection the registry now holds for `site_id`: the
/// registration put the UUID it generated there, and the updater talks to the
/// site over that connection's mTLS channel.
///
/// # Arguments
///
/// * `updater` - the updater of this controller run
/// * `registry` - the registry the registration just wrote
/// * `site_id` - the site the registration registered this host at
/// * `registration` - what the host is configured to do about the updater
///
/// # Errors
///
/// If the updater state cannot be written.
fn register_update_source(
    updater: &mut updater::WritableUpdater,
    registry: &mut config::Registry,
    site_id: &site_spec::SiteID,
    registration: &config::UpdaterRegistration,
) -> AnyhowResult<()> {
    let Some(connection) = registry.get_connection_as_mut(site_id) else {
        // Nothing registered means nothing to update from, so the updater keeps
        // whatever source it had.
        log::warn!("No registered connection to {site_id}, leaving the update source alone");
        return Ok(());
    };
    let source = updater::UpdateSource {
        uuid: connection.trust.uuid,
        // Only the site, by answering 501, can say that it serves no agent updates.
        available: true,
    };
    log::info!(
        "Candidate update source from this registration: connection {} to {}, available: {}",
        source.uuid,
        site_id,
        source.available
    );
    updater.register_update_source(registration, source, registry)
}

/// Which agent updater this host runs.
///
/// Temporary: it only exists to tell the two deployments apart right now, without a bakery
/// change, see [`detect_agent_updater`].
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum AgentUpdater {
    /// Integrated into the controller: there is no subprocess to drive.
    Integrated,
    /// The Python `cmk-update-agent`, driven as a subprocess.
    Python,
}

/// Tell whether the agent updates are handled by the controller itself rather than by the
/// Python agent updater running as a subprocess.
///
/// Only a missing Python updater executable means the controller is on its own. Every other
/// case counts as [`AgentUpdater::Python`], because that is the safe direction: a subprocess
/// that is not there only costs a warning, while wrongly assuming the integrated updater
/// skips the registration of an updater that nothing else registers.
///
/// Temporary: this is expected to be replaced by an explicit statement from the site, or to
/// be dropped, as soon as the integrated updater is baked for.
fn detect_agent_updater() -> AgentUpdater {
    match updater::get_agent_updater_executable() {
        Ok(path) => {
            log::info!("Found Python agent updater at '{}'", path);
            AgentUpdater::Python
        }
        Err(error) => {
            log::info!("No Python agent updater executable: {:#}", error);
            AgentUpdater::Integrated
        }
    }
}

/// This check is currently only useful on Unix. On Windows, the internal agent address can be passed
/// on the command line, so we cannot easily check this for any mode.
fn agent_socket_operational(mode: &cli::Mode) -> AnyhowResult<()> {
    match mode {
        cli::Mode::Register(_) | cli::Mode::RegisterNew(_) | cli::Mode::Import(_) => {
            let agent_channel = setup::agent_channel();
            if agent_channel.operational() {
                Ok(())
            } else {
                bail!(format!(
                    "Something seems wrong with the agent socket ({agent_channel}), aborting"
                ))
            }
        }
        _ => Ok(()),
    }
}
