// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The `install-agent` mode: the privileged install step of the integrated
//! agent updater, on Linux.
//!
//! A socket-activated systemd unit runs this mode as root, once per connection
//! the controller opens on the installer socket. That connection is the mode's
//! standard input and output: it reads one `InstallRequest`, verifies the
//! package against the trust anchors of the update configuration that
//! `CMK_AGENT_CTL_UPDATE_CONFIG` names, and hands it to `dpkg` or `rpm`.
//!
//! What a run made of the package goes into the install result file of the
//! controller, next to the journal of the unit instance and the exit code.
//! Still missing: sending the same result back over the connection. Until
//! then the controller reads the file, or settles the outcome by comparing
//! hashes on a later cycle.

use crate::constants;
use crate::types::AgentHash;
use crate::updater::{InstallRequest, InstallResult, TrustAnchors};
use anyhow::{bail, Context, Result as AnyhowResult};
use nix::fcntl::{fcntl, FcntlArg, SealFlag};
use nix::sys::memfd::{memfd_create, MemFdCreateFlag};
use std::fs::{File, OpenOptions};
use std::io::{Read, Write};
use std::os::unix::fs::OpenOptionsExt;
use std::os::unix::io::AsRawFd;
use std::path::{Path, PathBuf};
use std::process::{Command, Output, Stdio};

/// Upper bound of a package, in bytes.
///
/// An agent package is a few tens of megabytes. The bound exists because the
/// file is written by the agent user and root reads all of it into memory to
/// verify its signature.
const MAX_PACKAGE_BYTES: u64 = 128 * 1024 * 1024;

/// Permissions of the install result: root writes it, the controller reads it
/// as the agent user.
const RESULT_FILE_MODE: u32 = 0o644;

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

    /// Hash of the package, read off its file name, which the result carries
    /// back to the controller.
    hash: AgentHash,
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
        let hash = hash
            .parse::<AgentHash>()
            .with_context(|| format!("The package {path:?} is not named after an agent hash"))?;
        let manager = PackageManager::of(&path)?;
        Ok(AcceptedPackage {
            path,
            manager,
            hash,
        })
    }

    /// Read this package and check it against `anchors`.
    ///
    /// Consumes the acceptance: the result is the only handle that reaches a
    /// package manager, so an unverified package cannot be installed by
    /// mistake.
    ///
    /// # Arguments
    ///
    /// * `anchors` - the certificates of the root-owned update configuration
    /// * `signatures` - the signatures the request carried
    ///
    /// # Errors
    ///
    /// If the package cannot be read, is not a regular file, exceeds
    /// [`MAX_PACKAGE_BYTES`], or none of `signatures` is a valid signature of
    /// its bytes under one of the anchors.
    fn verify(
        self,
        anchors: &TrustAnchors,
        signatures: &[crate::agent_receiver_api::AgentSignature],
    ) -> AnyhowResult<VerifiedPackage> {
        // The agent user owns the download directory and can replace the entry
        // between `accept` and here: refuse a symlink, do not park in `open` on a
        // FIFO, and reject anything that is not a regular file.
        let file = OpenOptions::new()
            .read(true)
            .custom_flags(nix::libc::O_NOFOLLOW | nix::libc::O_NONBLOCK)
            .open(&self.path)
            .with_context(|| format!("Cannot read the package {:?}", self.path))?;
        if !file.metadata()?.is_file() {
            bail!("The package {:?} is not a regular file", self.path);
        }
        let mut bytes = Vec::new();
        // One byte over the bound tells a package of exactly the bound from one
        // that is too large to hold.
        (&file)
            .take(MAX_PACKAGE_BYTES + 1)
            .read_to_end(&mut bytes)
            .with_context(|| format!("Cannot read the package {:?}", self.path))?;
        if bytes.len() as u64 > MAX_PACKAGE_BYTES {
            bail!(
                "The package {:?} exceeds {MAX_PACKAGE_BYTES} bytes",
                self.path
            );
        }
        anchors.verify(&bytes, signatures).with_context(|| {
            format!(
                "Refusing the package {:?}: no signature of it matches a configured signature key",
                self.path
            )
        })?;
        log::info!("Verified the package {:?}", self.path);
        Ok(VerifiedPackage {
            file: sealed(&bytes)?,
            manager: self.manager,
            path: self.path,
        })
    }
}

