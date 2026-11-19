// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The interface between the controller and the privileged install step.
//!
//! One connection to the installer socket carries one package, TD 4.2:
//!
//! 1. The controller sends an [`InstallRequest`] line, followed by `size`
//!    bytes of the package.
//! 2. The unit answers with an [`InstallVerdict`] line.
//! 3. After an acceptance, the controller sends the line [`INSTALL`] and shuts
//!    down its write side.
//! 4. After the package manager has run, the unit sends the [`InstallResult`]
//!    line.
//!
//! `cmk-agent-ctl install-agent`, which the socket unit runs as root, speaks
//! the unit's side on its standard input and output. Both ends speak these
//! models, so they live with the other models of the updater.

use super::backend::UpdaterConfig;
use super::verification;
use crate::agent_receiver_api::AgentSignature;
use crate::types::AgentHash;
use anyhow::{bail, Context, Result as AnyhowResult};
use serde::de::DeserializeOwned;
use serde::{Deserialize, Serialize};
use std::io::{BufRead, Read, Write};
use std::path::Path;

#[cfg(unix)]
pub use client::{transfer, AcceptedTransfer, InstallTimeout, Verdict, INSTALL_TIMEOUT};

/// Upper bound of one line of the conversation, in bytes.
const MAX_LINE_BYTES: u64 = 64 * 1024;

/// The line with which the controller lets the unit install an accepted
/// package.
pub const INSTALL: &str = "install";

/// What the controller asks the installer unit to install.
///
/// Everything in it comes from the agent user and is therefore untrusted.
#[derive(Serialize, Deserialize, Debug, PartialEq, Eq)]
pub struct InstallRequest {
    /// `target_agent.aghash` of the status that named the package.
    pub aghash: AgentHash,

    /// `platform` of the agent info, which selects the package manager.
    pub platform: String,

    /// The number of package bytes that follow the request.
    pub size: u64,

    /// The signatures the site delivered with the package, which is
    /// `target_agent.signatures` of the update status it answered.
    pub signatures: Vec<AgentSignature>,
}

impl InstallRequest {
    /// Read the request line of a conversation. The package bytes stay in
    /// `source`.
    ///
    /// # Errors
    ///
    /// If the connection ends before the line, or if the line cannot be read,
    /// exceeds [`MAX_LINE_BYTES`] or is not a request.
    pub fn read(source: &mut impl BufRead) -> AnyhowResult<InstallRequest> {
        read_line(source, "the install request")?
            .context("The connection ended before the install request")
    }
}

/// The unit's answer to a package it has received.
#[derive(Serialize, Deserialize, Debug, PartialEq, Eq)]
pub struct InstallVerdict {
    /// Whether the package verified and the unit waits for [`INSTALL`].
    pub accepted: bool,

    /// Why the unit refused the package, absent on acceptance.
    pub error: Option<String>,
}

impl InstallVerdict {
    /// The verdict on a package whose reception ended with `outcome`.
    pub fn of<T>(outcome: &AnyhowResult<T>) -> InstallVerdict {
        InstallVerdict {
            accepted: outcome.is_ok(),
            error: outcome.as_ref().err().map(|error| format!("{error:#}")),
        }
    }
}

/// What the privileged install step made of the package it was handed.
///
/// The step sends it back and also writes it where the controller looks for
/// it, because installing an agent restarts the controller: the run that asked
/// is usually gone before the step is over, and a later one reads the file
/// instead.
#[derive(Serialize, Deserialize, Debug, PartialEq, Eq)]
pub struct InstallResult {
    /// `aghash` of the request.
    pub aghash: AgentHash,

    /// Whether the package manager succeeded.
    pub success: bool,

    /// Why it did not, absent on success.
    pub error: Option<String>,

    /// Unix time in seconds at which the step ended.
    pub finished: u64,
}

