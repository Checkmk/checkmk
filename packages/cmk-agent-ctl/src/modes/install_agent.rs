// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The `install-agent` mode: the privileged install step of the integrated
//! agent updater, on Linux.
//!
//! A socket-activated systemd unit runs this mode as root, once per connection
//! the controller opens on the installer socket. That connection is the mode's
//! standard input and output. The mode receives one package, verifies it
//! against the trust anchors of the update configuration that
//! `CMK_AGENT_CTL_UPDATE_CONFIG` names, and answers with its verdict. Once the
//! controller has sent `install`, it hands the package to `dpkg` or `rpm`.
//!
//! What the package manager did goes back over the connection and into the
//! install result file of the controller, next to the journal of the unit
//! instance and the exit code.

use crate::constants;
use crate::types::AgentHash;
use crate::updater::install;
use crate::updater::{InstallRequest, InstallResult, InstallVerdict, TrustAnchors};
use anyhow::{bail, Context, Result as AnyhowResult};
use nix::fcntl::{fcntl, FcntlArg, SealFlag};
use nix::sys::memfd::{memfd_create, MemFdCreateFlag};
use sha2::{Digest, Sha256};
use std::fs::{File, OpenOptions};
use std::io::{BufRead, Read, Seek, Write};
use std::os::unix::fs::OpenOptionsExt;
use std::os::unix::io::AsRawFd;
use std::path::{Path, PathBuf};
use std::process::{Command, Output, Stdio};

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
    /// The manager that installs packages of `platform`, as the agent info
    /// names it.
    fn of(platform: &str) -> AnyhowResult<PackageManager> {
        match platform {
            "linux_deb" => Ok(PackageManager::Dpkg),
            "linux_rpm" => Ok(PackageManager::Rpm),
            _ => bail!("No package manager installs packages of the platform {platform:?}"),
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

/// A package root has received and verified, as a sealed copy of its bytes.
struct VerifiedPackage {
    /// The sealed copy, see [`receive_package`]. Held open until the package
    /// manager has finished, because the path handed over resolves through it.
    file: File,

    manager: PackageManager,

    /// `aghash` of the request, which the result carries back.
    hash: AgentHash,
}

impl VerifiedPackage {
    /// The path the package manager is given.
    ///
    /// The child reopens it through `/proc`, which resolves in this process's
    /// descriptor table, so the descriptor has to stay open while the manager
    /// runs.
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
/// # Arguments
///
/// * `result_path` - where the outcome is written for the controller
///
/// # Errors
///
/// If the package is refused, if the controller ends the connection before it
/// sends `install`, or if the package manager fails. The error carries what
/// the package manager said, because that is the only diagnostic an operator
/// gets. A result that cannot be written or sent is not one of them: the
/// installation has happened either way.
pub fn install_agent(result_path: &Path) -> AnyhowResult<()> {
    let config_path = std::env::var_os(constants::ENV_UPDATE_CONFIG).map(PathBuf::from);
    serve(
        &mut std::io::stdin().lock(),
        &mut std::io::stdout().lock(),
        config_path.as_deref(),
        result_path,
    )
}

/// One conversation on the installer socket, from the request to the result.
///
/// # Arguments
///
/// * `input` - what the controller sends
/// * `output` - what goes back to the controller
/// * `config_path` - the update configuration the installer unit names
/// * `result_path` - where the outcome is written for the controller
///
/// # Errors
///
/// As [`install_agent`].
fn serve(
    input: &mut impl BufRead,
    output: &mut impl Write,
    config_path: Option<&Path>,
    result_path: &Path,
) -> AnyhowResult<()> {
    let received = receive(input, config_path);
    if let Err(error) = install::write_line(output, &InstallVerdict::of(&received)) {
        log::warn!("Could not send the verdict to the controller: {error:#}");
    }
    let package = received?;
    if !install::read_install(input)? {
        bail!(
            "The controller ended the connection before it asked to install agent package {}",
            package.hash
        );
    }
    let outcome = run_package_manager(&package);
    let result = InstallResult::of(package.hash.clone(), &outcome, now());
    report_result(result_path, &result);
    if let Err(error) = install::write_line(output, &result) {
        log::info!("Could not send the install result to the controller: {error:#}");
    }
    outcome
}

/// Receive the package of a request and verify it.
///
/// Once the request has parsed, all of its package is read before anything
/// can fail, so that the controller can finish sending and read the verdict.
///
/// # Errors
///
/// If the request cannot be read, the package does not arrive completely, the
/// platform has no package manager, the update configuration cannot be found,
/// or none of the signatures verifies.
fn receive(input: &mut impl BufRead, config_path: Option<&Path>) -> AnyhowResult<VerifiedPackage> {
    let request = InstallRequest::read(input)?;
    log::info!(
        "Install request for agent package {}, {} bytes, carrying {} signature(s)",
        request.aghash,
        request.size,
        request.signatures.len()
    );
    let file = receive_package(input, request.size)?;
    let manager = PackageManager::of(&request.platform)?;
    let anchors = TrustAnchors::load(update_config_path(config_path)?)?;
    anchors
        .verify(&sha256_of(&file)?, &request.signatures)
        .context("No signature of the package matches a configured signature key")?;
    log::info!("Verified agent package {}", request.aghash);
    Ok(VerifiedPackage {
        file,
        manager,
        hash: request.aghash,
    })
}

/// The next `size` bytes of `input`, in a memory file that nothing can change
/// any more.
///
/// The seal stops every write, root's own included, so that the bytes the
/// package manager installs are the bytes that were verified.
///
/// # Errors
///
/// If fewer than `size` bytes arrive, or if the memory file cannot be created,
/// written or sealed.
fn receive_package(input: &mut impl Read, size: u64) -> AnyhowResult<File> {
    let descriptor = memfd_create(c"cmk-agent-package", MemFdCreateFlag::MFD_ALLOW_SEALING)
        .context("Cannot create the memory file of the package")?;
    let mut file = File::from(descriptor);
    let received = std::io::copy(&mut input.by_ref().take(size), &mut file)
        .context("Cannot receive the package")?;
    if received < size {
        bail!("The controller ended the transfer after {received} of {size} bytes");
    }
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

/// SHA-256 of the sealed copy, which the signatures sign.
fn sha256_of(copy: &File) -> AnyhowResult<sha2::digest::Output<Sha256>> {
    let mut reader = copy;
    reader
        .rewind()
        .context("Cannot read the package in memory")?;
    let mut hasher = Sha256::new();
    std::io::copy(&mut reader, &mut hasher).context("Cannot read the package in memory")?;
    Ok(hasher.finalize())
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
fn update_config_path(config_path: Option<&Path>) -> AnyhowResult<&Path> {
    config_path.with_context(|| {
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
        "Invoking the package manager for agent package {}: {command:?}",
        package.hash
    );
    let output = command.stdin(Stdio::null()).output().with_context(|| {
        format!(
            "Failed to run the package manager for agent package {}",
            package.hash
        )
    })?;
    let said = output_of(&output);
    if !said.is_empty() {
        log::info!("The package manager said:\n{said}");
    }
    if !output.status.success() {
        bail!(
            "Installing agent package {} failed, {}: {said}",
            package.hash,
            output.status
        );
    }
    log::info!("Installed agent package {}", package.hash);
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

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::process::ExitStatusExt;

    const HASH: &str = "0123456789abcdef";

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
            PackageManager::of("linux_deb").unwrap(),
            PackageManager::Dpkg
        );
    }

    #[test]
    fn test_package_manager_of_an_rpm() {
        assert_eq!(
            PackageManager::of("linux_rpm").unwrap(),
            PackageManager::Rpm
        );
    }

    #[test]
    fn test_no_package_manager_for_another_platform() {
        assert!(PackageManager::of("windows_msi").is_err());
    }

    /// The command lines are a parity requirement, not a preference, so they
    /// are pinned.
    #[test]
    fn test_the_deb_command_line() {
        assert_eq!(
            command_line(PackageManager::Dpkg, "/proc/1/fd/3"),
            ["dpkg", "-i", "/proc/1/fd/3"]
        );
    }

    #[test]
    fn test_the_rpm_command_line() {
        assert_eq!(
            command_line(PackageManager::Rpm, "/proc/1/fd/3"),
            [
                "rpm",
                "-vU",
                "--oldpackage",
                "--replacepkgs",
                "/proc/1/fd/3"
            ]
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
    fn test_receive_exactly_the_announced_bytes() {
        let mut input = &b"package and more"[..];

        let file = receive_package(&mut input, 7).unwrap();

        let install_path = format!("/proc/{}/fd/{}", std::process::id(), file.as_raw_fd());
        assert_eq!(std::fs::read(install_path).unwrap(), b"package");
        assert_eq!(input, b" and more");
    }

    #[test]
    fn test_a_short_transfer_is_refused() {
        let error = receive_package(&mut &b"pack"[..], 7).unwrap_err();

        assert_eq!(
            error.to_string(),
            "The controller ended the transfer after 4 of 7 bytes"
        );
    }

    /// The package manager is pointed at this process's descriptor of the
    /// sealed copy.
    #[test]
    fn test_the_install_path_is_a_descriptor_of_this_process() {
        let package = VerifiedPackage {
            file: receive_package(&mut &b"package"[..], 7).unwrap(),
            manager: PackageManager::Dpkg,
            hash: HASH.parse().unwrap(),
        };

        let install_path = package.install_path();

        assert!(install_path.starts_with(format!("/proc/{}/fd", std::process::id())));
        assert_eq!(
            std::fs::read(&install_path).unwrap(),
            b"package",
            "the descriptor has to resolve to the package"
        );
    }

    /// Nothing can write the copy once it is sealed, this process included.
    /// The seal stops the write, not the open, which is why the descriptor is
    /// reopened for writing here and the write itself has to fail.
    #[test]
    fn test_the_sealed_copy_cannot_be_written() {
        let package = receive_package(&mut &b"package"[..], 7).unwrap();
        let install_path = format!("/proc/{}/fd/{}", std::process::id(), package.as_raw_fd());

        let written = OpenOptions::new()
            .write(true)
            .open(&install_path)
            .unwrap()
            .write_all(b"rewritten");

        assert!(written.is_err());
        assert_eq!(std::fs::read(&install_path).unwrap(), b"package");
    }

    #[test]
    fn test_the_hash_is_that_of_the_sealed_copy() {
        let copy = receive_package(&mut &b"package"[..], 7).unwrap();

        assert_eq!(sha256_of(&copy).unwrap(), Sha256::digest(b"package"));
    }

    /// An update configuration that trusts a certificate nothing signed with.
    /// Which signature is accepted is covered by the updater's verification
    /// matrix; what matters here is that an unsigned package never reaches a
    /// package manager.
    fn config(dir: &tempfile::TempDir) -> PathBuf {
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
        path
    }

    /// What the controller sends: a request for `platform` and its package,
    /// then the install line.
    fn conversation(platform: &str) -> Vec<u8> {
        let mut input = serde_json::to_vec(&InstallRequest {
            aghash: HASH.parse().unwrap(),
            platform: String::from(platform),
            size: 7,
            signatures: vec![],
        })
        .unwrap();
        input.extend(b"\npackage");
        input.extend(install::INSTALL.as_bytes());
        input.push(b'\n');
        input
    }

    /// The first line the controller gets back.
    fn verdict(output: &[u8]) -> InstallVerdict {
        install::read_line(&mut &output[..], "the verdict")
            .unwrap()
            .unwrap()
    }

    /// A refusal is answered, and nothing runs: no package manager, so no
    /// result either.
    #[test]
    fn test_a_package_no_signature_matches_is_refused() {
        let dir = tempfile::TempDir::new().unwrap();
        let result_path = dir.path().join("agent-install-result.json");
        let mut output = Vec::new();

        let outcome = serve(
            &mut &conversation("linux_deb")[..],
            &mut output,
            Some(&config(&dir)),
            &result_path,
        );

        assert!(outcome.is_err());
        let verdict = verdict(&output);
        assert!(!verdict.accepted);
        assert!(verdict
            .error
            .unwrap()
            .contains("No signature of the package matches a configured signature key"));
        assert!(!result_path.exists());
    }

    #[test]
    fn test_a_platform_without_a_package_manager_is_refused() {
        let dir = tempfile::TempDir::new().unwrap();
        let mut output = Vec::new();

        serve(
            &mut &conversation("windows_msi")[..],
            &mut output,
            Some(&config(&dir)),
            &dir.path().join("agent-install-result.json"),
        )
        .unwrap_err();

        assert!(verdict(&output)
            .error
            .unwrap()
            .contains("No package manager installs packages of the platform"));
    }

    #[test]
    fn test_a_request_that_does_not_parse_is_refused() {
        let dir = tempfile::TempDir::new().unwrap();
        let mut output = Vec::new();

        serve(
            &mut &b"/tmp/0123456789abcdef.deb\n"[..],
            &mut output,
            Some(&config(&dir)),
            &dir.path().join("agent-install-result.json"),
        )
        .unwrap_err();

        assert!(!verdict(&output).accepted);
    }

    /// The real controller side against the real unit side, over a socket: the
    /// verdict arrives although the unit refuses.
    #[test]
    fn test_the_controller_learns_a_refusal_over_the_socket() {
        let dir = tempfile::TempDir::new().unwrap();
        let socket = dir.path().join("cmk-agent-installer.sock");
        let listener = std::os::unix::net::UnixListener::bind(&socket).unwrap();
        let config_path = config(&dir);
        let result_path = dir.path().join("agent-install-result.json");
        let unit = std::thread::spawn(move || {
            let (connection, _) = listener.accept().unwrap();
            let mut output = connection.try_clone().unwrap();
            let _refused = serve(
                &mut std::io::BufReader::new(connection),
                &mut output,
                Some(&config_path),
                &result_path,
            );
        });
        let request = InstallRequest {
            aghash: HASH.parse().unwrap(),
            platform: String::from("linux_deb"),
            size: 7,
            signatures: vec![],
        };

        let verdict = install::transfer(
            &socket,
            &request,
            &mut &b"package"[..],
            install::INSTALL_TIMEOUT,
        )
        .unwrap();

        unit.join().unwrap();
        let install::Verdict::Refused(reason) = verdict else {
            panic!("the unit refused the package");
        };
        assert!(reason.contains("No signature of the package matches a configured signature key"));
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
}