/// An in-memory copy of `bytes` that nothing can change any more.
///
/// [`AcceptedPackage::verify`] checks bytes, not a file. The package lies in
/// the agent user's directory, so they can rewrite the same inode after the
/// signature matched and before the package manager reads it. This copy lives
/// only in memory and is sealed against every write, root's own included, so
/// what is installed is what was verified.
///
/// # Arguments
///
/// * `bytes` - the verified content
///
/// # Errors
///
/// If the memory file cannot be created, written or sealed.
fn sealed(bytes: &[u8]) -> AnyhowResult<File> {
    let descriptor = memfd_create(c"cmk-agent-package", MemFdCreateFlag::MFD_ALLOW_SEALING)
        .context("Cannot create the memory file of the package")?;
    let mut file = File::from(descriptor);
    file.write_all(bytes)
        .context("Cannot write the package into memory")?;
    fcntl(
        file.as_raw_fd(),
        FcntlArg::F_ADD_SEALS(
            SealFlag::F_SEAL_WRITE
                | SealFlag::F_SEAL_GROW
                | SealFlag::F_SEAL_SHRINK
                | SealFlag::F_SEAL_SEAL,
        ),
    )
    .context("Cannot seal the package in memory")?;
    Ok(file)
}

/// A package root has read and verified, as a sealed copy of its bytes.
///
/// The copy is what makes the verification mean anything. The download
/// directory belongs to the agent user, who may both replace the entry and
/// rewrite the bytes behind it between the check and the installation; the
/// copy cannot be changed by anybody once it is sealed.
struct VerifiedPackage {
    /// The sealed copy of the verified bytes, see [`sealed`]. Held open until
    /// the package manager has finished, because the path handed over resolves
    /// through it.
    file: File,

    /// The manager that installs it.
    manager: PackageManager,

    /// Where the package was taken from, for the log and for removing it.
    path: PathBuf,
}

impl VerifiedPackage {
    /// The path the package manager is given.
    ///
    /// This process's descriptor of the sealed copy rather than the directory
    /// entry, so that the manager installs the verified bytes whatever happens
    /// to the package on disk. The child reopens it through `/proc`, which
    /// resolves in this process's descriptor table, so the descriptor has to
    /// stay open while the manager runs.
    fn install_path(&self) -> PathBuf {
        PathBuf::from(format!(
            "/proc/{}/fd/{}",
            std::process::id(),
            self.file.as_raw_fd()
        ))
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
/// * `result_path` - where the outcome is written for the controller
///
/// # Errors
///
/// If the request cannot be read, if the update configuration cannot be found,
/// if the package is refused, or if the package manager fails. The error
/// carries what the package manager said, because that is the only diagnostic
/// an operator gets. A result that cannot be written is not one of them: the
/// installation has happened either way.
pub fn install_agent(package_dir: &Path, result_path: &Path) -> AnyhowResult<()> {
    let request = InstallRequest::read(std::io::stdin().lock())?;
    log::info!(
        "Install request for {:?}, carrying {} signature(s)",
        request.package,
        request.signatures.len()
    );
    let config_path = update_config_path()?;
    let accepted = AcceptedPackage::accept(&request.package, package_dir)?;
    install_and_report(accepted, &config_path, &request.signatures, result_path)
}

/// Install `accepted` and write what became of it to `result_path`.
///
/// Everything an [`InstallResult`] can report happens from here on: a package
/// the anchors refuse and a package manager that failed are outcomes the
/// controller has to tell apart, and both differ from a step that never ran.
/// What comes before, in [`install_agent`], stays unreported, because the
/// result is keyed by a hash that only an accepted package has.
///
/// # Arguments
///
/// * `accepted` - the package, consumed because only a verified one goes on
/// * `config_path` - the root-owned update configuration named by the unit
/// * `signatures` - the signatures the request carried
/// * `result_path` - where the outcome is written for the controller
///
/// # Errors
///
/// Whatever [`verify_and_run`] failed with, reported before it is returned.
fn install_and_report(
    accepted: AcceptedPackage,
    config_path: &Path,
    signatures: &[crate::agent_receiver_api::AgentSignature],
    result_path: &Path,
) -> AnyhowResult<()> {
    let hash = accepted.hash.clone();
    let outcome = verify_and_run(accepted, config_path, signatures);
    report_result(result_path, &InstallResult::of(hash, &outcome, now()));
    outcome
}

/// Verify `accepted` against the anchors of `config_path` and install it.
///
/// # Arguments
///
/// * `accepted` - the package, consumed because only a verified one goes on
/// * `config_path` - the root-owned update configuration named by the unit
/// * `signatures` - the signatures the request carried
///
/// # Errors
///
/// If the anchors cannot be loaded, if none of them covers the package, or if
/// the package manager fails.
fn verify_and_run(
    accepted: AcceptedPackage,
    config_path: &Path,
    signatures: &[crate::agent_receiver_api::AgentSignature],
) -> AnyhowResult<()> {
    let anchors = TrustAnchors::load(config_path)?;
    let package = accepted.verify(&anchors, signatures)?;
    let outcome = run_package_manager(&package);
    remove_package(&package.path);
    outcome
}

/// Unix time in seconds, for the timestamp of the result.
///
/// A clock that stands before the epoch counts as zero. The installation has
/// happened, and the controller compares hashes rather than timestamps.
fn now() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |since| since.as_secs())
}