impl InstallResult {
    /// The result of an install step of `aghash` that ended with `outcome`.
    ///
    /// Pure: the clock belongs to the caller, so this says what is written and
    /// nothing else, and a test needs no clock to pin it.
    ///
    /// # Arguments
    ///
    /// * `aghash` - hash of the package the step worked on
    /// * `outcome` - what the step returned
    /// * `finished` - Unix time in seconds at which it returned
    pub fn of(aghash: AgentHash, outcome: &AnyhowResult<()>, finished: u64) -> InstallResult {
        InstallResult {
            aghash,
            success: outcome.is_ok(),
            // `{:#}` carries the context chain, which is where the reason is:
            // the error itself names the package manager, not what it said.
            error: outcome.as_ref().err().map(|error| format!("{error:#}")),
            finished,
        }
    }
}

/// Read one line of JSON, or `None` when the connection ends before it.
///
/// # Arguments
///
/// * `source` - the connection
/// * `what` - what the line is, for the errors
///
/// # Errors
///
/// If the line cannot be read, exceeds [`MAX_LINE_BYTES`] or does not parse.
pub fn read_line<T: DeserializeOwned>(
    source: &mut impl BufRead,
    what: &str,
) -> AnyhowResult<Option<T>> {
    let mut line = Vec::new();
    // One byte over the bound, so that a line of exactly the bound is still
    // told apart from a stream that does not stop.
    Read::take(&mut *source, MAX_LINE_BYTES + 1)
        .read_until(b'\n', &mut line)
        .with_context(|| format!("Failed to read {what}"))?;
    if line.is_empty() {
        return Ok(None);
    }
    if line.len() as u64 > MAX_LINE_BYTES {
        bail!("{what} exceeds {MAX_LINE_BYTES} bytes");
    }
    serde_json::from_slice(&line)
        .map(Some)
        .with_context(|| format!("Failed to parse {what}"))
}

/// Write `message` as one line of JSON, and flush it.
///
/// # Errors
///
/// If `message` cannot be serialized, or the line cannot be written.
pub fn write_line(sink: &mut impl Write, message: &impl Serialize) -> AnyhowResult<()> {
    let mut line = serde_json::to_vec(message)?;
    line.push(b'\n');
    sink.write_all(&line)?;
    sink.flush()?;
    Ok(())
}

/// Whether the controller sent [`INSTALL`] before it ended the connection.
///
/// # Errors
///
/// If the connection cannot be read.
pub fn read_install(source: &mut impl BufRead) -> AnyhowResult<bool> {
    let mut line = Vec::new();
    Read::take(&mut *source, MAX_LINE_BYTES)
        .read_until(b'\n', &mut line)
        .context("Failed to read what the controller sent after the verdict")?;
    Ok(line.strip_suffix(b"\n").unwrap_or(&line) == INSTALL.as_bytes())
}

/// A read past the timeout of a socket fails with `WouldBlock` on Unix.
#[cfg(unix)]
pub fn timed_out(error: &anyhow::Error) -> bool {
    error.downcast_ref::<std::io::Error>().is_some_and(|error| {
        matches!(
            error.kind(),
            std::io::ErrorKind::WouldBlock | std::io::ErrorKind::TimedOut
        )
    })
}

/// The controller's side of the conversation.
#[cfg(unix)]
mod client {
    use super::{
        read_line, timed_out, write_line, InstallRequest, InstallResult, InstallVerdict, INSTALL,
    };
    use anyhow::{bail, Context, Result as AnyhowResult};
    use std::io::{BufReader, ErrorKind, Read, Write};
    use std::net::Shutdown;
    use std::os::unix::net::UnixStream;
    use std::path::{Path, PathBuf};
    use std::time::Duration;

    /// How long the controller waits for each read and each write on the installer
    /// socket. Past it the step may still be running: the controller only stops
    /// waiting.
    pub const INSTALL_TIMEOUT: Duration = Duration::from_secs(300);

    /// The install step got [`INSTALL`] and sent no result in time.
    ///
    /// An error of its own, because the package manager may still be running, and
    /// a later run settles what it made of the package.
    #[derive(Debug)]
    pub struct InstallTimeout {
        pub socket: PathBuf,
        pub timeout: Duration,
    }

