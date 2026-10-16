// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The `install-agent` mode: the privileged install step of the integrated
//! agent updater, on Linux.
//!
//! A socket-activated systemd unit runs this mode as root, once per connection
//! the controller opens on the installer socket. That connection is the mode's
//! standard input and output: it reads one `InstallRequest` and hands the
//! package to `dpkg` or `rpm`.
//!
//! Still missing: the signature check against the trust anchors of
//! `CMK_AGENT_CTL_UPDATE_CONFIG`, and the `InstallResult` answer. For now the
//! outcome of a run only reaches the journal of the unit instance.

use crate::types::AgentHash;
use crate::updater::InstallRequest;
use anyhow::{bail, Context, Result as AnyhowResult};
use std::path::{Path, PathBuf};
use std::process::{Command, Output, Stdio};

/// The package managers an agent package can be installed with.
///
/// Solaris is missing on purpose: the integrated updater is baked for Linux
/// and Windows, and Windows has no install step.
#[derive(Clone, Copy, Debug, PartialEq)]
enum PackageManager {
    Dpkg,
    Rpm,
}

impl PackageManager {
    /// The manager that installs a package, by the extension of its name.
    fn of(package: &Path) -> AnyhowResult<PackageManager> {
        match package.extension().and_then(|extension| extension.to_str()) {
            Some("deb") => Ok(PackageManager::Dpkg),
            Some("rpm") => Ok(PackageManager::Rpm),
            _ => bail!("Not an agent package: {package:?} - expected a .deb or .rpm file"),
        }
    }

    /// The command that installs `package`.
    ///
    /// The arguments are the ones of the Python updater
    /// (`_install_agent_linux_deb` and `_install_agent_linux_rpm`), so that a
    /// host is installed the same way whichever updater does it: `--oldpackage`
    /// because the site may offer an older package than the installed one,
    /// `--replacepkgs` to reinstall the version that is already there.
    fn command(self, package: &Path) -> Command {
        let mut command = match self {
            PackageManager::Dpkg => {
                let mut command = Command::new("dpkg");
                command.arg("-i");
                command
            }
            PackageManager::Rpm => {
                let mut command = Command::new("rpm");
                command.args(["-vU", "--oldpackage", "--replacepkgs"]);
                command
            }
        };
        command.arg(package);
        command
    }
}

/// A package this mode is willing to hand to a package manager.
struct AcceptedPackage {
    path: PathBuf,
    manager: PackageManager,
}

impl AcceptedPackage {
    /// Take the package of a request, or say why it is refused.
    ///
    /// The path comes from the agent user, so it is a claim: it has to resolve,
    /// links included, into `package_dir`, and to be named after an agent hash.
    /// The signature is what makes the step safe; these checks only turn a
    /// wrong request into a clear error.
    fn accept(package: &Path, package_dir: &Path) -> AnyhowResult<AcceptedPackage> {
        let resolved_dir = package_dir
            .canonicalize()
            .with_context(|| format!("Cannot resolve the download directory {package_dir:?}"))?;
        let path = package
            .canonicalize()
            .with_context(|| format!("Cannot resolve the package {package:?}"))?;
        if path.parent() != Some(resolved_dir.as_path()) {
            bail!("The package {path:?} lies outside the download directory {resolved_dir:?}");
        }
        let hash = path
            .file_stem()
            .and_then(|stem| stem.to_str())
            .with_context(|| format!("The package {path:?} has no file name"))?;
        hash.parse::<AgentHash>()
            .with_context(|| format!("The package {path:?} is not named after an agent hash"))?;
        let manager = PackageManager::of(&path)?;
        Ok(AcceptedPackage { path, manager })
    }
}

/// Install one agent package on behalf of the controller.
///
/// The package is removed afterwards, installed or not: a failed package is not
/// retried from disk, the controller downloads it again in its next cycle, as
/// the Python updater does.
///
/// # Arguments
///
/// * `package_dir` - the download directory the package has to lie in
///
/// # Errors
///
/// If the request cannot be read, if the package is refused, or if the package
/// manager fails. The error carries what the package manager said, because that
/// is the only diagnostic an operator gets.
pub fn install_agent(package_dir: &Path) -> AnyhowResult<()> {
    let request = InstallRequest::read(std::io::stdin().lock())?;
    log::info!(
        "Install request for {:?}, carrying {} signature(s)",
        request.package,
        request.signatures.len()
    );
    let package = AcceptedPackage::accept(&request.package, package_dir)?;
    log::warn!(
        "Installing {:?} without verifying its signature, which is not implemented yet",
        package.path
    );
    let outcome = run_package_manager(&package);
    remove_package(&package.path);
    outcome
}

/// Run the package manager of `package` and log everything it says.
///
/// The connection of the installer socket is this process's standard input and
/// output, so the package manager gets neither: letting it inherit them would
/// have it answer the controller in place of this mode.
fn run_package_manager(package: &AcceptedPackage) -> AnyhowResult<()> {
    let mut command = package.manager.command(&package.path);
    log::info!("Invoking the package manager: {command:?}");
    let output = command
        .stdin(Stdio::null())
        .output()
        .with_context(|| format!("Failed to run the package manager for {:?}", package.path))?;
    let said = output_of(&output);
    if !said.is_empty() {
        log::info!("The package manager said:\n{said}");
    }
    if !output.status.success() {
        bail!(
            "Installing {:?} failed, {}: {said}",
            package.path,
            output.status
        );
    }
    log::info!("Installed {:?}", package.path);
    Ok(())
}

