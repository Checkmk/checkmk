// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The interface between the controller and the privileged install step.
//!
//! The controller writes an [`InstallRequest`] to the installer socket and
//! shuts down its write side; `cmk-agent-ctl install-agent`, which the socket
//! unit runs as root, reads it from its standard input. Both ends speak these
//! models, so they live with the other models of the updater.

use super::backend::UpdaterConfig;
use super::verification;
use crate::agent_receiver_api::AgentSignature;
use anyhow::{bail, Context, Result as AnyhowResult};
use serde::{Deserialize, Serialize};
use std::io::Read;
#[cfg(unix)]
use std::io::Write;
#[cfg(unix)]
use std::net::Shutdown;
#[cfg(unix)]
use std::os::unix::net::UnixStream;
use std::path::{Path, PathBuf};

/// Upper bound of one request, in bytes.
const MAX_REQUEST_BYTES: u64 = 64 * 1024;

/// Upper bound of one answer, in bytes.
#[cfg(unix)]
const MAX_REPLY_BYTES: u64 = 64 * 1024;

/// What the controller asks the installer unit to install.
///
/// Everything in it comes from the agent user and is therefore untrusted.
#[derive(Serialize, Deserialize, Debug, PartialEq, Eq)]
pub struct InstallRequest {
    /// Absolute path of the package in the controller's download directory.
    pub package: PathBuf,

    /// The signatures the site delivered with the package, which is
    /// `target_agent.signatures` of the update status it answered.
    pub signatures: Vec<AgentSignature>,
}

impl InstallRequest {
    /// Read one request from the connection of the installer socket.
    ///
    /// Reads to the end of the input, because the protocol has the controller
    /// shut down its write side once the request is out.
    ///
    /// # Arguments
    ///
    /// * `source` - the connection, which is standard input under the socket
    ///   unit
    ///
    /// # Errors
    ///
    /// If the input cannot be read, exceeds [`MAX_REQUEST_BYTES`], or is not a
    /// request.
    pub fn read(source: impl Read) -> AnyhowResult<InstallRequest> {
        let mut raw = Vec::new();
        // One byte over the bound, so that a request of exactly the bound is
        // still told apart from a stream that does not stop.
        source
            .take(MAX_REQUEST_BYTES + 1)
            .read_to_end(&mut raw)
            .context("Failed to read the install request")?;
        if raw.len() as u64 > MAX_REQUEST_BYTES {
            bail!("The install request exceeds {MAX_REQUEST_BYTES} bytes");
        }
        serde_json::from_slice(&raw).context("Failed to parse the install request")
    }
}