    impl std::fmt::Display for InstallTimeout {
        fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
            write!(
                formatter,
                "The installer at {:?} did not finish within {:?}, it may still be running",
                self.socket, self.timeout
            )
        }
    }

    impl std::error::Error for InstallTimeout {}

    /// What the install step made of a package it received.
    pub enum Verdict {
        /// The step verified the package and waits for [`INSTALL`].
        Accepted(AcceptedTransfer),

        /// The step refused the package, for this reason.
        Refused(String),
    }

    /// The connection to an install step that holds a verified package.
    ///
    /// Dropping it ends the connection, and the step installs nothing.
    pub struct AcceptedTransfer {
        reader: BufReader<UnixStream>,
        writer: UnixStream,
        socket: PathBuf,
        timeout: Duration,
    }

    impl AcceptedTransfer {
        /// Let the step install the package, and wait for its result.
        ///
        /// # Returns
        ///
        /// The result the step sent, or `None` when the connection ended without
        /// one.
        ///
        /// # Errors
        ///
        /// If [`INSTALL`] cannot be sent. The step is gone then and has installed
        /// nothing. An [`InstallTimeout`] if the result does not arrive within the
        /// timeout of [`transfer`].
        pub fn install(mut self) -> AnyhowResult<Option<InstallResult>> {
            self.writer
                .write_all(format!("{INSTALL}\n").as_bytes())
                .context("Cannot tell the installer to install the package")?;
            if let Err(error) = self.writer.shutdown(Shutdown::Write) {
                log::warn!("Could not end the request to the installer: {error}");
            }
            match read_line(&mut self.reader, "the install result") {
                Ok(result) => Ok(result),
                Err(error) if timed_out(&error) => Err(InstallTimeout {
                    socket: self.socket,
                    timeout: self.timeout,
                }
                .into()),
                Err(error) => {
                    log::warn!("The installer sent no usable result: {error:#}");
                    Ok(None)
                }
            }
        }
    }

    /// Where sending a package broke off.
    enum Broken {
        /// The download failed. The step sees a short transfer and refuses it.
        Download(anyhow::Error),

        /// The step stopped reading, usually because it refused the request.
        Socket(anyhow::Error),
    }

    /// Send a package to the privileged install step and wait for its verdict.
    ///
    /// # Arguments
    ///
    /// * `socket` - `installer_socket` of the updater configuration
    /// * `request` - the request, whose `size` is the number of bytes `package`
    ///   delivers
    /// * `package` - the download
    /// * `timeout` - how long to wait for each read and each write on the socket
    ///
    /// # Errors
    ///
    /// If the socket cannot be reached, the package cannot be read or delivered,
    /// or the step sends no verdict in time. A refusal is no error but
    /// [`Verdict::Refused`].
    pub fn transfer(
        socket: &Path,
        request: &InstallRequest,
        package: &mut impl Read,
        timeout: Duration,
    ) -> AnyhowResult<Verdict> {
        let mut writer = UnixStream::connect(socket)
            .with_context(|| format!("Cannot reach the installer socket {socket:?}"))?;
        // Socket options, so they hold for the clone that reads as well.
        writer
            .set_read_timeout(Some(timeout))
            .and_then(|()| writer.set_write_timeout(Some(timeout)))
            .with_context(|| {
                format!("Cannot set the timeout of the installer socket {socket:?}")
            })?;
        let mut reader = BufReader::new(
            writer
                .try_clone()
                .with_context(|| format!("Cannot read from the installer socket {socket:?}"))?,
        );
        write_line(&mut writer, request)
            .with_context(|| format!("Cannot write the install request to {socket:?}"))?;
        match send_package(package, request.size, &mut writer) {
            Ok(()) => {}
            Err(Broken::Download(error)) => return Err(error),
            Err(Broken::Socket(error)) => {
                return match read_line::<InstallVerdict>(&mut reader, "the install verdict") {
                    Ok(Some(verdict)) if !verdict.accepted => Ok(refusal(verdict)),
                    _ => Err(error),
                }
            }
        }
        let verdict: InstallVerdict = match read_line(&mut reader, "the install verdict") {
            Err(error) if timed_out(&error) => {
                bail!("The installer at {socket:?} sent no verdict within {timeout:?}")
            }
            read => {
                read?.with_context(|| format!("The installer at {socket:?} sent no verdict"))?
            }
        };
        if !verdict.accepted {
            return Ok(refusal(verdict));
        }
        Ok(Verdict::Accepted(AcceptedTransfer {
            reader,
            writer,
            socket: socket.to_path_buf(),
            timeout,
        }))
    }

    fn refusal(verdict: InstallVerdict) -> Verdict {
        Verdict::Refused(
            verdict
                .error
                .unwrap_or_else(|| String::from("no reason given")),
        )
    }

    /// Copy exactly `size` bytes from `package` to `socket`.
    fn send_package(
        package: &mut impl Read,
        size: u64,
        socket: &mut impl Write,
    ) -> Result<(), Broken> {
        let mut buffer = vec![0_u8; 64 * 1024];
        let mut sent: u64 = 0;
        while sent < size {
            let wanted = (size - sent).min(buffer.len() as u64) as usize;
            let read = match package.read(&mut buffer[..wanted]) {
                Ok(0) => {
                    return Err(Broken::Download(anyhow::anyhow!(
                        "The download ended after {sent} of {size} bytes"
                    )))
                }
                Ok(read) => read,
                Err(error) if error.kind() == ErrorKind::Interrupted => continue,
                Err(error) => {
                    return Err(Broken::Download(
                        anyhow::Error::new(error).context("Cannot read the download"),
                    ))
                }
            };
            socket.write_all(&buffer[..read]).map_err(|error| {
                Broken::Socket(anyhow::Error::new(error).context("Cannot send the package"))
            })?;
            sent += read as u64;
        }
        Ok(())
    }
}