/// What the package manager wrote, both streams in one text, `stderr` first,
/// because that is where the reason of a failure is.
fn output_of(output: &Output) -> String {
    [&output.stderr, &output.stdout]
        .into_iter()
        .map(|stream| String::from_utf8_lossy(stream).trim().to_owned())
        .filter(|text| !text.is_empty())
        .collect::<Vec<String>>()
        .join("\n")
}

/// Remove the package, whatever the installation did with it.
///
/// A package that stays would be installed again by the next request that names
/// it, without anybody downloading or verifying it. Failing to remove it is not
/// worth failing the installation over.
fn remove_package(path: &Path) {
    if let Err(error) = std::fs::remove_file(path) {
        log::warn!("Could not remove the package {path:?}: {error:#}");
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::process::ExitStatusExt;

    const HASH: &str = "0123456789abcdef";

    /// A download directory holding one package file of `name`.
    fn package_dir(name: &str) -> tempfile::TempDir {
        let dir = tempfile::TempDir::new().unwrap();
        std::fs::write(dir.path().join(name), "package").unwrap();
        dir
    }

    fn command_line(manager: PackageManager, package: &str) -> Vec<String> {
        let command = manager.command(Path::new(package));
        std::iter::once(command.get_program())
            .chain(command.get_args())
            .map(|part| part.to_str().unwrap().to_owned())
            .collect()
    }

    fn output(code: i32, stdout: &str, stderr: &str) -> Output {
        Output {
            status: std::process::ExitStatus::from_raw(code << 8),
            stdout: Vec::from(stdout),
            stderr: Vec::from(stderr),
        }
    }

    #[test]
    fn test_package_manager_of_a_deb() {
        assert_eq!(
            PackageManager::of(Path::new("/update/0123456789abcdef.deb")).unwrap(),
            PackageManager::Dpkg
        );
    }

    #[test]
    fn test_package_manager_of_an_rpm() {
        assert_eq!(
            PackageManager::of(Path::new("/update/0123456789abcdef.rpm")).unwrap(),
            PackageManager::Rpm
        );
    }

    #[test]
    fn test_no_package_manager_for_another_package_type() {
        assert!(PackageManager::of(Path::new("/update/0123456789abcdef.pkg")).is_err());
        assert!(PackageManager::of(Path::new("/update/0123456789abcdef")).is_err());
    }

    /// The command lines are a parity requirement, not a preference, so they
    /// are pinned.
    #[test]
    fn test_the_deb_command_line() {
        assert_eq!(
            command_line(PackageManager::Dpkg, "/update/0123456789abcdef.deb"),
            ["dpkg", "-i", "/update/0123456789abcdef.deb"]
        );
    }

    #[test]
    fn test_the_rpm_command_line() {
        assert_eq!(
            command_line(PackageManager::Rpm, "/update/0123456789abcdef.rpm"),
            [
                "rpm",
                "-vU",
                "--oldpackage",
                "--replacepkgs",
                "/update/0123456789abcdef.rpm"
            ]
        );
    }

    #[test]
    fn test_accept_a_spooled_package() {
        let dir = package_dir(&format!("{HASH}.deb"));
        let accepted =
            AcceptedPackage::accept(&dir.path().join(format!("{HASH}.deb")), dir.path()).unwrap();
        assert_eq!(
            accepted.path,
            dir.path()
                .canonicalize()
                .unwrap()
                .join(format!("{HASH}.deb"))
        );
        assert_eq!(accepted.manager, PackageManager::Dpkg);
    }

    #[test]
    fn test_refuse_a_package_outside_the_download_directory() {
        let dir = package_dir(&format!("{HASH}.deb"));
        let elsewhere = package_dir(&format!("{HASH}.deb"));
        assert!(
            AcceptedPackage::accept(&elsewhere.path().join(format!("{HASH}.deb")), dir.path())
                .is_err()
        );
    }

    /// The agent user owns the download directory, so it can put a link there
    /// that points at a package of its own.
    #[test]
    fn test_refuse_a_link_out_of_the_download_directory() {
        let dir = package_dir("decoy.deb");
        let elsewhere = package_dir(&format!("{HASH}.deb"));
        let link = dir.path().join(format!("{HASH}.deb"));
        std::os::unix::fs::symlink(elsewhere.path().join(format!("{HASH}.deb")), &link).unwrap();
        assert!(AcceptedPackage::accept(&link, dir.path()).is_err());
    }

    #[test]
    fn test_refuse_a_package_that_is_not_named_after_a_hash() {
        let dir = package_dir("check-mk-agent.deb");
        assert!(
            AcceptedPackage::accept(&dir.path().join("check-mk-agent.deb"), dir.path()).is_err()
        );
    }

    #[test]
    fn test_output_of_both_streams() {
        assert_eq!(
            output_of(&output(
                1,
                "Unpacking check-mk-agent\n",
                "dpkg: error processing\n"
            )),
            "dpkg: error processing\nUnpacking check-mk-agent"
        );
    }

    #[test]
    fn test_output_of_one_stream_only() {
        assert_eq!(
            output_of(&output(0, "Setting up check-mk-agent\n", "")),
            "Setting up check-mk-agent"
        );
    }

    #[test]
    fn test_remove_a_package() {
        let dir = package_dir(&format!("{HASH}.deb"));
        let package = dir.path().join(format!("{HASH}.deb"));
        remove_package(&package);
        assert!(!package.exists());
    }
}