/// Write `result` where the controller looks for it, and keep going when that
/// fails: the package manager has run either way, and a later cycle settles
/// the outcome by comparing hashes.
fn report_result(path: &Path, result: &InstallResult) {
    match write_result(path, result) {
        Ok(()) => log::info!("Wrote the install result to {path:?}"),
        Err(error) => log::warn!("Could not write the install result to {path:?}: {error:#}"),
    }
}

/// Write `result` to `path` through a new temporary file and a rename.
///
/// The directory belongs to the agent user, who can plant anything where root
/// is about to write. `create_new` opens no file that exists, a symlink
/// included, so the write lands in a file of this run; the random name keeps a
/// planted one from failing every later run, and the rename replaces what sits
/// at `path` instead of following it.
///
/// # Errors
///
/// If the temporary file cannot be created or written, or not be moved into
/// place. Nothing of it stays behind in that case.
fn write_result(path: &Path, result: &InstallResult) -> AnyhowResult<()> {
    let temporary = path.with_extension(format!("{:016x}.tmp", rand::random::<u64>()));
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(RESULT_FILE_MODE)
        .open(&temporary)
        .with_context(|| format!("Cannot create {temporary:?}"))?;
    file.write_all(&serde_json::to_vec_pretty(result)?)
        .and_then(|()| std::fs::rename(&temporary, path))
        .inspect_err(|_| {
            let _ = std::fs::remove_file(&temporary);
        })
        .with_context(|| format!("Cannot write the install result to {path:?}"))
}

/// The update configuration the installer unit named.
///
/// Taken from the environment and from nowhere else. A fallback to a path this
/// process could derive itself would be a second, quieter way to decide what
/// root trusts, and the unit is the one place that is out of the agent user's
/// reach.
///
/// # Errors
///
/// If the variable is not set, which means the mode was not started by the
/// unit that is supposed to start it.
fn update_config_path() -> AnyhowResult<PathBuf> {
    std::env::var(constants::ENV_UPDATE_CONFIG)
        .map(PathBuf::from)
        .with_context(|| {
            format!(
                "{} is not set: this mode is run by the installer unit, which names the \
                 update configuration there",
                constants::ENV_UPDATE_CONFIG
            )
        })
}

