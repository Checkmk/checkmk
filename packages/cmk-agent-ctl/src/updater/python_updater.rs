// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The registration of the Python agent updater, which the controller runs as a
//! subprocess after its own registration (CMK-18329).

use crate::config::UpdaterRegistration;
use crate::constants::CMK_UPDATE_AGENT_CMD;
use crate::site_spec::Protocol;
use crate::types::Credentials;
use crate::{config, site_spec};
#[cfg(unix)]
use anyhow::bail;
use anyhow::{Context, Result as AnyhowResult};
#[cfg(unix)]
use log::info;
use log::warn;
#[cfg(unix)]
use std::os::unix::fs::PermissionsExt;
use std::process::Command;
#[cfg(windows)]
use winreg::enums::{HKEY_LOCAL_MACHINE, KEY_READ, KEY_WOW64_64KEY};
#[cfg(windows)]
use winreg::RegKey;

#[derive(Clone)]
pub struct UpdaterRegistrationInput {
    pub site_id: site_spec::SiteID,
    pub credentials: Credentials,
    pub protocol: Protocol,
    pub hostname: String,
}

/// Check whether the agent updater is already registered by calling
/// `cmk-update-agent show-config --json` and looking for a non-null `host_secret`
/// in the state file section of the output.
///
/// Returns `true` if the updater appears to be already registered (host_secret is present and
/// non-null), `false` if it is not yet registered (registration can proceed).
/// On any unexpected output, logs a warning and returns `true` to skip registration safely.
fn is_updater_registered(cmk_update_agent_path: &str) -> bool {
    let mut cmd = Command::new(cmk_update_agent_path);
    if cfg!(windows) {
        cmd.arg("updater");
    }
    cmd.arg("show-config")
        .arg("--json")
        .stdin(std::process::Stdio::null());

    let output = match cmd.output() {
        Ok(o) => o,
        Err(e) => {
            warn!(
                "Failed to execute '{} show-config --json': {}. Skipping updater registration.",
                CMK_UPDATE_AGENT_CMD, e
            );
            return true;
        }
    };

    let stdout = String::from_utf8_lossy(&output.stdout);

    let config: serde_json::Value = match serde_json::from_str(stdout.trim()) {
        Ok(v) => v,
        Err(e) => {
            warn!(
                "Failed to parse JSON from '{} show-config --json': {}. Skipping updater registration.",
                CMK_UPDATE_AGENT_CMD, e
            );
            return true;
        }
    };

    // host_secret absent or null in state file → not registered
    !matches!(
        config
            .get("cmk-update-agent.state")
            .and_then(|s| s.get("config"))
            .and_then(|c| c.get("host_secret")),
        None | Some(serde_json::Value::Null)
    )
}

/// Perform updater registration according to the configured `UpdaterRegistration` mode.
///
/// - `Keep`: only register if the updater is not yet registered (check status first).
/// - `Overwrite`: always register.
/// - `Manual`: do nothing.
pub(crate) fn maybe_register_updater(
    updater_registration: &UpdaterRegistration,
    credentials: &Credentials,
    connection_config: &config::RegistrationConnectionConfig,
    hostname: &str,
    registry: &mut config::Registry,
) -> AnyhowResult<()> {
    if matches!(updater_registration, UpdaterRegistration::Manual) {
        return Ok(());
    }

    let protocol =
        site_spec::discover_protocol(&connection_config.site_id, &connection_config.client_config)?;

    let updater_input = UpdaterRegistrationInput {
        site_id: connection_config.site_id.clone(),
        credentials: credentials.clone(),
        hostname: hostname.to_string(),
        protocol,
    };

    if matches!(updater_registration, UpdaterRegistration::Keep) {
        let agent_updater_executable = match get_agent_updater_executable() {
            Ok(path) => path,
            Err(e) => {
                warn!(
                    "You requested to register for automatic updates, \
                    but the agent updater is not found. \
                    Skipping agent updater registration. ({})",
                    e
                );
                return Ok(());
            }
        };

        if is_updater_registered(&agent_updater_executable) {
            println!(
                "Agent updater already registered for site {}. Skipping re-registration.",
                connection_config.site_id
            );
            return Ok(());
        }
    }

    register_updater_subprocess(&updater_input, registry)
}