/// The certificates the privileged install step accepts a package under.
///
/// Holds the PEM blocks, because a parsed certificate borrows the DER of its
/// block. The anchors decide alone: the certificates that travel in the
/// request are the site's claim and are only matched against these.
pub struct TrustAnchors {
    blocks: Vec<x509_parser::pem::Pem>,
}

impl TrustAnchors {
    /// The `signature_keys` of the update configuration at `path`.
    ///
    /// # Arguments
    ///
    /// * `path` - the configuration the installer unit names in its
    ///   `Environment=`. It must not come from the request: the agent user
    ///   writes the request, and the file named here is what decides whether
    ///   root installs a package at all.
    ///
    /// # Errors
    ///
    /// If there is no configuration at `path`, if it cannot be read, or if it
    /// carries no usable signature key. The last case is an error rather than
    /// an empty anchor set, because a step that trusts nothing must refuse
    /// everything, and refusing loudly beats installing quietly.
    pub fn load(path: &Path) -> AnyhowResult<TrustAnchors> {
        let config = UpdaterConfig::load_if_configured(path)?.with_context(|| {
            format!("No updater configuration at {path:?}, so nothing is trusted here")
        })?;
        let blocks = verification::pem_blocks(&config.signature_keys);
        if blocks.is_empty() {
            bail!("The updater configuration {path:?} carries no usable signature key");
        }
        Ok(TrustAnchors { blocks })
    }

    /// Check a package against the signatures the site delivered with it.
    ///
    /// # Arguments
    ///
    /// * `digest` - SHA-256 of the bytes that are about to be installed
    /// * `signatures` - `signatures` of the [`InstallRequest`]
    ///
    /// # Errors
    ///
    /// If none of `signatures` is a valid signature of `digest` under one of
    /// the anchors.
    pub fn verify(
        &self,
        digest: &verification::Sha256Digest,
        signatures: &[AgentSignature],
    ) -> AnyhowResult<()> {
        verification::verify_digest(
            digest,
            signatures,
            &verification::certificates(&self.blocks),
        )
    }
}