/// Hand `request` to the privileged install step and wait for it to finish.
///
/// The protocol of the installer socket: one request as one line of JSON, then
/// the write side is shut down, because the unit reads its input to the end.
/// The connection lives as long as the unit instance, so a return here means
/// the install step is over, whatever it made of the package.
///
/// What is installed is decided on the other side: the unit verifies the
/// package again against its own root-owned trust anchors. This end only names
/// the file and the signatures the site delivered with it.
///
/// # Arguments
///
/// * `socket` - the installer socket, `installer_socket` of the updater
///   configuration
/// * `request` - the spooled package and the signatures of the status that
///   named it
///
/// # Errors
///
/// If the socket cannot be reached, the request cannot be written, or the unit
/// answers more than [`MAX_REPLY_BYTES`].
#[cfg(unix)]
pub fn hand_over(socket: &Path, request: &InstallRequest) -> AnyhowResult<()> {
    let mut stream = UnixStream::connect(socket)
        .with_context(|| format!("Cannot reach the installer socket {socket:?}"))?;
    let mut line = serde_json::to_vec(request).context("Cannot serialize the install request")?;
    line.push(b'\n');
    stream
        .write_all(&line)
        .with_context(|| format!("Cannot write the install request to {socket:?}"))?;
    // Signal: writing is done.
    stream
        .shutdown(Shutdown::Write)
        .with_context(|| format!("Cannot finish the install request to {socket:?}"))?;

    let mut reply = Vec::new();
    // One byte over the bound, as in `InstallRequest::read`.
    (&stream)
        .take(MAX_REPLY_BYTES + 1)
        .read_to_end(&mut reply)
        .with_context(|| format!("Cannot read what the installer at {socket:?} answered"))?;
    if reply.len() as u64 > MAX_REPLY_BYTES {
        bail!("The installer at {socket:?} answered more than {MAX_REPLY_BYTES} bytes");
    }
    if !reply.is_empty() {
        log::info!(
            "The installer answered: {}",
            String::from_utf8_lossy(&reply).trim_end()
        );
    }
    Ok(())
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

    /// Check `package` against the signatures the site delivered with it.
    ///
    /// # Arguments
    ///
    /// * `package` - the bytes that are about to be installed, not the file
    ///   they were read from
    /// * `signatures` - `signatures` of the [`InstallRequest`]
    ///
    /// # Errors
    ///
    /// If none of `signatures` is a valid signature of `package` under one of
    /// the anchors.
    pub fn verify(&self, package: &[u8], signatures: &[AgentSignature]) -> AnyhowResult<()> {
        verification::verify(
            package,
            signatures,
            &verification::certificates(&self.blocks),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const PACKAGE: &str = "/opt/checkmk/agent/runtime/controller/update/0123456789abcdef.deb";

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
    fn config_with(keys: &[String], dir: &tempfile::TempDir) -> PathBuf {
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

        assert!(anchors.verify(b"an agent package", &[]).is_err());
    }

    fn request(body: &str) -> AnyhowResult<InstallRequest> {
        InstallRequest::read(body.as_bytes())
    }

    #[test]
    fn test_read_a_request() {
        assert_eq!(
            request(&format!(
                r#"{{"package": "{PACKAGE}", "signatures": [{{"certificate": "cert", "signature": "sig"}}]}}"#
            ))
            .unwrap(),
            InstallRequest {
                package: PathBuf::from(PACKAGE),
                signatures: vec![AgentSignature {
                    certificate: String::from("cert"),
                    signature: String::from("sig"),
                }],
            }
        );
    }

    #[test]
    fn test_read_something_that_is_not_a_request() {
        assert!(request("/tmp/0123456789abcdef.deb\n").is_err());
    }

    /// The sender is the agent user, so the reader stops instead of growing
    /// with whatever arrives.
    #[test]
    fn test_read_refuses_an_oversized_request() {
        let padding = "x".repeat(MAX_REQUEST_BYTES as usize);
        assert!(request(&format!(
            r#"{{"package": "{PACKAGE}{padding}", "signatures": []}}"#
        ))
        .is_err());
    }

    /// A socket in `dir` that takes one request, answers `reply` and hands the
    /// request it read back through its handle: the installer unit as far as
    /// [`hand_over`] can tell.
    #[cfg(unix)]
    fn installer_listening(
        dir: &tempfile::TempDir,
        reply: &'static [u8],
    ) -> (PathBuf, std::thread::JoinHandle<Vec<u8>>) {
        let path = dir.path().join("cmk-agent-installer.sock");
        let listener = std::os::unix::net::UnixListener::bind(&path).unwrap();
        let handle = std::thread::spawn(move || {
            let (mut connection, _) = listener.accept().unwrap();
            let mut raw = Vec::new();
            connection.read_to_end(&mut raw).unwrap();
            connection.write_all(reply).unwrap();
            raw
        });
        (path, handle)
    }

    #[cfg(unix)]
    fn an_install_request() -> InstallRequest {
        InstallRequest {
            package: PathBuf::from(PACKAGE),
            signatures: vec![AgentSignature {
                certificate: String::from("cert"),
                signature: String::from("sig"),
            }],
        }
    }

    #[cfg(unix)]
    #[test]
    fn test_hand_over_delivers_the_request() {
        let dir = tempfile::TempDir::new().unwrap();
        let (socket, installer) = installer_listening(&dir, b"");
        let request = an_install_request();

        hand_over(&socket, &request).unwrap();

        let delivered = installer.join().unwrap();
        assert_eq!(InstallRequest::read(&delivered[..]).unwrap(), request);
    }

    /// The unit answers nothing today, and whatever it may answer must not
    /// turn a finished install step into a failure here.
    #[cfg(unix)]
    #[test]
    fn test_hand_over_accepts_an_answer() {
        let dir = tempfile::TempDir::new().unwrap();
        let (socket, _installer) = installer_listening(&dir, b"{\"success\": true}\n");

        assert!(hand_over(&socket, &an_install_request()).is_ok());
    }

    /// A host whose installer unit is not there: the package was spooled, and
    /// nobody takes it.
    #[cfg(unix)]
    #[test]
    fn test_hand_over_without_an_installer() {
        let dir = tempfile::TempDir::new().unwrap();

        assert!(hand_over(&dir.path().join("none.sock"), &an_install_request()).is_err());
    }
}