fn _prepare_register_updater_cmd(
    updater_registration_config: &UpdaterRegistrationInput,
    cmk_update_agent_path: &str,
    password_file_path: &std::path::Path,
) -> AnyhowResult<Command> {
    let mut cmd = Command::new(cmk_update_agent_path);
    #[cfg(windows)]
    {
        cmd.arg("updater");
    }
    cmd.arg("register")
        .arg("-s")
        .arg(&updater_registration_config.site_id.server)
        .arg("-i")
        .arg(&updater_registration_config.site_id.site)
        .arg("-H")
        .arg(&updater_registration_config.hostname);
    match &updater_registration_config.credentials {
        Credentials::UsernamePassword { username, .. } => {
            cmd.arg("-U")
                .arg(username)
                .arg("-p")
                .arg(updater_registration_config.protocol.as_str())
                // this is a temporary solution, will be replaced with a more secure one in the future
                .arg("--password-file")
                .arg(password_file_path);
        }
        Credentials::OneTimeToken { ott } => {
            cmd.arg("-p")
                .arg(updater_registration_config.protocol.as_str())
                .arg("--ott")
                .arg(ott);
        }
    }
    cmd.arg("--non-interactive");
    cmd.stdin(std::process::Stdio::null());
    Ok(cmd)
}

#[cfg(unix)]
fn find_file_relatively(cmk_update_agent_cmd: &str) -> AnyhowResult<String> {
    let current_exe = std::env::current_exe().context("Failed to get current executable path")?;

    let agent_bin_dir = current_exe
        .parent()
        .context("Failed to get parent directory of current executable")?;

    let local_path = agent_bin_dir.join(cmk_update_agent_cmd);
    if local_path.exists() {
        info!(
            "Found {} in same directory as cmk-agent-ctl",
            cmk_update_agent_cmd
        );
        return Ok(local_path.to_string_lossy().to_string());
    }

    // Fallback
    info!("Checking PATH for {}", cmk_update_agent_cmd);
    if !Command::new("which")
        .arg(cmk_update_agent_cmd)
        .output()
        .context("Failed to execute 'which' command")?
        .status
        .success()
    {
        bail!(
            "{} not found in same directory or PATH",
            cmk_update_agent_cmd
        );
    }

    info!("Found {} in PATH", cmk_update_agent_cmd);
    Ok(cmk_update_agent_cmd.to_string())
}

/// Locate the Python agent updater executable, the one driven as a subprocess.
///
/// # Errors
///
/// Returns an error if the executable is not found, which also means that this host has
/// no Python agent updater at all.
pub(crate) fn get_agent_updater_executable() -> AnyhowResult<String> {
    #[cfg(unix)]
    return find_file_relatively(CMK_UPDATE_AGENT_CMD);
    #[cfg(windows)]
    // On Windows, the agent updater is invoked with `check_mk_agent.exe updater`,
    // so the executable we need is the windows agent
    return get_windows_agent_executable();
}

#[cfg(windows)]
fn get_windows_agent_executable() -> AnyhowResult<String> {
    // Windows agent controller is invoked either from install dir (manual calls),
    // or runtime dir (Windows agent subprocess),
    // so we can't retrieve the windows agent exe relatively.
    let key = RegKey::predef(HKEY_LOCAL_MACHINE).open_subkey_with_flags(
        r"SYSTEM\CurrentControlSet\Services\CheckmkService",
        KEY_READ | KEY_WOW64_64KEY,
    )?;
    let raw: String = key.get_value("ImagePath")?;
    Ok(raw.trim().trim_matches('"').to_string())
}