/// An install step for the tests of the controller's side: it takes one
/// package and answers as told.
#[cfg(all(test, unix))]
pub mod fake {
    use super::*;
    use std::io::BufReader;
    use std::path::PathBuf;

    /// What the fake step saw of one conversation.
    pub struct Conversation {
        pub request: InstallRequest,
        pub package: Vec<u8>,
        pub install: bool,
    }

    /// A step listening in `dir` that answers `verdict` and, after
    /// [`INSTALL`], calls `at_install` and sends `result`.
    pub fn installer(
        dir: &Path,
        verdict: InstallVerdict,
        result: Option<InstallResult>,
        at_install: impl FnOnce() + Send + 'static,
    ) -> (PathBuf, std::thread::JoinHandle<Conversation>) {
        let path = dir.join("cmk-agent-installer.sock");
        let listener = std::os::unix::net::UnixListener::bind(&path).unwrap();
        let handle = std::thread::spawn(move || {
            let (mut connection, _) = listener.accept().unwrap();
            let mut reader = BufReader::new(connection.try_clone().unwrap());
            let request = InstallRequest::read(&mut reader).unwrap();
            let mut package = Vec::new();
            Read::take(&mut reader, request.size)
                .read_to_end(&mut package)
                .unwrap();
            // After a short transfer the controller has gone, so nobody reads a verdict.
            let complete = package.len() as u64 == request.size;
            let accepted = complete && verdict.accepted;
            if complete {
                write_line(&mut connection, &verdict).unwrap();
            }
            let install = accepted && read_install(&mut reader).unwrap();
            if install {
                at_install();
                if let Some(result) = result {
                    write_line(&mut connection, &result).unwrap();
                }
            }
            Conversation {
                request,
                package,
                install,
            }
        });
        (path, handle)
    }

    pub fn accepted() -> InstallVerdict {
        InstallVerdict {
            accepted: true,
            error: None,
        }
    }