/// Run the package manager of `package` and log everything it says.
///
/// The connection of the installer socket is this process's standard input and
/// output, so the package manager gets neither: letting it inherit them would
/// have it answer the controller in place of this mode.
fn run_package_manager(package: &VerifiedPackage) -> AnyhowResult<()> {
    let mut command = package.manager.command(&package.install_path());
    log::info!(
        "Invoking the package manager for {:?}: {command:?}",
        package.path
    );
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

    /// Anchors over a certificate nothing signed with. Which signature is
    /// accepted is covered by the updater's verification matrix; what matters
    /// here is that an unsigned package never reaches a package manager.
    fn anchors(dir: &tempfile::TempDir) -> TrustAnchors {
        let key = rcgen::KeyPair::generate().unwrap();
        let der = rcgen::CertificateParams::default()
            .self_signed(&key)
            .unwrap()
            .der()
            .to_vec();
        let certificate =
            pem_rfc7468::encode_string("CERTIFICATE", pem_rfc7468::LineEnding::LF, &der).unwrap();
        let path = dir.path().join("cmk-agent-ctl-update.toml");
        std::fs::write(
            &path,
            format!("signature_keys = [\"\"\"\n{certificate}\"\"\"]\n"),
        )
        .unwrap();
        TrustAnchors::load(&path).unwrap()
    }

    #[test]
    fn test_refuse_a_package_no_signature_matches() {
        let dir = package_dir(&format!("{HASH}.deb"));
        let accepted =
            AcceptedPackage::accept(&dir.path().join(format!("{HASH}.deb")), dir.path()).unwrap();

        assert!(accepted.verify(&anchors(&dir), &[]).is_err());
    }

    /// The package manager is pointed at this process's descriptor, not at the
    /// directory entry the agent user can replace.
    #[test]
    fn test_the_install_path_is_a_descriptor_of_this_process() {
        let dir = package_dir(&format!("{HASH}.deb"));
        let path = dir.path().join(format!("{HASH}.deb"));
        let package = VerifiedPackage {
            file: sealed(b"package").unwrap(),
            manager: PackageManager::Dpkg,
            path,
        };

        let install_path = package.install_path();

        assert!(install_path.starts_with(format!("/proc/{}/fd", std::process::id())));
        assert_eq!(
            std::fs::read(&install_path).unwrap(),
            b"package",
            "the descriptor has to resolve to the package"
        );
    }

    /// Rewriting the package after it was verified does not change what the
    /// package manager installs.
    #[test]
    fn test_a_rewrite_of_the_package_does_not_reach_the_package_manager() {
        let dir = package_dir(&format!("{HASH}.deb"));
        let path = dir.path().join(format!("{HASH}.deb"));
        let package = VerifiedPackage {
            file: sealed(b"package").unwrap(),
            manager: PackageManager::Dpkg,
            path: path.clone(),
        };

        std::fs::write(&path, b"rewritten").unwrap();

        assert_eq!(
            std::fs::read(package.install_path()).unwrap(),
            b"package",
            "the sealed copy is what gets installed"
        );
    }

    /// A refusal is an outcome of its own: the controller has to tell it from
    /// an install step that never ran, so the result carries it.
    #[test]
    fn test_a_refused_package_is_reported() {
        let dir = package_dir(&format!("{HASH}.deb"));
        let accepted =
            AcceptedPackage::accept(&dir.path().join(format!("{HASH}.deb")), dir.path()).unwrap();
        let result_path = dir.path().join("agent-install-result.json");

        let outcome =
            install_and_report(accepted, &dir.path().join("absent.toml"), &[], &result_path);

        assert!(outcome.is_err());
        let result: InstallResult =
            serde_json::from_slice(&std::fs::read(&result_path).unwrap()).unwrap();
        assert_eq!(result.aghash, HASH.parse().unwrap());
        assert!(!result.success);
        assert!(result.error.unwrap().contains("No updater configuration"));
    }

    fn a_result() -> InstallResult {
        InstallResult {
            aghash: HASH.parse().unwrap(),
            success: true,
            error: None,
            finished: 1_760_000_000,
        }
    }

    /// What the controller finds afterwards: the result, and nothing of the
    /// temporary file the write went through.
    #[test]
    fn test_write_the_install_result() {
        let dir = tempfile::TempDir::new().unwrap();
        let path = dir.path().join("agent-install-result.json");

        write_result(&path, &a_result()).unwrap();

        assert_eq!(
            serde_json::from_slice::<InstallResult>(&std::fs::read(&path).unwrap()).unwrap(),
            a_result()
        );
        assert_eq!(std::fs::read_dir(dir.path()).unwrap().count(), 1);
    }

    /// The directory belongs to the agent user, who can point the result at a
    /// file root would then overwrite. The link is replaced, not followed.
    #[test]
    fn test_a_link_at_the_install_result_is_replaced() {
        let dir = tempfile::TempDir::new().unwrap();
        let elsewhere = dir.path().join("elsewhere");
        std::fs::write(&elsewhere, b"untouched").unwrap();
        let path = dir.path().join("agent-install-result.json");
        std::os::unix::fs::symlink(&elsewhere, &path).unwrap();

        write_result(&path, &a_result()).unwrap();

        assert_eq!(std::fs::read(&elsewhere).unwrap(), b"untouched");
        assert!(!std::fs::symlink_metadata(&path)
            .unwrap()
            .file_type()
            .is_symlink());
    }

    /// One file, holding the last run's outcome.
    #[test]
    fn test_the_install_result_replaces_the_one_before() {
        let dir = tempfile::TempDir::new().unwrap();
        let path = dir.path().join("agent-install-result.json");
        write_result(&path, &a_result()).unwrap();
        let failed = InstallResult {
            success: false,
            error: Some(String::from("Installing failed: exit status: 1")),
            ..a_result()
        };

        write_result(&path, &failed).unwrap();

        assert_eq!(
            serde_json::from_slice::<InstallResult>(&std::fs::read(&path).unwrap()).unwrap(),
            failed
        );
    }

    /// Nothing can write the copy once it is sealed, this process included.
    /// The seal stops the write, not the open, which is why the descriptor is
    /// reopened for writing here and the write itself has to fail.
    #[test]
    fn test_the_sealed_copy_cannot_be_written() {
        let package = sealed(b"package").unwrap();
        let install_path = format!("/proc/{}/fd/{}", std::process::id(), package.as_raw_fd());

        let written = OpenOptions::new()
            .write(true)
            .open(&install_path)
            .unwrap()
            .write_all(b"rewritten");

        assert!(written.is_err());
        assert_eq!(std::fs::read(&install_path).unwrap(), b"package");
    }
}