pub fn register_updater_subprocess(
    updater_registration_config: &UpdaterRegistrationInput,
    registry: &mut config::Registry,
) -> AnyhowResult<()> {
    let agent_updater_executable = match get_agent_updater_executable() {
        Ok(path) => path,
        Err(e) => {
            warn!(
                "You requested to register for automatic updates, \
                   but the Agent Updater is not found. \
                   Skipping Agent Updater registration. ({})",
                e
            );
            return Ok(()); // Skip updater registration gracefully
        }
    };

    let runtime_dir = registry
        .path()
        .parent()
        .expect("Failed to get runtime directory");
    let password_file_path = runtime_dir.join(".pwd");

    // A one-time token is passed on the command line instead: it is short-lived,
    // scoped to a single host and already visible in this process' command line.
    if let Credentials::UsernamePassword { password, .. } = &updater_registration_config.credentials
    {
        std::fs::write(&password_file_path, password)
            .context("Failed to write password to temporary file")?;

        #[cfg(unix)]
        std::fs::set_permissions(&password_file_path, std::fs::Permissions::from_mode(0o600))?;
    }

    let result = (|| {
        let mut cmd = match _prepare_register_updater_cmd(
            updater_registration_config,
            &agent_updater_executable,
            &password_file_path,
        ) {
            Ok(cmd) => cmd,
            Err(e) => {
                warn!(
                    "Warning: can't build {} command, error: {}",
                    CMK_UPDATE_AGENT_CMD, e
                );
                return Ok(()); // Skip updater registration gracefully
            }
        };

        println!("Attempting to register Agent Updater...",);
        let output = cmd.output().context(format!(
            "Failed to execute {CMK_UPDATE_AGENT_CMD} register command"
        ))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            if stderr.contains("unrecognized arguments: --ott") {
                warn!(
                    "Agent Updater registration failed: The installed agent updater does not \
                    support registration with a one-time token yet. Please update the agent \
                    or register the agent updater manually with user credentials. ({})",
                    stderr
                );
            } else {
                warn!("Agent Updater registration failed: {}", stderr);
            }
            return Ok(());
        }

        println!("Agent Updater registration complete.",);
        Ok(())
    })();

    let _ = std::fs::remove_file(&password_file_path);

    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types;
    use std::ffi::OsStr;

    #[test]
    fn test_prepare_register_updater_cmd() {
        let site_id = site_spec::SiteID {
            server: "test-server".to_string(),
            site: "test-site".to_string(),
        };
        let protocol = site_spec::Protocol::Http;
        let test_password_file = std::path::Path::new("/tmp/test-password-file");

        let cmd = _prepare_register_updater_cmd(
            &UpdaterRegistrationInput {
                site_id: site_id.clone(),
                credentials: types::Credentials::username_password(
                    "test-user".to_string(),
                    "test-password".to_string(),
                ),
                hostname: "test-host".to_string(),
                protocol,
            },
            CMK_UPDATE_AGENT_CMD,
            test_password_file,
        )
        .unwrap();

        let args: Vec<&OsStr> = cmd.get_args().collect();

        #[cfg(windows)]
        let expected_args = [
            "updater",
            "register",
            "-s",
            "test-server",
            "-i",
            "test-site",
            "-H",
            "test-host",
            "-U",
            "test-user",
            "-p",
            "http",
            "--password-file",
            test_password_file.to_str().unwrap(),
            "--non-interactive",
        ];
        #[cfg(unix)]
        let expected_args = [
            "register",
            "-s",
            "test-server",
            "-i",
            "test-site",
            "-H",
            "test-host",
            "-U",
            "test-user",
            "-p",
            "http",
            "--password-file",
            test_password_file.to_str().unwrap(),
            "--non-interactive",
        ];

        assert_eq!(cmd.get_program(), CMK_UPDATE_AGENT_CMD);
        assert_eq!(args.len(), expected_args.len());

        for (actual, expected) in args.iter().zip(expected_args.iter()) {
            assert_eq!(actual, expected);
        }
    }

    #[test]
    fn test_prepare_register_updater_cmd_with_ott() {
        let site_id = site_spec::SiteID {
            server: "test-server".to_string(),
            site: "test-site".to_string(),
        };
        let protocol = site_spec::Protocol::Http;
        let test_password_file = std::path::Path::new("/tmp/test-password-file");

        let cmd = _prepare_register_updater_cmd(
            &UpdaterRegistrationInput {
                site_id: site_id.clone(),
                credentials: types::Credentials::one_time_token("0:test-token".to_string()),
                hostname: "test-host".to_string(),
                protocol,
            },
            CMK_UPDATE_AGENT_CMD,
            test_password_file,
        )
        .unwrap();

        let args: Vec<&OsStr> = cmd.get_args().collect();

        #[cfg(windows)]
        let expected_args = [
            "updater",
            "register",
            "-s",
            "test-server",
            "-i",
            "test-site",
            "-H",
            "test-host",
            "-p",
            "http",
            "--ott",
            "0:test-token",
            "--non-interactive",
        ];
        #[cfg(unix)]
        let expected_args = [
            "register",
            "-s",
            "test-server",
            "-i",
            "test-site",
            "-H",
            "test-host",
            "-p",
            "http",
            "--ott",
            "0:test-token",
            "--non-interactive",
        ];

        assert_eq!(cmd.get_program(), CMK_UPDATE_AGENT_CMD);
        assert_eq!(args.len(), expected_args.len());

        for (actual, expected) in args.iter().zip(expected_args.iter()) {
            assert_eq!(actual, expected);
        }
    }
}