    pub fn refused(reason: &str) -> InstallVerdict {
        InstallVerdict {
            accepted: false,
            error: Some(String::from(reason)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sha2::Digest;

    const HASH: &str = "0123456789abcdef";

    /// Any certificate: which signature [`TrustAnchors::verify`] accepts is
    /// covered by the matrix in [`super::verification`], so these tests only
    /// need a configuration whose key parses.
    fn a_certificate() -> String {
        let key = rcgen::KeyPair::generate().unwrap();
        let der = rcgen::CertificateParams::default()
            .self_signed(&key)
            .unwrap()
            .der()
            .to_vec();
        pem_rfc7468::encode_string("CERTIFICATE", pem_rfc7468::LineEnding::LF, &der).unwrap()
    }

    /// An update configuration holding `keys`, as the bakery writes it.
    fn config_with(keys: &[String], dir: &tempfile::TempDir) -> std::path::PathBuf {
        let entries: Vec<String> = keys
            .iter()
            .map(|key| format!("\"\"\"\n{key}\"\"\""))
            .collect();
        let path = dir.path().join("cmk-agent-ctl-update.toml");
        std::fs::write(
            &path,
            format!(
                "activated = true\nsignature_keys = [{}]\n",
                entries.join(", ")
            ),
        )
        .unwrap();
        path
    }

    #[test]
    fn test_load_the_configured_anchors() {
        let dir = tempfile::TempDir::new().unwrap();
        let path = config_with(&[a_certificate()], &dir);

        assert_eq!(TrustAnchors::load(&path).unwrap().blocks.len(), 1);
    }

    /// Nothing to trust is not an empty anchor set that silently refuses every
    /// package later: it is a broken deployment, and it says so here.
    #[test]
    fn test_refuse_to_load_anchors_without_a_key() {
        let dir = tempfile::TempDir::new().unwrap();
        let path = config_with(&[], &dir);

        assert!(TrustAnchors::load(&path).is_err());
    }

    #[test]
    fn test_refuse_to_load_anchors_from_a_key_that_is_no_pem_block() {
        let dir = tempfile::TempDir::new().unwrap();
        let path = config_with(&[String::from("not a certificate\n")], &dir);

        assert!(TrustAnchors::load(&path).is_err());
    }

    /// The configuration is the unit's, and a missing one means the mode runs
    /// where no agent updates are configured.
    #[test]
    fn test_refuse_to_load_anchors_without_a_configuration() {
        let dir = tempfile::TempDir::new().unwrap();

        assert!(TrustAnchors::load(&dir.path().join("cmk-agent-ctl-update.toml")).is_err());
    }

    /// A site that signed nothing, or signed with a key this host does not
    /// carry, ends here.
    #[test]
    fn test_a_package_without_a_matching_signature_is_refused() {
        let dir = tempfile::TempDir::new().unwrap();
        let anchors = TrustAnchors::load(&config_with(&[a_certificate()], &dir)).unwrap();

        assert!(anchors
            .verify(&sha2::Sha256::digest(b"an agent package"), &[])
            .is_err());
    }

    fn a_request() -> InstallRequest {
        InstallRequest {
            aghash: HASH.parse().unwrap(),
            platform: String::from("linux_deb"),
            size: 7,
            signatures: vec![AgentSignature {
                certificate: String::from(
                    "-----BEGIN CERTIFICATE-----\nMIIB\r\nAAAA\n-----END CERTIFICATE-----\n",
                ),
                signature: String::from("sig"),
            }],
        }
    }

    #[test]
    fn test_read_a_request() {
        let mut source = &br#"{"aghash": "0123456789abcdef", "platform": "linux_deb", "size": 7, "signatures": [{"certificate": "-----BEGIN CERTIFICATE-----\nMIIB\r\nAAAA\n-----END CERTIFICATE-----\n", "signature": "sig"}]}
"#[..];

        assert_eq!(InstallRequest::read(&mut source).unwrap(), a_request());
    }

    /// The package follows the request on the same connection.
    #[test]
    fn test_reading_the_request_leaves_the_package() {
        let mut line = serde_json::to_vec(&a_request()).unwrap();
        line.extend(b"\npackage");
        let mut source = &line[..];

        InstallRequest::read(&mut source).unwrap();

        assert_eq!(source, b"package");
    }

    #[test]
    fn test_read_something_that_is_not_a_request() {
        assert!(InstallRequest::read(&mut &b"/tmp/0123456789abcdef.deb\n"[..]).is_err());
    }

    #[test]
    fn test_read_a_request_from_a_connection_that_ended() {
        assert!(InstallRequest::read(&mut &b""[..]).is_err());
    }

    /// The sender is the agent user, so the reader stops instead of growing
    /// with whatever arrives.
    #[test]
    fn test_read_refuses_an_oversized_request() {
        let padding = "x".repeat(MAX_LINE_BYTES as usize);
        let line = format!(r#"{{"aghash": "{HASH}{padding}"}}"#);

        assert!(InstallRequest::read(&mut line.as_bytes()).is_err());
    }

    #[test]
    fn test_the_install_line_asks_to_install() {
        assert!(read_install(&mut &b"install\n"[..]).unwrap());
    }

    #[test]
    fn test_a_connection_that_ended_asks_for_nothing() {
        assert!(!read_install(&mut &b""[..]).unwrap());
    }

    #[test]
    fn test_another_line_asks_for_nothing() {
        assert!(!read_install(&mut &b"installation\n"[..]).unwrap());
    }

    #[test]
    fn test_the_verdict_on_a_received_package() {
        assert_eq!(
            InstallVerdict::of(&Ok(())),
            InstallVerdict {
                accepted: true,
                error: None,
            }
        );
    }

    /// The controller records this text as the error of the update, so it
    /// carries the whole chain.
    #[test]
    fn test_the_verdict_on_a_refused_package() {
        let outcome: AnyhowResult<()> =
            Err(anyhow::anyhow!("no signature matches").context("Refusing the package"));

        assert_eq!(
            InstallVerdict::of(&outcome).error,
            Some(String::from("Refusing the package: no signature matches"))
        );
    }

    const FINISHED: u64 = 1_760_000_000;

    #[test]
    fn test_the_result_of_an_install_that_worked() {
        assert_eq!(
            InstallResult::of(HASH.parse().unwrap(), &Ok(()), FINISHED),
            InstallResult {
                aghash: HASH.parse().unwrap(),
                success: true,
                error: None,
                finished: FINISHED,
            }
        );
    }

    /// The controller shows this text to an operator, so it carries the whole
    /// chain and not only the outermost error.
    #[test]
    fn test_the_result_of_an_install_that_failed() {
        let outcome = Err(anyhow::anyhow!("exit status: 1").context("Installing failed"));

        let result = InstallResult::of(HASH.parse().unwrap(), &outcome, FINISHED);

        assert!(!result.success);
        assert_eq!(
            result.error,
            Some(String::from("Installing failed: exit status: 1"))
        );
    }

    #[cfg(unix)]
    mod client {
        use super::*;
        use std::io::BufReader;
        use std::time::Duration;

        fn a_result() -> InstallResult {
            InstallResult {
                aghash: HASH.parse().unwrap(),
                success: false,
                error: Some(String::from(
                    "dpkg: error processing archive /proc/1/fd/3\r\nErrors were encountered while processing:\n /proc/1/fd/3",
                )),
                finished: FINISHED,
            }
        }

        #[test]
        fn test_transfer_delivers_the_request_and_the_package() {
            let dir = tempfile::TempDir::new().unwrap();
            let (socket, installer) = fake::installer(dir.path(), fake::accepted(), None, || {});

            let Verdict::Accepted(_) =
                transfer(&socket, &a_request(), &mut &b"package"[..], INSTALL_TIMEOUT).unwrap()
            else {
                panic!("the installer accepted the package");
            };

            let conversation = installer.join().unwrap();
            assert_eq!(conversation.request, a_request());
            assert_eq!(conversation.package, b"package");
        }

        #[test]
        fn test_transfer_reports_a_refusal() {
            let dir = tempfile::TempDir::new().unwrap();
            let (socket, _installer) = fake::installer(
                dir.path(),
                fake::refused("no signature matches"),
                None,
                || {},
            );

            let Verdict::Refused(reason) =
                transfer(&socket, &a_request(), &mut &b"package"[..], INSTALL_TIMEOUT).unwrap()
            else {
                panic!("the installer refused the package");
            };

            assert_eq!(reason, "no signature matches");
        }

        /// A step that refuses the request reads no package, and the rest of the
        /// package does not fit into the socket buffer.
        #[test]
        fn test_transfer_reports_a_refusal_before_the_package() {
            let dir = tempfile::TempDir::new().unwrap();
            let socket = dir.path().join("cmk-agent-installer.sock");
            let listener = std::os::unix::net::UnixListener::bind(&socket).unwrap();
            let installer = std::thread::spawn(move || {
                let (mut connection, _) = listener.accept().unwrap();
                InstallRequest::read(&mut BufReader::new(connection.try_clone().unwrap())).unwrap();
                write_line(&mut connection, &fake::refused("bad request")).unwrap();
            });
            let package = vec![0_u8; 16 * 1024 * 1024];
            let request = InstallRequest {
                size: package.len() as u64,
                ..a_request()
            };

            let outcome = transfer(&socket, &request, &mut &package[..], INSTALL_TIMEOUT).unwrap();

            installer.join().unwrap();
            assert!(matches!(outcome, Verdict::Refused(reason) if reason == "bad request"));
        }

        #[test]
        fn test_transfer_of_a_short_download() {
            let dir = tempfile::TempDir::new().unwrap();
            let (socket, installer) = fake::installer(dir.path(), fake::accepted(), None, || {});

            let error = transfer(&socket, &a_request(), &mut &b"pack"[..], INSTALL_TIMEOUT)
                .err()
                .unwrap();

            assert_eq!(error.to_string(), "The download ended after 4 of 7 bytes");
            assert_eq!(installer.join().unwrap().package, b"pack");
        }

        #[test]
        fn test_transfer_without_an_installer() {
            let dir = tempfile::TempDir::new().unwrap();

            assert!(transfer(
                &dir.path().join("none.sock"),
                &a_request(),
                &mut &b"package"[..],
                INSTALL_TIMEOUT
            )
            .is_err());
        }

        #[test]
        fn test_install_returns_the_result() {
            let dir = tempfile::TempDir::new().unwrap();
            let (socket, installer) =
                fake::installer(dir.path(), fake::accepted(), Some(a_result()), || {});
            let Verdict::Accepted(accepted) =
                transfer(&socket, &a_request(), &mut &b"package"[..], INSTALL_TIMEOUT).unwrap()
            else {
                panic!("the installer accepted the package");
            };

            assert_eq!(accepted.install().unwrap(), Some(a_result()));
            assert!(installer.join().unwrap().install);
        }

        /// The installation restarts the controller, and with it often the
        /// installer's connection.
        #[test]
        fn test_install_without_a_result() {
            let dir = tempfile::TempDir::new().unwrap();
            let (socket, _installer) = fake::installer(dir.path(), fake::accepted(), None, || {});
            let Verdict::Accepted(accepted) =
                transfer(&socket, &a_request(), &mut &b"package"[..], INSTALL_TIMEOUT).unwrap()
            else {
                panic!("the installer accepted the package");
            };

            assert_eq!(accepted.install().unwrap(), None);
        }

        /// CMK-41888: a step that takes the package and never answers does not hold
        /// the controller for good. Nothing accepts the connection here, which looks
        /// the same from this end: connected, written, and never answered.
        #[test]
        fn test_transfer_stops_waiting_for_a_verdict() {
            let dir = tempfile::TempDir::new().unwrap();
            let socket = dir.path().join("cmk-agent-installer.sock");
            let _installer = std::os::unix::net::UnixListener::bind(&socket).unwrap();

            let error = transfer(
                &socket,
                &a_request(),
                &mut &b"package"[..],
                Duration::from_millis(100),
            )
            .err()
            .unwrap();

            assert!(
                error.to_string().contains("sent no verdict within 100ms"),
                "{error:#}"
            );
        }

        /// CMK-41888: the package manager may still be running, so the timeout is
        /// an error of its own.
        #[test]
        fn test_install_stops_waiting_for_the_result() {
            let dir = tempfile::TempDir::new().unwrap();
            let (release, released) = std::sync::mpsc::channel::<()>();
            let (socket, installer) =
                fake::installer(dir.path(), fake::accepted(), None, move || {
                    let _ = released.recv();
                });
            let Verdict::Accepted(accepted) = transfer(
                &socket,
                &a_request(),
                &mut &b"package"[..],
                Duration::from_millis(100),
            )
            .unwrap() else {
                panic!("the installer accepted the package");
            };

            let error = accepted.install().unwrap_err();

            drop(release);
            assert!(installer.join().unwrap().install);
            assert!(error.is::<InstallTimeout>(), "{error:#}");
            assert!(
                error.to_string().contains("did not finish within 100ms"),
                "{error:#}"
            );
        }

        /// Without the install line the step installs nothing.
        #[test]
        fn test_dropping_an_accepted_transfer_installs_nothing() {
            let dir = tempfile::TempDir::new().unwrap();
            let (socket, installer) = fake::installer(dir.path(), fake::accepted(), None, || {});

            drop(transfer(&socket, &a_request(), &mut &b"package"[..], INSTALL_TIMEOUT).unwrap());

            assert!(!installer.join().unwrap().install);
        }
    }
}
